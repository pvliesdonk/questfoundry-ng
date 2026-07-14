"""SEED — triage, scaffold, order (design doc 02).

Three passes sharing gate G2. The proposals carry *content*; the engine
derives all structure mechanically from the proposal's shape: beat
classes, dilemma impacts, `belongs_to` edges, and the intra-dilemma
Y ordering (pre-commit chain → per-path commit → post-commit chain).
Cross-dilemma interleaving is GROW's job (M2) — after SEED the beat
graph is a set of disconnected Y scaffolds plus a setup chain.

Triage gives every dilemma a disposition: *branched* (both answers get
paths — the fork the player will choose) or *locked* (one answer gets a
path — a fork-less storyline woven through every playthrough; the other
answer stays a permanent shadow). Branched counts must match the scope's
role budget exactly; up to `locked_dilemmas` may lock (B1).

Scope notes (tracked in docs/STATUS.md): no dilemma cuts at triage —
BRAINSTORM's overgeneration is absorbed entirely by locked dispositions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Consequence, Dilemma, DilemmaRole, Path
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    DilemmaImpact,
    ImpactEffect,
    StructuralPurpose,
    TemporalHint,
)
from questfoundry.models.world import Entity
from questfoundry.pipeline import weave
from questfoundry.pipeline.refpin import entity_ref_ids, pin, retained_entity_ids
from questfoundry.pipeline.types import (
    ApplyError,
    PassSpec,
    StageImpl,
    format_validation_error,
    resolve_entity_ref,
)
from questfoundry.project.io import Project

# -- pass 1: triage ---------------------------------------------------------


class CutSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    reason: str


class ConsequenceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str  # world state ("the mentor is hostile"), never player action


class PathSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = ""
    explores: str  # answer id
    consequences: list[ConsequenceSpec] = Field(min_length=1)


class LockSpec(BaseModel):
    """A locked disposition: the dilemma keeps exactly one path — the
    answer the story canonizes — and the other answer stays a permanent
    shadow (design doc 01 §4)."""

    model_config = ConfigDict(extra="forbid")

    dilemma: str
    reason: str


class TriageProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cut_entities: list[CutSpec] = []
    locked: list[LockSpec] = []
    paths: list[PathSpec] = Field(min_length=2)


def triage_proposal_schema(
    answer_ids: list[str],
    dilemma_ids: list[str] | None = None,
    entity_ids: list[str] | None = None,
) -> type[TriageProposal]:
    """Pin triage's three id-reference fields to enums of the real ids:
    `paths[].explores` to the answer ids (issue #40), `locked[].dilemma`
    to the dilemma ids (its sibling), and `cut_entities[].id` to the
    entity ids.

    Two unrelated strong model families invented readable-but-dangling
    answer slugs at triage and exhausted repairs (Ollama live validation,
    2026-07-11) — an under-specified prompt, not model noise. #40 pinned
    `explores`; a later live `gpt-oss:120b-cloud` run failed the identical
    way on `locked[].dilemma`, so the discipline generalized to every
    reference field (pipeline/refpin.py). The enum states the constraint
    in the schema for every provider, the correction brief names the valid
    ids on a miss, and under grammar-constrained decoding (A20) a dangling
    reference becomes unrepresentable at decode time. `explores` keeps
    graph order because answers are strictly equal (iron rule 3) and an
    ordered list a model could read as ranked must at least not be *our*
    ranking; dilemma/entity ordering carries no such marker.
    """
    resolvers = {
        ("PathSpec", "explores"): answer_ids or [],
        ("LockSpec", "dilemma"): dilemma_ids or [],
        ("CutSpec", "id"): entity_ids or [],
    }
    return pin(TriageProposal, "TriageProposal", resolvers)


def _triage_context(project: Project) -> dict:
    g = project.graph
    dilemmas = []
    for d in g.nodes_of(Dilemma):
        answers = [
            {"id": a, "text": g.node(a).text}  # type: ignore[union-attr]
            for a in queries.answers_of(g, d.id)
        ]
        dilemmas.append({"dilemma": d, "answers": answers})
    return {
        "vision": project.vision,
        "scope": project.vision.preset,
        "budget": project.vision.budget,
        "entities": g.nodes_of(Entity),
        "dilemmas": dilemmas,
    }


def _triage_apply(proposal: TriageProposal, project: Project) -> list[str]:
    g = project.graph
    for cut in proposal.cut_entities:
        mutations.set_entity_disposition(g, cut.id, retained=False)

    answer_dilemma = {
        a: d.id for d in g.nodes_of(Dilemma) for a in queries.answers_of(g, d.id)
    }
    explored_by_dilemma: dict[str, set[str]] = {}
    for spec in proposal.paths:
        did = answer_dilemma.get(spec.explores)
        if did is None:
            raise ApplyError(
                f"path {spec.id} explores unknown answer {spec.explores!r}; "
                f"explores must name one of the brainstormed answer ids: "
                f"{sorted(answer_dilemma)}"
            )
        explored_by_dilemma.setdefault(did, set()).add(spec.explores)

    locked_reasons = {s.dilemma: s.reason for s in proposal.locked}
    unknown = sorted(set(locked_reasons) - set(answer_dilemma.values()))
    if unknown:
        raise ApplyError(
            f"locked names unknown dilemma(s) {unknown}; lock only real dilemmas — "
            f"the ids are {sorted(set(answer_dilemma.values()))}"
        )

    # Every dilemma gets a disposition: branched (both answers explored)
    # or locked (one answer explored, declared with a reason). Branched
    # counts must match the role budget exactly (B1) — the scope table's,
    # coupled to vision.words_target when set (structural-depth W1).
    budget = project.vision.budget
    branched = {DilemmaRole.HARD: 0, DilemmaRole.SOFT: 0}
    for d in g.nodes_of(Dilemma):
        n = len(explored_by_dilemma.get(d.id, set()))
        if n == 2:
            if d.id in locked_reasons:
                raise ApplyError(
                    f"dilemma {d.id} is listed in locked but both its answers "
                    "have paths; a locked dilemma explores exactly one"
                )
            branched[d.role] += 1
        elif n == 1:
            if d.id not in locked_reasons:
                raise ApplyError(
                    f"dilemma {d.id} has a path for only one answer; either add "
                    "the other answer's path (branched) or declare it in locked "
                    "with a reason"
                )
        else:
            raise ApplyError(
                f"dilemma {d.id} has no path; branch it (two paths) or lock it "
                "(one path + a locked entry)"
            )
    want = {DilemmaRole.HARD: budget.hard, DilemmaRole.SOFT: budget.soft}
    for role, count in branched.items():
        if count != want[role]:
            raise ApplyError(
                f"exactly {want[role]} {role.value} dilemma(s) must be branched "
                f"(both answers explored); got {count}"
            )
    if len(locked_reasons) > budget.locked:
        raise ApplyError(
            f"this project allows at most {budget.locked} locked "
            f"dilemma(s); got {len(locked_reasons)}"
        )

    try:
        for spec in proposal.paths:
            mutations.add_path(
                g,
                Path(id=spec.id, created_by=Stage.SEED, name=spec.name),
                spec.explores,
                [
                    Consequence(id=c.id, created_by=Stage.SEED, text=c.text)
                    for c in spec.consequences
                ],
            )
    except ValidationError as e:
        raise ApplyError(f"invalid node in proposal: {format_validation_error(e)}") from e
    return [
        f"cut: {[c.id for c in proposal.cut_entities] or 'nothing'}",
        f"paths: {', '.join(p.id for p in proposal.paths)}",
        f"locked: {', '.join(sorted(locked_reasons)) or 'nothing'}",
    ]


# -- pass 2: scaffold -------------------------------------------------------


class HintSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dilemma: str
    position: Literal["before_commit", "after_commit"]


class BeatSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    effect: Literal["advances", "reveals", "complicates"] = "advances"
    entities: list[str] = []
    is_ending: bool = False
    hints: list[HintSpec] = []  # GROW interleave guidance ("before D1's commit")
    flexibility: str = ""  # intersection invitation ("the docks could be the market")


class PathScaffold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    commit: BeatSpec
    post_commit: list[BeatSpec] = Field(min_length=1)


class DilemmaScaffold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dilemma: str
    pre_commit: list[BeatSpec] = Field(min_length=1)
    paths: list[PathScaffold] = Field(min_length=2, max_length=2)


class LockedScaffold(BaseModel):
    """A locked dilemma's storyline: a fork-less chain every player
    experiences — lead-in, one resolution beat (the canonized answer
    settles), aftermath (design doc 01 §4)."""

    model_config = ConfigDict(extra="forbid")

    dilemma: str
    path: str
    lead_in: list[BeatSpec] = Field(min_length=1)
    resolution: BeatSpec
    aftermath: list[BeatSpec] = Field(min_length=1)


class ScaffoldProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setup: list[BeatSpec] = []
    scaffolds: list[DilemmaScaffold]
    locked_scaffolds: list[LockedScaffold] = []


def _scaffold_context(project: Project) -> dict:
    g = project.graph
    dilemmas = []
    for d in g.nodes_of(Dilemma):
        paths = []
        for path_id in queries.explored_paths(g, d.id):
            answer_id = g.out_ids(path_id, EdgeKind.EXPLORES)[0]
            paths.append(
                {
                    "id": path_id,
                    "answer": g.node(answer_id).text,  # type: ignore[union-attr]
                    "consequences": [
                        g.node(c).text  # type: ignore[union-attr]
                        for c in g.out_ids(path_id, EdgeKind.HAS_CONSEQUENCE)
                    ],
                }
            )
        dilemmas.append({"dilemma": d, "paths": paths, "locked": len(paths) == 1})
    return {
        "vision": project.vision,
        "scope": project.vision.preset,
        "entities": [e for e in g.nodes_of(Entity) if e.retained],
        "dilemmas": dilemmas,
    }


def _make_beat(
    g,
    spec: BeatSpec,
    *,
    beat_class: BeatClass,
    purpose: StructuralPurpose | None = None,
    impacts: list[DilemmaImpact] | None = None,
) -> Beat:
    try:
        return Beat(
            id=spec.id,
            created_by=Stage.SEED,
            summary=spec.summary,
            beat_class=beat_class,
            purpose=purpose,
            dilemma_impacts=impacts or [],
            entities=[resolve_entity_ref(g, e) for e in spec.entities],
            is_ending=spec.is_ending,
            temporal_hints=[
                TemporalHint(dilemma=h.dilemma, position=h.position) for h in spec.hints
            ],
            flexibility=spec.flexibility,
        )
    except ValidationError as e:
        raise ApplyError(f"invalid beat {spec.id}: {format_validation_error(e)}") from e


def _chain(g, beat_ids: list[str]) -> None:
    for before, after in zip(beat_ids, beat_ids[1:], strict=False):
        mutations.add_ordering(g, before, after)


def _scaffold_apply(proposal: ScaffoldProposal, project: Project) -> list[str]:
    g = project.graph
    branched_ids = set(queries.branched_dilemmas(g))
    locked_ids = set(queries.locked_dilemmas(g))
    covered = {s.dilemma for s in proposal.scaffolds}
    if covered != branched_ids:
        raise ApplyError(
            f"scaffolds must cover every branched dilemma exactly once; "
            f"missing {sorted(branched_ids - covered)}, "
            f"unknown or locked {sorted(covered - branched_ids)}"
        )
    covered_locked = {s.dilemma for s in proposal.locked_scaffolds}
    if covered_locked != locked_ids:
        raise ApplyError(
            f"locked_scaffolds must cover every locked dilemma exactly once; "
            f"missing {sorted(locked_ids - covered_locked)}, "
            f"unknown or branched {sorted(covered_locked - locked_ids)}"
        )

    expected = branched_ids | locked_ids
    all_specs = list(proposal.setup) + [
        s
        for scaffold in proposal.scaffolds
        for s in (
            *scaffold.pre_commit,
            *(b for p in scaffold.paths for b in (p.commit, *p.post_commit)),
        )
    ]
    locked_specs = [
        s
        for scaffold in proposal.locked_scaffolds
        for s in (*scaffold.lead_in, scaffold.resolution, *scaffold.aftermath)
    ]
    # Shape rules are collected and raised together: one violation per
    # repair round is whack-a-mole — the model fixes the named arm while
    # a sibling arm has the same defect, and burns its rounds one arm at
    # a time (live run 7 lost SEED to exactly this).
    problems: list[str] = []
    for spec in all_specs + locked_specs:
        for hint in spec.hints:
            if hint.dilemma not in expected:
                problems.append(f"beat {spec.id} hint names unknown dilemma {hint.dilemma!r}")
    for spec in locked_specs:
        if spec.is_ending:
            problems.append(
                f"beat {spec.id} sets is_ending but belongs to a locked storyline — "
                "a locked dilemma never ends the story; it weaves through it (I6)"
            )

    # Ending placement is decided here but otherwise only caught at GROW's
    # gate, unrepairably: a hard path's chain tail must be an ending (the
    # weave keeps the climax fork's and demotes the rest — I6), an ending
    # anywhere else contradicts continuation, and a soft path needs its
    # payoff beats (I7) before rejoining.
    preset = project.vision.preset
    shape = preset.shape

    def in_band(count: int, band: tuple[int, int], what: str) -> None:
        lo, hi = band
        if not lo <= count <= hi:
            problems.append(
                f"{what} has {count} beat(s); scope {preset.name!r} wants {lo}-{hi}"
            )

    in_band(len(proposal.setup), shape.setup, "setup")
    for scaffold in proposal.locked_scaffolds:
        in_band(
            len(scaffold.lead_in), shape.locked_lead_in, f"{scaffold.dilemma}'s lead_in"
        )
        in_band(
            len(scaffold.aftermath),
            shape.locked_aftermath,
            f"{scaffold.dilemma}'s aftermath",
        )
    for scaffold in proposal.scaffolds:
        in_band(
            len(scaffold.pre_commit), shape.pre_commit, f"{scaffold.dilemma}'s pre_commit"
        )
        for path_scaffold in scaffold.paths:
            in_band(
                len(path_scaffold.post_commit),
                shape.post_commit,
                f"{path_scaffold.path}'s post_commit",
            )
    for scaffold in proposal.scaffolds:
        dilemma = g.node(scaffold.dilemma)
        assert isinstance(dilemma, Dilemma)
        hard = dilemma.role == DilemmaRole.HARD
        tails = {p.post_commit[-1].id for p in scaffold.paths} if hard else set()
        for path_scaffold in scaffold.paths:
            if hard and not path_scaffold.post_commit[-1].is_ending:
                problems.append(
                    f"hard dilemma {scaffold.dilemma}: {path_scaffold.path}'s final "
                    f"post-commit beat {path_scaffold.post_commit[-1].id} must set "
                    f"is_ending: true — hard paths never rejoin; their chains resolve "
                    f"the story (I6)"
                )
            if not hard and len(path_scaffold.post_commit) < preset.min_payoff_beats:
                problems.append(
                    f"soft dilemma {scaffold.dilemma}: {path_scaffold.path} has "
                    f"{len(path_scaffold.post_commit)} post-commit payoff beat(s); "
                    f"scope {preset.name!r} requires >= {preset.min_payoff_beats} (I7)"
                )
        for spec in (
            *scaffold.pre_commit,
            *(b for p in scaffold.paths for b in (p.commit, *p.post_commit)),
        ):
            if spec.is_ending and spec.id not in tails:
                problems.append(
                    f"beat {spec.id} sets is_ending but is not a hard path's final "
                    f"post-commit beat — the story continues after it (I6)"
                )
    for spec in proposal.setup:
        if spec.is_ending:
            problems.append(f"setup beat {spec.id} must not be an ending")
    if problems:
        raise ApplyError(
            "fix all of the following in one pass, changing nothing else:\n- "
            + "\n- ".join(problems)
        )

    for spec in proposal.setup:
        beat = _make_beat(g, spec, beat_class=BeatClass.STRUCTURAL, purpose=StructuralPurpose.SETUP)
        mutations.add_beat(g, beat, [])
    _chain(g, [s.id for s in proposal.setup])

    applied = [f"setup: {len(proposal.setup)} beat(s)"]
    for scaffold in proposal.scaffolds:
        dilemma_id = scaffold.dilemma
        path_ids = [p.path for p in scaffold.paths]
        if sorted(path_ids) != queries.explored_paths(g, dilemma_id):
            raise ApplyError(
                f"scaffold for {dilemma_id} must name exactly its explored paths "
                f"{queries.explored_paths(g, dilemma_id)}, got {sorted(path_ids)}"
            )
        for spec in scaffold.pre_commit:
            beat = _make_beat(
                g,
                spec,
                beat_class=BeatClass.NARRATIVE,
                impacts=[DilemmaImpact(dilemma=dilemma_id, effect=ImpactEffect(spec.effect))],
            )
            mutations.add_beat(g, beat, path_ids)
        _chain(g, [s.id for s in scaffold.pre_commit])
        last_shared = scaffold.pre_commit[-1].id

        for path_scaffold in scaffold.paths:
            commit = _make_beat(
                g,
                path_scaffold.commit,
                beat_class=BeatClass.NARRATIVE,
                impacts=[DilemmaImpact(dilemma=dilemma_id, effect=ImpactEffect.COMMITS)],
            )
            mutations.add_beat(g, commit, [path_scaffold.path])
            mutations.add_ordering(g, last_shared, commit.id)
            for spec in path_scaffold.post_commit:
                beat = _make_beat(
                    g,
                    spec,
                    beat_class=BeatClass.NARRATIVE,
                    impacts=[
                        DilemmaImpact(dilemma=dilemma_id, effect=ImpactEffect(spec.effect))
                    ],
                )
                mutations.add_beat(g, beat, [path_scaffold.path])
            _chain(g, [commit.id, *[s.id for s in path_scaffold.post_commit]])
        applied.append(
            f"{dilemma_id}: Y with {len(scaffold.pre_commit)} shared beat(s), "
            f"{' + '.join(str(1 + len(p.post_commit)) for p in scaffold.paths)} exclusive"
        )

    for scaffold in proposal.locked_scaffolds:
        explored = queries.explored_paths(g, scaffold.dilemma)
        if [scaffold.path] != explored:
            raise ApplyError(
                f"locked scaffold for {scaffold.dilemma} must name its explored "
                f"path {explored}, got {scaffold.path!r}"
            )
        for spec in scaffold.lead_in:
            beat = _make_beat(
                g,
                spec,
                beat_class=BeatClass.NARRATIVE,
                impacts=[
                    DilemmaImpact(dilemma=scaffold.dilemma, effect=ImpactEffect(spec.effect))
                ],
            )
            mutations.add_beat(g, beat, [scaffold.path])
        resolution = _make_beat(
            g,
            scaffold.resolution,
            beat_class=BeatClass.NARRATIVE,
            impacts=[DilemmaImpact(dilemma=scaffold.dilemma, effect=ImpactEffect.COMMITS)],
        )
        mutations.add_beat(g, resolution, [scaffold.path])
        for spec in scaffold.aftermath:
            beat = _make_beat(
                g,
                spec,
                beat_class=BeatClass.NARRATIVE,
                impacts=[
                    DilemmaImpact(dilemma=scaffold.dilemma, effect=ImpactEffect(spec.effect))
                ],
            )
            mutations.add_beat(g, beat, [scaffold.path])
        _chain(
            g,
            [
                *(s.id for s in scaffold.lead_in),
                resolution.id,
                *(s.id for s in scaffold.aftermath),
            ],
        )
        applied.append(
            f"{scaffold.dilemma} (locked): chain of "
            f"{len(scaffold.lead_in) + 1 + len(scaffold.aftermath)} beat(s)"
        )
    return applied


# -- pass 3: order ----------------------------------------------------------


class RelationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["wraps", "serial", "concurrent"]
    a: str
    b: str


class OrderProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relations: list[RelationSpec]


def _order_context(project: Project) -> dict:
    # Dispositions exist by now (triage ran first) and the relation rules
    # depend on them — "the story ends at a branched hard resolution"
    # is unstatable without saying which dilemmas are branched.
    g = project.graph
    locked = set(queries.locked_dilemmas(g))
    return {
        "vision": project.vision,
        "dilemmas": [
            {"dilemma": d, "locked": d.id in locked} for d in g.nodes_of(Dilemma)
        ],
    }


def _order_apply(proposal: OrderProposal, project: Project) -> list[str]:
    kind_map = {
        "wraps": EdgeKind.WRAPS,
        "serial": EdgeKind.SERIAL,
        "concurrent": EdgeKind.CONCURRENT,
    }
    for rel in proposal.relations:
        mutations.add_dilemma_relation(project.graph, kind_map[rel.kind], rel.a, rel.b)
    # Relations can be pairwise-acyclic yet jointly unsatisfiable: the
    # story must END at a branched hard dilemma's resolution, so a serial
    # chain extending past every hard resolve leaves no feasible climax
    # (live run 8 wedged GROW exactly this way — serial(hard A, hard B)
    # plus serial(hard B, locked chain)). Probe the weave here, where a
    # repair round can fix it; GROW's WeaveError is unrepairable.
    try:
        weave.plan(project.graph)
    except weave.WeaveError as e:
        raise ApplyError(
            f"these relations leave no valid interleaving ({e}). The story "
            "must end at a branched HARD dilemma's resolution — nothing may "
            "be forced after every hard dilemma resolves. Drop or rethink "
            "the relation(s) that chain material after the last hard commit "
            "(a locked storyline serial-after a hard dilemma is the usual "
            "culprit; use wraps or concurrent instead)"
        ) from e
    return [f"relations: {', '.join(f'{r.a} {r.kind} {r.b}' for r in proposal.relations)}"]


def scaffold_proposal_schema(project: Project) -> type[ScaffoldProposal]:
    """Pin scaffold's reference fields: each `dilemma` to its disposition's
    ids (branched vs locked), each `path` to the explored paths of that
    disposition, every `BeatSpec.entities` ref to the entity ids, and every
    `HintSpec.dilemma` to a known dilemma (pipeline/refpin.py)."""
    g = project.graph
    branched = queries.branched_dilemmas(g)
    locked = queries.locked_dilemmas(g)
    resolvers = {
        ("DilemmaScaffold", "dilemma"): branched,
        ("PathScaffold", "path"): [p for d in branched for p in queries.explored_paths(g, d)],
        ("LockedScaffold", "dilemma"): locked,
        ("LockedScaffold", "path"): [p for d in locked for p in queries.explored_paths(g, d)],
        ("BeatSpec", "entities"): entity_ref_ids(g),
        ("HintSpec", "dilemma"): branched + locked,
    }
    return pin(ScaffoldProposal, "ScaffoldProposal", resolvers)


def order_proposal_schema(project: Project) -> type[OrderProposal]:
    """Pin order's `relations[].a`/`.b` to the dilemma ids."""
    dilemma_ids = [d.id for d in project.graph.nodes_of(Dilemma)]
    return pin(
        OrderProposal,
        "OrderProposal",
        {("RelationSpec", "a"): dilemma_ids, ("RelationSpec", "b"): dilemma_ids},
    )


def _seed_passes(project: Project) -> tuple[PassSpec, ...]:
    # Every pass's schema pins its id-reference fields to enums of the ids
    # that exist when the pass runs (graph order — pipeline/refpin.py), so
    # a dangling reference can't be emitted and kept-pass replay / ledger
    # resume revalidate against the same enums the proposal was accepted
    # under. Triage's references (answers, dilemmas, entities) all exist at
    # SEED start, so its schema is built eagerly here; scaffold and order
    # reference triage's own writes (branched/locked dispositions, explored
    # paths), so they pass a *callable* schema the runner resolves at
    # pass-run time — after triage has mutated the graph (PassSpec.schema_for).
    g = project.graph
    dilemmas = g.nodes_of(Dilemma)
    dilemma_ids = [d.id for d in dilemmas]
    answer_ids = [a for d in dilemmas for a in queries.answers_of(g, d.id)]
    # cut_entities[].id is validated by exact membership (set_entity_disposition),
    # so pin it to exact ids — not the bare-slug-inclusive resolve set.
    entity_ids = retained_entity_ids(g)
    return (
        PassSpec(
            name="triage",
            role="architect",
            template="seed_triage.j2",
            schema=triage_proposal_schema(answer_ids, dilemma_ids, entity_ids),
            build_context=_triage_context,
            apply=_triage_apply,
        ),
        PassSpec(
            name="scaffold",
            role="architect",
            template="seed_scaffold.j2",
            schema=scaffold_proposal_schema,
            build_context=_scaffold_context,
            apply=_scaffold_apply,
        ),
        PassSpec(
            name="order",
            role="architect",
            template="seed_order.j2",
            schema=order_proposal_schema,
            build_context=_order_context,
            apply=_order_apply,
        ),
    )


SEED_STAGE = StageImpl(
    stage=Stage.SEED,
    passes=_seed_passes,
    gate=lambda p: run_checks(p.graph, p.vision, Stage.SEED),
)
