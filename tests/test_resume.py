"""Crash resume via the in-flight proposal ledger (design doc 02 §3,
mini-ADR A16): accepted passes journal to `inflight/<stage>/` as they
land, an interrupted stage replays them without LLM calls, stale or
torn entries degrade to a live run, and the ledger is voided by any
stage-input change and consumed at the gate-passing checkpoint."""

from __future__ import annotations

import json

import pytest
import yaml

from questfoundry.graph import mutations
from questfoundry.graph.validate import Issue, Severity
from questfoundry.models.base import Stage
from questfoundry.models.world import Entity
from questfoundry.pipeline import ApplyError, PassSpec, StageImpl, runner
from questfoundry.project.io import Project, load_project
from tests.test_runner import (
    TEMPLATE_NAME,
    EntityProposal,
    FakeAdapter,
    VisionProposal,
    _scaffold,
    _use_test_templates,
    _vision_pass,
)


def _entity_pass(name: str) -> PassSpec:
    def apply(proposal: EntityProposal, project: Project) -> list[str]:
        eid = f"character:{proposal.name}"
        mutations.add_entity(
            project.graph,
            Entity(id=eid, created_by=Stage.BRAINSTORM, name=proposal.name.title(), concept="c"),
        )
        return [f"added {eid}"]

    return PassSpec(
        name=name,
        role="writer",
        template=TEMPLATE_NAME,
        schema=EntityProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=apply,
    )


def _two_pass_impl(first: str = "first", second: str = "second") -> StageImpl:
    return StageImpl(
        stage=Stage.DREAM, passes=(_entity_pass(first), _entity_pass(second)), gate=lambda p: []
    )


def _crash_mid_stage(tmp_path, monkeypatch, impl: StageImpl | None = None) -> Project:
    """Run a two-pass stage with only the first response queued: the
    second pass's adapter call raises, simulating a process death after
    pass one landed."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    adapter = FakeAdapter([EntityProposal(name="ada")])
    with pytest.raises(IndexError):
        runner.run_stage(project, impl or _two_pass_impl(), adapter)
    return project


def _seed_ledger(tmp_path, project: Project, name: str, proposal: dict) -> None:
    """Hand-write a ledger entry under the fingerprint the next run will
    compute, as if a crashed run had recorded it."""
    stage_dir = tmp_path / "inflight" / Stage.DREAM.value
    (stage_dir / "proposals").mkdir(parents=True)
    fingerprint = runner._stage_fingerprint(project, "")
    (stage_dir / "fingerprint.json").write_text(json.dumps({"fingerprint": fingerprint}))
    (stage_dir / "proposals" / f"{name.replace(':', '__')}.json").write_text(
        json.dumps({"pass": name, "proposal": proposal})
    )


def test_crash_leaves_ledger_and_untouched_working_tree(tmp_path, monkeypatch):
    _crash_mid_stage(tmp_path, monkeypatch)

    ledger = tmp_path / "inflight" / "dream" / "proposals" / "first.json"
    assert json.loads(ledger.read_text()) == {"pass": "first", "proposal": {"name": "ada"}}
    # nothing but the ledger reached disk: no advance, no snapshot, no nodes
    assert yaml.safe_load((tmp_path / "project.yaml").read_text())["stage"] == "new"
    assert not (tmp_path / "snapshots").exists()
    assert "character:ada" not in load_project(tmp_path).graph


def test_resume_replays_ledgered_pass_without_llm(tmp_path, monkeypatch):
    _crash_mid_stage(tmp_path, monkeypatch)

    project = load_project(tmp_path)
    adapter = FakeAdapter([EntityProposal(name="bo")])  # only the second pass may call
    report = runner.run_stage(project, _two_pass_impl(), adapter)

    assert report.success
    assert len(adapter.prompts) == 1
    assert report.passes[0].attempts == 0
    assert report.passes[0].applied == ["resumed: added character:ada"]
    assert report.passes[1].attempts == 1
    reloaded = load_project(tmp_path)
    assert "character:ada" in reloaded.graph
    assert "character:bo" in reloaded.graph


def test_checkpoint_consumes_the_ledger(tmp_path, monkeypatch):
    _crash_mid_stage(tmp_path, monkeypatch)
    project = load_project(tmp_path)

    report = runner.run_stage(project, _two_pass_impl(), FakeAdapter([EntityProposal(name="bo")]))

    assert report.success
    assert not (tmp_path / "inflight" / "dream").exists()
    # the proposals live in the snapshot now, available to `rerun --keep`
    assert set(runner.recorded_proposals(tmp_path, Stage.DREAM)) == {"first", "second"}


def test_stale_ledger_schema_degrades_to_live(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    _seed_ledger(tmp_path, project, "vision", {"wrong_field": 1})
    impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda p: [])

    report = runner.run_stage(project, impl, FakeAdapter([VisionProposal(audience="teens")]))

    assert report.success
    assert report.passes[0].attempts == 1
    assert report.passes[0].applied[0].startswith("stale in-flight proposal discarded")
    assert project.vision.audience == "teens"


def test_stale_ledger_apply_failure_restores_then_runs_live(tmp_path, monkeypatch):
    """A ledgered proposal whose apply raises midway must restore the
    partial mutation (PassSpec.apply contract) and then run live —
    unlike `--keep`, which fails the stage."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    _seed_ledger(tmp_path, project, "cast", {"name": "stale"})

    def apply(proposal: EntityProposal, project: Project) -> list[str]:
        if proposal.name == "stale":
            mutations.add_entity(
                project.graph,
                Entity(id="character:half", created_by=Stage.BRAINSTORM, name="H", concept="c"),
            )
            raise ApplyError("the beat this proposal cites no longer exists")
        mutations.add_entity(
            project.graph,
            Entity(id="character:good", created_by=Stage.BRAINSTORM, name="G", concept="c"),
        )
        return ["added character:good"]

    spec = PassSpec(
        name="cast",
        role="writer",
        template=TEMPLATE_NAME,
        schema=EntityProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=apply,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda p: [])

    report = runner.run_stage(project, impl, FakeAdapter([EntityProposal(name="fresh")]))

    assert report.success
    assert "character:half" not in project.graph
    assert "character:good" in project.graph


