"""The shared style layer for the styled exports (design doc 04 §7).

What print and screen genuinely share is not furniture — it is the
**accessibility contract**: a contrast-checked colour ramp, the ratio menu
DRESS may choose from, and the placement rule that turns a ratio into a
frame. Those live here. The furniture itself (running heads, title
screens) stays per-medium in `gamebook.py` and `html.py`, parameterized by
the small style records below.

The ramps are data, and `check_ramp` is what makes them trustworthy: every
role carries the WCAG floor its use demands, and a ramp that misses one
fails the build rather than shipping an unreadable page. The floors are
measured against the style's own page colour, so a light print style and a
dark screen style are held to the same standard without sharing a palette.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from questfoundry.models.enrichment import COVER_RATIO, RATIOS, Ratio


def ratio_value(ratio: str) -> float:
    """Width / height. Every consumer needs the number, and parsing the
    menu string in three places is how the three drift apart."""
    w, h = ratio.split(":")
    return float(w) / float(h)


# -- contrast ------------------------------------------------------------------

# WCAG 2.2 floors by role, measured against the style's page colour. Body
# ink is held well above the 4.5:1 minimum because a whole book is read at
# that size; `rule` covers non-text UI (borders, the focus ring) at 1.4.11's
# 3:1; `muted` and `accent` carry text at 1.4.3's 4.5:1.
CONTRAST_FLOORS: dict[str, float] = {"ink": 7.0, "muted": 4.5, "accent": 4.5, "rule": 3.0}


@dataclass(frozen=True)
class Ramp:
    """One style's colour roles as sRGB hex. Never colour alone (WCAG
    1.4.1): every role here is redundant with a word or a glyph in the
    templates — the ramp makes a page legible, it never carries meaning."""

    page: str  # the background everything else is measured against
    ink: str  # body text
    muted: str  # captions, running heads, secondary UI text
    accent: str  # codewords, section numerals
    rule: str  # borders, dividers, the focus ring

    def role(self, name: str) -> str:
        return getattr(self, name)


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def parse_hex(colour: str) -> tuple[int, int, int]:
    text = colour.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(
            f"colour {colour!r} is not a 6-digit sRGB hex — write it as '#RRGGBB'"
        )
    try:
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except ValueError:
        raise ValueError(
            f"colour {colour!r} is not a 6-digit sRGB hex — write it as '#RRGGBB'"
        ) from None


def relative_luminance(colour: str) -> float:
    r, g, b = parse_hex(colour)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    lo, hi = sorted((la, lb))
    return (hi + 0.05) / (lo + 0.05)


def check_ramp(ramp: Ramp, *, where: str) -> list[str]:
    """Every role against its floor. Returns build-failing problems, each
    naming the measured ratio, the floor it missed, and the direction to
    move — an accent that lands outside the ramp is a fixable colour, not
    a mystery."""
    problems: list[str] = []
    for role, floor in CONTRAST_FLOORS.items():
        measured = contrast_ratio(ramp.role(role), ramp.page)
        if measured < floor:
            lighten = relative_luminance(ramp.role(role)) < relative_luminance(ramp.page)
            direction = "lighten" if not lighten else "darken"
            problems.append(
                f"{where}: {role} {ramp.role(role)} on page {ramp.page} measures "
                f"{measured:.2f}:1, below the {floor}:1 floor — {direction} the page or "
                f"move {role} further from it until it clears {floor}:1"
            )
    return problems


# Paper: near-white stock, near-black ink; the accent is a deep ink-blue
# that reads as ink at codeword size and survives greyscale printing.
PAPERBACK_RAMP = Ramp(
    page="#FBF9F4", ink="#17181A", muted="#5C5E63", accent="#1F3C63", rule="#6E7075"
)

# Screen: the dark reading surface the current player already uses, with
# every role re-measured against it.
SHELF_RAMP = Ramp(
    page="#14171A", ink="#E4E0D6", muted="#9AA6AD", accent="#B9C9D6", rule="#7C8B94"
)

# The light reading mode 1d offers beside the dark one; the same roles,
# measured against paper-on-screen.
SHELF_LIGHT_RAMP = Ramp(
    page="#F4F2EC", ink="#1A1B1D", muted="#55585C", accent="#1F3C63", rule="#6B6E73"
)

# 1b reads as a bound edition rather than a mass-market paperback: a
# cooler sheet and an oxblood accent, the traditional second colour of a
# cloth-bound book.
BOUND_RAMP = Ramp(
    page="#F7F5F0", ink="#191715", muted="#57534E", accent="#6E1F2A", rule="#6A645E"
)

# 1c is type-driven, so its accent has to hold at display sizes as well as
# at codeword size: a saturated rust against a flatter, brighter sheet.
COMPENDIUM_RAMP = Ramp(
    page="#F2F1EC", ink="#111111", muted="#54524E", accent="#8A3B12", rule="#666158"
)


# -- placement ------------------------------------------------------------------


@dataclass(frozen=True)
class Placement:
    """How one ratio is framed in one medium. `width` is a fraction of the
    text measure: a landscape plate fills it, a portrait plate is capped so
    a tall frame does not swallow the page. Height always follows from the
    ratio — letterboxing distorts, and a distorted plate is a bug."""

    width: float


# A5 at the paperback measure: 3:2 and 1:1 sit at the measure, 2:3 is
# capped so a portrait plate leaves prose on the page with it.
PRINT_PLACEMENT: dict[str, Placement] = {
    "3:2": Placement(width=1.0),
    "1:1": Placement(width=0.72),
    "2:3": Placement(width=0.56),
}

# On screen the measure is already narrow and the page scrolls, so a
# portrait plate costs nothing but its own height.
SCREEN_PLACEMENT: dict[str, Placement] = {
    "3:2": Placement(width=1.0),
    "1:1": Placement(width=0.82),
    "2:3": Placement(width=0.66),
}


# -- styles ---------------------------------------------------------------------


# The axes the three print directions actually differ on. Each of these
# earned its place by varying across the built styles — none is a knob
# added for a style that might exist later.
SectionHead = Literal["inline", "margin"]
"""Where a section's numeral sits: in the text block (1a, 1c) or out in a
wide outer margin (1b), where its codewords join it."""

InstructionForm = Literal["hanging", "italic-block"]
"""How an instruction is set: hanging-indent with the turn-to number bold
at the right margin (1a, 1c), or an indented italic block whose number
stays inline at full size (1b)."""

CoverTreatment = Literal["full-bleed", "band"]
"""A whole page of art (1a, 1b) versus a top-anchored band with the title
set beneath it (1c)."""

FrontMatter = Literal["plain", "heavy"]
"""A quiet centred title page (1a, 1b) versus display type carrying the
front matter (1c)."""

TitleScreen = Literal["shelf", "room"]
"""The HTML way in: the cover as an inset object standing on a shelf (1d)
or filled to the viewport with the title set over it (1e)."""


@dataclass(frozen=True)
class PrintStyle:
    """A print direction: page geometry, type, its ramp, and the four
    furniture choices above. Lengths are millimetres, type sizes points —
    the units Typst takes."""

    name: str
    page_width: float
    page_height: float
    margin_inside: float
    margin_outside: float
    margin_top: float
    margin_bottom: float
    body_size: float
    leading: float  # em
    section_size: float
    ramp: Ramp
    placement: dict[str, Placement]
    running_heads: bool
    section_per_page: bool
    section_head: SectionHead = "inline"
    instruction_form: InstructionForm = "hanging"
    cover_treatment: CoverTreatment = "full-bleed"
    # Only meaningful when `cover_treatment` is "band": the fraction of the
    # page height the band occupies. The layout sets it, and `cover_floor`
    # scales the resolution floor by it — one number, two readers.
    cover_band_fraction: float = 0.0
    front_matter: FrontMatter = "plain"
    # Only meaningful when `section_head` is "margin": the width of the
    # marginal column and the gutter between it and the text block. They
    # must fit inside `margin_outside`, which `check_geometry` enforces.
    margin_note_width: float = 0.0
    margin_note_gutter: float = 0.0

    @property
    def measure_mm(self) -> float:
        return self.page_width - self.margin_inside - self.margin_outside


def check_geometry(style: PrintStyle) -> list[str]:
    """A marginal column that does not fit its margin silently overprints
    the page edge, which no test of the *ramp* would catch and no reader
    of the Typst would notice. Checked like the ramp: build-failing, with
    the numbers and the way out."""
    problems = []
    if style.section_head == "margin":
        needed = style.margin_note_width + style.margin_note_gutter
        if style.margin_note_width <= 0:
            problems.append(
                f"print style {style.name!r} sets its section head in the margin but "
                "margin_note_width is 0 — give the marginal column a width"
            )
        elif needed >= style.margin_outside:
            problems.append(
                f"print style {style.name!r}: the marginal column needs "
                f"{needed}mm (width {style.margin_note_width} + gutter "
                f"{style.margin_note_gutter}) but margin_outside is only "
                f"{style.margin_outside}mm — widen the outer margin or narrow the column"
            )
    if style.measure_mm <= 0:
        problems.append(
            f"print style {style.name!r}: the margins leave no text measure on a "
            f"{style.page_width}mm page — narrow them"
        )
    return problems


@dataclass(frozen=True)
class ScreenStyle:
    """An HTML player direction. `measure_ch` is the reading measure in
    characters — a ch-based measure is what lets the page reflow to 320px
    and survive 200% zoom without a horizontal scrollbar."""

    name: str
    ramp: Ramp
    light_ramp: Ramp
    measure_ch: int
    body_px: int
    placement: dict[str, Placement]
    title_screen: TitleScreen = "shelf"


PAPERBACK = PrintStyle(
    name="paperback",
    # A5, the trim the design directions are set at
    page_width=148.0,
    page_height=210.0,
    margin_inside=16.0,
    margin_outside=14.0,
    margin_top=16.0,
    margin_bottom=16.0,
    body_size=10.5,
    leading=0.62,
    section_size=12.0,
    ramp=PAPERBACK_RAMP,
    placement=PRINT_PLACEMENT,
    running_heads=True,
    section_per_page=False,
)

BOUND = PrintStyle(
    name="bound",
    page_width=148.0,
    page_height=210.0,
    # the wide outer margin is the direction: it carries the numerals and
    # codewords, and the narrower measure is what costs 1b its extra pages
    margin_inside=18.0,
    margin_outside=38.0,
    margin_top=17.0,
    margin_bottom=17.0,
    body_size=10.5,
    leading=0.66,
    section_size=15.0,
    ramp=BOUND_RAMP,
    placement=PRINT_PLACEMENT,
    running_heads=True,
    section_per_page=False,
    section_head="margin",
    instruction_form="italic-block",
    margin_note_width=26.0,
    margin_note_gutter=6.0,
)

COMPENDIUM = PrintStyle(
    name="compendium",
    page_width=148.0,
    page_height=210.0,
    margin_inside=17.0,
    margin_outside=15.0,
    margin_top=18.0,
    margin_bottom=16.0,
    body_size=10.0,
    leading=0.6,
    section_size=20.0,  # display-weight numerals: the type carries the book
    ramp=COMPENDIUM_RAMP,
    placement=PRINT_PLACEMENT,
    running_heads=True,
    section_per_page=False,
    cover_treatment="band",
    cover_band_fraction=0.46,
    front_matter="heavy",
)

SHELF = ScreenStyle(
    name="screen",
    ramp=SHELF_RAMP,
    light_ramp=SHELF_LIGHT_RAMP,
    measure_ch=66,
    body_px=18,
    placement=SCREEN_PLACEMENT,
)

# 1e: the same reading view, a different way in — the cover fills the
# viewport with the title set over it. Light mode is deliberately not
# offered: type over a photographic cover needs a dark scrim to clear its
# contrast floor, and a light scrim over the same art would not.
ROOM = ScreenStyle(
    name="table",
    ramp=SHELF_RAMP,
    light_ramp=SHELF_LIGHT_RAMP,
    measure_ch=64,
    body_px=18,
    placement=SCREEN_PLACEMENT,
    title_screen="room",
)

PRINT_STYLES: dict[str, PrintStyle] = {
    PAPERBACK.name: PAPERBACK,
    BOUND.name: BOUND,
    COMPENDIUM.name: COMPENDIUM,
}
SCREEN_STYLES: dict[str, ScreenStyle] = {SHELF.name: SHELF, ROOM.name: ROOM}

DEFAULT_PRINT_STYLE = PAPERBACK.name
DEFAULT_SCREEN_STYLE = SHELF.name


class StyleError(Exception):
    """An unusable style selection or an unusable ramp — an export-blocking
    configuration error, always phrased with the way out."""


def print_style(name: str, *, large_print: bool = False) -> PrintStyle:
    style = PRINT_STYLES.get(name)
    if style is None:
        raise StyleError(
            f"unknown print style {name!r} — use one of {', '.join(sorted(PRINT_STYLES))}"
        )
    if large_print:
        style = large_print_of(style)
    problems = check_ramp(style.ramp, where=f"print style {style.name!r}")
    problems += check_geometry(style)
    if problems:
        raise StyleError("\n".join(problems))
    return style


def screen_style(name: str, *, large_print: bool = False) -> ScreenStyle:
    style = SCREEN_STYLES.get(name)
    if style is None:
        raise StyleError(
            f"unknown screen style {name!r} — use one of {', '.join(sorted(SCREEN_STYLES))}"
        )
    if large_print:
        # the same modifier as print: bigger type, narrower measure, the
        # style's own palette and furniture untouched
        style = replace(
            style,
            name=f"{style.name}-large-print",
            body_px=round(style.body_px * 1.35),
            measure_ch=54,
        )
    problems = check_ramp(style.ramp, where=f"screen style {style.name!r} (dark)")
    problems += check_ramp(style.light_ramp, where=f"screen style {style.name!r} (light)")
    if problems:
        raise StyleError("\n".join(problems))
    return style


def large_print_of(style: PrintStyle) -> PrintStyle:
    """Large print is a modifier, not a sixth style (author, 2026-07-30):
    type scale, leading and measure over the style's own palette and
    furniture. The measure narrows by widening the margins, so the larger
    type still lands near the same characters-per-line — the thing that
    actually governs readability."""
    return replace(
        style,
        name=f"{style.name}-large-print",
        body_size=round(style.body_size * 1.35, 1),
        leading=round(style.leading * 1.15, 3),
        section_size=round(style.section_size * 1.3, 1),
        margin_inside=style.margin_inside + 2.0,
        margin_outside=style.margin_outside + 2.0,
    )


def image_width(placement: dict[str, Placement], ratio: str) -> float:
    """The fraction of the measure an image of this ratio occupies. An
    unknown ratio (a hand-edited brief predating the menu) falls back to
    the landscape rule rather than crashing the layout — `qf export`
    reports it, the page still builds."""
    return placement.get(ratio, placement["3:2"]).width


# -- art resolution -------------------------------------------------------------

# 300dpi at A5 trim plus bleed. A placement below its floor is upscaled by
# the printer into visible softness, so the export falls back to an inset
# plate instead — the honest fallback (design plan, "Ratified decisions"
# §1), reported as a warning rather than silently shipped.
FULL_BLEED_MIN_PIXELS = (1750, 2625)


def cover_floor(style: PrintStyle) -> tuple[int, int]:
    """The pixels a cover needs for *this* style's treatment.

    A band is not exempt from the floor, only shorter: it still runs the
    full page width, so it needs the same horizontal density and only its
    own fraction of the height. (An earlier note in the layout plan called
    the band "the one placement that does not need the floor"; that was
    wrong — cropping the frame does not reduce the density the printer
    renders it at.)
    """
    width, height = FULL_BLEED_MIN_PIXELS
    if style.cover_treatment == "band":
        return width, math.ceil(height * style.cover_band_fraction)
    return width, height


def cover_fits(style: PrintStyle, size: tuple[int, int]) -> bool:
    floor = cover_floor(style)
    return size[0] >= floor[0] and size[1] >= floor[1]


__all__ = [
    "BOUND",
    "COMPENDIUM",
    "COVER_RATIO",
    "DEFAULT_PRINT_STYLE",
    "DEFAULT_SCREEN_STYLE",
    "FULL_BLEED_MIN_PIXELS",
    "PAPERBACK",
    "PRINT_STYLES",
    "RATIOS",
    "ROOM",
    "SCREEN_STYLES",
    "SHELF",
    "Placement",
    "PrintStyle",
    "Ramp",
    "Ratio",
    "ScreenStyle",
    "StyleError",
    "check_geometry",
    "check_ramp",
    "cover_fits",
    "cover_floor",
    "contrast_ratio",
    "image_width",
    "large_print_of",
    "print_style",
    "ratio_value",
    "relative_luminance",
    "screen_style",
]
