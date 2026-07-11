"""Load -> save -> reload must be lossless (design principle 5)."""

import pytest

from questfoundry.models.base import Stage
from questfoundry.models.craft import CraftConfig
from questfoundry.project import load_project, save_project
from questfoundry.project.io import Project, ProjectError, scaffold_project


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
    # (prose_summary — the FILL-facing note — stays ON the YAML by design)
    assert (tmp_path / "prose" / "p-arrival.md").read_text() == arrival.prose
    yaml_text = (tmp_path / "graph" / "passages" / "p-arrival.yaml").read_text()
    assert "\nprose:" not in yaml_text and not yaml_text.startswith("prose:")
    assert "\nprose_summary:" in yaml_text
    reloaded = load_project(tmp_path)
    assert reloaded.graph.node("passage:p-arrival").prose == arrival.prose


def _digest(stage: str, note: str = "") -> str:
    return f"---\nstage: {stage}\nfingerprint: abc123\n---\n\nDigest body {note}.\n"


def test_craft_config_round_trips(vision, tmp_path):
    from questfoundry.graph.store import StoryGraph

    craft = CraftConfig(corpus="corpus/", folders=["voice"], top_k=6)
    save_project(
        Project(
            root=tmp_path, name="t", stage=Stage.DREAM, vision=vision,
            graph=StoryGraph(), craft=craft,
        )
    )
    reloaded = load_project(tmp_path)
    assert reloaded.craft == craft
    assert "craft" in (tmp_path / "project.yaml").read_text()


def test_research_digests_round_trip(vision, tmp_path):
    from questfoundry.graph.store import StoryGraph

    research = {"dream": _digest("dream"), "brainstorm": _digest("brainstorm", "two")}
    save_project(
        Project(
            root=tmp_path, name="t", stage=Stage.BRAINSTORM, vision=vision,
            graph=StoryGraph(), research=research,
        )
    )
    assert (tmp_path / "research" / "dream.md").read_text() == research["dream"]
    assert (tmp_path / "research" / "brainstorm.md").read_text() == research["brainstorm"]
    reloaded = load_project(tmp_path)
    assert reloaded.research == research


def test_research_prune_removes_stale_files(vision, tmp_path):
    from questfoundry.graph.store import StoryGraph

    project = Project(
        root=tmp_path, name="t", stage=Stage.BRAINSTORM, vision=vision,
        graph=StoryGraph(),
        research={"dream": _digest("dream"), "brainstorm": _digest("brainstorm")},
    )
    save_project(project)
    assert (tmp_path / "research" / "brainstorm.md").exists()

    project.research = {"dream": _digest("dream")}
    save_project(project)
    assert not (tmp_path / "research" / "brainstorm.md").exists()
    assert (tmp_path / "research" / "dream.md").exists()


def test_research_bad_filename_raises(tmp_path):
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "bogus.md").write_text(_digest("dream"), encoding="utf-8")
    (tmp_path / "project.yaml").write_text("name: t\nstage: dream\n", encoding="utf-8")
    (tmp_path / "vision.yaml").write_text(
        "premise: test\ngenre: test\ntone: test\n", encoding="utf-8"
    )
    with pytest.raises(ProjectError):
        load_project(tmp_path)


def test_research_missing_frontmatter_raises(tmp_path):
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "dream.md").write_text("no frontmatter here\n", encoding="utf-8")
    (tmp_path / "project.yaml").write_text("name: t\nstage: dream\n", encoding="utf-8")
    (tmp_path / "vision.yaml").write_text(
        "premise: test\ngenre: test\ntone: test\n", encoding="utf-8"
    )
    with pytest.raises(ProjectError):
        load_project(tmp_path)


def test_research_digest_for_later_stage_survives_save(vision, tmp_path):
    """A digest for a stage the project hasn't reached yet (e.g. seeded
    ahead by a hand edit, or left over from a rerun) round-trips
    untouched -- io.py never filters research by project.stage."""
    from questfoundry.graph.store import StoryGraph

    research = {"fill": _digest("fill")}
    project = Project(
        root=tmp_path, name="t", stage=Stage.DREAM, vision=vision,
        graph=StoryGraph(), research=research,
    )
    save_project(project)
    reloaded = load_project(tmp_path)
    assert reloaded.stage == Stage.DREAM
    assert reloaded.research == research
    save_project(reloaded)
    assert (tmp_path / "research" / "fill.md").read_text() == research["fill"]


def test_project_without_craft_or_research_is_byte_identical(vision, tmp_path):
    """M6 must be invisible without a craft: block: no new directory, no
    new project.yaml key, for a project that never sets craft/research."""
    from questfoundry.graph.store import StoryGraph

    project = Project(root=tmp_path, name="t", stage=Stage.DREAM, vision=vision, graph=StoryGraph())
    save_project(project)
    assert not (tmp_path / "research").exists()
    meta_text = (tmp_path / "project.yaml").read_text()
    assert "craft" not in meta_text

    reloaded = load_project(tmp_path)
    assert reloaded.craft is None
    assert reloaded.research == {}
    save_project(reloaded)
    assert not (tmp_path / "research").exists()
    assert (tmp_path / "project.yaml").read_text() == meta_text


def test_scaffold_project_does_not_create_research_dir(tmp_path):
    scaffold_project(tmp_path / "proj", "t", "micro")
    assert not (tmp_path / "proj" / "research").exists()
