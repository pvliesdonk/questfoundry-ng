"""M1 exit criterion: `run --to seed` produces a valid triaged, scaffolded
story from a one-paragraph premise, fully offline via recorded fixtures.
M2 exit criterion: `run --to grow` continues to a woven, frozen beat DAG
with four complete arcs."""

from pathlib import Path

import pytest

from questfoundry.graph import queries
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.llm import LLMAdapter, MockProvider
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Path as StoryPath
from questfoundry.models.structure import Beat, IntersectionGroup, StateFlag
from questfoundry.pipeline.runner import run_pipeline
from questfoundry.pipeline.stages import IMPLS
from questfoundry.play import walk_all_arcs
from questfoundry.project import load_project, save_project, scaffold_project

FIXTURES = Path(__file__).parent / "fixtures" / "keeper"

PREMISE = (
    "A lighthouse keeper discovers that the light is the only thing keeping "
    "something in the sea asleep. When a visiting cartographer offers her a way "
    "off the rock, she must decide what she owes the coast, and what she owes herself."
)


def _run_to(tmp_path, stage: Stage):
    project = scaffold_project(tmp_path / "keeper", name="The Keeper's Bargain", scope="micro")
    project.vision.premise = PREMISE
    save_project(project)
    adapter = LLMAdapter(
        MockProvider(FIXTURES),
        {"architect": "fixture-model", "writer": "fixture-model", "utility": "fixture-model"},
        ledger_path=project.root / "reports" / "ledger.jsonl",
    )
    reports = run_pipeline(project, stage, IMPLS, adapter)
    return reports, project


@pytest.fixture()
def reports_and_project(tmp_path):
    return _run_to(tmp_path, Stage.SEED)


