"""The shared style layer (design doc 04 §7).

The ramps are the accessibility contract in data form, so the tests that
matter are the ones that would catch a ramp drifting below its floor —
and the violating construction that proves the validator actually fails
the build rather than warning about it (AGENTS.md iron rule 6).
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from questfoundry.export import style as S

# -- contrast -------------------------------------------------------------------


def test_relative_luminance_and_contrast_match_wcag_reference():
    # the two endpoints WCAG pins exactly: white on black is 21:1
    assert S.relative_luminance("#FFFFFF") == pytest.approx(1.0)
    assert S.relative_luminance("#000000") == pytest.approx(0.0)
    assert S.contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert S.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)  # order-free


def test_parse_hex_rejects_a_non_hex_colour_with_the_way_out():
    with pytest.raises(ValueError, match="#RRGGBB"):
        S.parse_hex("cornflower")


@pytest.mark.parametrize(
    ("name", "ramp"),
    [
        ("paperback", S.PAPERBACK_RAMP),
        ("bound", S.BOUND_RAMP),
        ("compendium", S.COMPENDIUM_RAMP),
        ("shelf dark", S.SHELF_RAMP),
        ("shelf light", S.SHELF_LIGHT_RAMP),
    ],
)
def test_every_shipped_ramp_clears_every_floor(name, ramp):
    assert S.check_ramp(ramp, where=name) == []


def test_a_ramp_below_a_floor_fails_and_names_the_measurement_and_the_fix():
    # an accent that reads as a mid-grey on paper: legible-looking, and well
    # under the 4.5:1 text floor
    bad = S.Ramp(page="#FBF9F4", ink="#17181A", muted="#5C5E63", accent="#B9B4A8", rule="#6E7075")
    problems = S.check_ramp(bad, where="probe")
    assert len(problems) == 1
    (problem,) = problems
    assert "accent" in problem and "4.5:1" in problem
    assert "darken" in problem  # the accent is lighter than the page: move it down


def test_print_style_refuses_to_ship_a_style_whose_ramp_fails(monkeypatch):
    """The validator is a build gate, not a report: a style whose accent
    lands outside the ramp cannot be exported at all."""
    broken = dataclasses.replace(
        S.PAPERBACK,
        ramp=S.Ramp(
            page="#FFFFFF", ink="#FEFEFE", muted="#FEFEFE", accent="#FEFEFE", rule="#FEFEFE"
        ),
    )
    monkeypatch.setitem(S.PRINT_STYLES, "broken", broken)
    with pytest.raises(S.StyleError) as exc:
        S.print_style("broken")
    assert "below the" in str(exc.value)


# -- selection ------------------------------------------------------------------


def test_unknown_style_names_list_what_is_available():
    with pytest.raises(S.StyleError) as print_exc:
        S.print_style("folio")
    for built in ("paperback", "bound", "compendium"):
        assert built in str(print_exc.value)

    with pytest.raises(S.StyleError) as screen_exc:
        S.screen_style("kiosk")
    for built in ("screen", "table"):
        assert built in str(screen_exc.value)


def test_every_style_in_the_registry_is_selectable_and_passes_its_own_gates():
    """Registering a style is what makes `--style` offer it, so every entry
    must survive the ramp and geometry checks selection runs."""
    for name in S.PRINT_STYLES:
        assert S.print_style(name).name == name
        S.print_style(name, large_print=True)  # the modifier must not break it
    for name in S.SCREEN_STYLES:
        assert S.screen_style(name).name == name
        S.screen_style(name, large_print=True)


def test_large_print_is_a_modifier_over_the_style_not_a_separate_style():
    """Author, 2026-07-30: large print combines with any print style —
    type scale, leading and measure over that style's own palette and
    furniture."""
    plain = S.print_style("paperback")
    large = S.print_style("paperback", large_print=True)

    assert large.body_size > plain.body_size
    assert large.leading > plain.leading
    assert large.measure_mm < plain.measure_mm  # narrower measure, same page
    # the style's own identity is untouched
    assert large.ramp == plain.ramp
    assert large.page_width == plain.page_width and large.page_height == plain.page_height
    assert large.running_heads == plain.running_heads
    assert large.name == "paperback-large-print"


def test_screen_large_print_scales_type_and_narrows_the_measure():
    plain = S.screen_style("screen")
    large = S.screen_style("screen", large_print=True)
    assert large.body_px > plain.body_px
    assert large.measure_ch < plain.measure_ch
    assert large.ramp == plain.ramp
    assert large.name == "screen-large-print"


# -- ratios and placement -------------------------------------------------------


def test_the_ratio_menu_is_the_model_literal_so_it_cannot_drift():
    from questfoundry.models.enrichment import IllustrationBrief

    allowed = IllustrationBrief.model_json_schema()["properties"]["ratio"]["enum"]
    assert set(allowed) == set(S.RATIOS)


def test_ratio_value_is_width_over_height():
    assert S.ratio_value("3:2") == pytest.approx(1.5)
    assert S.ratio_value("2:3") == pytest.approx(2 / 3)
    assert S.ratio_value("1:1") == pytest.approx(1.0)


@pytest.mark.parametrize("placement", [S.PRINT_PLACEMENT, S.SCREEN_PLACEMENT])
def test_every_menu_ratio_has_a_placement_and_a_portrait_never_fills_the_measure(placement):
    assert set(placement) == set(S.RATIOS)
    assert placement["3:2"].width == 1.0  # landscape sits at the measure
    assert placement["2:3"].width < placement["1:1"].width < 1.0


def test_an_unknown_ratio_falls_back_to_landscape_rather_than_crashing():
    # a hand-edited brief predating the menu still lays out; `qf export`
    # reports it as a warning
    assert S.image_width(S.PRINT_PLACEMENT, "16:9") == S.PRINT_PLACEMENT["3:2"].width


def test_full_bleed_floor_is_300dpi_at_a5_plus_bleed():
    assert S.cover_floor(S.PAPERBACK) == S.FULL_BLEED_MIN_PIXELS
    assert S.cover_fits(S.PAPERBACK, S.FULL_BLEED_MIN_PIXELS)
    for short in ((-1, 0), (0, -1)):
        size = (S.FULL_BLEED_MIN_PIXELS[0] + short[0], S.FULL_BLEED_MIN_PIXELS[1] + short[1])
        assert not S.cover_fits(S.PAPERBACK, size)


def test_a_band_is_shorter_than_a_full_bleed_page_but_no_less_dense():
    """Cropping the frame does not reduce the density the printer renders it
    at: the band still runs the full page width, so only its height scales.
    (The layout plan first recorded the band as exempt from the floor; that
    was wrong, and the reviewer of PR #130 was right to call it.)"""
    full_w, full_h = S.FULL_BLEED_MIN_PIXELS
    band_w, band_h = S.cover_floor(S.COMPENDIUM)
    assert band_w == full_w  # same width, same density across the page
    assert band_h == math.ceil(full_h * S.COMPENDIUM.cover_band_fraction) < full_h

    # an image tall enough for the band but not a full page fits 1c, not 1a
    banded = (full_w, band_h)
    assert S.cover_fits(S.COMPENDIUM, banded)
    assert not S.cover_fits(S.PAPERBACK, banded)
    # and one too narrow fails both, however tall it is
    assert not S.cover_fits(S.COMPENDIUM, (full_w - 1, full_h))


# -- geometry (1b's marginal column) --------------------------------------------


def test_a_marginal_column_that_does_not_fit_its_margin_fails_the_build():
    """A column wider than its margin silently overprints the page edge —
    a defect no ramp check sees and no reader of the Typst notices."""
    too_wide = dataclasses.replace(S.BOUND, margin_note_width=40.0, margin_note_gutter=6.0)
    (problem,) = S.check_geometry(too_wide)
    assert "46.0mm" in problem and "38.0mm" in problem
    assert "widen the outer margin or narrow the column" in problem


def test_a_margin_head_with_no_column_width_fails_the_build():
    (problem,) = S.check_geometry(dataclasses.replace(S.BOUND, margin_note_width=0.0))
    assert "margin_note_width is 0" in problem


def test_geometry_is_clean_for_every_built_style():
    for style in S.PRINT_STYLES.values():
        assert S.check_geometry(style) == []


def test_bound_narrows_the_measure_which_is_what_costs_it_pages():
    """1b's wide outer margin is the direction, and the narrower measure is
    its documented cost (~15% more pages than 1a)."""
    assert S.BOUND.measure_mm < S.PAPERBACK.measure_mm
    assert S.BOUND.margin_outside > S.BOUND.margin_inside  # the column's home


def test_the_furniture_axes_actually_vary_across_the_built_print_styles():
    """Each axis on PrintStyle earned its place by differing between styles;
    an axis with one value across all three would be a knob, not a choice."""
    styles = list(S.PRINT_STYLES.values())
    for axis in ("section_head", "instruction_form", "cover_treatment", "front_matter"):
        assert len({getattr(s, axis) for s in styles}) > 1, f"{axis} never varies"
    assert len({s.title_screen for s in S.SCREEN_STYLES.values()}) > 1
