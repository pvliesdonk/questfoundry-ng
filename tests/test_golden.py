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
            in_view = [c for c in queries.commit_beats(g, path) if c in view]
            assert len(in_view) == 1


def test_residue_arms_mirror_the_truth_paths(golden):
    """The residue diamond: each path's gated arm appears exactly on the
    arcs that hold its flag — the tell arm is a 2-beat chain."""
    g = golden.graph
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        telling = selection["dilemma:truth"] == "path:tell"
        assert ("beat:counsel" in view) == telling, selection
        assert ("beat:honest-chart" in view) == telling, selection
        assert ("beat:unspoken" in view) == (not telling), selection


def test_soft_dilemma_converges_hard_never(golden):
    g = golden.graph
    tell, hide = "beat:tell-commit", "beat:hide-commit"
    assert queries.descendants(g, tell) & queries.descendants(g, hide)
    keep, break_ = "beat:keep-commit", "beat:break-commit"
    assert not (queries.descendants(g, keep) & queries.descendants(g, break_))


def test_residue_beats_are_post_freeze_additions(golden):
    frozen = set(golden.graph.frozen.beats)
    all_beats = {b.id for b in golden.graph.nodes_of(Beat)}
    assert all_beats - frozen == {"beat:counsel", "beat:honest-chart", "beat:unspoken"}


def test_locked_dilemma_resolves_on_every_arc(golden):
    """The second-keeper question is locked at triage: one explored path,
    no fork, no flags — a storyline every arc walks and resolves (I6)."""
    from questfoundry.models.structure import StateFlag

    g = golden.graph
    assert queries.locked_dilemmas(g) == ["dilemma:second-keeper"]
    (path,) = queries.explored_paths(g, "dilemma:second-keeper")
    assert queries.commit_beats(g, path) == ["beat:returned-boat"]
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        assert {"beat:mothers-line", "beat:returned-boat", "beat:inherited-watch"} <= view
    # a locked outcome is a world fact: no flag is granted by its path
    assert all(f.path != path for f in g.nodes_of(StateFlag))


def test_all_arc_walks_are_complete(golden):
    """M2 exit criterion: four complete, validated arcs through the
    golden story's beat DAG (`qf simulate --all-arcs`)."""
    from questfoundry.play import walk_all_arcs

    walks = walk_all_arcs(golden.graph)
    assert len(walks) == 4
    for walk in walks:
        assert walk.problems == [], walk.label
        assert walk.beats[0] == "beat:storm-glass"
        assert walk.ending in ("beat:keep-ending", "beat:break-ending")
        # the two flags of the selected paths are granted, at commit beats
        assert len(walk.flags) == 2
        for flag_id, grant in walk.flags.items():
            assert grant in walk.beats, flag_id


def test_start_passage_is_unique(golden):
    assert queries.start_passages(golden.graph) == ["passage:p-arrival"]


def test_endings_are_distinct_passages(golden):
    endings = [p for p in golden.graph.nodes_of(Passage) if p.ending]
    assert sorted(p.ending.id for p in endings) == ["e-long-watch", "e-wide-water"]
