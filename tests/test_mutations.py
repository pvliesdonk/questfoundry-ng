import pytest

from questfoundry.graph import mutations, queries
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.structure import IntersectionGroup
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat


def test_cross_dilemma_dual_belongs_to_is_rejected():
    g = StoryGraph()
    d1, p1a, _ = make_dilemma(g, "one")
    d2, p2a, _ = make_dilemma(g, "two")
    with pytest.raises(MutationError, match="cross-dilemma"):
        mutations.add_beat(g, narrative_beat("bad", d1), [p1a, p2a])


def test_commit_beat_must_belong_to_one_path():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    from questfoundry.models.structure import ImpactEffect

    with pytest.raises(MutationError, match="exactly one path"):
        mutations.add_beat(g, narrative_beat("bad", d, ImpactEffect.COMMITS), [pa, pb])


def test_ordering_rejects_cycles():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    with pytest.raises(MutationError, match="cycle"):
        mutations.add_ordering(g, "beat:one-post-a", "beat:one-pre")


def test_remove_ordering_requires_an_existing_edge():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    from questfoundry.models.base import EdgeKind

    mutations.remove_ordering(g, "beat:one-pre", "beat:one-commit-a")
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:one-pre", "beat:one-commit-a")
    with pytest.raises(MutationError, match="no ordering"):
        mutations.remove_ordering(g, "beat:one-pre", "beat:one-commit-a")


def test_freeze_blocks_beat_removal():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.remove_beat(g, "beat:one-post-a")  # fine before freeze
    mutations.add_beat(g, narrative_beat("one-post-a", d, is_ending=True), [pa])
    mutations.add_ordering(g, "beat:one-commit-a", "beat:one-post-a")
    mutations.freeze_topology(g)
    with pytest.raises(MutationError, match="frozen"):
        mutations.remove_beat(g, "beat:one-post-a")


def test_intersection_rejects_same_dilemma_members():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    group = IntersectionGroup(id="intersection:x", created_by=Stage.GROW)
    with pytest.raises(MutationError, match="dilemma"):
        mutations.add_intersection(g, group, ["beat:one-commit-a", "beat:one-pre"])


def test_answer_cannot_be_explored_twice():
    g = StoryGraph()
    make_dilemma(g, "one")
    from questfoundry.models.drama import Path as StoryPath

    with pytest.raises(MutationError, match="already explored"):
        mutations.add_path(g, StoryPath(id="path:dup", created_by=Stage.SEED), "answer:one-a", [])


def test_freeze_records_forks_and_convergence():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    record = mutations.freeze_topology(g)
    assert record.forks[d] == ["beat:one-commit-a", "beat:one-commit-b"]
    assert d not in record.convergences  # posts are endings; paths never rejoin
    assert queries.commit_beats(g, pa) == ["beat:one-commit-a"]
