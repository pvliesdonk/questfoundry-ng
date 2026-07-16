"""POLISH — compile the frozen beat DAG to passages (design doc 02).

Four passes sharing gate G4:

1. *finalize* — DAG additions only (I9 holds throughout): the LLM
   writes a flag-gated residue arm per path for every light-residue
   soft convergence (the residue diamond — an arm may carry a followup
   beat, and an identically gated chain collapses into one passage)
   and may propose false-branch diamonds on long linear runs; the
   engine splices them in. Skipped when nothing is needed.
2. *passages* — the engine computes collapse groups and the complete
   choice topology (endpoints, requires, grants); the LLM contributes
   only words: passage summaries, choice labels, ending titles, and —
   for heavy-residue soft convergences — one variant summary per path
   flag (the engine wires the gated variant passages). Not one call:
   finalize *expands* into independent, minimal-context passes — one
   `summary:<group>` per collapse group (its own beats are all the
   context a beat-derived summary needs) and one `labels:<group>` per
   source group with outgoing choices — because a single greedy call
   over the whole passage layer overran the context window at medium
   scope for no per-item benefit (docs/plans/passages-chunking.md).
3. *audit* — the prose-feasibility audit: the engine computes each
   passage's possibly-active flags; the LLM marks the flags a passage's
   prose must not address; gate I12 enforces the cap on the rest.
4. *arcs* — character-arc metadata per entity ("begins X, pivots at
   beat Y, ends Z per path"), FILL's per-passage arc position: the
   lever that paces specific aspects of a character per scene (plan:
   docs/plans/prose-quality.md W5).

M3 scope notes (tracked in docs/STATUS.md): false branches carry no
cosmetic flags yet. The pacing report is built (advisory B8, over beat
scene_type — graph/validate.py check_b8_pacing).
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from itertools import product

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import I12_AMBIGUOUS_CAP, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Dilemma
from questfoundry.models.presentation import Choice, Ending, Passage
from questfoundry.models.structure import Beat, BeatClass, StateFlag, StructuralPurpose
from questfoundry.models.world import ArcPivot, Entity, EntityArc, PathEnd
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline.refpin import entity_ref_ids, pin
from questfoundry.pipeline.types import (
    ApplyError,
    PassSpec,
    StageImpl,
    format_validation_error,
    resolve_entity_ref,
)
from questfoundry.project.io import Project

# -- pass 1: finalize ---------------------------------------------------------


class FollowupSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    entities: list[str] = []


class ForkSpec(BaseModel):
    """A second same-gate branch, making the arm a tensored diamond (M8):
    the reader who made this upstream choice gets a choice in how to
    carry it — texture only, both branches rejoin where the arm does."""

    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    entities: list[str] = []
    followup: FollowupSpec | None = None


class ResidueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dilemma: str
    path: str  # whose memory this arm carries; gated on that path's flag
    world: str = ""  # which world's convergence (multi-hard); "" when shared
    id: str
    summary: str
    entities: list[str] = []
    followup: FollowupSpec | None = None  # a second gated beat when the memory needs room
    fork: ForkSpec | None = None  # a second branch: the tensored arm


class ArmSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    entities: list[str] = []
    followup: FollowupSpec | None = None  # optional second beat when the flavor needs room


class FalseBranchSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before: str  # linear beat edge to fork
    after: str
    # arm count = the engine-assigned shape (PR-3): 1 = sidetrack (the direct
    # edge stays, an optional detour the reader may decline), 2 = diamond, 3 =
    # diamond with a third arm. The count is mandatory per the CADENCE table.
    arms: list[ArmSpec] = Field(min_length=1, max_length=3)


class TextureBeatSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    entities: list[str] = []


class TextureWorldSpec(BaseModel):
    """A parallel texture world over an offered stretch (structural-depth
    W3, invariant I15): the same events re-textured — one beat per trunk
    beat, in order; the engine mirrors annotations and wires the fork."""

    model_config = ConfigDict(extra="forbid")

    site: int  # index into the offered TEXTURE WORLDS sites
    premise: str  # the fresh rendering's backdrop, one line (any consequence-free axis)
    # rendering 0's backdrop — the trunk segment's own premise (cosmetic-forks
    # §2): grounded in what the trunk beats already carry, sharpening where the
    # weave left it vague. Renderings are peers, so the trunk names its axis too
    # (FILL grounds both worlds' prose, the entry label names both).
    trunk_premise: str
    beats: list[TextureBeatSpec] = Field(min_length=1)


class FinalizeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residue: list[ResidueSpec] = []
    false_branches: list[FalseBranchSpec] = []
    texture_worlds: list[TextureWorldSpec] = []


def _light_needs(project: Project) -> list[pc.ConvergenceNeed]:
    return [n for n in pc.convergence_needs(project.graph) if n.weight == "light"]


def _texture_and_cadence(project: Project) -> tuple[list[list[str]], list[dict], set[str]]:
    """The two engine-sized fork budgets, computed together so they agree
    (context and apply both call this — deterministic either way):
    texture sites first (structural-depth W3 — the cheapest choices in
    reader-words, capped by the words budget), then the words-aware
    diamond budget (M8) sized on a scratch graph already carrying probe
    arms, so the cadence the model sees accounts for the worlds it is
    asked to write. Returns (texture stretches, cadence table, the beats
    of long runs false branches may target — arm beats excluded: theirs
    arrive mirrored from the trunk). Both budgets' counts are mandatory,
    enforced by _finalize_apply (a weak tier proposed zero sites against
    a full budget and shipped a flat book, 2026-07-14)."""
    g = project.graph
    preset = project.vision.preset
    sites = pc.texture_plan(g, preset, words_target=project.vision.words_target)
    scratch = copy.deepcopy(g)
    for k, run in enumerate(sites):
        arm = [
            Beat(
                id=f"beat:texture-probe-{k}-{i}",
                created_by=Stage.POLISH,
                summary="probe",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.TEXTURE_WORLD,
            )
            for i in range(len(run))
        ]
        pc.insert_texture_world(scratch, arm, run)
    runs = pc.collapse_groups(scratch)
    plan = pc.cadence_plan(scratch, preset)
    cadence = [
        {
            "beats": runs[i],
            "edges": [(before, after) for before, after, _ in sites],
            "arm_counts": [arms for _, _, arms in sites],
        }
        for i, sites in sorted(plan.items())
    ]
    arm_ids = {
        b.id for b in scratch.nodes_of(Beat) if b.purpose == StructuralPurpose.TEXTURE_WORLD
    }
    long_run_beats = {
        b for i in pc.long_linear_runs(runs) for b in runs[i]
    } - arm_ids
    return sites, cadence, long_run_beats


def _finalize_skip(project: Project) -> str | None:
    sites, cadence, _ = _texture_and_cadence(project)
    if _light_needs(project) or cadence or sites:
        return None
    return "no light-residue convergences, no texture sites, and no cadence budget"


def _finalize_context(project: Project) -> dict:
    g = project.graph
    needs = []
    for need in _light_needs(project):
        needs.append(
            {
                "need": need,
                "dilemma": g.node(need.dilemma),
                "rejoin": [g.node(b) for b in need.rejoin],
                "tails": {
                    path: g.node(t)
                    for path, t in _convergence_tails(project, need).items()
                },
            }
        )
    # Reserved dilemmas are POLISH's texture feedstock (structural-depth
    # W2): real story material for false-branch arms, so the model grafts
    # instead of inventing. Advisory context only — never woven.
    reserve = [
        {
            "dilemma": d,
            "entities": [
                g.node(e).name  # type: ignore[union-attr]
                for e in g.out_ids(d.id, EdgeKind.ANCHORED_TO)
            ],
        }
        for d in sorted(g.nodes_of(Dilemma), key=lambda n: n.id)
        if d.reserved
    ]
    sites, cadence, _ = _texture_and_cadence(project)
    return {
        "vision": project.vision,
        # The roster of ids every `entities` field must draw from. Texture
        # sites are shown as beat summaries only, so without this a summary
        # naming "Sheriff Harold Finch" leads the model to coin
        # `character:finch` when the id is `character:marshal` (the live
        # weak-tier finalize halt, 2026-07-15): the schema pins entities to
        # these ids but the prompt never showed them.
        "cast": _arc_entities(g),
        "needs": needs,
        "cadence": cadence,
        "texture_sites": [
            {"index": i, "beats": [g.node(b) for b in run]} for i, run in enumerate(sites)
        ],
        "reserve": reserve,
    }


def _convergence_tails(project: Project, need: pc.ConvergenceNeed) -> dict[str, str]:
    g = project.graph
    tails = {}
    for path in need.path_flags:
        for b in queries.exclusive_beats(g, path):
            if queries.frontier_feeds(g, b, list(need.rejoin)):
                tails[path] = b
    return tails


def _finalize_apply(proposal: FinalizeProposal, project: Project) -> list[str]:
    g = project.graph
    # Residue arms and cadence false branches are both additions to the
    # *frozen* pre-finalize topology, so both validate against the pristine
    # structure the model was shown (and the schema pinned against). Snapshot
    # the long runs and convergence needs now, and splice the false branches
    # BEFORE residue: residue splicing shortens the runs it neighbours, so a
    # beat inside a long run at proposal time can fall out of one once
    # residue lands — and its diamond would be wrongly rejected against a
    # structure the model never saw (live gpt-oss:120b cloud, 2026-07-11: a
    # cadence diamond at a bridge beat that residue at the adjacent
    # convergence broke out of its run). The two never target the same
    # region — false branches sit in choice-free runs, residue at
    # convergence rejoins — so the order is a consistency choice, not a
    # semantic one.
    needs = {(n.dilemma, n.world): n for n in _light_needs(project)}
    # Both fork budgets are requirements, not suggestions: they are sized
    # to bring words-per-choice into the B6 band, and a proposal that
    # leaves either unfilled ships a book-shaped story (live gpt-oss:120b,
    # 2026-07-14: four finalize rounds each proposed zero sites against a
    # full budget — the medium landed at 10 branch points over 112
    # passages). Checked before any splice so a shortfall mutates nothing.
    sites, cadence, long_run_beats = _texture_and_cadence(project)
    proposed_sites = sorted(spec.site for spec in proposal.texture_worlds)
    if proposed_sites != list(range(len(sites))):
        wanted = "; ".join(
            f"site {i}: {run[0]} .. {run[-1]} ({len(run)} beats)"
            for i, run in enumerate(sites)
        )
        raise ApplyError(
            "the texture-world budget is mandatory, not advisory: emit exactly "
            f"one texture_worlds entry per offered site — {wanted or 'none'}; "
            f"this proposal covers sites {proposed_sites}. Each entry names its "
            "site index, a one-line premise, and one beat per trunk beat, in order"
        )
    for spec in proposal.texture_worlds:
        if not spec.premise.strip():
            raise ApplyError(
                f"texture world at site {spec.site} has an empty premise; state "
                "in one line what differs in this rendering — name a story "
                "element the beats, cast, or reserved material already carry "
                "and how this rendering varies it (any consequence-free axis)"
            )
        if not spec.trunk_premise.strip():
            raise ApplyError(
                f"texture world at site {spec.site} has an empty trunk_premise; "
                "rendering 0 (the trunk segment) names its own backdrop too — "
                "state in one line the world the trunk beats already carry, "
                "sharpening it only where the weave left it vague"
            )
        if len(spec.beats) != len(sites[spec.site]):
            raise ApplyError(
                f"texture world at site {spec.site} has {len(spec.beats)} beat(s) "
                f"against a {len(sites[spec.site])}-beat stretch; the arm mirrors "
                "the trunk beat-for-beat (I15) — write exactly one beat per trunk "
                "beat, in order"
            )
    run_of = {b: i for i, run in enumerate(cadence) for b in run["beats"]}
    # Per run, the multiset of arm counts placed must match the engine-assigned
    # shape mix (PR-3): shape is mandatory, not model-chosen — given the choice
    # a weak tier placed 44/44 sidetracks. This enforces count AND shape at once.
    placed_arms: dict[int, list[int]] = {}
    for spec in proposal.false_branches:
        if spec.before in run_of:
            placed_arms.setdefault(run_of[spec.before], []).append(len(spec.arms))
    mismatched = [
        (run, sorted(run["arm_counts"]), sorted(placed_arms.get(i, [])))
        for i, run in enumerate(cadence)
        if sorted(run["arm_counts"]) != sorted(placed_arms.get(i, []))
    ]
    if mismatched:
        detail = "; ".join(
            f"the run {run['beats'][0]} -> {run['beats'][-1]} needs sites with arm "
            f"counts {want} (1=sidetrack, 2=diamond, 3=diamond+3rd-arm), this proposal "
            f"placed {got}"
            for run, want, got in mismatched
        )
        raise ApplyError(
            f"the cadence budget is mandatory, not advisory: {detail} — the engine "
            "assigns the shape mix; place exactly the arm counts listed for each run "
            "under CADENCE (each on any of that run's suggested seam edges), keeping "
            "the sites you already placed correctly"
        )
    lines = []
    # Texture worlds splice first: the cadence table was sized on a graph
    # carrying them, and a diamond landing inside a mirrored stretch needs
    # the real arms present to mirror into (pc.insert_cadence_diamond).
    for spec in sorted(proposal.texture_worlds, key=lambda s: s.site):
        try:
            arm = [
                Beat(
                    id=b.id,
                    created_by=Stage.POLISH,
                    summary=b.summary,
                    beat_class=BeatClass.STRUCTURAL,
                    purpose=StructuralPurpose.TEXTURE_WORLD,
                    texture_premise=spec.premise.strip(),
                    entities=[resolve_entity_ref(g, e) for e in b.entities],
                )
                for b in spec.beats
            ]
        except ValidationError as e:
            raise ApplyError(
                f"invalid texture-world beat at site {spec.site}: "
                f"{format_validation_error(e)}"
            ) from e
        try:
            pc.insert_texture_world(g, arm, sites[spec.site])
            # Rendering 0's premise: the trunk segment names its own backdrop
            # too (renderings are peers, §2). A legal presentation addition on
            # the frozen trunk beats (the freeze is topological — 01 §6).
            for trunk_beat in sites[spec.site]:
                mutations.set_beat_texture_premise(g, trunk_beat, spec.trunk_premise.strip())
        except (mutations.MutationError, KeyError) as e:
            # duplicate ids arrive pre-converted by add_beat; MutationError
            # messages from the splice carry their own correctives
            raise ApplyError(f"texture world at site {spec.site}: {e}") from e
        lines.append(
            f"texture world '{spec.premise.strip()}' (trunk '{spec.trunk_premise.strip()}') "
            f"parallels {sites[spec.site][0]} .. {sites[spec.site][-1]} ({len(arm)} beats)"
        )
    for spec in proposal.false_branches:
        if spec.before not in long_run_beats or spec.after not in long_run_beats:
            raise ApplyError(
                f"false branch at {spec.before} -> {spec.after} is not inside a long "
                "linear run — place both endpoints on adjacent beats of one of the "
                "runs listed under CADENCE in the prompt (the suggested seam edges "
                "there are always valid), or drop this site"
            )
        try:
            chains = [
                [
                    Beat(
                        id=b.id,
                        created_by=Stage.POLISH,
                        summary=b.summary,
                        beat_class=BeatClass.STRUCTURAL,
                        purpose=StructuralPurpose.FALSE_BRANCH,
                        entities=[resolve_entity_ref(g, e) for e in b.entities],
                    )
                    for b in ([arm] if arm.followup is None else [arm, arm.followup])
                ]
                for arm in spec.arms
            ]
        except ValidationError as e:
            raise ApplyError(f"invalid false-branch arm: {format_validation_error(e)}") from e
        try:
            # the cadence splices mirror themselves into any texture arm
            # paralleling the edge (structural-depth W3; both worlds keep
            # the same choice topology)
            if len(chains) == 1:
                pc.insert_cadence_sidetrack(g, chains[0], spec.before, spec.after)
            else:
                pc.insert_cadence_diamond(g, chains, spec.before, spec.after)
        except (mutations.MutationError, KeyError) as e:
            # add_beat already converts a duplicate-id KeyError into an
            # actionable MutationError; the KeyError arm here catches the
            # store's GraphError family (its messages carry their own
            # correctives), so the wrap adds location, not a diagnosis
            raise ApplyError(f"false branch {spec.before} -> {spec.after}: {e}") from e
        if len(chains) == 1:
            lines.append(f"sidetrack {chains[0][0].id} off {spec.before} -> {spec.after}")
        else:
            lines.append(
                f"diamond {' / '.join(c[0].id for c in chains)} "
                f"between {spec.before} -> {spec.after}"
            )

    covered: set[tuple[str, str, str]] = set()
    for spec in proposal.residue:
        need = needs.get((spec.dilemma, spec.world))
        if need is None:
            expected = sorted(
                f"dilemma {d}" + (f" in world {w}" if w else "") for d, w in needs
            )
            # State the corrective, not just the mismatch (AGENTS.md error
            # contract; the Closed Circle live run exhausted repairs on a
            # world added to a shared convergence with only the list to
            # infer from — same treatment as the duplicate-arm error below)
            raise ApplyError(
                f"residue {spec.id}: (dilemma, world) must match exactly one "
                f"convergence of {expected}; got {spec.dilemma!r} in world {spec.world!r}. "
                "A convergence listed WITHOUT a world is shared: leave its world out "
                "(or \"\") — do not attach one. A convergence listed WITH a world "
                "takes that exact world string. Correct this entry to one of the "
                "listed (dilemma, world) pairs."
            )
        flags = need.path_flags.get(spec.path)
        if flags is None:
            raise ApplyError(
                f"residue {spec.id}: path must be exactly one of "
                f"{sorted(need.path_flags)}; got {spec.path!r}"
            )
        flag = flags[0]  # any of the path's flags marks the choice; first is deterministic
        if (spec.dilemma, spec.world, spec.path) in covered:
            raise ApplyError(
                f"residue {spec.id}: path {spec.path} already has a residue arm at "
                "this convergence — emit exactly one arm entry per path. Drop this "
                "duplicate; then, on that path's single arm, if you meant a longer "
                "arm add a `followup` beat, or if you meant two textures of the same "
                "choice add a `fork` (a second branch behind the same gate). Never a "
                "second arm entry for the same path."
            )
        def gated_chain(head, flag=flag, spec=spec):
            try:
                return [
                    Beat(
                        id=b.id,
                        created_by=Stage.POLISH,
                        summary=b.summary,
                        beat_class=BeatClass.STRUCTURAL,
                        purpose=StructuralPurpose.RESIDUE,
                        entities=[resolve_entity_ref(g, e) for e in b.entities],
                        requires_flags=[flag],
                    )
                    for b in ([head] if head.followup is None else [head, head.followup])
                ]
            except ValidationError as e:
                raise ApplyError(
                    f"invalid residue beat {spec.id}: {format_validation_error(e)}"
                ) from e

        chain = gated_chain(spec)
        try:
            if spec.fork is None:
                pc.insert_residue_chain(g, chain, spec.path, need.rejoin)
            else:
                pc.insert_residue_diamond(
                    g, chain, gated_chain(spec.fork), spec.path, need.rejoin
                )
        except (mutations.MutationError, KeyError) as e:
            # same shape as the false-branch catch above: duplicate ids arrive
            # pre-converted by add_beat, GraphError carries its own corrective
            raise ApplyError(f"residue {spec.id}: {e}") from e
        covered.add((spec.dilemma, spec.world, spec.path))
        arm = " -> ".join(b.id for b in chain)
        if spec.fork is not None:
            arm += f" / {spec.fork.id}"
        lines.append(f"{arm} carries {spec.path}'s memory into {'/'.join(need.rejoin)}")
    missing = [
        (d, w, p) for (d, w), need in needs.items() for p in need.path_flags
        if (d, w, p) not in covered
    ]
    if missing:
        labels = sorted(f"{p} at {d}" + (f" (world {w})" if w else "") for d, w, p in missing)
        raise ApplyError(
            "every light-residue convergence needs one residue arm per path — the "
            f"story must remember whichever side was chosen; missing {labels}"
        )

    return lines or ["nothing inserted"]


# -- pass 2: passages (finalize-expanded per-group summary + per-source labels) --
#
# The passage layer is NOT emitted in one greedy call. Finalize expands into
# independent, minimal-context passes (docs/plans/passages-chunking.md; mini-ADR
# A21): one `summary:<group>` per collapse group and one `labels:<group>` per
# source group with outgoing choices. A single call over every group and edge
# overran `num_ctx` at medium scope (the medium-scale AdapterError the
# narration_scope live runs hit) while giving no per-item benefit — a passage
# summary is derived from that group's own beats alone. The engine still computes
# every bit of structure; the LLM contributes only words. Because passage
# creation (`summary:<group>`) and choice wiring (`labels:<group>`) are now
# separate passes, each variant's gate is recovered from the persisted
# `Passage.variant_flag` (the create-time mapping the single pass held in memory).


class VariantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag: str
    id: str
    summary: str


class SummaryProposal(BaseModel):
    """One collapse group's passage content."""

    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    ending_title: str = ""  # required iff the group contains an ending beat
    variants: list[VariantSpec] = []  # required iff the group needs variants


class EdgeLabelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    dst: int = Field(alias="to")
    label: str


class LabelsProposal(BaseModel):
    """One source group's outgoing choice labels (one per destination group)."""

    model_config = ConfigDict(extra="forbid")

    labels: list[EdgeLabelSpec]


def _groups(project: Project) -> list[list[str]]:
    """The capped collapse groups — the single grouping every POLISH passage
    pass indexes into, so `summary:<i>` / `labels:<i>` names stay stable.
    Viewpoint-split: a head-switch is a passage boundary (I14)."""
    return pc.collapse_groups(
        project.graph,
        max_beats=project.vision.preset.passage_beats_max,
        split_viewpoints=True,
    )


def _variant_needs(g) -> dict[str, list[str]]:
    """frontier beat -> path flags, for heavy-residue soft dilemmas. A
    single-beat frontier is the convergence passage; a multi-beat one is
    a deeper hard fork, and each world's frontier beat gets its own
    flag-gated variants (per-world variants, design doc 01 §5)."""
    needs: dict[str, list[str]] = {}
    for n in pc.convergence_needs(g):
        if n.weight != "heavy":
            continue
        for beat_id in n.rejoin:
            # one variant gate per path: its first flag, deterministically
            merged = set(needs.get(beat_id, [])) | {fl[0] for fl in n.path_flags.values()}
            needs[beat_id] = sorted(merged)
    return needs


