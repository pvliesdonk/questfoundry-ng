"""First exports (design doc 04): canonical runtime JSON with its own
round-trip validator, the standalone HTML player, Twee/SugarCube."""

from __future__ import annotations

import json

from questfoundry.export.html import build_html
from questfoundry.export.runtime_json import build_runtime, validate_runtime
from questfoundry.export.twee import build_twee


def test_runtime_round_trip_on_golden(golden):
    data = build_runtime(golden)
    assert data["format"] == "questfoundry-runtime"
    assert data["start"] == "p-arrival"
    assert len(data["passages"]) == 9
    assert validate_runtime(data) == []
    # gated choice survives export
    tremor = data["passages"]["p-tremor"]
    gated = [c for c in tremor["choices"] if c["requires"]]
    assert gated and gated[0]["requires"] == ["flag:elias-knows"]
    # working data never ships
    assert "beats" not in json.dumps(data)


def test_runtime_validator_catches_broken_documents(golden):
    data = build_runtime(golden)
    # sever the grant that opens the gated detour -> the runtime walk
    # must notice the counsel passage is unreachable
    for p in data["passages"].values():
        for c in p["choices"]:
            c["grants"] = [g for g in c["grants"] if g != "flag:elias-knows"]
    problems = validate_runtime(data)
    assert any("p-counsel is unreachable" in p for p in problems)

    data = build_runtime(golden)
    data["passages"]["p-tremor"]["choices"][0]["to"] = "p-nowhere"
    assert any("unknown passage" in p for p in validate_runtime(data))

    data = build_runtime(golden)
    data["passages"]["p-long-watch"]["prose"] = ""
    assert any("no prose" in p for p in validate_runtime(data))


def test_html_player_is_self_contained(golden):
    html = build_html(golden)
    assert html.startswith("<!DOCTYPE html>")
    assert '"questfoundry-runtime"' in html
    assert "The Keeper&#x27;s Bargain" in html or "The Keeper's Bargain" in html
    # nothing fetched from anywhere: no external URLs
    assert "http://" not in html and "https://" not in html
    # the embedded JSON cannot terminate the script element early: the
    # only literal "</script>" is the player's own closing tag
    assert html.count("</script>") == 1


def test_html_cover_screen_when_image_exists(golden, tmp_path):
    import base64
    import shutil

    from questfoundry.project import load_project

    dest = tmp_path / "keepers-bargain"
    shutil.copytree(golden.root, dest)
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    (dest / "art" / "images").mkdir(parents=True, exist_ok=True)
    (dest / "art" / "images" / "cover.png").write_bytes(png)

    html = build_html(load_project(dest))
    # the title screen sets the cover as an inset object, its image inlined
    # as a data URI, beside the Begin control
    assert 'id="cover-art"' in html
    assert '"cover": {"image": "data:image/png;base64,' in html
    assert 'id="begin"' in html
    # still self-contained
    assert "http://" not in html and "https://" not in html


def test_html_no_cover_screen_without_image(golden):
    # the golden ships a cover brief but no rendered cover.png -> no cover in JSON
    html = build_html(golden)
    assert '"cover":' not in html


def test_twee_export_shape(golden):
    twee = build_twee(golden, "TEST-IFID-1234")
    assert ":: StoryTitle" in twee and ":: StoryData" in twee
    assert '"ifid": "TEST-IFID-1234"' in twee
    assert '"start": "p-arrival"' in twee
    # grants become entry <<set>>s on the passage that carries the commit
    assert "<<set $f_elias_knows to true>>" in twee.split(":: p-lamp-room")[1].split("::")[0]
    # gated link guarded
    assert "<<if $f_elias_knows>>[[Ask Elias what he would do->p-counsel]]<</if>>" in twee
    # every passage present
    for slug in ("p-arrival", "p-tremor", "p-counsel", "p-long-watch", "p-wide-water"):
        assert f":: {slug}\n" in twee


