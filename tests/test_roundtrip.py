"""Load -> save -> reload must be lossless (design principle 5)."""

from questfoundry.project import load_project, save_project
from questfoundry.project.io import Project


def graph_signature(g):
    import json

    nodes = {node_id: g.node(node_id).model_dump(mode="json") for node_id in _ids(g)}
    edges = sorted(
        (e.kind.value, e.src, e.dst, json.dumps(e.payload, sort_keys=True)) for e in g.edges
    )
    frozen = g.frozen.model_dump(mode="json") if g.frozen else None
    return nodes, edges, frozen


def _ids(g):
    from questfoundry.models.base import Node

    return sorted(n.id for n in g.nodes_of(Node))


def test_roundtrip_is_lossless(golden, tmp_path):
    save_project(
        Project(
            root=tmp_path,
            name=golden.name,
            stage=golden.stage,
            vision=golden.vision,
            graph=golden.graph,
        )
    )
    reloaded = load_project(tmp_path)
    assert reloaded.name == golden.name
    assert reloaded.stage == golden.stage
    assert reloaded.vision == golden.vision
    assert graph_signature(reloaded.graph) == graph_signature(golden.graph)
