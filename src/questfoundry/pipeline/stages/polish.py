"""POLISH — compile the frozen beat DAG to passages (design doc 02).

Three passes sharing gate G4:

1. *finalize* — DAG additions only (I9 holds throughout): the LLM
   writes flag-gated residue beats for every light-residue soft
   convergence and may propose false-branch diamonds on long linear
   runs; the engine splices them in. Skipped when nothing is needed.
2. *passages* — the engine computes collapse groups and the complete
   choice topology (endpoints, requires, grants); the LLM contributes
   only words: passage summaries, choice labels, ending titles, and —
   for heavy-residue soft convergences — one variant summary per path
   flag (the engine wires the gated variant passages).
3. *audit* — the prose-feasibility audit: the engine computes each
   passage's possibly-active flags; the LLM marks the flags a passage's
   prose must not address; gate I12 enforces the cap on the rest.

M3 scope notes (tracked in docs/STATUS.md): false branches carry no
cosmetic flags yet; character-arc metadata and the pacing report are
deferred to M4 with their consumer (FILL).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import run_checks
from questfoundry.models.base import Stage
from questfoundry.models.presentation import Choice, Ending, Passage
from questfoundry.models.structure import Beat, BeatClass, StateFlag, StructuralPurpose
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl
from questfoundry.project.io import Project

# -- pass 1: finalize ---------------------------------------------------------


class ResidueSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dilemma: str
    path: str  # whose mood this beat sets; gated on that path's flag
    world: str = ""  # which world's convergence (multi-hard); "" when shared
    id: str
    summary: str
    entities: list[str] = []


class ArmSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    entities: list[str] = []


class FalseBranchSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before: str  # linear beat edge to fork
    after: str
    arms: list[ArmSpec] = Field(min_length=2, max_length=2)


class FinalizeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residue: list[ResidueSpec] = []
    false_branches: list[FalseBranchSpec] = []


def _light_needs(project: Project) -> list[pc.ConvergenceNeed]:
    return [n for n in pc.convergence_needs(project.graph) if n.weight == "light"]


def _long_runs(project: Project) -> list[list[str]]:
    groups = pc.collapse_groups(project.graph)
    return [groups[i] for i in pc.long_linear_runs(groups)]


def _finalize_skip(project: Project) -> str | None:
    if _light_needs(project) or _long_runs(project):
        return None
    return "no light-residue convergences and no long linear runs"


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
    return {"vision": project.vision, "needs": needs, "long_runs": _long_runs(project)}


def _convergence_tails(project: Project, need: pc.ConvergenceNeed) -> dict[str, str]:
    g = project.graph
    tails = {}
    for path in need.path_flags:
        for b in queries.exclusive_beats(g, path):
            if set(need.rejoin) & set(queries.successors(g, b)):
                tails[path] = b
    return tails


def _finalize_apply(proposal: FinalizeProposal, project: Project) -> list[str]:
    g = project.graph
    needs = {(n.dilemma, n.world): n for n in _light_needs(project)}
    covered: set[tuple[str, str]] = set()
    lines = []
    for spec in proposal.residue:
        need = needs.get((spec.dilemma, spec.world))
        if need is None:
            expected = sorted(
                f"dilemma {d}" + (f" in world {w}" if w else "") for d, w in needs
            )
            raise ApplyError(
                f"residue {spec.id}: (dilemma, world) must match exactly one "
                f"convergence of {expected}; got {spec.dilemma!r} in world {spec.world!r}"
            )
        flag = need.path_flags.get(spec.path)
        if flag is None:
            raise ApplyError(
                f"residue {spec.id}: path must be exactly one of "
                f"{sorted(need.path_flags)}; got {spec.path!r}"
            )
        try:
            beat = Beat(
                id=spec.id,
                created_by=Stage.POLISH,
                summary=spec.summary,
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.RESIDUE,
                entities=spec.entities,
                requires_flags=[flag],
            )
        except ValidationError as e:
            raise ApplyError(f"invalid residue beat {spec.id}: {e}") from e
        try:
            pc.insert_residue_beat(g, beat, spec.path, need.rejoin)
        except KeyError as e:  # duplicate beat id (e.g. one slug reused across worlds)
            raise ApplyError(f"residue {spec.id}: {e}") from e
        covered.add((spec.dilemma, spec.world))
        lines.append(f"{spec.id} sets {spec.path}'s mood before {'/'.join(need.rejoin)}")
    missing = set(needs) - covered
    if missing:
        labels = sorted(f"{d}" + (f" (world {w})" if w else "") for d, w in missing)
        raise ApplyError(
            f"every light-residue convergence needs >=1 residue beat; missing {labels}"
        )

    long_run_beats = {b for run in _long_runs(project) for b in run}
    for spec in proposal.false_branches:
        if spec.before not in long_run_beats or spec.after not in long_run_beats:
            raise ApplyError(
                f"false branch at {spec.before} -> {spec.after} is not inside a long linear run"
            )
        try:
            arms = [
                Beat(
                    id=arm.id,
                    created_by=Stage.POLISH,
                    summary=arm.summary,
                    beat_class=BeatClass.STRUCTURAL,
                    purpose=StructuralPurpose.FALSE_BRANCH,
                    entities=arm.entities,
                )
                for arm in spec.arms
            ]
        except ValidationError as e:
            raise ApplyError(f"invalid false-branch arm: {e}") from e
        pc.insert_false_branch(g, arms[0], arms[1], spec.before, spec.after)
        lines.append(f"diamond {arms[0].id} / {arms[1].id} between {spec.before} -> {spec.after}")
    return lines or ["nothing inserted"]


# -- pass 2: passages ---------------------------------------------------------


class VariantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag: str
    id: str
    summary: str


class PassageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group: int
    id: str
    summary: str
    ending_title: str = ""  # required iff the group contains an ending beat
    variants: list[VariantSpec] = []  # required iff the group needs variants


class LabelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    src: int = Field(alias="from")
    dst: int = Field(alias="to")
    label: str


class PassagesProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passages: list[PassageSpec]
    labels: list[LabelSpec]


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
            merged = set(needs.get(beat_id, [])) | set(n.path_flags.values())
            needs[beat_id] = sorted(merged)
    return needs


def _passages_context(project: Project) -> dict:
    g = project.graph
    groups = pc.collapse_groups(g)
    variant_needs = _variant_needs(g)
    rendered = []
    for i, group in enumerate(groups):
        beats = [g.node(b) for b in group]
        needs = [flags for c, flags in variant_needs.items() if c in group]
        rendered.append(
            {
                "index": i,
                "beats": beats,
                "is_ending": pc.ending_beat(g, group) is not None,
                "gate": pc.choice_requires(g, group),
                "variant_flags": needs[0] if needs else [],
            }
        )
    edges = [
        {
            "src": a,
            "dst": b,
            "grants": pc.choice_grants(g, groups[b]),
            "requires": pc.choice_requires(g, groups[b]),
        }
        for a, b in pc.group_edges(groups, g)
    ]
    return {"vision": project.vision, "groups": rendered, "edges": edges}


def _ending_id(passage_id: str) -> str:
    slug = passage_id.split(":", 1)[1]
    return "e-" + slug.removeprefix("p-")


def _passages_apply(proposal: PassagesProposal, project: Project) -> list[str]:
    g = project.graph
    groups = pc.collapse_groups(g)
    edges = pc.group_edges(groups, g)
    variant_needs = _variant_needs(g)

    by_group = {spec.group: spec for spec in proposal.passages}
    if sorted(by_group) != list(range(len(groups))) or len(proposal.passages) != len(groups):
        raise ApplyError(f"passages must cover each group 0..{len(groups) - 1} exactly once")
    labeled = {(spec.src, spec.dst): spec.label for spec in proposal.labels}
    if sorted(labeled) != edges or len(proposal.labels) != len(edges):
        raise ApplyError(f"labels must cover each choice edge exactly once: {edges}")
    for label in labeled.values():
        if not label.strip():
            raise ApplyError("choice labels must be non-empty")

    # passage ids per group; variant groups create one passage per flag
    ids_of_group: dict[int, list[tuple[str, list[str]]]] = {}  # group -> [(passage id, gate)]
    lines = []
    for i, group in enumerate(groups):
        spec = by_group[i]
        needs = [flags for c, flags in variant_needs.items() if c in group]
        ending = pc.ending_beat(g, group)
        entities = pc.group_entities(g, group)

        def build(pid: str, summary: str, *, entities=entities, spec=spec, ending=ending):
            try:
                return Passage(
                    id=pid,
                    created_by=Stage.POLISH,
                    summary=summary,
                    entities=entities,
                    ending=(
                        Ending(id=_ending_id(pid), title=spec.ending_title) if ending else None
                    ),
                )
            except ValidationError as e:
                raise ApplyError(f"invalid passage {pid}: {e}") from e

        if ending and not spec.ending_title.strip():
            raise ApplyError(f"group {i} contains an ending beat; ending_title is required")
        if needs:
            flags = needs[0]
            if sorted(v.flag for v in spec.variants) != flags:
                raise ApplyError(
                    f"group {i} needs one variant per flag {flags} (heavy residue)"
                )
            members: list[tuple[str, list[str]]] = []
            for v in spec.variants:
                mutations.add_passage(g, build(v.id, v.summary), group)
                members.append((v.id, [v.flag]))
            base = members[0][0]
            for vid, _ in members[1:]:
                mutations.add_variant(g, vid, base)
            ids_of_group[i] = members
            lines.append(f"group {i}: variants {', '.join(m[0] for m in members)}")
        else:
            if spec.variants:
                raise ApplyError(f"group {i} needs no variants")
            mutations.add_passage(g, build(spec.id, spec.summary), group)
            ids_of_group[i] = [(spec.id, [])]
            lines.append(f"group {i}: {spec.id} ({len(group)} beat(s))")

    def gate_holdable_from(group: list[str], flag_id: str) -> bool:
        return any(
            grant in group or grant in queries.ancestors(g, group[-1])
            for grant in queries.grant_beats(g, flag_id)
        )

    for a, b in edges:
        base_requires = pc.choice_requires(g, groups[b])
        grants = pc.choice_grants(g, groups[b])
        for src_id, _ in ids_of_group[a]:
            for dst_id, variant_gate in ids_of_group[b]:
                # a variant's gate must be holdable on arcs that reach this
                # source, or the choice could never be taken (I10)
                if any(not gate_holdable_from(groups[a], f) for f in variant_gate):
                    continue
                choice = Choice(
                    label=labeled[(a, b)],
                    requires=sorted({*base_requires, *variant_gate}),
                    grants=grants,
                )
                mutations.add_choice(g, src_id, dst_id, choice)
    lines.append(f"choices: {len(edges)} edge(s) wired")
    return lines


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


POLISH_STAGE = StageImpl(
    stage=Stage.POLISH,
    passes=(
        PassSpec(
            name="finalize",
            role="writer",
            template="polish_finalize.j2",
            schema=FinalizeProposal,
            build_context=_finalize_context,
            apply=_finalize_apply,
            skip_if=_finalize_skip,
        ),
        PassSpec(
            name="passages",
            role="writer",
            template="polish_passages.j2",
            schema=PassagesProposal,
            build_context=_passages_context,
            apply=_passages_apply,
        ),
        PassSpec(
            name="audit",
            role="architect",
            template="polish_audit.j2",
            schema=AuditProposal,
            build_context=_audit_context,
            apply=_audit_apply,
        ),
    ),
    gate=lambda p: run_checks(p.graph, p.vision, Stage.POLISH),
)
