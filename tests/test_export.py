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
    # the cover screen, its image inlined as a data URI, and a Begin control
    assert 'id="cover"' in html
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
