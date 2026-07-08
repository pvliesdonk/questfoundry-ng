"""Presentation layer: passages and choices — what the player sees."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from questfoundry.models.base import Node


class Ending(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str


class Choice(BaseModel):
    """Payload of a choice edge: label, gate (requires), grants."""

    model_config = ConfigDict(extra="forbid")

    label: str
    requires: list[str] = []
    grants: list[str] = []


class Passage(Node):
    """A prose container holding one or more beats (grouped_in edges).
    In memory the prose lives on the node; on disk it is a sibling
    markdown file (`prose/<slug>.md`), not part of the passage YAML."""

    summary: str
    entities: list[str] = []
    ending: Ending | None = None
    # POLISH feasibility audit: flags declared irrelevant to this passage
    # (omitted from prose); the remainder must stay within the I12 cap.
    irrelevant_flags: list[str] = []
    prose: str = ""  # markdown; written by FILL through the mutation layer
