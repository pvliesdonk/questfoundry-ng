"""Braid metrics and their consumers (docs/plans/weave-linearization.md):
the phase model made countable, per-arc; candidate scoring at the weave;
B12 on the realized graph."""

from __future__ import annotations

from questfoundry.graph import braid, mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import Stage
from questfoundry.models.structure import ImpactEffect
from questfoundry.pipeline import weave
from tests.conftest import make_dilemma, narrative_beat
from tests.test_weave import seeded_story


def _tok(thread: str | None, commit: bool = False) -> braid.BraidToken:
    return braid.BraidToken(frozenset() if thread is None else frozenset({thread}), commit)


# -- score_arc: the phase model on token sequences ----------------------------


def test_a_middle_capsule_is_counted_and_penalized():
    # both threads introduce early, then A plays out as a 5-beat lump
    tokens = (
        [_tok("A"), _tok("B")]
        + [_tok("A")] * 5
        + [_tok("B"), _tok("A", commit=True), _tok("B"), _tok("B"), _tok("B", commit=True)]
    )
    score = braid.score_arc(tokens)
    assert score.middle_run == 5
    assert score.late_intros == 0
    assert score.penalty() > 0


def test_blocks_of_two_or_three_are_clean():
    tokens = (
        [_tok("A"), _tok("B")]
        + [_tok("A"), _tok("A"), _tok("B"), _tok("B"), _tok("A"), _tok("A"), _tok("A")]
        + [_tok("B"), _tok("A", commit=True), _tok("B"), _tok("B"), _tok("B", commit=True)]
    )
    score = braid.score_arc(tokens)
    assert score.middle_run == 3
    assert score.ping_pong <= 2  # the block pattern, not beat-by-beat alternation
    assert score.penalty() == score.ping_pong  # no run excess, no gaps, no late intros


def test_ping_pong_alternation_is_counted():
    tokens = [_tok("A"), _tok("B")] + [_tok("A"), _tok("B")] * 4 + [
        _tok("A", commit=True),
        _tok("B"),
        _tok("B"),
        _tok("B", commit=True),
    ]
    score = braid.score_arc(tokens)
    assert score.ping_pong >= 4


def test_late_intro_falls_outside_the_window():
    # B first appears at position 8 of 12 — outside the len/3 window
    tokens = [_tok("A")] * 8 + [
        _tok("B"),
        _tok("A", commit=True),
        _tok("B"),
        _tok("B", commit=True),
    ]
    score = braid.score_arc(tokens)
    assert score.late_intros == 1


def test_clustered_commits_shrink_the_gap():
    tokens = [_tok("A"), _tok("B"), _tok("A"), _tok("B")] + [
        _tok("A", commit=True),
        _tok("B", commit=True),
    ]
    score = braid.score_arc(tokens)
    assert score.commit_gap == 0
    assert score.penalty() >= 2 * braid.COMMIT_GAP_MIN


def test_neutral_beats_break_runs_without_owning_one():
    tokens = [_tok("A"), _tok("B")] + [
        _tok("A"),
        _tok("A"),
        _tok(None),  # a bridge: interrupts A's run, starts none
        _tok("A"),
        _tok("A"),
        _tok("B"),
        _tok("A", commit=True),
        _tok("B"),
        _tok("B"),
        _tok("B", commit=True),
    ]
    assert braid.score_arc(tokens).middle_run == 2


def test_single_thread_is_degenerate_and_quiet():
    score = braid.score_arc([_tok("A")] * 6 + [_tok("A", commit=True)])
    assert score.degenerate
    assert score.penalty() == 0


def test_worst_aggregates_the_arc_a_reader_would_complain_about():
    good = braid.BraidScore(middle_run=2, late_intros=0, commit_gap=4, ping_pong=0)
    lumpy = braid.BraidScore(middle_run=6, late_intros=1, commit_gap=1, ping_pong=2)
    agg = braid.worst([good, lumpy, braid.BraidScore(degenerate=True)])
    assert (agg.middle_run, agg.late_intros, agg.commit_gap, agg.ping_pong) == (6, 1, 1, 2)
    assert braid.worst([braid.BraidScore(degenerate=True)]).degenerate


# -- candidate scoring at the weave -------------------------------------------