def _cosmetic_diamond_runtime(n: int) -> dict:
    """A runtime doc of n spine passages d0..dn where each di (i<n) offers two
    choices to d(i+1), each granting a distinct UNCONSUMED cosmetic flag
    (nothing ever `requires` them). A player reaching di can hold any subset of
    the granted flags, so d(n) is reachable with 2**n flag-sets. Before the fix
    validate_runtime keyed its walk on (passage, accumulated-flags) and blew up
    to 2**n states — the cosmetic-keyword OOM that killed `qf export` on the
    live medium run. No gate ever tests a granted flag, so all are inert."""
    passages: dict = {}
    flags: dict = {}
    for i in range(n + 1):
        if i == n:
            passages[f"d{i}"] = {
                "prose": "end.", "choices": [], "ending": {"id": "e", "title": "End"}
            }
            continue
        choices = []
        for arm in ("a", "b"):
            fid = f"flag:cw-{i}-{arm}"
            flags[fid] = {}
            choices.append(
                {"label": f"{i}{arm}", "to": f"d{i + 1}", "requires": [], "grants": [fid]}
            )
        passages[f"d{i}"] = {"prose": "on.", "choices": choices, "ending": None}
    return {
        "format": "questfoundry-runtime",
        "version": 1,
        "meta": {"title": "t", "author": "a", "scope": "micro"},
        "start": "d0",
        "passages": passages,
        "flags": flags,
        "entities": {},
        "codex": [],
        "art": [],
    }


def test_validate_runtime_does_not_explode_on_unconsumed_cosmetic_grants():
    # 2**24 flag-sets reach the last passage pre-fix; the gate-relevant
    # projection keeps the walk linear because no choice tests these flags.
    data = _cosmetic_diamond_runtime(24)
    assert validate_runtime(data) == []


# -- 1d Shelf: the accessibility contract is structural (design doc 04 §7) ----


def test_player_semantics_are_real_elements_not_styled_divs(golden):
    html = build_html(golden)
    # choices are buttons in a labelled nav; the section is an article that
    # can take focus and is named by its heading
    assert '<nav id="choices-nav" aria-label="Choices">' in html
    assert 'b.type = "button"' in html
    assert '<article id="section" tabindex="-1" aria-labelledby="section-heading">' in html
    assert 'el("section").focus();' in html
    # status changes reach a screen reader without stealing focus
    assert 'id="announce" class="visually-hidden" role="status" aria-live="polite"' in html


def test_player_honours_reduced_motion_in_both_css_and_the_turn(golden):
    html = build_html(golden)
    assert "@media (prefers-reduced-motion: reduce) { :root { --turn: 0ms; } }" in html
    # the JS turn must collapse too, or the fade would still delay the render
    assert 'matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 180' in html


def test_player_measure_is_ch_based_so_it_reflows_and_zooms(golden):
    html = build_html(golden)
    assert "--measure: 66ch;" in html
    assert "max-width: var(--measure);" in html


def test_reading_mode_control_is_a_pressed_toggle_over_two_checked_ramps(golden):
    from questfoundry.export.style import SHELF

    html = build_html(golden)
    assert 'data-mode="dark" aria-pressed="true"' in html
    assert 'data-mode="light" aria-pressed="false"' in html
    # both ramps are shipped, and both are the contrast-checked ones
    assert SHELF.ramp.page in html and SHELF.light_ramp.page in html
    assert ':root[data-mode="light"]' in html


def test_choices_are_omitted_not_disabled_when_their_gate_is_unmet(golden):
    """Runtime semantics (§1 rule 2): the reader must not see the
    machinery. Nothing in the player renders an unavailable choice."""
    html = build_html(golden)
    assert "p.choices.filter(c => has(c.requires))" in html
    # no element is ever rendered in a disabled state
    assert "disabled" not in html.replace("never disabled", "")