def _group_variant_flags(g, group: list[str]) -> list[str]:
    """The per-path gate flags a heavy-residue frontier group needs variants
    for; empty for an ordinary group."""
    needs = [flags for c, flags in _variant_needs(g).items() if c in group]
    return needs[0] if needs else []


def _group_passages(g, group: list[str]) -> list[tuple[str, list[str]]]:
    """The passage(s) a group's beats belong to, each paired with its gate
    recovered from the persisted `variant_flag` — one entry for an ordinary
    group, one per variant for a heavy-residue frontier group. Read by
    `labels:<group>` after the `summary:<group>` passes mint the passages, so
    wiring can gate variants without the create-time mapping the single pass
    once held in memory."""
    result: list[tuple[str, list[str]]] = []
    for pid in queries.passages_of_beat(g, group[0]):
        vf = g.node(pid).variant_flag
        result.append((pid, [vf] if vf else []))
    return result


def _ending_id(passage_id: str) -> str:
    slug = passage_id.split(":", 1)[1]
    return "e-" + slug.removeprefix("p-")


def _summary_context(i: int) -> Callable[[Project], dict]:
    def build(project: Project) -> dict:
        g = project.graph
        group = _groups(project)[i]
        flag_text = {f.id: f.description for f in g.nodes_of(StateFlag)}
        return {
            "vision": project.vision,
            "index": i,
            "beats": [g.node(b) for b in group],
            "is_ending": pc.ending_beat(g, group) is not None,
            "gate": pc.choice_requires(g, group),
            "variant_flags": [
                (fl, flag_text.get(fl, "")) for fl in _group_variant_flags(g, group)
            ],
        }

    return build