def test_braid_score_for_scores_induced_arcs_not_the_spine():
    g = StoryGraph()
    seeded_story(g)
    planned = weave.plan(g)
    orders = weave.candidates(planned)
    scores = [weave.braid_score_for(g, planned, order) for order in orders]
    assert all(not s.degenerate for s in scores)  # two threads: at the floor, live
    # determinism: same order, same score
    assert weave.braid_score_for(g, planned, orders[0]) == scores[0]


def test_shown_candidates_rank_by_braid_and_carry_the_line(tmp_path, vision):
    from questfoundry.pipeline.stages.grow import _shown_candidates, _weave_context
    from questfoundry.project.io import Project

    g = StoryGraph()
    seeded_story(g)
    project = Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)
    _, shown = _shown_candidates(project)
    penalties = [score.penalty() for _, score in shown]
    assert penalties == sorted(penalties)  # best-braided first
    context = _weave_context(project)
    assert all(c["braid"].startswith("braid:") for c in context["candidates"])


# -- B12 on the realized graph ------------------------------------------------


def _chain(g: StoryGraph, entries: list[tuple[str, str, str, bool]]) -> None:
    """Wire entries [(slug, dilemma, path, commits)] as one chain."""
    prev = None
    for slug, dilemma, path, commits in entries:
        effect = ImpactEffect.COMMITS if commits else ImpactEffect.ADVANCES
        beat = narrative_beat(slug, dilemma, effect)
        mutations.add_beat(g, beat, [path])
        if prev:
            mutations.add_ordering(g, prev, beat.id)
        prev = beat.id


def _b12(g, vision):
    return [
        i
        for i in run_checks(g, vision, Stage.GROW)
        if i.check == "B12" and i.severity == Severity.WARNING
    ]


def test_b12_warns_on_a_middle_capsule(vision):
    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    _chain(
        g,
        [("a0", da, pa, False), ("b0", db, pb, False)]
        + [(f"a{i}", da, pa, False) for i in range(1, 6)]  # the capsule
        + [
            ("b1", db, pb, False),
            ("ac", da, pa, True),
            ("b2", db, pb, False),
            ("b3", db, pb, False),
            ("bc", db, pb, True),
        ],
    )
    issues = _b12(g, vision)
    assert any("capsule" in i.message for i in issues)


def test_b12_is_quiet_on_a_braided_chain(vision):
    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    _chain(
        g,
        [
            ("a0", da, pa, False),
            ("b0", db, pb, False),
            ("a1", da, pa, False),
            ("a2", da, pa, False),
            ("b1", db, pb, False),
            ("b2", db, pb, False),
            ("a3", da, pa, False),
            ("ac", da, pa, True),
            ("b3", db, pb, False),
            ("b4", db, pb, False),
            ("bc", db, pb, True),
        ],
    )
    assert not _b12(g, vision)


def test_b12_warns_on_beat_by_beat_ping_pong(vision):
    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    _chain(
        g,
        [("a0", da, pa, False), ("b0", db, pb, False)]
        + [
            (f"a{i}", da, pa, False) if i % 2 else (f"b{i}", db, pb, False)
            for i in range(1, 8)
        ]
        + [
            ("ac", da, pa, True),
            ("b8", db, pb, False),
            ("b9", db, pb, False),
            ("bc", db, pb, True),
        ],
    )
    issues = _b12(g, vision)
    assert any("never lets a scene breathe" in i.message for i in issues)


def test_b12_is_quiet_below_the_thread_floor(vision):
    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    _chain(g, [(f"a{i}", da, pa, False) for i in range(6)] + [("ac", da, pa, True)])
    assert not _b12(g, vision)


# -- swap_linear_beats: the repair primitive (moment 2) -----------------------


def _two_locked(g: StoryGraph):
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    return da, pa, db, pb


def _alternating(g: StoryGraph, da, pa, db, pb):
    _chain(
        g,
        [
            ("a0", da, pa, False),
            ("b0", db, pb, False),
            ("a1", da, pa, False),
            ("b1", db, pb, False),
            ("ac", da, pa, True),
            ("b2", db, pb, False),
            ("bc", db, pb, True),
        ],
    )


def test_swap_rewires_the_pair_and_returns_the_stale_beats():
    g = StoryGraph()
    da, pa, db, pb = _two_locked(g)
    _alternating(g, da, pa, db, pb)
    affected = mutations.swap_linear_beats(g, "beat:b0", "beat:a1")
    assert affected == ["beat:a1", "beat:b0", "beat:b1"]
    from questfoundry.models.base import EdgeKind

    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:a0", "beat:a1")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:a1", "beat:b0")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:b0", "beat:b1")
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:b0", "beat:a1")


