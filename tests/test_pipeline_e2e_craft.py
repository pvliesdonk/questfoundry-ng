"""M6 exit slice: `run --to seed` grounded in a craft corpus (design doc
02 §1, mini-ADR A13). `tests/fixtures/keeper-craft/calls/` splices a
research-proposal fixture at the head of every stage ahead of the
keeper fixtures' existing calls (positional replay ignores prompt
bytes, so the splice is purely about call *count and order*):

    000 research(dream)      001 dream envision
    002 research(brainstorm) 003 brainstorm cast
    004 research(seed)       005 seed triage  006 seed scaffold  007 seed order

The point of this suite is that M6 is invisible without a `craft:`
block (see `test_pipeline_e2e.py`, untouched by this work) and fully
wired with one."""

from pathlib import Path

import pytest

from questfoundry.graph.validate import Severity, run_checks
from questfoundry.llm import LLMAdapter, MockProvider
from questfoundry.models.base import Stage
from questfoundry.models.craft import CraftConfig
from questfoundry.pipeline.research import digest_meta
from questfoundry.pipeline.runner import run_pipeline
from questfoundry.pipeline.stages import IMPLS
from questfoundry.project import save_project, scaffold_project

FIXTURES = Path(__file__).parent / "fixtures" / "keeper-craft"
CORPUS = Path(__file__).parent / "fixtures" / "corpus"

PREMISE = (
    "A lighthouse keeper discovers that the light is the only thing keeping "
    "something in the sea asleep. When a visiting cartographer offers her a way "
    "off the rock, she must decide what she owes the coast, and what she owes herself."
)


@pytest.fixture()
def reports_and_project(tmp_path):
    project = scaffold_project(tmp_path / "keeper", name="The Keeper's Bargain", scope="micro")
    project.vision.premise = PREMISE
    project.craft = CraftConfig(corpus=str(CORPUS), search_mode="keyword", top_k=2, max_queries=5)
    save_project(project)
    adapter = LLMAdapter(
        MockProvider(FIXTURES),
        {"architect": "fixture-model", "writer": "fixture-model", "utility": "fixture-model"},
        ledger_path=project.root / "reports" / "ledger.jsonl",
    )
    reports = run_pipeline(project, Stage.SEED, IMPLS, adapter)
    return reports, project


def test_pipeline_reaches_seed_with_a_corpus(reports_and_project):
    reports, project = reports_and_project
    assert [r.stage for r in reports] == [Stage.DREAM, Stage.BRAINSTORM, Stage.SEED]
    assert all(r.success for r in reports), [r.error or r.issues for r in reports]
    assert project.stage == Stage.SEED


def test_seeded_story_with_corpus_passes_all_gates(reports_and_project):
    _, project = reports_and_project
    issues = run_checks(project.graph, project.vision, project.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []


def test_research_digests_reach_disk_for_every_stage(reports_and_project):
    _, project = reports_and_project
    for stage in ("dream", "brainstorm", "seed"):
        path = project.root / "research" / f"{stage}.md"
        assert path.exists()
        assert path.read_text(encoding="utf-8").startswith("---\n")


def test_reports_name_the_corpus_fingerprint(reports_and_project):
    _, project = reports_and_project
    for stage in ("dream", "brainstorm", "seed"):
        digest = (project.root / "research" / f"{stage}.md").read_text(encoding="utf-8")
        fingerprint = digest_meta(digest)["corpus_fingerprint"]
        report = (project.root / "reports" / f"{stage}.md").read_text(encoding="utf-8")
        assert fingerprint[:12] in report


def test_research_calls_precede_every_stages_ordinary_passes(reports_and_project):
    reports, _ = reports_and_project
    for report in reports:
        assert report.passes[0].name == "research"
        assert report.passes[0].attempts == 1  # a corpus is configured: it actually ran