def _summary_schema(i: int) -> Callable[[Project], type[BaseModel]]:
    """An ordinary group forbids variants outright (grammar-level, like
    finalize's empty false-branch list); a heavy-residue frontier group pins
    `variants[].flag` to its per-path gate flags."""

    def schema(project: Project) -> type[BaseModel]:
        flags = _group_variant_flags(project.graph, _groups(project)[i])
        if not flags:
            return create_model(
                "SummaryProposal",
                __base__=SummaryProposal,
                variants=(list[VariantSpec], Field(default=[], max_length=0)),
            )
        return pin(SummaryProposal, "SummaryProposal", {("VariantSpec", "flag"): flags})

    return schema


def _summary_apply(i: int) -> Callable[[BaseModel, Project], list[str]]:
    def apply(proposal: SummaryProposal, project: Project) -> list[str]:
        g = project.graph
        group = _groups(project)[i]
        flags = _group_variant_flags(g, group)
        ending = pc.ending_beat(g, group)
        entities = pc.group_entities(g, group)

        def build(pid: str, summary: str, *, variant_flag=None):
            try:
                return Passage(
                    id=pid,
                    created_by=Stage.POLISH,
                    summary=summary,
                    entities=entities,
                    variant_flag=variant_flag,
                    ending=(
                        Ending(id=_ending_id(pid), title=proposal.ending_title)
                        if ending
                        else None
                    ),
                )
            except ValidationError as e:
                raise ApplyError(f"invalid passage {pid}: {format_validation_error(e)}") from e

        if ending and not proposal.ending_title.strip():
            raise ApplyError(f"group {i} contains an ending beat; ending_title is required")
        if flags:
            if sorted(v.flag for v in proposal.variants) != flags:
                raise ApplyError(f"group {i} needs one variant per flag {flags} (heavy residue)")
            members: list[str] = []
            for v in proposal.variants:
                mutations.add_passage(g, build(v.id, v.summary, variant_flag=v.flag), group)
                members.append(v.id)
            for vid in members[1:]:
                mutations.add_variant(g, vid, members[0])
            return [f"group {i}: variants {', '.join(members)}"]
        if proposal.variants:
            raise ApplyError(
                f"group {i} needs no variants — it is not a heavy-residue frontier; "
                "re-emit with variants: []"
            )
        mutations.add_passage(g, build(proposal.id, proposal.summary), group)
        return [f"group {i}: {proposal.id} ({len(group)} beat(s))"]

    return apply


