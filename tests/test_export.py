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
    assert len(data["passages"]) == 8
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
