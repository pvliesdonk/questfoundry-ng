"""The shared style layer (design doc 04 §7).

The ramps are the accessibility contract in data form, so the tests that
matter are the ones that would catch a ramp drifting below its floor —
and the violating construction that proves the validator actually fails
the build rather than warning about it (AGENTS.md iron rule 6).
"""

from __future__ import annotations

import dataclasses

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
    with pytest.raises(S.StyleError, match="paperback"):
        S.print_style("bound")  # 1b: designed, not built yet
    with pytest.raises(S.StyleError, match="screen"):
        S.screen_style("table")  # 1e: same


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
    assert S.full_bleed_ok(S.FULL_BLEED_MIN_PIXELS)
    assert not S.full_bleed_ok((S.FULL_BLEED_MIN_PIXELS[0] - 1, S.FULL_BLEED_MIN_PIXELS[1]))
    assert not S.full_bleed_ok((S.FULL_BLEED_MIN_PIXELS[0], S.FULL_BLEED_MIN_PIXELS[1] - 1))
