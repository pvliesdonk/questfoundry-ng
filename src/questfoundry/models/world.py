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