def test_art_carries_alt_and_reserves_its_ratio_before_loading(golden):
    html = build_html(golden)
    assert 'img.alt = art.alt || "";' in html
    # the frame is reserved from the declared ratio, so nothing shifts mid-turn
    assert 'img.style.aspectRatio = (art.ratio || "3:2").replace(":", " / ");' in html
    assert '"1:1": "82%"' in html  # the screen placement table reaches the page


def test_large_print_html_scales_type_and_narrows_the_measure(golden):
    from questfoundry.export.style import screen_style

    large = build_html(golden, style=screen_style("screen", large_print=True))
    assert "--measure: 54ch;" in large
    assert "--body: 24px;" in large
    assert "http://" not in large and "https://" not in large  # still self-contained


# -- image metadata at the persistent boundary --------------------------------


def test_validate_rejects_art_without_alt_text(golden):
    data = build_runtime(golden)
    data["art"] = [
        {"passage": "p-arrival", "image": "art/images/p-arrival.png",
         "caption": "c", "alt": "   ", "ratio": "3:2"}
    ]
    (problem,) = validate_runtime(data)
    assert "p-arrival" in problem and "no alt text" in problem and "PDF/UA-1" in problem


def test_validate_rejects_a_ratio_outside_the_provider_portable_menu(golden):
    data = build_runtime(golden)
    data["art"] = [
        {"passage": "p-arrival", "image": "art/images/p-arrival.png",
         "caption": "c", "alt": "A lighthouse stands on iron stilts under a storm sky.",
         "ratio": "16:9"}
    ]
    (problem,) = validate_runtime(data)
    assert "16:9" in problem and "2:3, 3:2, 1:1" in problem


def test_validate_checks_the_cover_on_the_same_terms(golden):
    data = build_runtime(golden)
    data["cover"] = {"image": "art/images/cover.png", "alt": "", "ratio": "2:3"}
    assert any("cover entry has no alt text" in p for p in validate_runtime(data))


def test_cover_alt_containing_a_quote_stays_inside_its_attribute(golden, tmp_path):
    """Alt text is prose, and nothing forbids it a quotation mark ("a door
    marked "keep out" in chalk"). The cover's alt is the one place it is
    string-templated into HTML rather than assigned as a JS property, so a
    text-content escape here would end the attribute early and spill the
    rest of the sentence into the page as markup."""
    import base64
    import shutil

    from questfoundry.project import load_project

    dest = tmp_path / "keepers-bargain"
    shutil.copytree(golden.root, dest)
    (dest / "art" / "images").mkdir(parents=True, exist_ok=True)
    (dest / "art" / "images" / "cover.png").write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
            "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
    )
    project = load_project(dest)
    project.enrichment.cover.alt = (
        'A lantern glows over a door marked "keep out" in chalk, <script>, & rain.'
    )

    html = build_html(project)
    tag = html.split('<img id="cover-art"', 1)[1].split(">", 1)[0]
    assert '"keep out"' not in tag  # the raw quotes never reach the attribute
    assert "&quot;keep out&quot;" in tag
    assert "&lt;script&gt;" in tag and "&amp; rain" in tag
    # and the tag is the only thing between the delimiters: nothing spilled
    assert tag.count('alt="') == 1


# -- 1e Room: the other way in (design doc 04 §7) -----------------------------


def _with_cover(golden, tmp_path):
    import base64
    import shutil

    from questfoundry.project import load_project

    dest = tmp_path / "keepers-bargain"
    shutil.copytree(golden.root, dest)
    (dest / "art" / "images").mkdir(parents=True, exist_ok=True)
    (dest / "art" / "images" / "cover.png").write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
            "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
    )
    return load_project(dest)


def test_room_fills_the_viewport_with_the_cover_and_scrims_the_type(golden, tmp_path):
    from questfoundry.export.style import screen_style

    project = _with_cover(golden, tmp_path)
    room = build_html(project, style=screen_style("table"))
    assert '<div id="title-screen" data-variant="room" data-scrim>' in room
    assert '<div id="scrim"></div>' in room
    assert 'position: fixed; inset: 0;\n       width: 100%; height: 100%; object-fit: cover' in room


