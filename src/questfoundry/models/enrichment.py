"""Enrichment layer (design doc 01 §7): what DRESS adds without changing
the story — art direction, per-entity visual profiles, prioritized
illustration briefs, the cover brief, and the diegetic codex. None of it
is graph data: enrichment describes the story, so it lives beside the
graph on the Project (like the Voice) and ships only through exports.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict

# The provider-portable, book-shaped ratio menu (author ratification,
# 2026-07-30): the intersection of what the image providers can actually
# produce, narrowed to the ratios a page or a screen places well. A new
# ratio is a menu change, gated on provider support — never a free string.
Ratio = Literal["2:3", "3:2", "1:1"]
RATIOS: tuple[Ratio, ...] = get_args(Ratio)


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
    # Accessibility metadata, not decoration: the caption is *beside* the
    # picture (both sighted and screen readers get it), the alt text stands
    # *for* it. PDF/UA-1 makes it mandatory — the Typst compiler refuses a
    # build whose image has none. Defaulted so a project dressed before this
    # field existed still loads; the export refuses to place an image without
    # it, and DRESS refuses to propose one.
    alt: str = ""
    ratio: Ratio = "3:2"  # landscape suits a plate over prose in both media


class CoverBrief(BaseModel):
    """The cover illustration request (design doc 04 §4). Not a passage —
    the front-page image, seen before reading, so its prompt is
    atmospheric and spoiler-safe (setting, mood, genre iconography, an
    emblematic object; no plot or ending reveals). Rendered to
    ``art/images/cover.png`` by ``qf illustrate``; the title itself is the
    project's, drawn in the export layout, not baked into the image."""

    model_config = ConfigDict(extra="forbid")

    prompt: str  # image prompt; established visual facts + art direction only
    alt: str = ""  # see IllustrationBrief.alt; the cover is an image like any other


COVER_RATIO: Ratio = "2:3"
"""The cover's ratio is fixed, not per-image data: a book cover is portrait,
and every style places it at the same geometry (design doc 04 §7)."""


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
    cover: CoverBrief | None = None
    profiles: list[VisualProfile] = []
    briefs: list[IllustrationBrief] = []
    codex: list[CodexEntry] = []

    @property
    def empty(self) -> bool:
        return self.direction is None and self.cover is None and not (
            self.profiles or self.briefs or self.codex
        )