def test_torn_ledger_entry_is_stale_not_fatal(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    _seed_ledger(tmp_path, project, "vision", {"audience": "x"})
    torn = tmp_path / "inflight" / "dream" / "proposals" / "vision.json"
    torn.write_bytes(b'{"pass": "vis')  # crash mid-write of a pre-atomic era
    impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda p: [])

    report = runner.run_stage(project, impl, FakeAdapter([VisionProposal(audience="teens")]))

    assert report.success
    assert report.passes[0].attempts == 1  # ran live; no stale note, no crash


def test_explicit_keep_beats_the_ledger_and_stays_loud(tmp_path, monkeypatch):
    """`--keep` is the author demanding that proposal: it takes
    precedence over a valid ledger entry and a stale keep still fails
    the stage instead of degrading."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    _seed_ledger(tmp_path, project, "vision", {"audience": "ledgered"})
    impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda p: [])

    report = runner.run_stage(
        project, impl, FakeAdapter([]), keep={"vision": {"wrong_field": 1}}
    )

    assert not report.success
    assert "no longer matches its schema" in (report.error or "")


def test_gate_failure_retains_the_ledger_for_a_free_retry(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    impl = StageImpl(
        stage=Stage.DREAM,
        passes=(_vision_pass(),),
        gate=lambda p: [Issue(check="X1", severity=Severity.ERROR, message="broken")],
    )

    first = runner.run_stage(project, impl, FakeAdapter([VisionProposal(audience="teens")]))
    assert not first.success
    assert (tmp_path / "inflight" / "dream" / "proposals" / "vision.json").exists()

    # unchanged inputs: the retry replays free and hits the same gate
    retry_adapter = FakeAdapter([])
    second = runner.run_stage(load_project(tmp_path), impl, retry_adapter)
    assert not second.success
    assert retry_adapter.prompts == []
    assert second.passes[0].applied == ["resumed: set audience to 'teens'"]


def test_prepare_rerun_discards_all_inflight_state(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    runner.run_stage(
        project,
        StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda p: []),
        FakeAdapter([VisionProposal(audience="a")]),
    )
    # a BRAINSTORM run crashes, leaving its ledger behind
    with pytest.raises(IndexError):
        runner.run_stage(
            project,
            StageImpl(
                stage=Stage.BRAINSTORM,
                passes=(_entity_pass("cast"), _entity_pass("more")),
                gate=lambda p: [],
            ),
            FakeAdapter([EntityProposal(name="ada")]),
        )
    assert (tmp_path / "inflight").exists()

    runner.prepare_rerun(tmp_path, Stage.DREAM)

    assert not (tmp_path / "inflight").exists()


def test_input_edit_voids_the_ledger(tmp_path, monkeypatch):
    """An author edit between the crash and the re-run must not replay
    proposals generated against the old inputs — review = edit +
    revalidate wins over resume."""
    _crash_mid_stage(tmp_path, monkeypatch)

    vision_path = tmp_path / "vision.yaml"
    vision = yaml.safe_load(vision_path.read_text())
    vision["premise"] = "an edited premise"
    vision_path.write_text(yaml.safe_dump(vision, sort_keys=False))

    project = load_project(tmp_path)
    adapter = FakeAdapter([EntityProposal(name="ada"), EntityProposal(name="bo")])
    report = runner.run_stage(project, _two_pass_impl(), adapter)

    assert report.success
    assert len(adapter.prompts) == 2  # both passes ran live
    assert all(p.attempts == 1 for p in report.passes)


def test_skip_if_beats_the_ledger(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    _seed_ledger(tmp_path, project, "optional", {"audience": "x"})
    spec = PassSpec(
        name="optional",
        role="architect",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=lambda proposal, project: ["should never run"],
        skip_if=lambda project: "nothing to do",
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda p: [])

    report = runner.run_stage(project, impl, FakeAdapter([]))

    assert report.success
    assert report.passes[0].applied == ["skipped: nothing to do"]


def test_colon_pass_names_round_trip_in_the_ledger(tmp_path, monkeypatch):
    impl = StageImpl(
        stage=Stage.DREAM,
        passes=(_entity_pass("write:the-lamp"), _entity_pass("second")),
        gate=lambda p: [],
    )
    _crash_mid_stage(tmp_path, monkeypatch, impl)

    assert (tmp_path / "inflight" / "dream" / "proposals" / "write__the-lamp.json").exists()

    report = runner.run_stage(
        load_project(tmp_path), impl, FakeAdapter([EntityProposal(name="bo")])
    )
    assert report.success
    assert report.passes[0].name == "write:the-lamp"
    assert report.passes[0].applied == ["resumed: added character:ada"]