def _sibling_labels(g, passages: list[tuple[str, list[str]]]) -> list[str]:
    """Labels already worded onto choices entering a destination's passage(s)
    — the parallel edges a cosmetic rejoin must differ from (cosmetic-forks
    §5). Ordering defers rejoin renderings after their siblings, so by the
    time this runs those siblings' choices exist; the rendering's own choices
    do not yet. Deduped, first-seen order (edge order is deterministic)."""
    labels: list[str] = []
    for pid, _ in passages:
        for e in g.in_edges(pid, EdgeKind.CHOICE):
            lbl = e.payload.get("label")
            if lbl and lbl not in labels:
                labels.append(lbl)
    return labels


def _labels_context(a: int) -> Callable[[Project], dict]:
    def build(project: Project) -> dict:
        g = project.graph
        groups = _groups(project)
        # A rejoin rendering carries residue relative to the sibling edges into
        # its destination; only then do we surface those siblings (cosmetic-
        # forks §5). A trunk/ordinary pass keeps its context byte-identical.
        is_rendering = a in pc.cosmetic_rejoin_sources(groups, g)
        out = [b for x, b in pc.group_edges(groups, g) if x == a]
        dests = []
        for b in out:
            passages = _group_passages(g, groups[b])
            dests.append(
                {
                    "index": b,
                    # A group-edge carries ONE label, engine-fanned across a heavy-
                    # residue destination's variant passages, so a single
                    # representative summary is the right granularity: the label is
                    # the world-agnostic action the reader takes, before the
                    # world-state a variant presents is known. Deterministic pick
                    # (passages_of_beat sorts by id).
                    "summary": g.node(passages[0][0]).summary if passages else "",
                    "requires": pc.choice_requires(g, groups[b]),
                    "grants": pc.choice_grants(g, groups[b]),
                    "is_ending": pc.ending_beat(g, groups[b]) is not None,
                    "siblings": _sibling_labels(g, passages) if is_rendering else [],
                    # a cosmetic-fork rendering's head beat carries its premise
                    # (the fresh arm's, or rendering 0's trunk_premise) — the
                    # entry label may name the world this choice enters (§2)
                    "premise": g.node(groups[b][0]).texture_premise,
                }
            )
        return {
            "vision": project.vision,
            "index": a,
            "beats": [g.node(x) for x in groups[a]],
            "dests": dests,
            "is_rendering": is_rendering,
        }

    return build


def _labels_apply(a: int) -> Callable[[BaseModel, Project], list[str]]:
    def apply(proposal: LabelsProposal, project: Project) -> list[str]:
        g = project.graph
        groups = _groups(project)
        out = [b for x, b in pc.group_edges(groups, g) if x == a]

        labeled: dict[int, str] = {}
        for spec in proposal.labels:
            if spec.dst in labeled:
                raise ApplyError(
                    f"group {a}: destination group {spec.dst} labeled twice — "
                    "one label per outgoing choice"
                )
            labeled[spec.dst] = spec.label
        if sorted(labeled) != sorted(out):
            raise ApplyError(
                f"group {a}: label each outgoing choice exactly once; "
                f"destination groups are {sorted(out)}"
            )
        stripped = {b: lbl.strip() for b, lbl in labeled.items()}
        if any(not lbl for lbl in stripped.values()):
            raise ApplyError("choice labels must be non-empty")
        if len(set(stripped.values())) != len(stripped):
            raise ApplyError(
                f"group {a}: choices leaving one passage must have distinct labels; "
                f"got {sorted(stripped.values())}"
            )

        def gate_holdable_from(group: list[str], flag_id: str) -> bool:
            return any(
                grant in group or grant in queries.ancestors(g, group[-1])
                for grant in queries.grant_beats(g, flag_id)
            )

        src_passages = _group_passages(g, groups[a])
        lines = []
        for b in out:
            base_requires = pc.choice_requires(g, groups[b])
            grants = pc.choice_grants(g, groups[b])
            for src_id, _ in src_passages:
                for dst_id, variant_gate in _group_passages(g, groups[b]):
                    # a variant's gate must be holdable on arcs that reach this
                    # source, or the choice could never be taken (I10)
                    if any(not gate_holdable_from(groups[a], f) for f in variant_gate):
                        continue
                    choice = Choice(
                        label=labeled[b],
                        requires=sorted({*base_requires, *variant_gate}),
                        grants=grants,
                    )
                    mutations.add_choice(g, src_id, dst_id, choice)
            lines.append(f"group {a} -> {b}: {labeled[b]!r}")
        return lines

    return apply


