"""BRAINSTORM — populate the world: cast and dilemmas (design doc 02)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.graph import mutations
from questfoundry.graph.validate import run_checks
from questfoundry.models.base import Stage
from questfoundry.models.drama import (
    Answer,
    Dilemma,
    DilemmaRole,
    EndingSalience,
    ResidueWeight,
)
from questfoundry.models.world import Entity
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl
from questfoundry.project.io import Project


class EntitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str  # category-prefixed: character:slug, location:slug, ...
    name: str
    concept: str
    pronouns: str = ""
    details: dict[str, str] = {}


class AnswerSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class DilemmaSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    why_it_matters: str
    role: DilemmaRole
    residue_weight: ResidueWeight
    ending_salience: EndingSalience
    answers: list[AnswerSpec] = Field(min_length=2, max_length=2)
    anchored_to: list[str] = Field(min_length=1)


class BrainstormProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entities: list[EntitySpec]
    dilemmas: list[DilemmaSpec]


def _context(project: Project) -> dict:
    return {"vision": project.vision, "scope": project.vision.preset}


def _apply(proposal: BrainstormProposal, project: Project) -> list[str]:
    g = project.graph
    try:
        for spec in proposal.entities:
            mutations.add_entity(
                g,
                Entity(
                    id=spec.id,
                    created_by=Stage.BRAINSTORM,
                    name=spec.name,
                    concept=spec.concept,
                    pronouns=spec.pronouns,
                    base=spec.details,
                ),
            )
        for spec in proposal.dilemmas:
            mutations.add_dilemma(
                g,
                Dilemma(
                    id=spec.id,
                    created_by=Stage.BRAINSTORM,
                    question=spec.question,
                    why_it_matters=spec.why_it_matters,
                    role=spec.role,
                    residue_weight=spec.residue_weight,
                    ending_salience=spec.ending_salience,
                ),
                tuple(
                    Answer(id=a.id, created_by=Stage.BRAINSTORM, text=a.text)
                    for a in spec.answers
                ),
                spec.anchored_to,
            )
    except ValidationError as e:
        raise ApplyError(f"invalid node in proposal: {e}") from e
    return [
        f"cast: {len(proposal.entities)} entities",
        f"dilemmas: {', '.join(d.id for d in proposal.dilemmas)}",
    ]


BRAINSTORM_STAGE = StageImpl(
    stage=Stage.BRAINSTORM,
    passes=(
        PassSpec(
            name="populate",
            role="architect",
            template="brainstorm.j2",
            schema=BrainstormProposal,
            build_context=_context,
            apply=_apply,
        ),
    ),
    gate=lambda p: run_checks(p.graph, p.vision, Stage.BRAINSTORM),
)
