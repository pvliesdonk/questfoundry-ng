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

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import run_checks
from questfoundry.models.base import Stage
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
    # 2 arms = a diamond (fork, rejoin immediately); 1 arm = a sidetrack
    # (the direct edge stays — an optional detour the reader may decline)
    arms: list[ArmSpec] = Field(min_length=1, max_length=2)


class FinalizeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residue: list[ResidueSpec] = []
    false_branches: list[FalseBranchSpec] = []


def _light_needs(project: Project) -> list[pc.ConvergenceNeed]:
    return [n for n in pc.convergence_needs(project.graph) if n.weight == "light"]


def _long_runs(project: Project) -> list[list[str]]:
    groups = pc.collapse_groups(project.graph)
    return [groups[i] for i in pc.long_linear_runs(groups)]


def _cadence(project: Project) -> list[dict]:
    """The words-aware diamond budget per long run (M8): the engine sizes
    the cadence and suggests the seam edges; the model writes the arms
    (and may move a site along its run — the budget is advisory)."""
    runs = pc.collapse_groups(project.graph)
    plan = pc.cadence_plan(project.graph, project.vision.preset)
    return [{"beats": runs[i], "edges": edges} for i, edges in sorted(plan.items())]


def _finalize_skip(project: Project) -> str | None:
    if _light_needs(project) or _cadence(project):
        return None
    return "no light-residue convergences and no cadence budget"


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
    return {"vision": project.vision, "needs": needs, "cadence": _cadence(project)}


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
    long_run_beats = {b for run in _long_runs(project) for b in run}
    lines = []
    for spec in proposal.false_branches:
        if spec.before not in long_run_beats or spec.after not in long_run_beats:
            raise ApplyError(
                f"false branch at {spec.before} -> {spec.after} is not inside a long linear run"
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
            if len(chains) == 1:
                pc.insert_sidetrack(g, chains[0], spec.before, spec.after)
            else:
                pc.insert_false_branch(g, chains[0], chains[1], spec.before, spec.after)
        except (mutations.MutationError, KeyError) as e:
            # Symmetric with the residue path below: a new false-branch beat id
            # colliding with an existing beat raised a bare KeyError that
            # escaped the repair loop entirely (only the residue path caught
            # it). Make it repairable with context.
            raise ApplyError(f"false branch {spec.before} -> {spec.after}: {e}") from e
        if len(chains) == 1:
            lines.append(f"sidetrack {chains[0][0].id} off {spec.before} -> {spec.after}")
        else:
            lines.append(
                f"diamond {chains[0][0].id} / {chains[1][0].id} "
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
        except (mutations.MutationError, KeyError) as e:  # duplicate beat id / bad splice
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
            raise ApplyError(f"group {i} needs no variants")
        mutations.add_passage(g, build(proposal.id, proposal.summary), group)
        return [f"group {i}: {proposal.id} ({len(group)} beat(s))"]

    return apply


def _labels_context(a: int) -> Callable[[Project], dict]:
    def build(project: Project) -> dict:
        g = project.graph
        groups = _groups(project)
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
                }
            )
        return {
            "vision": project.vision,
            "index": a,
            "beats": [g.node(x) for x in groups[a]],
            "dests": dests,
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
    reference destinations that must already exist."""
    g = project.graph
    groups = _groups(project)
    source_groups = sorted({a for a, _ in pc.group_edges(groups, g)})
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


class AuditProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit: list[AuditEntry]


def _audited_passages(project: Project) -> list[tuple[Passage, list[str]]]:
    g = project.graph
    result = []
    for passage in sorted(g.nodes_of(Passage), key=lambda p: p.id):
        flags = pc.active_flags(g, queries.beats_of_passage(g, passage.id))
        if flags:
            result.append((passage, flags))
    return result


def _audit_context(project: Project) -> dict:
    g = project.graph
    flag_text = {f.id: f.description for f in g.nodes_of(StateFlag)}
    return {
        "vision": project.vision,
        "passages": [
            {"passage": p, "active": [(f, flag_text[f]) for f in flags]}
            for p, flags in _audited_passages(project)
        ],
        "cap": 3,
    }


def _audit_apply(proposal: AuditProposal, project: Project) -> list[str]:
    g = project.graph
    expected = {p.id: flags for p, flags in _audited_passages(project)}
    seen = set()
    lines = []
    for entry in proposal.audit:
        # live models drop the id namespace ("p-x" for "passage:p-x");
        # the prefix is unambiguous here, so accept the slug form
        if entry.passage not in expected and f"passage:{entry.passage}" in expected:
            entry.passage = f"passage:{entry.passage}"
        if entry.passage not in expected:
            raise ApplyError(
                f"{entry.passage} is not a passage with active flags; "
                f"audit exactly these ids: {sorted(expected)}"
            )
        if entry.passage in seen:
            raise ApplyError(f"{entry.passage} audited twice")
        seen.add(entry.passage)
        stray = set(entry.irrelevant) - set(expected[entry.passage])
        if stray:
            raise ApplyError(
                f"{entry.passage}: {sorted(stray)} are not active there; "
                f"active flags are {expected[entry.passage]}"
            )
        mutations.set_passage_irrelevant_flags(g, entry.passage, entry.irrelevant)
        if entry.irrelevant:
            lines.append(f"{entry.passage}: don't address {', '.join(entry.irrelevant)}")
    missing = set(expected) - seen
    if missing:
        raise ApplyError(f"audit must cover every listed passage; missing {sorted(missing)}")
    return lines or ["all active flags judged relevant"]


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
            raise ApplyError(f"{entity_id} arced twice")
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
    none was structurally possible and exhausted repairs."""
    needs = _light_needs(project)
    entities = entity_ref_ids(project.graph)
    long_beats = [b for run in _long_runs(project) for b in run]
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
            ("FalseBranchSpec", "before"): long_beats,
            ("FalseBranchSpec", "after"): long_beats,
        },
    )
    if not long_beats:
        schema = create_model(
            "FinalizeProposal",
            __base__=schema,
            false_branches=(list[FalseBranchSpec], Field(default=[], max_length=0)),
        )
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


def audit_proposal_schema(project: Project) -> type[AuditProposal]:
    """Pin `audit[].passage` to the passages that have active flags (both
    exact ids and their unambiguous slugs, which the apply also accepts)
    and `irrelevant[]` to the flags active in those passages. Resolved
    after the passages pass mints the passages (PassSpec.schema_for)."""
    audited = _audited_passages(project)
    ids = sorted(p.id for p, _ in audited)
    passage_refs = ids + [i.split(":", 1)[1] for i in ids]
    flags = list(dict.fromkeys(f for _, fl in audited for f in fl))
    return pin(
        AuditProposal,
        "AuditProposal",
        {("AuditEntry", "passage"): passage_refs, ("AuditEntry", "irrelevant"): flags},
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
