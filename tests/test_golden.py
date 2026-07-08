"""The Keeper's Bargain — golden-story assertions (M0 exit criterion)."""

from questfoundry.graph import queries
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import Beat


def test_four_arcs(golden):
    selections = queries.arc_selections(golden.graph)
    assert len(selections) == 4


def test_every_arc_is_complete(golden):
    g = golden.graph
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        endings = [b for b in view if g.node(b).is_ending]
        assert len(endings) == 1, selection
        for path in selection.values():
            assert queries.commit_beat(g, path) in view


def test_residue_beat_only_on_telling_arcs(golden):
    g = golden.graph
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        expected = selection["dilemma:truth"] == "path:tell"
        assert ("beat:counsel" in view) == expected, selection


def test_soft_dilemma_converges_hard_never(golden):
    g = golden.graph
    tell, hide = "beat:tell-commit", "beat:hide-commit"
    assert queries.descendants(g, tell) & queries.descendants(g, hide)
    keep, break_ = "beat:keep-commit", "beat:break-commit"
    assert not (queries.descendants(g, keep) & queries.descendants(g, break_))


def test_counsel_is_a_post_freeze_addition(golden):
    frozen = set(golden.graph.frozen.beats)
    all_beats = {b.id for b in golden.graph.nodes_of(Beat)}
    assert all_beats - frozen == {"beat:counsel"}


def test_start_passage_is_unique(golden):
    assert queries.start_passages(golden.graph) == ["passage:p-arrival"]


def test_endings_are_distinct_passages(golden):
    endings = [p for p in golden.graph.nodes_of(Passage) if p.ending]
    assert sorted(p.ending.id for p in endings) == ["e-long-watch", "e-wide-water"]
