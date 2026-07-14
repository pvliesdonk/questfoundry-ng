"""Concept layer: the Vision (creative contract) and scope presets.

Scope presets bind the hard budgets that make cost a contract
(design doc 01 §2). Gates check them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from questfoundry.models.structure import SceneType


class ScaffoldShape(BaseModel):
    """Per-scope SEED chain depths (M8): how much pre-commit development,
    payoff, and locked-storyline material a scaffold carries. Bands, not
    points — the model chooses within them; `_scaffold_apply` enforces
    them repairably. Depth was a universal prompt literal before M8, so
    micro and long got the same skeleton."""

    model_config = ConfigDict(frozen=True)

    setup: tuple[int, int]
    pre_commit: tuple[int, int]  # shared chain per branched dilemma
    post_commit: tuple[int, int]  # per path; soft also >= min_payoff_beats (I7)
    locked_lead_in: tuple[int, int]
    locked_aftermath: tuple[int, int]


class ScopePreset(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    # The primary scale anchor (A19): total prose words the scope targets.
    # Every other band below is derived from it via measured ratios and
    # the structural simulation (tests/scale.py) — recorded in design doc
    # 01 §2 so recalibration stays arithmetic.
    words_total: tuple[int, int]
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
    # collapse cap: a passage carries at most this many beats. Every beat
    # has a prose claim but the word budget is per passage, so unbounded
    # collapse crushes deep runs into single passages and added structure
    # mints no pages. Diamonds meter choices; the cap cuts prose.
    passage_beats_max: int
    shape: ScaffoldShape

    def words_for(self, *, intensity: SceneType, ending: bool = False) -> tuple[int, int]:
        """The word band a passage writes toward, from its aggregate prose
        intensity (the highest-ranked scene_type among its beats — see
        ``structure.passage_intensity``) and whether it ends the story.
        A *scene* may rise to the full band; a *sequel* is reactive and
        plainer; a *micro_beat* is the shortest breath — a transition, or
        a texture arm (residue / false-branch fall back to micro_beat,
        which is why texture passages keep exactly their pre-scene_type
        short band: live runs wrote arms at ~0.95x narrative weight, the
        false-choice tax in word form, and the cadence math only closes
        when an arm costs a fraction of a narrative passage). Endings get
        headroom above the scene band — a climax resolution runs long
        (opus endings measured ~600) and must not be squeezed by the
        cadence arithmetic."""
        lo, hi = self.words_per_passage
        if ending:
            return (lo, hi + 100)
        span = hi - lo
        if intensity == SceneType.SCENE:
            return (lo, hi)
        if intensity == SceneType.SEQUEL:
            return (lo, lo + 2 * span // 3)
        return (lo, lo + span // 3)


# The scale table is words-primary (A19, M8): words_total anchors each
# scope; passage/arc-beat bands derive from it via the structural
# simulation (tests/scale.py — synthetic scaffolds through the real
# weave and collapse) padded for live-run inflation (bridges, models
# exceeding minimums: sim ran ~0.75-0.85x of the measured live short).
# micro's shape pins the pre-M8 prompt literals so the golden story and
# every recorded fixture hold unedited; its cap (5) covers the golden
# story's largest hand-authored group.
SCOPE_PRESETS: dict[str, ScopePreset] = {
    p.name: p
    for p in (
        ScopePreset(
            name="micro",
            words_total=(2400, 9000),
            hard_dilemmas=1,
            soft_dilemmas=1,
            locked_dilemmas=1,
            cast_min=3,
            cast_max=5,
            passages_min=8,
            passages_max=24,
            min_payoff_beats=1,
            arc_beats_min=10,
            arc_beats_max=30,
            words_per_passage=(150, 450),
            passage_beats_max=5,
            shape=ScaffoldShape(
                setup=(1, 2),
                pre_commit=(2, 3),
                post_commit=(1, 3),
                locked_lead_in=(1, 3),
                locked_aftermath=(1, 2),
            ),
        ),
        ScopePreset(
            name="short",
            words_total=(9000, 22000),
            hard_dilemmas=1,
            soft_dilemmas=2,
            locked_dilemmas=2,
            cast_min=5,
            cast_max=8,
            passages_min=24,
            passages_max=64,
            min_payoff_beats=2,
            arc_beats_min=32,
            arc_beats_max=78,
            words_per_passage=(150, 500),
            passage_beats_max=3,
            shape=ScaffoldShape(
                setup=(1, 2),
                pre_commit=(3, 4),
                post_commit=(2, 4),
                locked_lead_in=(2, 4),
                locked_aftermath=(1, 3),
            ),
        ),
        ScopePreset(
            name="medium",
            words_total=(20000, 55000),
            hard_dilemmas=2,
            soft_dilemmas=3,
            locked_dilemmas=3,
            cast_min=8,
            cast_max=12,
            passages_min=90,
            passages_max=160,
            min_payoff_beats=3,
            arc_beats_min=80,
            arc_beats_max=150,
            words_per_passage=(200, 550),
            passage_beats_max=3,
            shape=ScaffoldShape(
                setup=(2, 3),
                pre_commit=(4, 6),
                post_commit=(3, 5),
                locked_lead_in=(3, 5),
                locked_aftermath=(2, 3),
            ),
        ),
        ScopePreset(
            name="long",
            words_total=(45000, 95000),
            hard_dilemmas=2,
            soft_dilemmas=4,
            locked_dilemmas=4,
            cast_min=10,
            cast_max=16,
            passages_min=140,
            passages_max=280,
            min_payoff_beats=4,
            arc_beats_min=130,
            arc_beats_max=245,
            words_per_passage=(200, 500),
            passage_beats_max=3,
            shape=ScaffoldShape(
                setup=(2, 3),
                pre_commit=(5, 8),
                post_commit=(4, 7),
                locked_lead_in=(4, 6),
                locked_aftermath=(2, 4),
            ),
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
    # A thin voice makes the writer lean on whatever styled text sits in
    # its prompt (live run 8: rendered facts performed verbatim); the
    # imagery palette and dialogue rules give it somewhere else to reach.
    # Defaults stay empty so author-provided voice.yaml files load unchanged.
    imagery: str = ""
    dialogue: str = ""
    banned: list[str] = []
    notes: str = ""
    # The scheme's marked deviant register in one description — form, person,
    # tense, whose voice ("first-person past-tense journal entries in
    # Eleanor's voice"); empty when the scheme has none. An interlude passage
    # (beats annotated `interlude` at GROW) is written and reviewed against
    # this instead of the book-default pov/tense (rotating-pov-build.md).
    interlude: str = ""


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
