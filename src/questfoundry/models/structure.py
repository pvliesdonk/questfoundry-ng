"""Structure layer: beats, the beat DAG, state flags, intersections."""

from __future__ import annotations

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


class FlagSource(StrEnum):
    DILEMMA = "dilemma"  # derived from a path consequence, granted at its commit beat
    COSMETIC = "cosmetic"  # granted by a false-branch choice edge


class StateFlag(Node):
    """A boolean world-state marker ("the cartographer knows"), never a
    player action. ``codeword`` is set only if SHIP projects it to print."""

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
