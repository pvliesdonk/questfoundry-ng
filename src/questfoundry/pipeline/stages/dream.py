"""DREAM — expand the premise into the creative contract (design doc 02)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from questfoundry.graph.validate import run_checks
from questfoundry.models.base import Stage
from questfoundry.models.concept import ContentNotes, Vision
from questfoundry.pipeline.types import PassSpec, StageImpl
from questfoundry.project.io import Project


class DreamProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    genre: str
    subgenre: str = ""
    tone: str
    themes: list[str] = Field(min_length=2, max_length=4)  # the prompt's "2-4", enforced
    audience: str = ""
    content_include: list[str] = []
    content_avoid: list[str] = []
    pov_hint: str = ""


def _context(project: Project) -> dict:
    preset = project.vision.preset
    return {"premise": project.vision.premise, "scope": preset}


def _apply(proposal: DreamProposal, project: Project) -> list[str]:
    # premise and scope are the author's; everything else is the model's
    project.vision = Vision(
        premise=project.vision.premise,
        scope=project.vision.scope,
        genre=proposal.genre,
        subgenre=proposal.subgenre,
        tone=proposal.tone,
        themes=proposal.themes,
        audience=proposal.audience,
        content_notes=ContentNotes(
            include=proposal.content_include, avoid=proposal.content_avoid
        ),
        pov_hint=proposal.pov_hint,
    )
    return [f"vision: {proposal.genre} / {proposal.tone} / {len(proposal.themes)} theme(s)"]


DREAM_STAGE = StageImpl(
    stage=Stage.DREAM,
    passes=(
        PassSpec(
            name="envision",
            role="architect",
            template="dream.j2",
            schema=DreamProposal,
            build_context=_context,
            apply=_apply,
        ),
    ),
    gate=lambda p: run_checks(p.graph, p.vision, Stage.DREAM),
)
