"""GROW stage internals: intersection validation, weave choice, flag
derivation, bridge splicing, and the freeze-on-clean-gate contract."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.structure import FlagSource, StateFlag
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import (
    BridgeProposal,
    BridgeSpec,
    IntersectionProposal,
    IntersectionSpec,
    WeaveChoice,
    _bridge_apply,
    _bridge_skip,
    _derive_flags,
    _gaps,
    _intersections_apply,
    _spread,
    _weave_apply,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.test_weave import seeded_story


@pytest.fixture()
def project(tmp_path, vision) -> Project:
    g = StoryGraph()
    seeded_story(g)
    return Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)


def group(members: list[str], id: str = "intersection:x") -> IntersectionProposal:
    return IntersectionProposal(groups=[IntersectionSpec(id=id, members=members)])


def test_intersections_reject_non_shared_members(project):
    with pytest.raises(ApplyError, match="not a shared pre-commit beat"):
        _intersections_apply(group(["beat:main-commit-a", "beat:sub-pre0"]), project)


def test_intersections_reject_same_dilemma_members(project):
    with pytest.raises(mutations.MutationError, match="two beats of dilemma"):
        _intersections_apply(group(["beat:main-pre0", "beat:main-pre1"]), project)


def test_intersections_reject_double_membership(project):
    proposal = IntersectionProposal(
        groups=[
            IntersectionSpec(id="intersection:x", members=["beat:main-pre0", "beat:sub-pre0"]),
            IntersectionSpec(id="intersection:y", members=["beat:main-pre0", "beat:sub-pre1"]),
        ]
    )
    with pytest.raises(ApplyError, match="more than one intersection"):
        _intersections_apply(proposal, project)


def test_empty_intersection_proposal_is_valid(project):
    assert _intersections_apply(IntersectionProposal(groups=[]), project) == [
        "no intersections proposed"
    ]


def test_weave_choice_out_of_range_is_repairable(project):
    with pytest.raises(ApplyError, match="out of range"):
        _weave_apply(WeaveChoice(choice=99), project)


def test_weave_apply_rewires_and_derives_flags(project):
    lines = _weave_apply(WeaveChoice(choice=0), project)
    g = project.graph
    assert len(queries.roots(g)) == 1
    flags = g.nodes_of(StateFlag)
    assert len(flags) == 4  # one per consequence (conftest gives each path one)
    for flag in flags:
        assert flag.source == FlagSource.DILEMMA
        assert g.out_ids(flag.id, EdgeKind.DERIVED_FROM)
    assert any("interleaving #0" in line for line in lines)


def test_gap_detection_and_bridge_splice(project):
    g = project.graph
    planned = weave.plan(g)
    weave.realize(g, planned, weave.candidates(planned)[0])
    # disjoint entity sets across one adjacency -> exactly that gap
    a, b = "beat:main-pre0", "beat:main-pre1"
    g.node(a).entities = ["character:one"]
    g.node(b).entities = ["character:two"]
    assert _gaps(g) == [(a, b)]
    assert _bridge_skip(project) is None

    proposal = BridgeProposal(
        bridges=[
            BridgeSpec(
                gap=0,
                id="beat:crossing",
                summary="s",
                entities=["character:one", "character:two"],  # one from each side
            )
        ]
    )
    _bridge_apply(proposal, project)
    assert not g.has_edge(EdgeKind.PREDECESSOR, a, b)
    assert g.has_edge(EdgeKind.PREDECESSOR, a, "beat:crossing")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:crossing", b)
    assert _gaps(g) == []


def test_bridge_must_cover_each_gap_exactly_once(project):
    g = project.graph
    planned = weave.plan(g)
    weave.realize(g, planned, weave.candidates(planned)[0])
    g.node("beat:main-pre0").entities = ["character:one"]
    g.node("beat:main-pre1").entities = ["character:two"]
    with pytest.raises(ApplyError, match="exactly once"):
        _bridge_apply(BridgeProposal(bridges=[]), project)


def test_bridge_skips_when_no_gaps(project):
    assert _bridge_skip(project) == "no entity-disjoint adjacencies"


def test_derive_flags_is_total_over_explored_paths(project):
    lines = _derive_flags(project.graph)
    assert len(lines) == 4
    derived = {
        e.dst for e in project.graph.edges if e.kind == EdgeKind.DERIVED_FROM
    }
    consequences = {
        e.dst for e in project.graph.edges if e.kind == EdgeKind.HAS_CONSEQUENCE
    }
    assert derived == consequences


def test_spread_keeps_ends_and_order():
    assert _spread(list(range(5)), 8) == [0, 1, 2, 3, 4]
    spread = _spread(list(range(64)), 8)
    assert len(spread) == 8
    assert spread[0] == 0 and spread[-1] == 63
    assert spread == sorted(spread)
