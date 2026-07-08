"""The stage runner loop: render -> complete -> apply (with repair) ->
gate -> checkpoint (design doc 02 §1). No LLM package involved — a fake
adapter stands in for `questfoundry.llm`."""

from __future__ import annotations

import pytest
import yaml
from jinja2 import DictLoader, Environment, StrictUndefined
from pydantic import BaseModel

from questfoundry.graph import mutations
from questfoundry.graph.validate import Issue, Severity
from questfoundry.models.base import Stage
from questfoundry.models.world import Entity
from questfoundry.pipeline import ApplyError, PassSpec, StageImpl, runner
from questfoundry.project.io import Project, load_project, save_project, scaffold_project

TEMPLATE_NAME = "vision.j2"
TEMPLATE_SOURCE = (
    "Audience hint: {{ audience_hint }}\n"
    "Notes: {{ notes }}\n"
    "{% for e in repair_errors %}Repair error: {{ e }}\n{% endfor %}"
)


class VisionProposal(BaseModel):
    audience: str


class EntityProposal(BaseModel):
    name: str


class FakeAdapter:
    """Records every rendered prompt and returns queued responses in order."""

    def __init__(self, responses: list[BaseModel]):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def complete(
        self, *, system: str, prompt: str, schema: type[BaseModel], role: str
    ) -> BaseModel:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def _use_test_templates(monkeypatch) -> None:
    env = Environment(
        loader=DictLoader({TEMPLATE_NAME: TEMPLATE_SOURCE}),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    monkeypatch.setattr(runner, "_environment", lambda: env)


def _scaffold(tmp_path) -> Project:
    """`scaffold_project` currently lands at Stage.DREAM (another
    workstream owns fixing that); the runner's contract starts at NEW."""
    project = scaffold_project(tmp_path, "test-project", "micro")
    project.stage = Stage.NEW
    save_project(project)
    return project


def _vision_pass(name: str = "vision") -> PassSpec:
    def apply(proposal: VisionProposal, project: Project) -> list[str]:
        project.vision.audience = proposal.audience
        return [f"set audience to {proposal.audience!r}"]

    return PassSpec(
        name=name,
        role="architect",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": project.vision.premise},
        apply=apply,
    )


def test_happy_path_advances_saves_and_checkpoints(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda project: [])
    adapter = FakeAdapter([VisionProposal(audience="teens")])

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert project.stage == Stage.DREAM
    assert len(report.passes) == 1
    assert report.passes[0].name == "vision"
    assert report.passes[0].attempts == 1
    assert report.passes[0].applied == ["set audience to 'teens'"]

    reloaded = load_project(tmp_path)
    assert reloaded.stage == Stage.DREAM
    assert reloaded.vision.audience == "teens"

    assert (tmp_path / "snapshots" / "dream" / "vision.yaml").exists()
    assert (tmp_path / "reports" / "dream.md").exists()


def test_repair_loop_restores_graph_and_carries_error_into_prompt(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    calls = {"n": 0}

    def apply(proposal: EntityProposal, project: Project) -> list[str]:
        calls["n"] += 1
        if calls["n"] == 1:
            mutations.add_entity(
                project.graph,
                Entity(id="character:bad", created_by=Stage.BRAINSTORM, name="Bad", concept="c"),
            )
            raise ApplyError("needs fixing")
        mutations.add_entity(
            project.graph,
            Entity(id="character:good", created_by=Stage.BRAINSTORM, name="Good", concept="c"),
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
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda project: [])
    adapter = FakeAdapter([EntityProposal(name="x"), EntityProposal(name="x")])

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert report.passes[0].attempts == 2
    assert len(adapter.prompts) == 2
    assert "needs fixing" in adapter.prompts[1]
    assert "needs fixing" not in adapter.prompts[0]
    assert "character:bad" not in project.graph
    assert "character:good" in project.graph


def test_repairs_exhausted_leaves_project_untouched(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    def apply(proposal: EntityProposal, project: Project) -> list[str]:
        raise ApplyError("always fails")

    spec = PassSpec(
        name="cast",
        role="writer",
        template=TEMPLATE_NAME,
        schema=EntityProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=apply,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda project: [])
    adapter = FakeAdapter([EntityProposal(name="x")] * 10)

    report = runner.run_stage(project, impl, adapter, max_repairs=2)

    assert not report.success
    assert report.error is not None
    assert "cast" in report.error
    assert "always fails" in report.error
    assert project.stage == Stage.NEW

    on_disk = yaml.safe_load((tmp_path / "project.yaml").read_text())
    assert on_disk["stage"] == "new"
    assert not (tmp_path / "snapshots").exists()


def test_gate_failure_blocks_advance_and_snapshot(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    impl = StageImpl(
        stage=Stage.DREAM,
        passes=(_vision_pass(),),
        gate=lambda project: [Issue(check="X1", severity=Severity.ERROR, message="broken")],
    )
    adapter = FakeAdapter([VisionProposal(audience="teens")])

    report = runner.run_stage(project, impl, adapter)

    assert not report.success
    assert project.stage == Stage.NEW
    assert not (tmp_path / "snapshots").exists()

    on_disk = yaml.safe_load((tmp_path / "project.yaml").read_text())
    assert on_disk["stage"] == "new"


def test_precondition_wrong_stage_raises(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    impl = StageImpl(stage=Stage.BRAINSTORM, passes=(_vision_pass(),), gate=lambda project: [])
    adapter = FakeAdapter([VisionProposal(audience="teens")])

    with pytest.raises(runner.RunnerError):
        runner.run_stage(project, impl, adapter)


def test_run_pipeline_advances_then_stops_at_first_failure(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    dream_impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda project: [])
    brainstorm_impl = StageImpl(
        stage=Stage.BRAINSTORM,
        passes=(_vision_pass("brainstorm-pass"),),
        gate=lambda project: [Issue(check="X1", severity=Severity.ERROR, message="broken")],
    )
    seed_calls = {"n": 0}

    def seed_gate(project):
        seed_calls["n"] += 1
        return []

    seed_impl = StageImpl(stage=Stage.SEED, passes=(_vision_pass("seed-pass"),), gate=seed_gate)

    adapter = FakeAdapter(
        [VisionProposal(audience="a"), VisionProposal(audience="b"), VisionProposal(audience="c")]
    )
    impls = {Stage.DREAM: dream_impl, Stage.BRAINSTORM: brainstorm_impl, Stage.SEED: seed_impl}

    reports = runner.run_pipeline(project, Stage.SEED, impls, adapter)

    assert len(reports) == 2
    assert reports[0].success and reports[0].stage == Stage.DREAM
    assert not reports[1].success and reports[1].stage == Stage.BRAINSTORM
    assert seed_calls["n"] == 0
    assert project.stage == Stage.DREAM


def test_run_pipeline_missing_impl_raises_with_stage_name(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    dream_impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda project: [])
    adapter = FakeAdapter([VisionProposal(audience="a")])

    with pytest.raises(runner.RunnerError, match="brainstorm"):
        runner.run_pipeline(project, Stage.BRAINSTORM, {Stage.DREAM: dream_impl}, adapter)
