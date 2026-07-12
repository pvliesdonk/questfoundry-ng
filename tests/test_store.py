"""Store-level GraphError contract (the error-message audit, 2026-07-12):
a store write that rejects a bad reference raises GraphError — a KeyError
subclass the runner catches as repairable — with a recovery_action, never
a bare, uncaught KeyError. Tests of the store module may call its private
write surface; nothing else may (iron rule 1)."""

from __future__ import annotations

import pytest

from questfoundry.graph.store import GraphError, StoryGraph
from questfoundry.models.base import Edge, EdgeKind, Stage
from questfoundry.models.structure import Beat, BeatClass, StructuralPurpose


def _beat(slug: str) -> Beat:
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.SEED,
        summary="s",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.SETUP,
    )


def test_duplicate_node_id_raises_graph_error_with_recovery():
    g = StoryGraph()
    g._add_node(_beat("a"))
    with pytest.raises(GraphError, match="already used") as exc:
        g._add_node(_beat("a"))
    assert "fresh, unique id" in str(exc.value)  # recovery_action


def test_edge_missing_endpoint_raises_graph_error_with_recovery():
    g = StoryGraph()
    g._add_node(_beat("a"))
    with pytest.raises(GraphError, match="not a known node") as exc:
        g._add_edge(Edge(kind=EdgeKind.PREDECESSOR, src="beat:a", dst="beat:missing"))
    assert "reference an existing node id" in str(exc.value)  # recovery_action


def test_duplicate_edge_raises_graph_error_with_recovery():
    g = StoryGraph()
    g._add_node(_beat("a"))
    g._add_node(_beat("b"))
    g._add_edge(Edge(kind=EdgeKind.PREDECESSOR, src="beat:a", dst="beat:b"))
    with pytest.raises(GraphError, match="already exists") as exc:
        g._add_edge(Edge(kind=EdgeKind.PREDECESSOR, src="beat:a", dst="beat:b"))
    assert "do not" in str(exc.value)  # recovery_action


def test_graph_error_is_a_keyerror_subclass():
    """add_beat's existing `except KeyError` converter must still catch it."""
    assert issubclass(GraphError, KeyError)
