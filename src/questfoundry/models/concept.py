"""Concept layer: the Vision (creative contract) and scope presets.

Scope presets bind the hard budgets that make cost a contract
(design doc 01 §2). Gates check them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScopePreset(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    hard_dilemmas: int
    soft_dilemmas: int
    cast_min: int
    cast_max: int
    passages_min: int
    passages_max: int
    # I7: minimum exclusive post-commit beats per soft path before convergence
    min_payoff_beats: int
    # B4 (advisory): beats per computed arc, checked at gate G3
    arc_beats_min: int
    arc_beats_max: int
    words_per_passage: tuple[int, int]


SCOPE_PRESETS: dict[str, ScopePreset] = {
    p.name: p
    for p in (
        ScopePreset(
            name="micro",
            hard_dilemmas=1,
            soft_dilemmas=1,
            cast_min=3,
            cast_max=5,
            passages_min=15,
            passages_max=25,
            min_payoff_beats=1,
            arc_beats_min=8,
            arc_beats_max=24,
            words_per_passage=(150, 450),
        ),
        ScopePreset(
            name="short",
            hard_dilemmas=1,
            soft_dilemmas=2,
            cast_min=5,
            cast_max=8,
            passages_min=30,
            passages_max=50,
            min_payoff_beats=2,
            arc_beats_min=14,
            arc_beats_max=40,
            words_per_passage=(150, 500),
        ),
        ScopePreset(
            name="medium",
            hard_dilemmas=2,
            soft_dilemmas=2,
            cast_min=7,
            cast_max=10,
            passages_min=60,
            passages_max=90,
            min_payoff_beats=2,
            arc_beats_min=24,
            arc_beats_max=60,
            words_per_passage=(200, 550),
        ),
        ScopePreset(
            name="long",
            hard_dilemmas=2,
            soft_dilemmas=3,
            cast_min=9,
            cast_max=14,
            passages_min=100,
            passages_max=150,
            min_payoff_beats=3,
            arc_beats_min=40,
            arc_beats_max=100,
            words_per_passage=(200, 600),
        ),
    )
}


class ContentNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include: list[str] = []
    avoid: list[str] = []


class Vision(BaseModel):
    """Singleton creative contract produced by DREAM."""

    model_config = ConfigDict(extra="forbid")

    premise: str
    genre: str
    subgenre: str = ""
    tone: str
    themes: list[str] = []
    audience: str = ""
    content_notes: ContentNotes = ContentNotes()
    pov_hint: str = ""
    scope: str = "micro"

    @property
    def preset(self) -> ScopePreset:
        return SCOPE_PRESETS[self.scope]