def _polish_expand(project: Project) -> list[PassSpec]:
    """Finalize's post-apply expansion: the collapse groups exist only after
    finalize adds its residue/false-branch/bridge beats, so the per-group
    passage passes are enumerated here and spliced in right after finalize
    (runner `PassSpec.expand`). Deterministic — the same post-finalize graph
    yields the same pass names on ledger resume (docs/plans/passages-chunking.md).
    All `summary:<group>` passes precede every `labels:<group>` pass: labels
    reference destinations that must already exist. Cosmetic-fork renderings
    word their rejoin label AFTER the parallel trunk/sibling edges into the
    same destination (a stable two-key sort), so each carries its rendering's
    residue rather than re-offering a sibling's action (cosmetic-forks §5)."""
    g = project.graph
    groups = _groups(project)
    rejoin_sources = pc.cosmetic_rejoin_sources(groups, g)
    source_groups = sorted(
        {a for a, _ in pc.group_edges(groups, g)},
        key=lambda a: (a in rejoin_sources, a),
    )
    passes: list[PassSpec] = []
    for i in range(len(groups)):
        passes.append(
            PassSpec(
                name=f"summary:{i}",
                role="writer",
                template="polish_summary.j2",
                schema=_summary_schema(i),
                build_context=_summary_context(i),
                apply=_summary_apply(i),
            )
        )
    for a in source_groups:
        passes.append(
            PassSpec(
                name=f"labels:{a}",
                role="writer",
                template="polish_labels.j2",
                schema=LabelsProposal,
                build_context=_labels_context(a),
                apply=_labels_apply(a),
            )
        )
    return passes


# -- pass 3: audit ------------------------------------------------------------


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage: str
    irrelevant: list[str] = []
    # dilemma ids to SPLIT this passage on (I12's escape valve, author-
    # directed 2026-07-14): when more states genuinely matter than the cap
    # allows, the engine re-presents the moment as flag-gated variants —
    # arrivals at each variant hold a known side, so the state honestly
    # stops counting, instead of being marked irrelevant to meet a budget.
    split_on: list[str] = []


class AuditProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit: list[AuditEntry]


def _audited_passages(project: Project) -> list[tuple[Passage, list[list[str]]]]:
    """Passages carrying ambiguous state, with their I12 dilemma groups —
    a dilemma's per-path flags are ONE binary state (the unit correction,
    2026-07-14); passage-level gates (variants) condition arrivals."""
    g = project.graph
    result = []
    for passage in sorted(g.nodes_of(Passage), key=lambda p: p.id):
        groups = queries.ambiguous_dilemma_groups(
            g,
            queries.beats_of_passage(g, passage.id),
            queries.passage_gate_flags(g, passage.id),
        )
        if groups:
            result.append((passage, groups))
    return result


def _audit_context(project: Project) -> dict:
    g = project.graph
    flag_text = {f.id: f.description for f in g.nodes_of(StateFlag)}

    def dilemma_of(group: list[str]) -> str:
        flag = g.node(group[0])
        assert isinstance(flag, StateFlag) and flag.path is not None
        return queries.dilemma_of_path(g, flag.path)

    passages = []
    for p, groups in _audited_passages(project):
        states = [
            {
                "dilemma": dilemma_of(grp),
                "question": g.node(dilemma_of(grp)).question,  # type: ignore[union-attr]
                "flags": [(f, flag_text[f]) for f in grp],
            }
            for grp in groups
        ]
        passages.append(
            {
                "passage": p,
                "states": states,
                "over": max(0, len(groups) - I12_AMBIGUOUS_CAP),
            }
        )
    return {
        "vision": project.vision,
        "passages": passages,
        "cap": I12_AMBIGUOUS_CAP,
    }


def _audit_apply(
    proposal: AuditProposal, project: Project, only: set[str] | None = None
) -> list[str]:
    """Two-phase, all violations batched into ONE repairable error (the
    scaffold precedent — raising the first violation of a joint proposal fed
    the repair loop one problem per round, and the live texture-trial
    exhausted repairs playing whack-a-mole). The I12 cap is enforced here,
    at the pass that can still fix it, in the honest unit (dilemma states,
    not flags) and with the honest escape (split_on — variants keyed on a
    dilemma — never irrelevance as budget-filler).

    ``only`` restricts the expected passage set to a subset — the audit runs
    one passage per pass (``_audit_expand``), since each passage's I12
    resolution is independent (``states − splits ≤ cap`` per passage) and a
    single call over every audited passage (~137 at medium, many near-
    identical texture renderings) degenerates into wholesale repetition (the
    A21 giant-call defect, live 2026-07-15). None keeps the joint behavior
    the unit tests exercise."""
    g = project.graph
    audited = _audited_passages(project)
    if only is not None:
        audited = [(p, groups) for p, groups in audited if p.id in only]
    expected = {p.id: groups for p, groups in audited}
    endings = {p.id for p, _ in audited if p.ending is not None}

    def dilemma_of(group: list[str]) -> str:
        flag = g.node(group[0])
        assert isinstance(flag, StateFlag) and flag.path is not None
        return queries.dilemma_of_path(g, flag.path)

    problems: list[str] = []
    seen: set[str] = set()
    for entry in proposal.audit:
        # live models drop the id namespace ("p-x" for "passage:p-x");
        # the prefix is unambiguous here, so accept the slug form
        if entry.passage not in expected and f"passage:{entry.passage}" in expected:
            entry.passage = f"passage:{entry.passage}"
        if entry.passage not in expected:
            problems.append(
                f"{entry.passage} is not a passage with ambiguous states; "
                f"audit exactly these ids: {sorted(expected)}"
            )
            continue
        if entry.passage in seen:
            problems.append(
                f"{entry.passage} audited twice — keep one audit entry per passage"
            )
            continue
        seen.add(entry.passage)
        groups = expected[entry.passage]
        flat = {f for grp in groups for f in grp}
        stray = set(entry.irrelevant) - flat
        if stray:
            problems.append(
                f"{entry.passage}: {sorted(stray)} are not ambiguous there — "
                f"drop them from irrelevant; the ambiguous flags are {sorted(flat)}"
            )
        relevant = [grp for grp in groups if not set(grp) <= set(entry.irrelevant)]
        relevant_dilemmas = {dilemma_of(grp) for grp in relevant}
        bad_split = [d for d in entry.split_on if d not in relevant_dilemmas]
        if bad_split:
            problems.append(
                f"{entry.passage}: split_on {bad_split} name no ambiguous state "
                f"here — split only on {sorted(relevant_dilemmas)}, or drop the split"
            )
            continue
        if len(entry.split_on) != len(set(entry.split_on)):
            problems.append(f"{entry.passage}: split_on lists a dilemma twice")
            continue
        if len(entry.split_on) > 2:
            problems.append(
                f"{entry.passage}: split on at most 2 dilemmas (4 variants); "
                "mark more states irrelevant instead"
            )
            continue
        if entry.split_on and entry.passage in endings:
            problems.append(
                f"{entry.passage} is an ending and cannot split (variants would "
                "multiply the story's ending set, fixed at the freeze); drop its "
                "split_on and mark only the states this final scene genuinely "
                "does not address as irrelevant"
            )
            continue
        left = len(relevant) - len(entry.split_on)
        if left > I12_AMBIGUOUS_CAP:
            over = left - I12_AMBIGUOUS_CAP
            states = [f"{dilemma_of(grp)}: {grp}" for grp in relevant]
            problems.append(
                f"{entry.passage} leaves {len(relevant)} dilemma states relevant "
                f"({states}) and splits {len(entry.split_on)}; a writer can honor "
                f"at most {I12_AMBIGUOUS_CAP} states in one passage (I12) — for at "
                f"least {over} more state(s), either mark ALL of that state's "
                "flags irrelevant (only if the scene genuinely doesn't touch it) "
                "or add its dilemma to split_on (the engine then re-presents this "
                "moment as gated variants — the honest choice when the state matters)"
            )
    missing = set(expected) - seen
    if missing:
        problems.append(f"audit must cover every listed passage; missing {sorted(missing)}")
    if problems:
        raise ApplyError(
            "audit rejected — fix ALL of the following in one corrected "
            "proposal, keeping every entry that is not named:\n- " + "\n- ".join(problems)
        )

    lines = []
    for entry in proposal.audit:
        mutations.set_passage_irrelevant_flags(g, entry.passage, entry.irrelevant)
        if entry.irrelevant:
            lines.append(f"{entry.passage}: don't address {', '.join(entry.irrelevant)}")
        if entry.split_on:
            sides = [
                [flags[0] for _, flags in sorted(queries.dilemma_flags(g, d).items())]
                for d in sorted(entry.split_on)
            ]
            gate_sets = [list(combo) for combo in product(*sides)]
            ids = mutations.split_passage(g, entry.passage, gate_sets)
            lines.append(
                f"{entry.passage}: split on {sorted(entry.split_on)} -> {', '.join(ids)}"
            )
    return lines or ["all ambiguous states judged relevant"]


