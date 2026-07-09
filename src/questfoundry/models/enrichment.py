"""Enrichment layer (design doc 01 §7): what DRESS adds without changing
the story — art direction, per-entity visual profiles, prioritized
illustration briefs, and the diegetic codex. None of it is graph data:
enrichment describes the story, so it lives beside the graph on the
Project (like the Voice) and ships only through exports.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ArtDirection(BaseModel):
    """Singleton visual contract: how every illustration should look."""

    model_config = ConfigDict(extra="forbid")

    style: str
    palette: str
    influences: list[str] = []
    notes: str = ""


class VisualProfile(BaseModel):
    """Canonical visual facts for one entity, drawn from its base state
    and the finished prose — the reference every brief must agree with."""

    model_config = ConfigDict(extra="forbid")

    entity: str  # entity node id
    appearance: str
    iconography: list[str] = []  # recurring visual motifs


class IllustrationBrief(BaseModel):
    """One prioritized illustration request for a passage."""

    model_config = ConfigDict(extra="forbid")

    passage: str  # passage node id
    priority: int  # 1 = illustrate first
    caption: str
    prompt: str  # image prompt; may reference only established visual facts
    entities: list[str] = []  # entity ids depicted (subset of the passage's)


class CodexEntry(BaseModel):
    """An in-world encyclopedia entry. Spoiler-safe by contract (gate G6):
    reveals nothing the earliest-reaching arc hasn't."""

    model_config = ConfigDict(extra="forbid")

    entity: str  # entity node id
    title: str
    body: str  # markdown


class Enrichment(BaseModel):
    """Everything DRESS produces, bundled for load/save and gate G6."""

    model_config = ConfigDict(extra="forbid")

    direction: ArtDirection | None = None
    profiles: list[VisualProfile] = []
    briefs: list[IllustrationBrief] = []
    codex: list[CodexEntry] = []

    @property
    def empty(self) -> bool:
        return self.direction is None and not (self.profiles or self.briefs or self.codex)
