"""M1 exit criterion: `run --to seed` produces a valid triaged, scaffolded
story from a one-paragraph premise, fully offline via recorded fixtures."""

from pathlib import Path

import pytest

from questfoundry.graph import queries
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.llm import LLMAdapter, MockProvider
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Path as StoryPath
from questfoundry.models.structure import Beat
from questfoundry.pipeline.runner import run_pipeline
from questfoundry.pipeline.stages import IMPLS
from questfoundry.project import load_project, save_project, scaffold_project

FIXTURES = Path(__file__).parent / "fixtures" / "keeper"

PREMISE = (
    "A lighthouse keeper discovers that the light is the only thing keeping "
    "something in the sea asleep. When a visiting cartographer offers her a way "
    "off the rock, she must decide what she owes the coast, and what she owes herself."
)


@pytest.fixture()
def reports_and_project(tmp_path):
    project = scaffold_project(tmp_path / "keeper", name="The Keeper's Bargain", scope="micro")
    project.vision.premise = PREMISE
    save_project(project)
    adapter = LLMAdapter(
        MockProvider(FIXTURES),
        {"architect": "fixture-model", "writer": "fixture-model", "utility": "fixture-model"},
        ledger_path=project.root / "reports" / "ledger.jsonl",
    )
    reports = run_pipeline(project, Stage.SEED, IMPLS, adapter)
    return reports, project


def test_pipeline_reaches_seed(reports_and_project):
    reports, project = reports_and_project
    assert [r.stage for r in reports] == [Stage.DREAM, Stage.BRAINSTORM, Stage.SEED]
    assert all(r.success for r in reports), [r.error or r.issues for r in reports]
    assert project.stage == Stage.SEED


def test_seeded_story_passes_all_gates(reports_and_project):
    _, project = reports_and_project
    issues = run_checks(project.graph, project.vision, project.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []


def test_seeded_structure_shape(reports_and_project):
    _, project = reports_and_project
    g = project.graph
    assert len(g.nodes_of(StoryPath)) == 4
    assert len(g.nodes_of(Beat)) == 15
    # each explored path has exactly one commit beat, wired by the engine
    for path in g.nodes_of(StoryPath):
        assert queries.commit_beat(g, path.id) is not None
    # SEED wired intra-dilemma Y edges only: setup chain + two Y scaffolds
    # -> 3 disconnected components -> 3 roots (GROW interleaves in M2)
    assert len(queries.roots(g)) == 3
    # ordering relation recorded
    assert g.has_edge(EdgeKind.WRAPS, "dilemma:bargain", "dilemma:truth")


def test_seeded_project_roundtrips(reports_and_project):
    _, project = reports_and_project
    reloaded = load_project(project.root)
    assert reloaded.stage == Stage.SEED
    assert len(reloaded.graph.nodes_of(Beat)) == 15
    issues = run_checks(reloaded.graph, reloaded.vision, reloaded.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []


def test_checkpoints_and_ledger_written(reports_and_project):
    _, project = reports_and_project
    for stage in ("dream", "brainstorm", "seed"):
        assert (project.root / "snapshots" / stage / "project.yaml").exists()
        assert (project.root / "reports" / f"{stage}.md").exists()
    ledger = (project.root / "reports" / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 5  # dream 1 + brainstorm 1 + seed 3, no repairs