def test_swap_refuses_a_non_adjacent_pair():
    import pytest

    g = StoryGraph()
    da, pa, db, pb = _two_locked(g)
    _alternating(g, da, pa, db, pb)
    with pytest.raises(mutations.MutationError, match=r"not adjacent"):
        mutations.swap_linear_beats(g, "beat:a0", "beat:a1")


def test_swap_refuses_the_walls_of_the_linear_run():
    import pytest

    g = StoryGraph()
    da, pa, db, pb = _two_locked(g)
    _alternating(g, da, pa, db, pb)
    # beat:a0 is the root: not strictly interior
    with pytest.raises(mutations.MutationError, match=r"not strictly interior"):
        mutations.swap_linear_beats(g, "beat:a0", "beat:b0")
    # beat:bc is terminal
    with pytest.raises(mutations.MutationError, match=r"not strictly interior"):
        mutations.swap_linear_beats(g, "beat:b2", "beat:bc")


def test_swap_refuses_a_same_storyline_pair():
    import pytest

    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    _chain(
        g,
        [
            ("a0", da, pa, False),
            ("a1", da, pa, False),
            ("a2", da, pa, False),
            ("b0", db, pb, False),
            ("ac", da, pa, True),
            ("bc", db, pb, True),
        ],
    )
    with pytest.raises(mutations.MutationError, match=r"same storyline"):
        mutations.swap_linear_beats(g, "beat:a1", "beat:a2")


def test_swap_refuses_intersection_group_members():
    import pytest

    from questfoundry.models.base import Stage as St
    from questfoundry.models.structure import IntersectionGroup

    g = StoryGraph()
    da, pa, db, pb = _two_locked(g)
    _alternating(g, da, pa, db, pb)
    mutations.add_intersection(
        g,
        IntersectionGroup(id="intersection:x", created_by=St.GROW),
        ["beat:b0", "beat:a1"],
    )
    with pytest.raises(mutations.MutationError, match=r"arrangement is pinned"):
        mutations.swap_linear_beats(g, "beat:b0", "beat:a1")


def test_swap_refuses_to_cross_a_temporal_hint():
    import pytest

    from questfoundry.models.structure import HintPosition, TemporalHint

    g = StoryGraph()
    da, pa, db, pb = _two_locked(g)
    _chain(
        g,
        [
            ("a0", da, pa, False),
            ("b0", db, pb, False),
            ("a1", da, pa, False),
            ("bc", db, pb, True),
            ("a2", da, pa, False),
            ("ac", da, pa, True),
        ],
    )
    hinted = g.node("beat:a1")
    hinted.temporal_hints = [TemporalHint(dilemma=db, position=HintPosition.BEFORE_COMMIT)]
    with pytest.raises(mutations.MutationError, match=r"cross the hint"):
        mutations.swap_linear_beats(g, "beat:a1", "beat:bc")


def test_swaps_cannot_change_a_groups_internal_arrangement():
    # No gate check exists behind the group pin, deliberately: contiguity
    # is not a graph invariant (the golden story legally separates its
    # group's members). The guarantee is by construction — any adjacent
    # swap that could alter member spacing has a member in the pair, and
    # members are refused. Golden-shaped construction: m1 -> x -> m2.
    import pytest

    from questfoundry.models.base import Stage as St
    from questfoundry.models.structure import IntersectionGroup

    g = StoryGraph()
    da, pa, db, pb = _two_locked(g)
    dc, pc, _ = make_dilemma(g, "cc", explore=1)
    _chain(
        g,
        [
            ("a0", da, pa, False),
            ("m1", db, pb, False),
            ("x", dc, pc, False),
            ("m2", da, pa, False),
            ("b1", db, pb, False),
            ("cc0", dc, pc, True),
            ("ac", da, pa, True),
            ("bc", db, pb, True),
        ],
    )
    mutations.add_intersection(
        g,
        IntersectionGroup(id="intersection:x", created_by=St.GROW),
        ["beat:m1", "beat:m2"],
    )
    # moving x out from between the members requires swapping it with one
    for pair in (("beat:m1", "beat:x"), ("beat:x", "beat:m2")):
        with pytest.raises(mutations.MutationError, match=r"arrangement is pinned"):
            mutations.swap_linear_beats(g, *pair)