def _audit_one_context(pid: str) -> Callable[[Project], dict]:
    """One passage's slice of the audit context (the template loops over
    ``passages``; here it is a single-element list)."""

    def build(project: Project) -> dict:
        ctx = _audit_context(project)
        ctx["passages"] = [p for p in ctx["passages"] if p["passage"] == pid]
        return ctx

    return build


def _audit_one_schema(pid: str) -> Callable[[Project], type[BaseModel]]:
    def schema(project: Project) -> type[BaseModel]:
        return audit_proposal_schema(project, only={pid})

    return schema


def _audit_one_apply(pid: str) -> Callable[[BaseModel, Project], list[str]]:
    def apply(proposal: AuditProposal, project: Project) -> list[str]:
        return _audit_apply(proposal, project, only={pid})

    return apply


def _audit_expand(project: Project) -> list[PassSpec]:
    """Per-passage audit passes (A21 for the audit): one ``audit:<pid>`` per
    ambiguous-state passage. Each passage's I12 resolution is independent
    (``states − splits ≤ cap`` per passage, and a split leaves every variant
    ``≤ cap`` by construction — no post-split re-audit), so per-passage is
    exact; the single joint call degenerated into wholesale repetition at
    medium scale (~137 near-identical passages doubled, live 2026-07-15).
    Deterministic (``_audited_passages`` is id-sorted) for ledger resume."""
    return [
        PassSpec(
            name=f"audit:{p.id}",
            role="architect",
            template="polish_audit.j2",
            schema=_audit_one_schema(p.id),
            build_context=_audit_one_context(p.id),
            apply=_audit_one_apply(p.id),
        )
        for p, _ in _audited_passages(project)
    ]


# -- pass 4: arcs -------------------------------------------------------------


class ArcPivotSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat: str
    becomes: str


class PathEndSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    state: str


class ArcSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    begins: str
    pivots: list[ArcPivotSpec] = []
    ends: list[PathEndSpec] = []


class ArcsProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arcs: list[ArcSpec] = Field(min_length=1)


def _arc_entities(g) -> list[Entity]:
    """Every retained entity is arc-eligible (author doctrine,
    2026-07-12): a character without an arc is an extra, a location a
    backdrop, an object a mcguffin, a faction a link — all of them can
    be given choices. The LLM decides which to arc; leaving one unarced
    declares it scenery."""
    return [e for e in sorted(g.nodes_of(Entity), key=lambda e: e.id) if e.retained]


def _arcs_context(project: Project) -> dict:
    g = project.graph
    order = queries.topological_order(g) or []
    names = queries.path_names(g)
    paths = [
        {
            "id": p,
            "question": g.node(queries.dilemma_of_path(g, p)).question,
            "answer": names[p],
        }
        for d in sorted(d.id for d in g.nodes_of(Dilemma))
        for p in queries.explored_paths(g, d)
    ]
    return {
        "vision": project.vision,
        "entities": _arc_entities(g),
        "beats": [g.node(b) for b in order],
        "paths": paths,
    }


def _arcs_apply(proposal: ArcsProposal, project: Project) -> list[str]:
    g = project.graph
    eligible = {e.id for e in _arc_entities(g)}
    seen: set[str] = set()
    lines = []
    for spec in proposal.arcs:
        entity_id = resolve_entity_ref(g, spec.entity)
        if entity_id not in eligible:
            raise ApplyError(
                f"{entity_id} is not a retained entity; arc exactly these: {sorted(eligible)}"
            )
        if entity_id in seen:
            raise ApplyError(f"{entity_id} arced twice — keep one arc entry per entity")
        seen.add(entity_id)
        arc = EntityArc(
            begins=spec.begins,
            pivots=[ArcPivot(beat=p.beat, becomes=p.becomes) for p in spec.pivots],
            ends=[PathEnd(path=e.path, state=e.state) for e in spec.ends],
        )
        mutations.set_entity_arc(g, entity_id, arc)
        lines.append(
            f"{entity_id}: {len(arc.pivots)} pivot(s), {len(arc.ends)} path end(s)"
        )
    return lines


