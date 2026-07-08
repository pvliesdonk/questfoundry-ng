"""SEED — triage, scaffold, order (design doc 02).

Three passes sharing gate G2. The proposals carry *content*; the engine
derives all structure mechanically from the proposal's shape: beat
classes, dilemma impacts, `belongs_to` edges, and the intra-dilemma
Y ordering (pre-commit chain → per-path commit → post-commit chain).
Cross-dilemma interleaving is GROW's job (M2) — after SEED the beat
graph is a set of disconnected Y scaffolds plus a setup chain.

M1 scope notes (tracked in docs/STATUS.md): every retained dilemma
explores both answers (locked-dilemma shadows deferred); no dilemma
cuts at triage; no temporal hints or flexibility edges yet.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Consequence, Dilemma, Path
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    DilemmaImpact,
    ImpactEffect,
    StructuralPurpose,
)
from questfoundry.models.world import Entity
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl
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


class TriageProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cut_entities: list[CutSpec] = []
    paths: list[PathSpec] = Field(min_length=2)


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
        "entities": g.nodes_of(Entity),
        "dilemmas": dilemmas,
    }


def _triage_apply(proposal: TriageProposal, project: Project) -> list[str]:
    g = project.graph
    for cut in proposal.cut_entities:
        mutations.set_entity_disposition(g, cut.id, retained=False)
    explored = {p.explores for p in proposal.paths}
    for d in g.nodes_of(Dilemma):
        missing = set(queries.answers_of(g, d.id)) - explored
        if missing:
            raise ApplyError(
                f"dilemma {d.id}: every answer needs a path in M1; missing {sorted(missing)}"
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
        raise ApplyError(f"invalid node in proposal: {e}") from e
    return [
        f"cut: {[c.id for c in proposal.cut_entities] or 'nothing'}",
        f"paths: {', '.join(p.id for p in proposal.paths)}",
    ]


# -- pass 2: scaffold -------------------------------------------------------


class BeatSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    effect: Literal["advances", "reveals", "complicates"] = "advances"
    entities: list[str] = []
    is_ending: bool = False


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


class ScaffoldProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setup: list[BeatSpec] = []
    scaffolds: list[DilemmaScaffold]


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
        dilemmas.append({"dilemma": d, "paths": paths})
    return {
        "vision": project.vision,
        "scope": project.vision.preset,
        "entities": [e for e in g.nodes_of(Entity) if e.retained],
        "dilemmas": dilemmas,
    }


def _make_beat(
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
            entities=spec.entities,
            is_ending=spec.is_ending,
        )
    except ValidationError as e:
        raise ApplyError(f"invalid beat {spec.id}: {e}") from e


def _chain(g, beat_ids: list[str]) -> None:
    for before, after in zip(beat_ids, beat_ids[1:], strict=False):
        mutations.add_ordering(g, before, after)


def _scaffold_apply(proposal: ScaffoldProposal, project: Project) -> list[str]:
    g = project.graph
    covered = {s.dilemma for s in proposal.scaffolds}
    expected = {d.id for d in g.nodes_of(Dilemma)}
    if covered != expected:
        raise ApplyError(
            f"scaffolds must cover every dilemma exactly once; "
            f"missing {sorted(expected - covered)}, unknown {sorted(covered - expected)}"
        )

    for spec in proposal.setup:
        beat = _make_beat(spec, beat_class=BeatClass.STRUCTURAL, purpose=StructuralPurpose.SETUP)
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
                spec,
                beat_class=BeatClass.NARRATIVE,
                impacts=[DilemmaImpact(dilemma=dilemma_id, effect=ImpactEffect(spec.effect))],
            )
            mutations.add_beat(g, beat, path_ids)
        _chain(g, [s.id for s in scaffold.pre_commit])
        last_shared = scaffold.pre_commit[-1].id

        for path_scaffold in scaffold.paths:
            commit = _make_beat(
                path_scaffold.commit,
                beat_class=BeatClass.NARRATIVE,
                impacts=[DilemmaImpact(dilemma=dilemma_id, effect=ImpactEffect.COMMITS)],
            )
            mutations.add_beat(g, commit, [path_scaffold.path])
            mutations.add_ordering(g, last_shared, commit.id)
            for spec in path_scaffold.post_commit:
                beat = _make_beat(
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
    return {
        "vision": project.vision,
        "dilemmas": project.graph.nodes_of(Dilemma),
    }


def _order_apply(proposal: OrderProposal, project: Project) -> list[str]:
    kind_map = {
        "wraps": EdgeKind.WRAPS,
        "serial": EdgeKind.SERIAL,
        "concurrent": EdgeKind.CONCURRENT,
    }
    for rel in proposal.relations:
        mutations.add_dilemma_relation(project.graph, kind_map[rel.kind], rel.a, rel.b)
    return [f"relations: {', '.join(f'{r.a} {r.kind} {r.b}' for r in proposal.relations)}"]


SEED_STAGE = StageImpl(
    stage=Stage.SEED,
    passes=(
        PassSpec(
            name="triage",
            role="architect",
            template="seed_triage.j2",
            schema=TriageProposal,
            build_context=_triage_context,
            apply=_triage_apply,
        ),
        PassSpec(
            name="scaffold",
            role="architect",
            template="seed_scaffold.j2",
            schema=ScaffoldProposal,
            build_context=_scaffold_context,
            apply=_scaffold_apply,
        ),
        PassSpec(
            name="order",
            role="architect",
            template="seed_order.j2",
            schema=OrderProposal,
            build_context=_order_context,
            apply=_order_apply,
        ),
    ),
    gate=lambda p: run_checks(p.graph, p.vision, Stage.SEED),
)
