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
    # B1: how many extra dilemmas triage may lock (single explored path —
    # fork-less woven storylines; design doc 01 §4). An allowance, not a floor.
    locked_dilemmas: int
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


# Passage bands recalibrated 2026-07-09 against the first live runs: the
# original numbers were beat counts from the one-beat-one-passage era.
# A band now reflects what the fixed 3+3+3 scaffold structurally yields
# plus POLISH's cadence diamonds; medium is measured (live run 5), the
# others are extrapolated pending runs. Choice-density feel is B6's job,
# not passage inventory. Deeper scaffolds (locked dilemmas, longer Ys)
# will raise these deliberately — see STATUS open items.
SCOPE_PRESETS: dict[str, ScopePreset] = {
    p.name: p
    for p in (
        ScopePreset(
            name="micro",
            hard_dilemmas=1,
            soft_dilemmas=1,
            locked_dilemmas=1,
            cast_min=3,
            cast_max=5,
            passages_min=10,
            passages_max=20,
            min_payoff_beats=1,
            arc_beats_min=8,
            arc_beats_max=24,
            words_per_passage=(150, 450),
        ),
        ScopePreset(
            name="short",
            hard_dilemmas=1,
            soft_dilemmas=2,
            locked_dilemmas=2,
            cast_min=5,
            cast_max=8,
            passages_min=18,
            passages_max=30,
            min_payoff_beats=2,
            arc_beats_min=14,
            arc_beats_max=40,
            words_per_passage=(150, 500),
        ),
        ScopePreset(
            name="medium",
            hard_dilemmas=2,
            soft_dilemmas=2,
            locked_dilemmas=3,
            cast_min=7,
            cast_max=10,
            passages_min=25,
            passages_max=40,
            min_payoff_beats=2,
            arc_beats_min=24,
            arc_beats_max=60,
            words_per_passage=(200, 650),
        ),
        ScopePreset(
            name="long",
            hard_dilemmas=2,
            soft_dilemmas=3,
            locked_dilemmas=4,
            cast_min=9,
            cast_max=14,
            passages_min=35,
            passages_max=60,
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


class Voice(BaseModel):
    """Singleton prose contract created by FILL before any prose — the
    operational descendant of the vision (design doc 01 §2)."""

    model_config = ConfigDict(extra="forbid")

    pov: str
    tense: str
    diction: str  # the design docs' "register"; renamed (pydantic shadow)
    rhythm: str = ""
    banned: list[str] = []
    notes: str = ""


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