def finalize_proposal_schema(project: Project) -> type[FinalizeProposal]:
    """Pin finalize's references: each residue's `dilemma`/`world`/`path`
    to the light-residue convergences' own values, false-branch `before`/
    `after` to the long-linear-run beats, and every `entities` ref to the
    entity ids. The apply still enforces the joint (dilemma, world, path)
    constraint the independent enums cannot express (pipeline/refpin.py).

    A false branch splices only into a long linear run, so when there is
    none the list must be empty — an empty `before`/`after` enum can't
    express "no items", so forbid the list outright (`max_length=0`). This
    is the reference discipline's list cousin: a reference *list* whose
    valid target set is empty must itself be empty. Without it a model
    (live gpt-oss:120b cloud, 2026-07-11) proposed a cadence diamond where
    none was structurally possible and exhausted repairs. `texture_worlds`
    gets the same treatment when no sites are offered; its `site` index
    is an int the pin machinery cannot enum, so exact coverage stays the
    apply's job (checked before any splice, with the sites named)."""
    needs = _light_needs(project)
    entities = entity_ref_ids(project.graph)
    sites, _, long_run_beats = _texture_and_cadence(project)
    long_beats = sorted(long_run_beats)
    schema = pin(
        FinalizeProposal,
        "FinalizeProposal",
        {
            ("ResidueSpec", "dilemma"): list(dict.fromkeys(n.dilemma for n in needs)),
            ("ResidueSpec", "world"): list(dict.fromkeys(n.world for n in needs)),
            ("ResidueSpec", "path"): list(dict.fromkeys(p for n in needs for p in n.path_flags)),
            ("ResidueSpec", "entities"): entities,
            ("FollowupSpec", "entities"): entities,
            ("ForkSpec", "entities"): entities,
            ("ArmSpec", "entities"): entities,
            ("TextureBeatSpec", "entities"): entities,
            ("FalseBranchSpec", "before"): long_beats,
            ("FalseBranchSpec", "after"): long_beats,
        },
    )
    overrides: dict = {}
    if not long_beats:
        overrides["false_branches"] = (list[FalseBranchSpec], Field(default=[], max_length=0))
    if not sites:
        overrides["texture_worlds"] = (list[TextureWorldSpec], Field(default=[], max_length=0))
    if overrides:
        schema = create_model("FinalizeProposal", __base__=schema, **overrides)
    return schema


def arcs_proposal_schema(project: Project) -> type[ArcsProposal]:
    """Pin `arcs[].entity` to the retained entities (exact ids plus the
    bare slugs `resolve_entity_ref` also accepts), `pivots[].beat` to
    the real beats, and `ends[].path` to the explored paths."""
    g = project.graph
    eligible = [e.id for e in _arc_entities(g)]
    all_slugs = [i.split(":", 1)[1] for i in entity_ref_ids(g) if ":" in i]
    slugs = [
        i.split(":", 1)[1]
        for i in eligible
        if all_slugs.count(i.split(":", 1)[1]) == 1
    ]
    paths = [
        p
        for d in sorted(d.id for d in g.nodes_of(Dilemma))
        for p in queries.explored_paths(g, d)
    ]
    return pin(
        ArcsProposal,
        "ArcsProposal",
        {
            ("ArcSpec", "entity"): eligible + slugs,
            ("ArcPivotSpec", "beat"): queries.topological_order(g) or [],
            ("PathEndSpec", "path"): paths,
        },
    )


def audit_proposal_schema(
    project: Project, only: set[str] | None = None
) -> type[AuditProposal]:
    """Pin `audit[].passage` to the passages that have ambiguous states
    (both exact ids and their unambiguous slugs, which the apply also
    accepts), `irrelevant[]` to those passages' ambiguous flags, and
    `split_on[]` to the dilemmas those states belong to. Resolved after
    the passages pass mints the passages (PassSpec.schema_for). ``only``
    restricts to a single passage's audit pass (``_audit_expand``)."""
    g = project.graph
    audited = _audited_passages(project)
    if only is not None:
        audited = [(p, groups) for p, groups in audited if p.id in only]
    ids = sorted(p.id for p, _ in audited)
    passage_refs = ids + [i.split(":", 1)[1] for i in ids]
    flags = list(dict.fromkeys(f for _, groups in audited for grp in groups for f in grp))
    dilemmas = sorted(
        {
            queries.dilemma_of_path(g, g.node(grp[0]).path)  # type: ignore[union-attr]
            for _, groups in audited
            for grp in groups
        }
    )
    return pin(
        AuditProposal,
        "AuditProposal",
        {
            ("AuditEntry", "passage"): passage_refs,
            ("AuditEntry", "irrelevant"): flags,
            ("AuditEntry", "split_on"): dilemmas,
        },
    )


POLISH_STAGE = StageImpl(
    stage=Stage.POLISH,
    passes=(
        PassSpec(
            name="finalize",
            role="writer",
            template="polish_finalize.j2",
            schema=finalize_proposal_schema,
            build_context=_finalize_context,
            apply=_finalize_apply,
            skip_if=_finalize_skip,
            # The passage layer: finalize expands into per-group summary + per-source
            # label passes (their count is unknown until finalize's additions land).
            expand=_polish_expand,
        ),
        PassSpec(
            name="audit",
            role="architect",
            template="polish_audit.j2",
            schema=audit_proposal_schema,
            build_context=_audit_context,
            apply=_audit_apply,
            # Decomposed per passage (A21): this planner makes no call; its
            # expand splices one `audit:<pid>` pass per ambiguous-state
            # passage. A single joint call over ~137 near-identical passages
            # degenerated into wholesale repetition (live 2026-07-15).
            skip_if=lambda project: (
                f"decomposed into {len(_audited_passages(project))} per-passage audit(s)"
                if _audited_passages(project)
                else "no passage carries ambiguous state"
            ),
            expand=_audit_expand,
        ),
        PassSpec(
            name="arcs",
            role="writer",
            template="polish_arcs.j2",
            schema=arcs_proposal_schema,
            build_context=_arcs_context,
            apply=_arcs_apply,
        ),
    ),
    gate=lambda p: run_checks(p.graph, p.vision, Stage.POLISH),
)