# -- braid-respecting POLISH (moment 3) ---------------------------------------


def test_collapse_cap_cut_prefers_a_thread_switch():
    from questfoundry.pipeline import passages as pc

    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    # linear run: a0 a1 a2 | b0 b1 b2 — the switch sits one short of the cap
    _chain(
        g,
        [(f"a{i}", da, pa, False) for i in range(3)]
        + [(f"b{i}", db, pb, i == 2) for i in range(3)],
    )
    groups = pc.collapse_groups(g, max_beats=4)
    # greedy would cut [a0 a1 a2 b0][b1 b2]; the braid-aware cutter follows
    # the switch: [a0 a1 a2][b0 b1 b2]
    assert groups == [
        ["beat:a0", "beat:a1", "beat:a2"],
        ["beat:b0", "beat:b1", "beat:b2"],
    ]


def test_collapse_cap_without_a_switch_cuts_at_the_cap():
    from questfoundry.pipeline import passages as pc

    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    _chain(g, [(f"a{i}", da, pa, i == 5) for i in range(6)])
    groups = pc.collapse_groups(g, max_beats=4)
    assert [len(grp) for grp in groups] == [4, 2]  # the pre-braid behavior


def test_thread_switch_definition():
    from questfoundry.pipeline import passages as pc

    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    _chain(g, [("a0", da, pa, False), ("b0", db, pb, False), ("b1", db, pb, True)])
    assert pc.thread_switch(g, "beat:a0", "beat:b0")  # different storylines
    assert not pc.thread_switch(g, "beat:b0", "beat:b1")  # same storyline
    # a beat with no storyline (bridge-like) switches against anything
    from questfoundry.models.base import Stage as St
    from questfoundry.models.structure import Beat, BeatClass, StructuralPurpose

    mutations.add_beat(
        g,
        Beat(
            id="beat:bridge",
            created_by=St.GROW,
            summary="b",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.BRIDGE,
        ),
        [],
    )
    assert pc.thread_switch(g, "beat:b1", "beat:bridge")


def test_stretch_seam_pick_prefers_a_nearby_switch_over_the_exact_middle():
    from questfoundry.pipeline import passages as pc

    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    # a2 -> a3 sits at the middle (same storyline); a4 -> b0 is a switch
    # two seams away — the switch wins within the two-seam slack
    _chain(
        g,
        [(f"a{i}", da, pa, False) for i in range(5)]
        + [("b0", db, pb, False), ("b1", db, pb, False)]
        + [("ac", da, pa, True), ("bc", db, pb, True)],
    )
    beats = [f"beat:a{i}" for i in range(5)] + ["beat:b0", "beat:b1"]
    pos = {b: i for i, b in enumerate(beats)}
    seams = [(beats[i], beats[i + 1]) for i in range(len(beats) - 1)]
    picked = pc.pick_stretch_seam(g, seams, pos, len(beats) / 2)
    assert picked == ("beat:a4", "beat:b0")  # the switch, not the mid-block cut
    # with no switch in reach, the nearest-middle rule is the fallback
    same_thread = seams[:4]  # a0..a4 seams only
    assert pc.pick_stretch_seam(g, same_thread, pos, len(beats) / 2) == (
        "beat:a3",
        "beat:a4",
    )  # nearest the middle (mid 3.5 -> pos 3 wins)


def test_fine_tuning_takes_switch_seams_first():
    from questfoundry.pipeline import passages as pc

    g = StoryGraph()
    da, pa, _ = make_dilemma(g, "aa", explore=1)
    db, pb, _ = make_dilemma(g, "bb", explore=1)
    _chain(
        g,
        [
            ("a0", da, pa, False),
            ("a1", da, pa, False),
            ("b0", db, pb, False),
            ("b1", db, pb, False),
            ("ac", da, pa, True),
            ("bc", db, pb, True),
        ],
    )
    ordered = [
        ("beat:a0", "beat:a1"),  # mid-block
        ("beat:a1", "beat:b0"),  # switch
        ("beat:b0", "beat:b1"),  # mid-block
    ]
    result = pc.switch_seams_first(g, ordered)
    assert result[0] == ("beat:a1", "beat:b0")
    # original order preserved within each class
    assert result[1:] == [("beat:a0", "beat:a1"), ("beat:b0", "beat:b1")]
