"""GROW's deterministic interleaving core: units, constraints, candidate
enumeration, and spine realization (design doc 02, GROW)."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import DilemmaRole
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    HintPosition,
    ImpactEffect,
    IntersectionGroup,
    StateFlag,
    StructuralPurpose,
    TemporalHint,
)
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import _derive_flags
from tests.conftest import make_dilemma, make_locked_chain, narrative_beat


def scaffold(
    g: StoryGraph,
    slug: str,
    dilemma: str,
    path_a: str,
    path_b: str,
    *,
    pre: int = 2,
    endings: bool = True,
    hints: dict[str, list[TemporalHint]] | None = None,
) -> None:
    """A SEED-shaped Y: pre chain -> per-path commit -> one post beat."""
    prev = None
    for i in range(pre):
        beat = narrative_beat(f"{slug}-pre{i}", dilemma)
        beat.temporal_hints = (hints or {}).get(f"{slug}-pre{i}", [])
        mutations.add_beat(g, beat, [path_a, path_b])
        if prev:
            mutations.add_ordering(g, prev, beat.id)
        prev = beat.id
    for side, path in (("a", path_a), ("b", path_b)):
        commit = narrative_beat(f"{slug}-commit-{side}", dilemma, ImpactEffect.COMMITS)
        post = narrative_beat(f"{slug}-post-{side}", dilemma, is_ending=endings)
        mutations.add_beat(g, commit, [path])
        mutations.add_beat(g, post, [path])
        mutations.add_ordering(g, prev, commit.id)
        mutations.add_ordering(g, commit.id, post.id)


def seeded_story(g: StoryGraph, *, wraps: bool = True) -> None:
    """Setup chain + hard 'main' wrapping soft 'sub' — the micro shape."""
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD)
    d2, p2a, p2b = make_dilemma(g, "sub", role=DilemmaRole.SOFT)
    mutations.add_beat(
        g,
        Beat(
            id="beat:opening",
            created_by=Stage.SEED,
            summary="opening",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.SETUP,
        ),
        [],
    )
    scaffold(g, "main", d1, p1a, p1b)
    scaffold(g, "sub", d2, p2a, p2b, endings=False)
    if wraps:
        mutations.add_dilemma_relation(g, EdgeKind.WRAPS, d1, d2)


def test_candidates_respect_wraps_and_hard_last():
    g = StoryGraph()
    seeded_story(g)
    cands = weave.candidates(weave.plan(g))
    assert cands
    for order in cands:
        assert order[0] == "setup"
        assert order[-1] == "resolve:dilemma:main"
        # wraps: the backbone introduces first, the subplot resolves inside it
        assert order.index("pre:beat:main-pre0") < order.index("pre:beat:sub-pre0")
        assert order.index("resolve:dilemma:sub") < order.index("resolve:dilemma:main")


def test_realize_yields_a_valid_frozen_ready_dag(vision):
    g = StoryGraph()
    seeded_story(g)
    planned = weave.plan(g)
    chosen = weave.candidates(planned)[0]
    weave.realize(g, planned, chosen)
    _derive_flags(g)
    assert len(queries.roots(g)) == 1
    g3 = {"I4", "I5", "I6", "I7", "I8", "I9", "G3-FLAGS"}
    issues = run_checks(g, vision, Stage.GROW)
    assert [i for i in issues if i.severity == Severity.ERROR and i.check in g3] == []
    assert len(queries.arc_selections(g)) == 4


def test_realize_is_a_full_recompute_not_an_append():
    g = StoryGraph()
    seeded_story(g)
    planned = weave.plan(g)
    order = weave.candidates(planned)[0]
    # deterministic first candidate: main-pre1 is followed by sub's units,
    # so SEED's direct pre->commit seam for 'main' must be rewired away
    assert order.index("pre:beat:main-pre1") + 1 == order.index("pre:beat:sub-pre0")
    weave.realize(g, planned, order)
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:main-pre1", "beat:main-commit-a")
    for tail in ("beat:sub-post-a", "beat:sub-post-b"):
        for head in ("beat:main-commit-a", "beat:main-commit-b"):
            assert g.has_edge(EdgeKind.PREDECESSOR, tail, head)
    assert queries.roots(g) == ["beat:opening"]


def test_satisfiable_hint_constrains_candidates():
    g = StoryGraph()
    seeded_story(g)
    # place main's second pre beat after the subplot has fully resolved
    hint = TemporalHint(dilemma="dilemma:sub", position=HintPosition.AFTER_COMMIT)
    beat = g.node("beat:main-pre1")
    assert isinstance(beat, Beat)
    beat.temporal_hints = [hint]
    planned = weave.plan(g)
    assert planned.dropped_hints == []
    for order in weave.candidates(planned):
        assert order.index("resolve:dilemma:sub") < order.index("pre:beat:main-pre1")


def test_unsatisfiable_hint_is_dropped_and_reported():
    g = StoryGraph()
    seeded_story(g)
    # nothing shared can follow the hard fork, so this can never hold
    hint = TemporalHint(dilemma="dilemma:main", position=HintPosition.AFTER_COMMIT)
    beat = g.node("beat:sub-pre0")
    assert isinstance(beat, Beat)
    beat.temporal_hints = [hint]
    planned = weave.plan(g)
    assert any("unsatisfiable" in d for d in planned.dropped_hints)
    assert weave.candidates(planned)


def test_serial_relation_orders_whole_dilemmas():
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD)
    d2, p2a, p2b = make_dilemma(g, "sub", role=DilemmaRole.SOFT)
    d3, p3a, p3b = make_dilemma(g, "sub2", role=DilemmaRole.SOFT)
    scaffold(g, "main", d1, p1a, p1b)
    scaffold(g, "sub", d2, p2a, p2b, endings=False)
    scaffold(g, "sub2", d3, p3a, p3b, endings=False)
    mutations.add_dilemma_relation(g, EdgeKind.SERIAL, d2, d3)
    for order in weave.candidates(weave.plan(g)):
        assert order.index("resolve:dilemma:sub") < order.index("pre:beat:sub2-pre0")


def test_intersection_group_members_stay_adjacent():
    g = StoryGraph()
    seeded_story(g)
    group = IntersectionGroup(id="intersection:shared-scene", created_by=Stage.GROW)
    mutations.add_intersection(g, group, ["beat:main-pre1", "beat:sub-pre0"])
    planned = weave.plan(g)
    key = "group:intersection:shared-scene"
    assert key in planned.units
    orders = weave.candidates(planned)
    weave.realize(g, planned, orders[0])
    members = sorted(["beat:main-pre1", "beat:sub-pre0"])
    assert g.has_edge(EdgeKind.PREDECESSOR, members[0], members[1])


# -- locked storylines (fork-less linear units; design doc 01 §4) ------------


def locked_story(g: StoryGraph) -> tuple[str, str]:
    """seeded_story plus a locked soft dilemma. Returns (dilemma, path)."""
    seeded_story(g)
    dl, path, _ = make_dilemma(g, "lock", explore=1)
    make_locked_chain(g, "lock", dl, path)
    return dl, path


def test_locked_chain_weaves_as_movable_units():
    g = StoryGraph()
    locked_story(g)
    planned = weave.plan(g)
    assert planned.locked_of_beat["beat:lock-lead"] == "dilemma:lock"
    for order in weave.candidates(planned):
        # chain order holds while other units may interleave between links
        assert (
            order.index("pre:beat:lock-lead")
            < order.index("pre:beat:lock-resolve")
            < order.index("pre:beat:lock-after")
        )
        assert order[-1] == "resolve:dilemma:main"


def test_locked_story_realizes_gate_clean(vision):
    g = StoryGraph()
    locked_story(g)
    planned = weave.plan(g)
    weave.realize(g, planned, weave.candidates(planned)[0])
    _derive_flags(g)
    checked = {"I3", "I4", "I5", "I6", "I7", "I8", "I9", "G3-FLAGS", "B1"}
    issues = run_checks(g, vision, Stage.GROW)
    assert [i for i in issues if i.severity == Severity.ERROR and i.check in checked] == []
    # no fork, no arc multiplication: still 2x2, and every arc walks the chain
    selections = queries.arc_selections(g)
    assert len(selections) == 4
    for selection in selections:
        view = queries.arc_view(g, selection)
        assert {"beat:lock-lead", "beat:lock-resolve", "beat:lock-after"} <= view
    # the locked outcome derived no flag
    assert all(f.path != "path:lock-a" for f in g.nodes_of(StateFlag))


def test_wraps_anchors_a_locked_dilemma_at_its_resolution():
    g = StoryGraph()
    dl, _ = locked_story(g)
    mutations.add_dilemma_relation(g, EdgeKind.WRAPS, "dilemma:main", dl)
    for order in weave.candidates(weave.plan(g)):
        assert order.index("pre:beat:main-pre0") < order.index("pre:beat:lock-lead")
        assert order.index("pre:beat:lock-resolve") < order.index("resolve:dilemma:main")


def test_locked_beats_may_intersect_other_dilemmas():
    g = StoryGraph()
    locked_story(g)
    group = IntersectionGroup(id="intersection:collision", created_by=Stage.GROW)
    mutations.add_intersection(g, group, ["beat:main-pre1", "beat:lock-lead"])
    planned = weave.plan(g)
    orders = weave.candidates(planned)
    weave.realize(g, planned, orders[0])
    members = sorted(["beat:main-pre1", "beat:lock-lead"])
    assert g.has_edge(EdgeKind.PREDECESSOR, members[0], members[1])


def test_locked_chain_with_two_resolutions_is_rejected():
    g = StoryGraph()
    seeded_story(g)
    dl, path, _ = make_dilemma(g, "lock", explore=1)
    mutations.add_beat(g, narrative_beat("lock-r1", dl, ImpactEffect.COMMITS), [path])
    mutations.add_beat(g, narrative_beat("lock-r2", dl, ImpactEffect.COMMITS), [path])
    mutations.add_ordering(g, "beat:lock-r1", "beat:lock-r2")
    with pytest.raises(weave.WeaveError, match="resolution beats"):
        weave.plan(g)


def test_zero_hard_dilemmas_are_rejected():
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "one", role=DilemmaRole.SOFT)
    scaffold(g, "one", d1, p1a, p1b, endings=False)
    with pytest.raises(weave.WeaveError, match="hard dilemma"):
        weave.plan(g)


def test_a_locked_hard_dilemma_is_no_backbone():
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "one", role=DilemmaRole.SOFT)
    scaffold(g, "one", d1, p1a, p1b, endings=False)
    dl, path, _ = make_dilemma(g, "lock", role=DilemmaRole.HARD, explore=1)
    make_locked_chain(g, "lock", dl, path)
    with pytest.raises(weave.WeaveError, match="branched hard"):
        weave.plan(g)


def test_partial_order_must_place_every_unit():
    g = StoryGraph()
    seeded_story(g)
    planned = weave.plan(g)
    order = weave.candidates(planned)[0]
    with pytest.raises(weave.WeaveError, match="every unit"):
        weave.realize(g, planned, order[:-1])


def test_unweavable_leftover_beats_are_rejected():
    g = StoryGraph()
    seeded_story(g)
    mutations.add_beat(
        g,
        Beat(
            id="beat:orphan",
            created_by=Stage.SEED,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.EPILOGUE,
        ),
        [],
    )
    with pytest.raises(weave.WeaveError, match="outside any weavable unit"):
        weave.plan(g)
