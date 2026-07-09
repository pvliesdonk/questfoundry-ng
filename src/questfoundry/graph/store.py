"""The typed story graph store.

Read access is open; ALL writes go through `questfoundry.graph.mutations`
(the module-private `_add_node` / `_add_edge` / `_remove_*` methods are
its implementation surface). Note this is a convention, not an enforced
access boundary — Python offers none — so the single-write-path guarantee
is upheld by code review: nothing outside `mutations.py` (and tests of
this module) may call the underscore methods. A ~`long` story is ~10^3
nodes, so everything is in memory and O(V+E) algorithms are fine
(design doc 03 §3).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

from questfoundry.models.base import Edge, EdgeKind, Node

N = TypeVar("N", bound=Node)


class FreezeRecord(BaseModel):
    """Topology fingerprint taken at the end of GROW (invariant I9).

    Frozen beats may never be deleted; dilemma commit forks and soft
    convergence points may never move.
    """

    model_config = ConfigDict(extra="forbid")

    beats: list[str]
    # dilemma id -> its commit beat ids (the fork structure; one commit
    # per path per world once a dilemma resolves inside a hard fork)
    forks: dict[str, list[str]]
    # soft dilemma id -> the single beat per world where its paths
    # rejoin; a world whose rejoin frontier is a deeper hard fork is
    # omitted (those beats are that dilemma's commits, frozen under forks)
    convergences: dict[str, list[str]]

    @field_validator("convergences", mode="before")
    @classmethod
    def _coerce_single_beat(cls, value: dict) -> dict:
        # pre-multi-hard freeze files recorded one beat per dilemma
        return {k: [v] if isinstance(v, str) else v for k, v in value.items()}


class StoryGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._out: dict[tuple[str, EdgeKind], list[Edge]] = defaultdict(list)
        self._in: dict[tuple[str, EdgeKind], list[Edge]] = defaultdict(list)
        self.frozen: FreezeRecord | None = None

    # -- read API ---------------------------------------------------------

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def get(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def nodes_of(self, node_type: type[N]) -> list[N]:
        return [n for n in self._nodes.values() if isinstance(n, node_type)]

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def out_edges(self, src: str, kind: EdgeKind) -> list[Edge]:
        return list(self._out.get((src, kind), ()))

    def in_edges(self, dst: str, kind: EdgeKind) -> list[Edge]:
        return list(self._in.get((dst, kind), ()))

    def out_ids(self, src: str, kind: EdgeKind) -> list[str]:
        return [e.dst for e in self._out.get((src, kind), ())]

    def in_ids(self, dst: str, kind: EdgeKind) -> list[str]:
        return [e.src for e in self._in.get((dst, kind), ())]

    def has_edge(self, kind: EdgeKind, src: str, dst: str) -> bool:
        return any(e.dst == dst for e in self._out.get((src, kind), ()))

    # -- write API (mutations module only) --------------------------------

    def _add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise KeyError(f"duplicate node id {node.id!r}")
        self._nodes[node.id] = node

    def _add_edge(self, edge: Edge) -> None:
        for endpoint in (edge.src, edge.dst):
            if endpoint not in self._nodes:
                raise KeyError(f"edge {edge.key()} references missing node {endpoint!r}")
        if self.has_edge(edge.kind, edge.src, edge.dst):
            raise KeyError(f"duplicate edge {edge.key()}")
        self._edges.append(edge)
        self._out[(edge.src, edge.kind)].append(edge)
        self._in[(edge.dst, edge.kind)].append(edge)

    def _remove_node(self, node_id: str) -> None:
        del self._nodes[node_id]
        self._edges = [e for e in self._edges if node_id not in (e.src, e.dst)]
        for index in (self._out, self._in):
            for key in list(index):
                index[key] = [e for e in index[key] if node_id not in (e.src, e.dst)]
                if not index[key]:
                    del index[key]

    def _remove_edge(self, kind: EdgeKind, src: str, dst: str) -> None:
        def keep(e: Edge) -> bool:
            return e.key() != (kind.value, src, dst)

        before = len(self._edges)
        self._edges = [e for e in self._edges if keep(e)]
        if len(self._edges) == before:
            raise KeyError(f"no such edge {(kind.value, src, dst)}")
        self._out[(src, kind)] = [e for e in self._out[(src, kind)] if keep(e)]
        self._in[(dst, kind)] = [e for e in self._in[(dst, kind)] if keep(e)]