@pytest.fixture()
def grown(tmp_path):
    return _run_to(tmp_path, Stage.GROW)


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
    assert len(g.nodes_of(Beat)) == 16
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
    assert len(reloaded.graph.nodes_of(Beat)) == 16
    issues = run_checks(reloaded.graph, reloaded.vision, reloaded.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []


def test_seed_records_hints_and_flexibility(reports_and_project):
    _, project = reports_and_project
    tremor = project.graph.node("beat:the-tremor")
    assert [h.dilemma for h in tremor.temporal_hints] == ["dilemma:truth"]
    assert "readings" in tremor.flexibility
    soundings = project.graph.node("beat:false-soundings")
    assert soundings.flexibility


def test_checkpoints_and_ledger_written(reports_and_project):
    _, project = reports_and_project
    for stage in ("dream", "brainstorm", "seed"):
        assert (project.root / "snapshots" / stage / "project.yaml").exists()
        assert (project.root / "reports" / f"{stage}.md").exists()
    ledger = (project.root / "reports" / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 5  # dream 1 + brainstorm 1 + seed 3, no repairs


# -- M2: GROW -----------------------------------------------------------------


def test_pipeline_reaches_grow(grown):
    reports, project = grown
    assert [r.stage for r in reports] == [
        Stage.DREAM,
        Stage.BRAINSTORM,
        Stage.SEED,
        Stage.GROW,
    ]
    assert all(r.success for r in reports), [r.error or r.issues for r in reports]
    assert project.stage == Stage.GROW


def test_grow_weaves_one_dag_with_four_complete_arcs(grown):
    _, project = grown
    g = project.graph
    assert len(queries.roots(g)) == 1
    walks = walk_all_arcs(g)
    assert len(walks) == 4
    for walk in walks:
        assert walk.problems == []
        assert walk.ending is not None
        # every arc commits both dilemmas and grants exactly its two flags
        assert len(walk.flags) == 2


def test_grow_derives_a_flag_per_consequence(grown):
    _, project = grown
    g = project.graph
    flags = g.nodes_of(StateFlag)
    assert len(flags) == 4
    for flag in flags:
        (cid,) = g.out_ids(flag.id, EdgeKind.DERIVED_FROM)
        assert cid.startswith("consequence:")
        assert queries.grant_beat(g, flag.id) is not None


def test_grow_records_the_intersection(grown):
    _, project = grown
    g = project.graph
    (grp,) = g.nodes_of(IntersectionGroup)
    members = sorted(g.in_ids(grp.id, EdgeKind.IN_GROUP))
    assert members == ["beat:false-soundings", "beat:the-tremor"]
    # placed adjacently, as the group demands
    assert g.has_edge(EdgeKind.PREDECESSOR, members[0], members[1])


def test_grow_freezes_topology(grown):
    _, project = grown
    g = project.graph
    assert g.frozen is not None
    # the soft dilemma converges on a shared beat, not a branch beat
    assert g.frozen.convergences == {"dilemma:truth": "beat:the-offer"}
    assert (project.root / "graph" / "freeze.yaml").exists()


def test_grow_bridge_pass_skipped_when_no_gaps(grown):
    reports, project = grown
    grow_report = reports[-1]
    bridge = next(p for p in grow_report.passes if p.name == "bridge")
    assert bridge.attempts == 0
    assert bridge.applied == ["skipped: no entity-disjoint adjacencies"]
    ledger = (project.root / "reports" / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 7  # 5 through SEED + intersections + weave


def test_grown_project_roundtrips_frozen(grown):
    _, project = grown
    reloaded = load_project(project.root)
    assert reloaded.stage == Stage.GROW
    assert reloaded.graph.frozen == project.graph.frozen
    issues = run_checks(reloaded.graph, reloaded.vision, reloaded.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []


# -- M3: POLISH ---------------------------------------------------------------


@pytest.fixture()
def polished(tmp_path):
    return _run_to(tmp_path, Stage.POLISH)


def test_pipeline_reaches_polish(polished):
    reports, project = polished
    assert reports[-1].stage == Stage.POLISH
    assert all(r.success for r in reports), [r.error or r.issues for r in reports]
    assert project.stage == Stage.POLISH
    ledger = (project.root / "reports" / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 10  # 7 through GROW + finalize + passages + audit


def test_polish_builds_the_passage_layer(polished):
    _, project = polished
    g = project.graph
    from questfoundry.models.presentation import Passage

    passages = g.nodes_of(Passage)
    assert len(passages) == 8
    endings = sorted(p.ending.title for p in passages if p.ending)
    assert endings == ["The Long Watch", "The Wide Water"]
    # residue beats on both sides of the truth convergence, flag-gated
    residue = [
        b
        for b in g.nodes_of(Beat)
        if b.beat_class.value == "structural" and b.purpose and b.purpose.value == "residue"
    ]
    assert sorted(r.requires_flags[0] for r in residue) == [
        "flag:elias-knows",
        "flag:lie-between",
    ]
    # the audit kept ending passages inside the I12 cap by marking
    # the truth flags irrelevant decades later
    long_watch = next(p for p in passages if p.ending and p.ending.id == "e-long-watch")
    assert long_watch.irrelevant_flags == ["flag:elias-knows", "flag:lie-between"]


def test_polished_story_plays_four_distinct_journeys(polished):
    _, project = polished
    from questfoundry.play import Player

    endings = set()
    routes = set()
    for first in (0, 1):
        for last in (0, 1):
            player = Player(project.graph)
            player.choose(first)  # tell or hide
            while player.ending is None:
                player.choose(last if len(player.choices()) > 1 else 0)
            endings.add(player.ending.title)
            routes.add(tuple(player.visited))
    assert endings == {"The Long Watch", "The Wide Water"}
    assert len(routes) == 4


def test_polished_project_roundtrips(polished):
    _, project = polished
    reloaded = load_project(project.root)
    assert reloaded.stage == Stage.POLISH
    issues = run_checks(reloaded.graph, reloaded.vision, reloaded.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []


# -- M4: FILL & first exports --------------------------------------------------


@pytest.fixture()
def filled(tmp_path):
    return _run_to(tmp_path, Stage.FILL)


def test_pipeline_reaches_fill_through_one_review_round(filled):
    reports, project = filled
    fill = reports[-1]
    assert fill.stage == Stage.FILL and fill.success, fill.error or fill.issues
    assert project.stage == Stage.FILL
    by_name = {p.name: p for p in fill.passes}
    assert by_name["voice"].attempts == 1
    # the first-written passage failed review once and was rewritten
    assert by_name["write:p-wrong-depths"].attempts == 2
    ledger = (project.root / "reports" / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 29  # 10 through POLISH + voice + 8x(write+review) + 1 revision pair


def test_fill_wrote_every_passage_within_budget(filled):
    _, project = filled
    from questfoundry.models.presentation import Passage

    lo, hi = project.vision.preset.words_per_passage
    for p in project.graph.nodes_of(Passage):
        count = len(p.prose.split())
        assert lo <= count <= hi, f"{p.id}: {count} words"
    assert project.voice is not None
    assert (project.root / "voice.yaml").exists()
    assert (project.root / "prose" / "p-the-offer.md").exists()


def test_fill_micro_details_landed_on_base_state(filled):
    _, project = filled
    keeper = project.graph.node("character:keeper")
    cartographer = project.graph.node("character:cartographer")
    assert "habit" in keeper.base or "habit" in cartographer.base


def test_filled_story_exports_and_replays(filled):
    _, project = filled
    from questfoundry.export.html import build_html
    from questfoundry.export.runtime_json import build_runtime, validate_runtime
    from questfoundry.export.twee import build_twee

    data = build_runtime(project)
    assert validate_runtime(data) == []
    html = build_html(project)
    assert '"questfoundry-runtime"' in html
    twee = build_twee(project, "E2E-IFID")
    assert ":: p-wrong-depths" in twee

    # the runtime document alone supports all four journeys
    endings = set()
    for first in (0, 1):
        for last in (0, 1):
            at, flags = data["start"], set()
            while data["passages"][at]["ending"] is None:
                offered = [
                    c
                    for c in data["passages"][at]["choices"]
                    if set(c["requires"]) <= flags
                ]
                pick = offered[first if at == data["start"] else (last if len(offered) > 1 else 0)]
                flags |= set(pick["grants"])
                at = pick["to"]
            endings.add(data["passages"][at]["ending"]["title"])
    assert endings == {"The Long Watch", "The Wide Water"}


def test_filled_project_roundtrips(filled):
    _, project = filled
    reloaded = load_project(project.root)
    assert reloaded.stage == Stage.FILL
    assert reloaded.voice == project.voice
    issues = run_checks(reloaded.graph, reloaded.vision, reloaded.stage)
    assert [i for i in issues if i.severity == Severity.ERROR] == []
