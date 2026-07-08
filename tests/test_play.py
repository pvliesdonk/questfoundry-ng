"""M3 exit criterion: the golden story is playable end-to-end — choices,
gates, four distinct journeys — with zero prose (the engine renders beat
summaries)."""

from __future__ import annotations

import pytest

from questfoundry.play import Player, PlayError


def journey(g, labels: list[str]) -> Player:
    """Play by choosing the option with each given label, in order."""
    player = Player(g)
    for label in labels:
        offered = {c.label: i for i, c in enumerate(player.choices())}
        assert label in offered, f"{label!r} not offered at {player.passage_id}: {offered}"
        player.choose(offered[label])
    return player


TELL = "Take him down to the lamp room and tell him the truth"
HIDE = "Blame the instruments and burn the page"
ONWARD_TELL = "Stand the watch together until the sea turns"
ONWARD_HIDE = "Let the weather take the blame and the days pass"
KEEP = "Send the ship away and tend the light"
BREAK = "Cap the lamp and go aboard"
COUNSEL = "Ask Elias what he would do"


def test_four_distinct_journeys_reach_their_endings(golden):
    g = golden.graph
    outcomes = {
        (TELL, ONWARD_TELL, KEEP): ("The Long Watch", {"flag:elias-knows", "flag:bound-to-light"}),
        (TELL, ONWARD_TELL, BREAK): ("The Wide Water", {"flag:elias-knows", "flag:sleeper-waking"}),
        (HIDE, ONWARD_HIDE, KEEP): ("The Long Watch", {"flag:lie-between", "flag:bound-to-light"}),
        (HIDE, ONWARD_HIDE, BREAK): ("The Wide Water", {"flag:lie-between", "flag:sleeper-waking"}),
    }
    routes = set()
    for picks, (title, flags) in outcomes.items():
        player = journey(g, list(picks))
        assert player.ending is not None and player.ending.title == title
        assert player.flags == flags
        routes.add(tuple(player.visited))
    assert len(routes) == 4


def test_gated_choice_hidden_without_its_flag(golden):
    g = golden.graph
    telling = journey(g, [TELL, ONWARD_TELL])
    assert COUNSEL in [c.label for c in telling.choices()]
    hiding = journey(g, [HIDE, ONWARD_HIDE])
    assert COUNSEL not in [c.label for c in hiding.choices()]


def test_counsel_detour_rejoins_the_fork(golden):
    player = journey(golden.graph, [TELL, ONWARD_TELL, COUNSEL, KEEP])
    assert player.ending is not None and player.ending.title == "The Long Watch"
    assert "passage:p-counsel" in player.visited


def test_prose_renders_beat_summaries_in_order(golden):
    player = Player(golden.graph)
    prose = player.prose()
    assert len(prose) == 4  # p-arrival holds four beats
    assert "Storm season" in prose[0]


def test_engine_guards(golden):
    player = Player(golden.graph)
    with pytest.raises(PlayError, match="out of range"):
        player.choose(9)
    finished = journey(golden.graph, [TELL, ONWARD_TELL, KEEP])
    with pytest.raises(PlayError, match="ended"):
        finished.choose(0)
