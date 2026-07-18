"""POLISH — compile the frozen beat DAG to passages (design doc 02).

Passes sharing gate G4:

1. *finalize* — the loop (cosmetic-forks §3/§6), DAG additions only (I9
   holds throughout). Round 0 (`finalize:0`) is residue: the LLM writes
   a flag-gated arm per path for every light-residue soft convergence
   (an arm may carry a followup beat; an identically gated chain
   collapses into one passage) — obligations before decoration. Budget
   rounds (`finalize:<n>`, n >= 1) are engine-only planners: each
   recomputes `pc.fork_plan` on the current graph and expands into one
   small `fork:<n>:<k>` pass per admitted cosmetic-fork site (shape and
   arm count engine-assigned; the model words premises and beats; the
   apply splices via the one cosmetic-fork primitive and mints one
   keyword per non-empty rendering). A terminal round expands into the
   passage passes.
2. *passages* — the engine computes collapse groups and the complete
   choice topology (endpoints, requires, grants); the LLM contributes
   only words: passage summaries, choice labels, ending titles, and —
   for heavy-residue soft convergences — one variant summary per path
   flag (the engine wires the gated variant passages). Not one call:
   the terminal round *expands* into independent, minimal-context
   passes — one `summary:<group>` per collapse group (its own beats are
   all the context a beat-derived summary needs) and one
   `labels:<group>` per source group with outgoing choices — because a
   single greedy call over the whole passage layer overran the context
   window at medium scope for no per-item benefit
   (docs/plans/passages-chunking.md).
3. *audit* — the prose-feasibility audit: the engine computes each
   passage's possibly-active flags; the LLM marks the flags a passage's
   prose must not address; gate I12 enforces the cap on the rest.
4. *arcs* — character-arc metadata per entity ("begins X, pivots at
   beat Y, ends Z per path"), FILL's per-passage arc position: the
   lever that paces specific aspects of a character per scene (plan:
   docs/plans/prose-quality.md W5).

The pacing report is built (advisory B8, over beat scene_type —
graph/validate.py check_b8_pacing).
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import product

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import I12_AMBIGUOUS_CAP, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Dilemma
from questfoundry.models.presentation import Choice, Ending, Passage
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    FlagSource,
    StateFlag,
    StructuralPurpose,
)
from questfoundry.models.world import ArcPivot, Entity, EntityArc, PathEnd
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline.refpin import entity_ref_ids, enum_type, pin
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


class FinalizeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residue: list[ResidueSpec] = []


def _light_needs(project: Project) -> list[pc.ConvergenceNeed]:
    return [n for n in pc.convergence_needs(project.graph) if n.weight == "light"]


def _finalize_skip(project: Project) -> str | None:
    if _light_needs(project):
        return None
    return "no light-residue convergences"


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
    return {
        "vision": project.vision,
        # The roster of ids every `entities` field must draw from. Without
        # it a summary naming "Sheriff Harold Finch" leads the model to coin
        # `character:finch` when the id is `character:marshal` (the live
        # weak-tier finalize halt, 2026-07-15): the schema pins entities to
        # these ids but the prompt never showed them.
        "cast": _arc_entities(g),
        "needs": needs,
    }


def _reserve_context(g) -> list[dict]:
    """Reserved dilemmas are POLISH's texture feedstock (structural-depth
    W2): real story material for cosmetic-fork renderings, so the model
    grafts instead of inventing. Advisory context only — never woven."""
    return [
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


def _convergence_tails(project: Project, need: pc.ConvergenceNeed) -> dict[str, str]:
    g = project.graph
    tails = {}
    for path in need.path_flags:
        for b in queries.exclusive_beats(g, path):
            if queries.frontier_feeds(g, b, list(need.rejoin)):
                tails[path] = b
    return tails


def _finalize_apply(proposal: FinalizeProposal, project: Project) -> list[str]:
    """Round 0 of the finalize loop: residue only (cosmetic-forks §6).
    Obligations land before decoration — the budget rounds (`finalize:<n>`,
    n >= 1) compute their fork sites on the graph residue has already
    rerouted, so no splice-order subtlety survives."""
    g = project.graph
    needs = {(n.dilemma, n.world): n for n in _light_needs(project)}
    lines: list[str] = []

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


# -- pass 1b: the fork rounds (finalize:<n>, cosmetic-forks §3/§6) -------------
#
# Finalize is a fixed-point iteration of the one cosmetic-fork splice. Each
# round `finalize:<n>` (n >= 1) is an engine-only planner pass — it always
# skips (no LLM call) and its `expand` recomputes `pc.fork_plan` on the
# *current* graph: one small `fork:<n>:<k>` pass per admitted site, then the
# next round's planner. A terminal round (empty plan) expands into the
# passage passes instead. Every planning input is a pure function of the
# graph, so ledger resume reproduces the same pass names (A16).


class ForkBeatSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    entities: list[str] = []


class RenderingSpec(BaseModel):
    """One fresh rendering: its premise (the value on the consequence-free
    axis this rendering varies) and its beats — exactly one per segment beat
    for a segment-scale site (I15), one or two for an edge-scale arm."""

    model_config = ConfigDict(extra="forbid")

    premise: str
    beats: list[ForkBeatSpec] = Field(min_length=1)


class ForkProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # rendering 0's backdrop — required (non-empty) iff the site is
    # segment-scale: the trunk segment names its own axis value too
    # (renderings are peers, cosmetic-forks §2)
    trunk_premise: str = ""
    renderings: list[RenderingSpec] = Field(min_length=1)


class GatedRenderingSpec(RenderingSpec):
    keyword: str


class GatedForkProposal(ForkProposal):
    """Edge-scale sites with offered keywords MAY attach one keyword-gated
    extra rendering — visible only to holders, same size budget as any
    rendering (acknowledges, never rewards; cosmetic-forks §4). Consumption
    is always optional, never assigned."""

    gated: GatedRenderingSpec | None = None


def _fork_schema(site: pc.ForkSite) -> Callable[[Project], type[BaseModel]]:
    """Per-site schema: `renderings` pinned to exactly the assigned arm
    count, beat counts pinned (segment length, or 1-2 for an edge arm),
    entities pinned to the roster, and — on an edge site with offers — the
    gated rendering's `keyword` pinned to the offered set. A site without
    offers (or any segment-scale site) uses the gated-less base model, so a
    disallowed consumption is unrepresentable."""

    def schema(project: Project) -> type[BaseModel]:
        entities = entity_ref_ids(project.graph)
        beat_spec = pin(
            ForkBeatSpec, "ForkBeatSpec", {("ForkBeatSpec", "entities"): entities}
        )
        n = len(site.segment)
        lo, hi = (n, n) if n else (1, 2)
        rendering = create_model(
            "RenderingSpec",
            __base__=RenderingSpec,
            beats=(list[beat_spec], Field(min_length=lo, max_length=hi)),  # type: ignore[valid-type]
        )
        fields: dict = {
            "renderings": (
                list[rendering],  # type: ignore[valid-type]
                Field(min_length=site.arms, max_length=site.arms),
            ),
        }
        if site.keywords and not site.segment:
            gated = create_model(
                "GatedRenderingSpec",
                __base__=GatedRenderingSpec,
                beats=(list[beat_spec], Field(min_length=1, max_length=2)),  # type: ignore[valid-type]
                keyword=(enum_type(list(site.keywords)), ...),
            )
            fields["gated"] = (gated | None, Field(default=None))
            return create_model("GatedForkProposal", __base__=GatedForkProposal, **fields)
        return create_model("ForkProposal", __base__=ForkProposal, **fields)

    return schema


def _fork_context(site: pc.ForkSite) -> Callable[[Project], dict]:
    def build(project: Project) -> dict:
        g = project.graph
        anchor = site.segment[0] if site.segment else site.before
        return {
            "vision": project.vision,
            "cast": _arc_entities(g),
            "reserve": _reserve_context(g),
            "segment": [g.node(b) for b in site.segment],
            "before": g.node(site.before) if not site.segment else None,
            "after": g.node(site.after) if not site.segment else None,
            "arms": site.arms,
            "keywords": [
                (f, g.node(f).description)  # type: ignore[union-attr]
                for f in site.keywords
            ],
            # a site inside an existing rendering inherits its backdrop: the
            # summaries written here must stay inside that world (the FILL
            # premise-stack lever is deferred — BACKLOG — so consistency is
            # carried by the summaries themselves)
            "host_premise": g.node(anchor).texture_premise,  # type: ignore[union-attr]
        }

    return build


def _mint_keyword(g, head_id: str, premise: str) -> str:
    """Mint one cosmetic keyword for a non-empty rendering at splice time
    (engine-deterministic, never model-proposed): `flag:cw-<head-slug>`,
    suffixed on collision; the description is the rendering's premise — it
    is what later consumption prompts read (cosmetic-forks §4)."""
    slug = head_id.split(":", 1)[1]
    flag_id = f"flag:cw-{slug}"
    n = 2
    while g.get(flag_id) is not None:
        flag_id = f"flag:cw-{slug}-{n}"
        n += 1
    mutations.add_flag(
        g,
        StateFlag(
            id=flag_id,
            created_by=Stage.POLISH,
            description=premise,
            source=FlagSource.COSMETIC,
        ),
    )
    mutations.add_beat_flag_grant(g, head_id, flag_id)
    return flag_id


def _fork_apply(site: pc.ForkSite) -> Callable[[BaseModel, Project], list[str]]:
    def apply(proposal: ForkProposal, project: Project) -> list[str]:
        g = project.graph
        segment = list(site.segment)
        where = (
            f"{segment[0]} .. {segment[-1]}" if segment else f"{site.before} -> {site.after}"
        )
        renderings = list(proposal.renderings)
        gated = getattr(proposal, "gated", None)
        for k, spec in enumerate([*renderings, *([gated] if gated else [])]):
            if not spec.premise.strip():
                raise ApplyError(
                    f"rendering {k} at {where} has an empty premise; state in one "
                    "line what differs in this rendering — name a story element "
                    "the beats, cast, or reserved material already carry and how "
                    "this rendering varies it (any consequence-free axis)"
                )
        if segment:
            if not proposal.trunk_premise.strip():
                raise ApplyError(
                    f"the fork at {where} has an empty trunk_premise; rendering 0 "
                    "(the trunk segment) names its own backdrop too — state in one "
                    "line the world the trunk beats already carry, sharpening it "
                    "only where the weave left it vague"
                )
            for spec in renderings:
                if len(spec.beats) != len(segment):
                    raise ApplyError(
                        f"a rendering at {where} has {len(spec.beats)} beat(s) "
                        f"against a {len(segment)}-beat segment; a rendering "
                        "re-expresses the segment beat-for-beat (I15) — write "
                        "exactly one beat per segment beat, in order"
                    )
        elif proposal.trunk_premise.strip():
            raise ApplyError(
                f"the fork at {where} is edge-scale — its segment is empty, so "
                "there is no rendering 0 to describe; re-emit with trunk_premise "
                'left out (or "")'
            )

        purpose = (
            StructuralPurpose.TEXTURE_WORLD if segment else StructuralPurpose.FALSE_BRANCH
        )

        def build_chain(spec: RenderingSpec, requires: list[str]) -> list[Beat]:
            try:
                return [
                    Beat(
                        id=b.id,
                        created_by=Stage.POLISH,
                        summary=b.summary,
                        beat_class=BeatClass.STRUCTURAL,
                        purpose=purpose,
                        texture_premise=spec.premise.strip(),
                        requires_flags=list(requires),
                        entities=[resolve_entity_ref(g, e) for e in b.entities],
                    )
                    for b in spec.beats
                ]
            except ValidationError as e:
                raise ApplyError(
                    f"invalid rendering beat at {where}: {format_validation_error(e)}"
                ) from e

        fresh = [build_chain(spec, []) for spec in renderings]
        if gated is not None:
            fresh.append(build_chain(gated, [gated.keyword]))
        try:
            if segment:
                pc.insert_cosmetic_fork(g, [pc.SEGMENT_RENDERING, *fresh], segment=segment)
                # Rendering 0's premise: a legal presentation addition on the
                # frozen trunk beats (the freeze is topological — 01 §6).
                for trunk_beat in segment:
                    mutations.set_beat_texture_premise(
                        g, trunk_beat, proposal.trunk_premise.strip()
                    )
            elif site.arms == 1:
                pc.insert_cosmetic_fork(
                    g, [pc.EMPTY_RENDERING, *fresh], before=site.before, after=site.after
                )
            else:
                pc.insert_cosmetic_fork(g, fresh, before=site.before, after=site.after)
        except (mutations.MutationError, KeyError) as e:
            # duplicate ids arrive pre-converted by add_beat; MutationError
            # messages from the splice carry their own correctives
            raise ApplyError(f"cosmetic fork at {where}: {e}") from e

        # Mint one keyword per non-empty rendering — rendering 0's frozen head
        # included, the gated rendering included, the empty rendering excluded
        # (ratified decision 3: walking past a sidetrack leaves no mark).
        heads = []
        if segment:
            heads.append((segment[0], proposal.trunk_premise.strip()))
        heads.extend((chain[0].id, chain[0].texture_premise) for chain in fresh)
        minted = [_mint_keyword(g, head, premise) for head, premise in heads]

        shape = {True: "two-worlds", False: {1: "sidetrack", 2: "diamond", 3: "diamond+3"}}
        name = shape[True] if segment else shape[False][site.arms]  # type: ignore[index]
        lines = [
            f"{name} at {where}: rendering(s) "
            + " / ".join(spec.premise.strip() for spec in renderings)
            + (f" (trunk: {proposal.trunk_premise.strip()})" if segment else "")
            + f"; minted {', '.join(minted)}"
        ]
        if gated is not None:
            lines.append(
                f"gated rendering '{gated.premise.strip()}' consumes {gated.keyword}"
            )
        return lines

    return apply


def _fork_pass(n: int, k: int, site: pc.ForkSite) -> PassSpec:
    return PassSpec(
        name=f"fork:{n}:{k}",
        role="writer",
        template="polish_fork.j2",
        schema=_fork_schema(site),
        build_context=_fork_context(site),
        apply=_fork_apply(site),
    )


def _round_spec(n: int) -> PassSpec:
    """An engine-only planner pass: always skipped (its skip reason reports
    the round decision), never calls the LLM; the work is in `expand`.

    ``fork_plan`` is expensive (a scratch deep-copy plus repeated walk
    projections per candidate site), and the runner calls ``skip_if`` and
    ``expand`` back to back on the same graph — the pass always skips, so
    nothing mutates in between. ``skip_if`` therefore stashes its plan for
    ``expand`` to consume once (popped, so any other path recomputes; the
    result is identical either way — the plan is a pure function of the
    unchanged graph, which is also what ledger resume relies on)."""
    stash: dict[str, list[pc.ForkSite]] = {}

    def skip(project: Project) -> str:
        plan = pc.fork_plan(
            project.graph, project.vision.preset, project.vision.words_target
        )
        stash["plan"] = plan
        if plan:
            return f"engine round {n}: {len(plan)} fork site(s) scheduled"
        return (
            f"engine round {n}: terminal — B6 target reached, or no qualifying "
            "site fits the words headroom"
        )

    def expand(project: Project) -> list[PassSpec]:
        plan = stash.pop("plan", None)
        if plan is None:
            plan = pc.fork_plan(
                project.graph, project.vision.preset, project.vision.words_target
            )
        if not plan:
            return _polish_expand(project)
        passes = [_fork_pass(n, k, site) for k, site in enumerate(plan)]
        passes.append(_round_spec(n + 1))
        return passes

    return PassSpec(
        name=f"finalize:{n}",
        role="writer",
        template="polish_fork.j2",  # never rendered — the pass always skips
        schema=ForkProposal,
        build_context=lambda project: {},
        apply=lambda proposal, project: [],
        skip_if=skip,
        expand=expand,
    )


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


def _labels_schema(a: int) -> Callable[[Project], type[BaseModel]]:
    """Pin the labels list to exactly this source group's out-destinations:
    each `to` is a `Literal` of the real destination groups and the list length
    is fixed to the number of exits. A single-exit passage is then structurally
    incapable of carrying two labels — the live failure (medium run 2026-07-18,
    `labels:34`): a passage whose beats *narrate* several actions ("she ignores
    the passage… she scours the woods") drew one label per described action, all
    onto the group's single exit, and no repair round recovered because the
    schema let the malformed shape be expressed. Length + enum narrow the space
    to what the pass can mean; the apply-layer checks stay the joint-constraint
    guard for the multi-exit case an independent enum cannot express (no
    duplicate destination, exact coverage) — the refpin.py division of labor."""

    def schema(project: Project) -> type[BaseModel]:
        out = [b for x, b in pc.group_edges(_groups(project), project.graph) if x == a]
        if not out:  # no labels pass is created for an exit-less group; be total
            return LabelsProposal
        pinned = create_model(
            "EdgeLabelSpec",
            __base__=EdgeLabelSpec,
            dst=(enum_type(out), EdgeLabelSpec.model_fields["dst"]),
        )
        return create_model(
            "LabelsProposal",
            __base__=LabelsProposal,
            labels=(list[pinned], Field(min_length=len(out), max_length=len(out))),  # type: ignore[valid-type]
        )

    return schema


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
                schema=_labels_schema(a),
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
        # ``p["passage"]`` is the Passage NODE: compare its id, never the
        # object (the object==str comparison rendered every per-passage audit
        # prompt with an EMPTY passage list while the schema still demanded
        # the entry — the undiagnosed audit halt of the 2026-07-15 medium
        # validation run, found by PR-5's offline loop fixture)
        ctx = _audit_context(project)
        ctx["passages"] = [p for p in ctx["passages"] if p["passage"].id == pid]
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
    """Pin the residue references: each entry's `dilemma`/`world`/`path` to
    the light-residue convergences' own values and every `entities` ref to
    the entity ids. The apply still enforces the joint (dilemma, world,
    path) constraint the independent enums cannot express
    (pipeline/refpin.py). The fork halves left with the loop (cosmetic-forks
    §6): round 0 is residue only, and the budget rounds pin per site."""
    needs = _light_needs(project)
    entities = entity_ref_ids(project.graph)
    return pin(
        FinalizeProposal,
        "FinalizeProposal",
        {
            ("ResidueSpec", "dilemma"): list(dict.fromkeys(n.dilemma for n in needs)),
            ("ResidueSpec", "world"): list(dict.fromkeys(n.world for n in needs)),
            ("ResidueSpec", "path"): list(dict.fromkeys(p for n in needs for p in n.path_flags)),
            ("ResidueSpec", "entities"): entities,
            ("FollowupSpec", "entities"): entities,
            ("ForkSpec", "entities"): entities,
        },
    )


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
            name="finalize:0",
            role="writer",
            template="polish_finalize.j2",
            schema=finalize_proposal_schema,
            build_context=_finalize_context,
            apply=_finalize_apply,
            skip_if=_finalize_skip,
            # Round 0 is residue — obligations before decoration. Its expand
            # schedules the first budget round; the fork rounds iterate until
            # a terminal (empty) plan, which expands into the passage passes
            # (their count is unknown until every fork has landed).
            expand=lambda project: [_round_spec(1)],
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
