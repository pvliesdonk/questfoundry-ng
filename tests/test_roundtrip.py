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


def test_roundtrip_preserves_intersections_and_child_provenance(vision, tmp_path):
    """Intersection groups reach disk, and answers/consequences keep a
    created_by that differs from their parent's (regression: both were
    silently dropped by save_project)."""
    from questfoundry.graph import mutations
    from questfoundry.graph.store import StoryGraph
    from questfoundry.models.base import Stage
    from questfoundry.models.structure import IntersectionGroup
    from tests.conftest import make_dilemma, make_y_scaffold

    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "one")
    d2, p2a, p2b = make_dilemma(g, "two")
    make_y_scaffold(g, "one", d1, p1a, p1b)
    make_y_scaffold(g, "two", d2, p2a, p2b)
    mutations.add_intersection(
        g,
        IntersectionGroup(
            id="intersection:shared-scene",
            created_by=Stage.GROW,
            location="location:dock",
            rationale="both pre-commit scenes happen at the dock",
        ),
        ["beat:one-pre", "beat:two-pre"],
    )
    # off-default provenance on embedded children
    g.node("answer:one-a").created_by = Stage.SEED
    g.node("consequence:two-b").created_by = Stage.GROW

    save_project(Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g))
    reloaded = load_project(tmp_path)
    assert graph_signature(reloaded.graph) == graph_signature(g)
    assert reloaded.graph.node("answer:one-a").created_by == Stage.SEED
    assert reloaded.graph.node("consequence:two-b").created_by == Stage.GROW


def test_roundtrip_preserves_hints_and_flexibility(vision, tmp_path):
    from questfoundry.graph.store import StoryGraph
    from questfoundry.models.base import Stage
    from questfoundry.models.structure import HintPosition, TemporalHint
    from tests.conftest import make_dilemma, make_y_scaffold

    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "one")
    d2, p2a, p2b = make_dilemma(g, "two")
    make_y_scaffold(g, "one", d1, p1a, p1b)
    make_y_scaffold(g, "two", d2, p2a, p2b)
    beat = g.node("beat:one-pre")
    beat.temporal_hints = [TemporalHint(dilemma=d2, position=HintPosition.BEFORE_COMMIT)]
    beat.flexibility = "this scene could happen at the dock"

    save_project(Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g))
    reloaded = load_project(tmp_path)
    assert graph_signature(reloaded.graph) == graph_signature(g)
    loaded = reloaded.graph.node("beat:one-pre")
    assert loaded.temporal_hints == beat.temporal_hints
    assert loaded.flexibility == beat.flexibility


def test_save_prunes_removed_nodes(vision, tmp_path):
    """Violating construction (crash-resumed medium live run, 2026-07-09):
    the weave removes the template Y beats, but save_project left their
    files on disk — reloading resurrected them as orphan roots still
    carrying commit impacts (I9 fork drift, duplicate commits, I6 x24).
    Saving must delete per-node files whose node is gone."""
    from questfoundry.graph.store import StoryGraph
    from questfoundry.models.base import Stage
    from tests.test_multihard import realize_first, two_hard_story

    g = StoryGraph()
    two_hard_story(g)
    project = Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)
    save_project(project)  # the template Y reaches disk at the SEED checkpoint
    assert (tmp_path / "graph" / "beats" / "twist-commit-a.yaml").exists()

    realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")  # removes the template Y
    save_project(project)
    assert not (tmp_path / "graph" / "beats" / "twist-commit-a.yaml").exists()
    reloaded = load_project(tmp_path)
    assert graph_signature(reloaded.graph) == graph_signature(g)


def test_roundtrip_is_lossless(golden, tmp_path):
    save_project(
        Project(
            root=tmp_path,
            name=golden.name,
            stage=golden.stage,
            vision=golden.vision,
            graph=golden.graph,
            voice=golden.voice,
            ifid=golden.ifid,
        )
    )
    reloaded = load_project(tmp_path)
    assert reloaded.name == golden.name
    assert reloaded.stage == golden.stage
    assert reloaded.vision == golden.vision
    assert reloaded.voice == golden.voice
    assert reloaded.ifid == golden.ifid
    assert graph_signature(reloaded.graph) == graph_signature(golden.graph)


def test_roundtrip_preserves_prose_as_sibling_files(golden, tmp_path):
    assert golden.voice is not None  # the golden story carries a voice
    arrival = golden.graph.node("passage:p-arrival")
    assert arrival.prose.strip()
    save_project(
        Project(
            root=tmp_path,
            name=golden.name,
            stage=golden.stage,
            vision=golden.vision,
            graph=golden.graph,
            voice=golden.voice,
        )
    )
    # prose is a sibling markdown file, never part of the passage YAML
    assert (tmp_path / "prose" / "p-arrival.md").read_text() == arrival.prose
    assert "prose" not in (tmp_path / "graph" / "passages" / "p-arrival.yaml").read_text()
    reloaded = load_project(tmp_path)
    assert reloaded.graph.node("passage:p-arrival").prose == arrival.prose
