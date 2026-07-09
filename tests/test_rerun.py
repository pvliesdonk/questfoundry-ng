"""Partial regeneration (`qf rerun --keep`, design doc 02 §3): accepted
proposals persist at checkpoint, kept passes re-apply without an LLM
call, and `prepare_rerun` rewinds stage artifacts while preserving the
author's knobs (steering, vision edits)."""

from __future__ import annotations

import pytest
import yaml

from questfoundry.models.base import Stage
from questfoundry.pipeline import PassSpec, StageImpl, runner
from questfoundry.project.io import load_project
from tests.test_runner import (
    TEMPLATE_NAME,
    FakeAdapter,
    VisionProposal,
    _scaffold,
    _use_test_templates,
    _vision_pass,
)


def _dream_impl(pass_name: str = "vision") -> StageImpl:
    return StageImpl(stage=Stage.DREAM, passes=(_vision_pass(pass_name),), gate=lambda p: [])


def test_checkpoint_persists_accepted_proposals(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    adapter = FakeAdapter([VisionProposal(audience="teens")])

    report = runner.run_stage(project, _dream_impl(), adapter)

    assert report.success
    assert report.passes[0].proposal == {"audience": "teens"}
    recorded = runner.recorded_proposals(tmp_path, Stage.DREAM)
    assert recorded == {"vision": {"audience": "teens"}}


def test_recorded_proposals_round_trip_colon_names(tmp_path, monkeypatch):
    """FILL-style pass names carry a colon; the sanitized filename must
    map back to the original name."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    adapter = FakeAdapter([VisionProposal(audience="a")])

    report = runner.run_stage(project, _dream_impl("write:the-lamp"), adapter)

    assert report.success
    assert (tmp_path / "snapshots" / "dream" / "proposals" / "write__the-lamp.json").exists()
    assert "write:the-lamp" in runner.recorded_proposals(tmp_path, Stage.DREAM)


def test_kept_pass_applies_without_llm_call(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    adapter = FakeAdapter([])  # any adapter call would pop from an empty list

    report = runner.run_stage(
        project, _dream_impl(), adapter, keep={"vision": {"audience": "teens"}}
    )

    assert report.success
    assert adapter.prompts == []
    assert report.passes[0].attempts == 0
    assert report.passes[0].applied == ["kept: set audience to 'teens'"]
    assert project.vision.audience == "teens"
    # the kept proposal is re-persisted, so a later rerun can keep it again
    assert runner.recorded_proposals(tmp_path, Stage.DREAM)["vision"] == {"audience": "teens"}


def test_stale_kept_proposal_fails_loud(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    report = runner.run_stage(
        project, _dream_impl(), FakeAdapter([]), keep={"vision": {"wrong_field": 1}}
    )

    assert not report.success
    assert "vision" in (report.error or "")
    assert "no longer matches its schema" in (report.error or "")


def test_stale_kept_proposal_apply_failure_fails_loud(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    def apply(proposal, project):
        from questfoundry.pipeline import ApplyError

        raise ApplyError("the passage this proposal wrote no longer exists")

    spec = PassSpec(
        name="vision",
        role="writer",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=apply,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda p: [])

    report = runner.run_stage(
        project, impl, FakeAdapter([]), keep={"vision": {"audience": "x"}}
    )

    assert not report.success
    assert "no longer applies" in (report.error or "")


def test_stale_kept_proposal_restores_partial_mutation(tmp_path, monkeypatch):
    """Real apply functions mutate incrementally and may raise midway
    (e.g. GROW's intersections); a failing kept proposal must restore
    the project like the ordinary repair path does (PassSpec.apply
    contract)."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    def apply(proposal, project):
        from questfoundry.graph import mutations
        from questfoundry.models.world import Entity
        from questfoundry.pipeline import ApplyError

        mutations.add_entity(
            project.graph,
            Entity(id="character:half", created_by=Stage.BRAINSTORM, name="Half", concept="c"),
        )
        project.vision.audience = "clobbered"
        raise ApplyError("stale after the partial write")

    spec = PassSpec(
        name="vision",
        role="writer",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=apply,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda p: [])

    report = runner.run_stage(
        project, impl, FakeAdapter([]), keep={"vision": {"audience": "x"}}
    )

    assert not report.success
    assert "character:half" not in project.graph
    assert project.vision.audience != "clobbered"


def test_prepare_rerun_restores_predecessor_and_keeps_author_knobs(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    adapter = FakeAdapter([VisionProposal(audience="dream"), VisionProposal(audience="brain")])
    runner.run_stage(project, _dream_impl(), adapter)
    brainstorm = StageImpl(
        stage=Stage.BRAINSTORM, passes=(_vision_pass("cast"),), gate=lambda p: []
    )
    runner.run_stage(project, brainstorm, adapter)
    assert project.stage == Stage.BRAINSTORM

    # author edits after the run: steering (project.yaml) and vision.yaml
    meta_path = tmp_path / "project.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["steering"] = {"brainstorm": "fewer ghosts"}
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))
    vision_path = tmp_path / "vision.yaml"
    vision = yaml.safe_load(vision_path.read_text())
    vision["premise"] = "an edited premise"
    vision_path.write_text(yaml.safe_dump(vision, sort_keys=False))

    runner.prepare_rerun(tmp_path, Stage.BRAINSTORM)

    reloaded = load_project(tmp_path)
    assert reloaded.stage == Stage.DREAM
    assert reloaded.steering == {"brainstorm": "fewer ghosts"}  # knob preserved
    assert reloaded.vision.premise == "an edited premise"  # vision never restored
    # recorded proposals for the rerun target are still available to --keep
    assert "cast" in runner.recorded_proposals(tmp_path, Stage.BRAINSTORM)


def test_prepare_rerun_without_predecessor_snapshot_raises(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    _scaffold(tmp_path)
    with pytest.raises(runner.RunnerError, match="brainstorm.*dream|dream"):
        runner.prepare_rerun(tmp_path, Stage.BRAINSTORM)


def test_prepare_rerun_of_dream_needs_no_snapshot(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    runner.run_stage(project, _dream_impl(), FakeAdapter([VisionProposal(audience="a")]))

    runner.prepare_rerun(tmp_path, Stage.DREAM)

    reloaded = load_project(tmp_path)
    assert reloaded.stage == Stage.NEW