def test_shelf_and_room_differ_only_in_the_way_in(golden, tmp_path):
    """The reading view is shared: a direction is how the cover is set, not
    a second player."""
    from questfoundry.export.style import screen_style

    project = _with_cover(golden, tmp_path)
    shelf = build_html(project, style=screen_style("screen"))
    room = build_html(project, style=screen_style("table"))

    assert '<div id="shelf">' in shelf and '<div id="shelf">' not in room
    assert '<div id="scrim"></div>' in room and '<div id="scrim"></div>' not in shelf
    # everything past the title screen is the same player
    assert shelf.split("<main id=\"reader\"")[1] == room.split("<main id=\"reader\"")[1]


def test_room_still_names_the_story_and_offers_the_same_controls(golden, tmp_path):
    from questfoundry.export.style import screen_style

    project = _with_cover(golden, tmp_path)
    room = build_html(project, style=screen_style("table"))
    assert "<h1 id=\"story-title\">The Keeper" in room  # the title is substituted, not left raw
    assert "__TITLE__" not in room
    for control in ('id="begin"', 'id="continue"', 'id="howto-open"', 'id="reading-mode"'):
        assert control in room


def test_room_without_a_cover_drops_the_scrim_rather_than_darkening_nothing(golden):
    from questfoundry.export.style import screen_style

    # the golden ships a cover brief but no rendered cover.png
    room = build_html(golden, style=screen_style("table"))
    assert 'data-variant="room"' in room
    assert '<div id="scrim"></div>' not in room
    assert 'id="cover-art"' not in room


def test_room_re_measures_its_controls_against_the_scrim_not_the_page(golden, tmp_path):
    """A ramp role is checked against the page colour it belongs to. Over a
    scrimmed cover that page is gone, so the pressed control cannot keep
    using `--accent` — in light mode that is a dark blue on near-black."""
    from questfoundry.export.style import screen_style

    project = _with_cover(golden, tmp_path)
    room = build_html(project, style=screen_style("table"))
    override = room.split('#title-screen[data-scrim] #reading-mode button')[1]
    assert "color: #FFFFFF" in override.split("}")[0]
    # and the pressed state is never carried by colour alone (WCAG 1.4.1)
    assert "border-color: #F2EFE8" in override.split("}")[0]


def test_a_room_with_no_cover_keeps_the_ramp_and_stays_legible_in_both_modes(golden):
    """The scrim-measured literals are only valid over a scrim. Without a
    cover there is none, so the room must fall back to the ramp's own
    checked roles — forcing near-white type onto the light page would be a
    1.03:1 contrast failure (found in review of PR #130)."""
    from questfoundry.export.style import contrast_ratio, screen_style

    style = screen_style("table")
    room = build_html(golden, style=style)  # the golden has no rendered cover
    # the element carries no scrim attribute and no scrim is drawn, so none
    # of the scrim-measured rules can match
    assert '<div id="title-screen" data-variant="room">' in room
    assert "data-scrim>" not in room
    assert '<div id="scrim">' not in room

    # and no rule sets a forced literal outside a [data-scrim] selector, so a
    # future edit cannot reintroduce near-white type on the light page
    css = room.split("<style>")[1].split("</style>")[0]
    for rule in css.split("}"):
        if "#F2EFE8" in rule or "#D6D2C8" in rule or "#E6E2DA" in rule:
            assert "[data-scrim]" in rule, rule

    # what the type actually renders against, in both modes, clears the floor
    for ramp in (style.ramp, style.light_ramp):
        assert contrast_ratio(ramp.ink, ramp.page) >= 7.0
        assert contrast_ratio(ramp.muted, ramp.page) >= 4.5
