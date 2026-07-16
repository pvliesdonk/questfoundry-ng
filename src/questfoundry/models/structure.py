"""Structure layer: beats, the beat DAG, state flags, intersections."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import NamedTuple

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
    # run-scale parallel world: mirrors a trunk stretch beat-for-beat
    # (structural-depth W3; invariant I15). Deliberately NOT a texture
    # purpose in the word-band sense — arm beats carry their twins'
    # copied annotations and write at the mirrored band, never the
    # short texture band (the asymmetry the mirroring exists to prevent).
    TEXTURE_WORLD = "texture_world"


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


class NarrationScope(StrEnum):
    """A beat's POV/coda register — the per-beat signal FILL reads to know
    whether a beat is narrated inside the story's single Voice POV or may
    step back to a detached coda (design doc 01 §Beat annotations). A
    *limited* beat stays inside the viewpoint the Voice fixes — no mind but
    the narrator's, though psychic distance may still widen to report a
    world fact the narrator could plausibly know. A *wide* beat is a
    sanctioned coda licensed to narrate beyond the viewpoint character's
    horizon — world aftermath once the dilemmas resolve, or a character's
    fate after they exit the story. Populated at GROW pre-freeze as intrinsic
    beat content (settled at the freeze like ``summary``/``scene_type``); a
    beat left unset falls back by purpose (``effective_narration_scope``).
    ``wide`` is the marked exception: epilogue beats default to it, every
    other beat to ``limited``."""

    LIMITED = "limited"
    WIDE = "wide"


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
    # Cosmetic flags this beat grants (cosmetic-forks PR-4): symmetric with
    # `requires_flags`, set by the cosmetic-fork splice on each non-empty
    # rendering's head beat — rendering 0's frozen head included (a legal
    # presentation addition, §2). This is the beat-layer grant, mirroring how
    # a dilemma flag is granted at its path's commit; `choice_grants` projects
    # it onto the rendering's entry edges for the runtime. Engine-set only.
    grants_flags: list[str] = []
    is_ending: bool = False
    temporal_hints: list[TemporalHint] = []  # SEED -> GROW interleave guidance
    flexibility: str = ""  # SEED -> GROW intersection invitation
    # GROW's annotate pass writes these pre-freeze; None means "not
    # annotated" and the effective value is derived (effective_scene_type /
    # effective_narration_scope).
    scene_type: SceneType | None = None
    narration_scope: NarrationScope | None = None
    # GROW's annotate pass, pre-freeze: the character entity whose head
    # narrates this beat (design doc 01 §5; rotating-pov-build.md). None =
    # not annotated — a wildcard at POLISH collapse and in passage_viewpoint,
    # never guessed beat-locally. A `wide` beat carries no viewpoint by
    # construction (the coda register has no head). `interlude` marks a beat
    # of the Voice's marked deviant register (first-person journal etc.);
    # meaningful only with a viewpoint.
    viewpoint: str | None = None
    interlude: bool = False
    # texture_world beats only (structural-depth W3): the trunk beat this
    # arm beat mirrors. Set by the engine splice, never model-proposed —
    # insertion provenance the mirror-parity gate (I15) checks against;
    # it cannot be recomputed unambiguously once several forks share
    # endpoints, which is why it is stored (cf. A14's world-suffixed ids).
    mirrors: str | None = None
    # texture_world beats only (W4, the context lever): the rendering's
    # one-line premise — what differs against the trunk, on any
    # consequence-free axis: place, means, company, or a detail of
    # things and people (01 §6, author clarification 2026-07-14).
    # Declared in the finalize proposal and persisted so FILL's write
    # prompt can name the difference it is grounding — the same
    # persist-for-a-later-pass precedent as Passage.variant_flag (A21).
    texture_premise: str = ""

    @model_validator(mode="after")
    def _class_consistency(self) -> Beat:
        if self.mirrors is not None and self.purpose != StructuralPurpose.TEXTURE_WORLD:
            raise ValueError(f"beat {self.id} carries mirrors but is not a texture_world beat")
        # texture_premise is legal on ANY beat: it names the consequence-free
        # axis a cosmetic-fork rendering varies, and rendering 0 — the trunk
        # segment's own (GROW) beats — carries its premise too (cosmetic-forks
        # §2; premise per rendering). Engine-set only (finalize apply), not a
        # model-set field, so no purpose coupling constrains it.
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

    @model_validator(mode="after")
    def _interlude_needs_viewpoint(self) -> Beat:
        if self.interlude and self.viewpoint is None:
            raise ValueError(f"beat {self.id} is an interlude but names no viewpoint")
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
    every texture purpose maps to micro_beat. ``texture_world`` is
    deliberately absent from the micro set: an arm beat carries its
    twin's *effective* annotations, engine-copied at the splice (I15),
    so the fallback never fires on a valid arm — and a hand-authored
    unannotated one takes the conservative scene default like any
    other, never the short band its trunk twin might not have."""
    if beat.scene_type is not None:
        return beat.scene_type
    if beat.purpose in (
        StructuralPurpose.BRIDGE,
        StructuralPurpose.RESIDUE,
        StructuralPurpose.FALSE_BRANCH,
    ):
        return SceneType.MICRO_BEAT
    return SceneType.SCENE


def effective_narration_scope(beat: Beat) -> NarrationScope:
    """A beat's POV/coda register, resolving the fallback for beats no
    annotate pass reached. GROW's LLM annotation wins; else an ``epilogue``
    beat is the sanctioned world-coda site -> wide; else — every other beat,
    including POLISH-added residue/false-branch/bridge and any unannotated
    narrative/setup beat — is narrated inside the Voice's POV -> limited
    (the conservative default; ``wide`` is always the marked exception)."""
    if beat.narration_scope is not None:
        return beat.narration_scope
    if beat.purpose == StructuralPurpose.EPILOGUE:
        return NarrationScope.WIDE
    return NarrationScope.LIMITED


class PassageViewpoint(NamedTuple):
    viewpoint: str | None  # character entity id; None = no head assigned
    interlude: bool


def passage_viewpoint(beats: Iterable[Beat]) -> PassageViewpoint:
    """A passage's viewpoint head, derived from its member beats — the
    single derivation authority (rotating-pov-build.md), computed at
    consumption and never stored on the passage. The unique
    ``(viewpoint, interlude)`` among beats that carry one; beats without
    (bridge/residue/false-branch, ``wide`` codas) are wildcards. No beat
    annotated -> ``(None, False)``: FILL degrades to the book-wide
    ``Voice.pov`` rule. Uniqueness is invariant I14's guarantee (one head
    per passage, gate G4); a conflict here is an engine bug, not a
    repairable model error."""
    heads = {(b.viewpoint, b.interlude) for b in beats if b.viewpoint is not None}
    if not heads:
        return PassageViewpoint(None, False)
    if len(heads) > 1:
        raise ValueError(f"passage beats disagree on viewpoint (I14): {sorted(heads)}")
    ((viewpoint, interlude),) = heads
    return PassageViewpoint(viewpoint, interlude)


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
    COSMETIC = "cosmetic"  # granted by a cosmetic-fork rendering head
    # (`Beat.grants_flags`), projected onto its entry choice edge (PR-4)


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
