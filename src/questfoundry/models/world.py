"""World layer: entities with base state and flag-activated overlays."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from questfoundry.models.base import Node


class EntityCategory(StrEnum):
    CHARACTER = "character"
    LOCATION = "location"
    OBJECT = "object"
    FACTION = "faction"


class Overlay(BaseModel):
    """Conditional entity state: when all flags in `when` are active,
    `details` add to / override the base state. Overlays compose."""

    model_config = ConfigDict(extra="forbid")

    when: list[str]
    details: dict[str, str]


class ArcPivot(BaseModel):
    """One turn in an entity's arc, anchored to a real beat: from that
    beat on, the entity reads as `becomes` (brief register)."""

    model_config = ConfigDict(extra="forbid")

    beat: str
    becomes: str


class PathEnd(BaseModel):
    """Where the arc lands on one explored path (brief register)."""

    model_config = ConfigDict(extra="forbid")

    path: str
    state: str


class EntityArc(BaseModel):
    """Character-arc metadata, POLISH's last output (design doc 02:
    "begins X, pivots at beat Y, ends Z per path"). FILL consumes it as
    the per-passage arc position — the lever that paces *specific
    aspects* of an entity per scene instead of every fact in every
    scene. Never player-facing."""

    model_config = ConfigDict(extra="forbid")

    begins: str
    pivots: list[ArcPivot] = []
    ends: list[PathEnd] = []


class Entity(Node):
    """A character, location, object, or faction.

    The id's kind prefix IS the category (``character:keeper``) — the
    category namespaces the id (design doc 01 §3).
    """

    name: str
    concept: str
    pronouns: str = ""  # characters: "she/her", "they/them", … — prose is held to it
    base: dict[str, str] = {}
    overlays: list[Overlay] = []
    retained: bool = True  # SEED triage disposition
    arc: EntityArc | None = None  # POLISH arcs pass; FILL-facing only
    # The POV scheme roster (pov-sequences.md): characters only, set by
    # GROW's scheme pass from vision.pov_hint. `pov_head` = a followed
    # head (I17 holds base-register beats to the roster); at most one
    # `interlude_carrier` = the declared deviant register's voice, roster
    # membership not required. Both default False: pre-roster projects
    # load unchanged and I17 skips (graceful degradation).
    pov_head: bool = False
    interlude_carrier: bool = False

    @model_validator(mode="after")
    def _category_prefix(self) -> Entity:
        if self.kind_prefix not in set(EntityCategory):
            raise ValueError(
                f"entity id {self.id!r} must be prefixed with one of "
                f"{[c.value for c in EntityCategory]}"
            )
        return self

    @property
    def category(self) -> EntityCategory:
        return EntityCategory(self.kind_prefix)
