"""Structure layer: beats, the beat DAG, state flags, intersections."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from questfoundry.models.base import Node


class ImpactEffect(StrEnum):
    ADVANCES = "advances"
    REVEALS = "reveals"
    COMPLICATES = "complicates"
    COMMITS = "commits"


class DilemmaImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dilemma: str  # dilemma node id
    effect: ImpactEffect


class BeatClass(StrEnum):
    NARRATIVE = "narrative"  # serves a dilemma; carries impacts + belongs_to
    STRUCTURAL = "structural"  # serves the shape; zero impacts, zero belongs_to


class HintPosition(StrEnum):
    BEFORE_COMMIT = "before_commit"
    AFTER_COMMIT = "after_commit"


class TemporalHint(BaseModel):
    """SEED's guidance to GROW: place this beat before/after another
    dilemma's commit fork. Hints are advisory — GROW drops them (with a
    report note) if they make the interleaving unsatisfiable."""

    model_config = ConfigDict(extra="forbid")

    dilemma: str  # dilemma node id
    position: HintPosition


class StructuralPurpose(StrEnum):
    SETUP = "setup"
    EPILOGUE = "epilogue"
    BRIDGE = "bridge"
    RESIDUE = "residue"  # flag-gated mood-setter (requires_flags is set)
    FALSE_BRANCH = "false_branch"


class SceneType(StrEnum):
    """Swain's beat rhythm — the intrinsic prose-intensity signal a beat
    carries into FILL (design doc 01 §10.3). A *scene* is active conflict
    (goal, obstacle, turn) and earns heightened prose and a fuller word
    band; a *sequel* is the reactive processing between scenes and stays
    plain and shorter; a *micro_beat* is a pure transition, brief and
    low-key. Populated at GROW pre-freeze as an intrinsic beat property
    (why the beat exists), settled at the freeze like ``summary``; a beat
    left unset falls back by purpose (``effective_scene_type``)."""

    SCENE = "scene"
    SEQUEL = "sequel"
    MICRO_BEAT = "micro_beat"


class Beat(Node):
    """A concrete story moment — the atomic unit from SEED onward.

    ``belongs_to`` lives as graph edges, not on the model; class-level
    consistency between impacts and edges is invariant I5, checked by
    the graph layer where the edges are visible.
    """

    summary: str
    beat_class: BeatClass
    purpose: StructuralPurpose | None = None  # structural beats only
    dilemma_impacts: list[DilemmaImpact] = []
    entities: list[str] = []
    requires_flags: list[str] = []  # conditional traversal (residue beats)
    is_ending: bool = False
    temporal_hints: list[TemporalHint] = []  # SEED -> GROW interleave guidance
    flexibility: str = ""  # SEED -> GROW intersection invitation
    # GROW's annotate pass writes this pre-freeze; None means "not
    # annotated" and the effective value is derived (effective_scene_type).
    scene_type: SceneType | None = None

    @model_validator(mode="after")
    def _class_consistency(self) -> Beat:
        if self.beat_class == BeatClass.STRUCTURAL:
            if self.dilemma_impacts:
                raise ValueError(f"structural beat {self.id} must not carry dilemma_impacts")
            if self.purpose is None:
                raise ValueError(f"structural beat {self.id} must declare a purpose")
        else:
            if not self.dilemma_impacts:
                raise ValueError(f"narrative beat {self.id} must carry >=1 dilemma_impact")
            if self.purpose is not None:
                raise ValueError(f"narrative beat {self.id} must not declare a structural purpose")
        return self

    @property
    def commits_dilemmas(self) -> list[str]:
        return [i.dilemma for i in self.dilemma_impacts if i.effect == ImpactEffect.COMMITS]

    @property
    def is_texture(self) -> bool:
        """Texture beats — residue and false-branch arms — are a breath
        of flavor beside the story's forward motion; a passage made only
        of them writes toward the short word band (ScopePreset.words_for).
        ``effective_scene_type`` subsumes this for FILL (both texture
        purposes map to ``micro_beat``); ``is_texture`` stays the
        convenience predicate, consistent with it by construction."""
        return self.purpose in (StructuralPurpose.RESIDUE, StructuralPurpose.FALSE_BRANCH)


# Prose-intensity ranking for aggregating a passage's beats (FILL's
# ScopePreset.words_for / _passage_intensity). SceneType is a StrEnum, so a
# bare max() over its members orders them lexicographically
# ("micro_beat" < "scene" < "sequel") and would let a sequel outrank a
# scene — every aggregation goes through this map's key.
_INTENSITY_RANK: dict[SceneType, int] = {
    SceneType.SCENE: 2,
    SceneType.SEQUEL: 1,
    SceneType.MICRO_BEAT: 0,
}


def intensity_rank(scene_type: SceneType) -> int:
    """Sort key for prose intensity (SCENE > SEQUEL > MICRO_BEAT). Use
    with ``max(..., key=...)`` — never a bare ``max()`` over the enum."""
    return _INTENSITY_RANK[scene_type]


def effective_scene_type(beat: Beat) -> SceneType:
    """A beat's prose intensity, resolving the fallback for beats no
    annotate pass reached. GROW's LLM annotation wins; else a structural
    transition/texture beat (bridge added post-annotate, residue and
    false-branch added at POLISH) is short by construction -> micro_beat;
    else — an unannotated narrative/setup/epilogue beat, only on partial
    coverage — default to scene (heritage R-4b.1: conservative, never
    starves prose). Consistent with ``Beat.is_texture`` by construction:
    every texture purpose maps to micro_beat."""
    if beat.scene_type is not None:
        return beat.scene_type
    if beat.purpose in (
        StructuralPurpose.BRIDGE,
        StructuralPurpose.RESIDUE,
        StructuralPurpose.FALSE_BRANCH,
    ):
        return SceneType.MICRO_BEAT
    return SceneType.SCENE


def passage_intensity(beats: Iterable[Beat]) -> SceneType:
    """A collapsed passage's prose intensity: the highest-ranked
    ``effective_scene_type`` among its beats — a scene beat justifies the
    words and a sequel riding along must not starve it. Aggregation goes
    through ``intensity_rank`` (never a bare ``max`` over the StrEnum).
    Empty -> scene (the safe full band)."""
    beats = list(beats)
    if not beats:
        return SceneType.SCENE
    return max((effective_scene_type(b) for b in beats), key=intensity_rank)


class FlagSource(StrEnum):
    DILEMMA = "dilemma"  # derived from a path consequence, granted at its commit beat
    COSMETIC = "cosmetic"  # granted by a false-branch choice edge


class StateFlag(Node):
    """A boolean world-state marker ("the cartographer knows"), never a
    player action. ``codeword`` is the print projection's player-facing
    word, suggested by DRESS for flags the print export will gate on
    (mini-ADR A12); stable once set."""

    description: str
    source: FlagSource
    path: str | None = None  # dilemma flags: the path whose commit grants it
    codeword: str | None = None

    @model_validator(mode="after")
    def _dilemma_flags_have_path(self) -> StateFlag:
        if self.source == FlagSource.DILEMMA and not self.path:
            raise ValueError(f"dilemma flag {self.id} must name the path that grants it")
        return self


class IntersectionGroup(Node):
    """Co-occurrence declaration: beats from *different* dilemmas share a
    scene (members via in_group edges). Same-dilemma members violate I8."""

    location: str | None = None
    rationale: str = ""
