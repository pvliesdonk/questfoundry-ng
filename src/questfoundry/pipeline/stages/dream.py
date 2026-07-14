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
    return {
        "premise": project.vision.premise,
        "scope": preset,
        "pov_hint": project.vision.pov_hint,
    }


def _apply(proposal: DreamProposal, project: Project) -> list[str]:
    # premise, scope, and the authored pov_hint are the author's; everything
    # else is the model's. POV provenance is two fields (Vision docstring):
    # the engine copies `pov_hint` through untouched — two live runs
    # (2026-07-14, gpt-oss:120b and kimi-k2.5) replaced an authored rotating
    # scheme with an invented single-head one, because the prompt never saw
    # the authored value and unconditionally asked the model to "decide" one —
    # while the model's own decision lands in `pov_hint_decided`, freely
    # re-decided on every run/rerun exactly like genre and tone (so a first
    # run's guess never masquerades as an author mandate on a rerun; PR #74
    # review).
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
        pov_hint=project.vision.pov_hint,
        pov_hint_decided=proposal.pov_hint,
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
