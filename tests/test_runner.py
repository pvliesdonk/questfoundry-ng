"""The stage runner loop: render -> complete -> apply (with repair) ->
gate -> checkpoint (design doc 02 §1). No LLM package involved — a fake
adapter stands in for `questfoundry.llm`."""

from __future__ import annotations

from dataclasses import replace

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


def test_skip_if_bypasses_the_llm_call(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    skipped = PassSpec(
        name="optional",
        role="architect",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=lambda proposal, project: ["should never run"],
        skip_if=lambda project: "nothing to do",
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(), skipped), gate=lambda p: [])
    adapter = FakeAdapter([VisionProposal(audience="teens")])

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert len(adapter.prompts) == 1  # only the vision pass hit the adapter
    assert report.passes[1].name == "optional"
    assert report.passes[1].attempts == 0
    assert report.passes[1].applied == ["skipped: nothing to do"]


def test_review_hook_rides_the_repair_loop(tmp_path, monkeypatch):
    """A failing review restores state and re-prompts with the issues;
    a pass on the retry succeeds with attempts=2."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    verdicts = iter([["too purple"], []])

    def review(proposal, project, adapter):
        return next(verdicts)

    spec = PassSpec(
        name="vision",
        role="writer",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=_vision_pass().apply,
        review=review,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda p: [])
    adapter = FakeAdapter([VisionProposal(audience="one"), VisionProposal(audience="two")])

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert report.passes[0].attempts == 2
    assert project.vision.audience == "two"  # the reviewed-out draft was restored away
    assert "Repair error: too purple" in adapter.prompts[1]


def test_review_exhaustion_names_the_structure(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    spec = PassSpec(
        name="vision",
        role="writer",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=_vision_pass().apply,
        review=lambda proposal, project, adapter: ["still wrong"],
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(spec,), gate=lambda p: [])
    adapter = FakeAdapter([VisionProposal(audience=str(i)) for i in range(3)])

    report = runner.run_stage(project, impl, adapter)

    assert not report.success
    assert "structure is wrong" in (report.error or "")
    assert project.vision.audience != "2"  # nothing from the failed drafts stuck


def test_dynamic_pass_lists_are_computed_from_the_project(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    project.vision.premise = "two-pass premise"

    def passes(p):
        assert p.vision.premise == "two-pass premise"
        return (_vision_pass("first"), _vision_pass("second"))

    impl = StageImpl(stage=Stage.DREAM, passes=passes, gate=lambda p: [])
    adapter = FakeAdapter([VisionProposal(audience="a"), VisionProposal(audience="b")])

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert [p.name for p in report.passes] == ["first", "second"]


def test_expand_splices_successor_passes(tmp_path, monkeypatch):
    """A completed pass's `expand` result runs right after it, before any
    later pass — POLISH's finalize -> per-group passages/labels."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    planner = replace(
        _vision_pass("planner"),
        expand=lambda p: [_vision_pass("exp-a"), _vision_pass("exp-b")],
    )
    impl = StageImpl(
        stage=Stage.DREAM, passes=(planner, _vision_pass("trailing")), gate=lambda p: []
    )
    adapter = FakeAdapter([VisionProposal(audience=a) for a in ("p", "a", "b", "t")])

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert [p.name for p in report.passes] == ["planner", "exp-a", "exp-b", "trailing"]


def test_expand_runs_even_when_the_expanding_pass_is_skipped(tmp_path, monkeypatch):
    """finalize may `skip_if` there is nothing to add, but the passages it
    would have produced still must be enumerated — expansion runs on skip."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    planner = replace(
        _vision_pass("planner"),
        skip_if=lambda p: "nothing to add",
        expand=lambda p: [_vision_pass("exp-a")],
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(planner,), gate=lambda p: [])
    adapter = FakeAdapter([VisionProposal(audience="a")])  # only exp-a hits the adapter

    report = runner.run_stage(project, impl, adapter)

    assert report.success
    assert [p.name for p in report.passes] == ["planner", "exp-a"]
    assert report.passes[0].applied == ["skipped: nothing to add"]
    assert len(adapter.prompts) == 1


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


def test_progress_events_trace_the_stage(tmp_path, monkeypatch):
    """The heartbeat seam (roadmap §M10): one event at pass start, one at
    resolution, with 1-based index over the full pass list — skipped
    passes included, so m/n never jumps."""
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    noop = PassSpec(
        name="noop",
        role="utility",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=lambda proposal, project: [],
        skip_if=lambda project: "nothing to do",
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(noop, _vision_pass()), gate=lambda project: [])
    adapter = FakeAdapter([VisionProposal(audience="teens")])
    events = []

    report = runner.run_stage(project, impl, adapter, progress=events.append)

    assert report.success
    assert [(e.index, e.total, e.name, e.status) for e in events] == [
        (1, 2, "noop", "skipped"),
        (2, 2, "vision", "start"),
        (2, 2, "vision", "done"),
    ]
    assert events[-1].attempts == 1
    assert all(e.stage == Stage.DREAM for e in events)


def test_progress_reports_failed_pass(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    def bad_apply(proposal, project):
        raise ApplyError("nope")

    bad = PassSpec(
        name="bad",
        role="utility",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=bad_apply,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(bad,), gate=lambda project: [])
    adapter = FakeAdapter([VisionProposal(audience="x")])
    events = []

    report = runner.run_stage(project, impl, adapter, max_repairs=0, progress=events.append)

    assert not report.success
    assert [e.status for e in events] == ["start", "failed"]


def test_progress_reports_kept_pass(tmp_path, monkeypatch):
    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)
    impl = StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda project: [])
    adapter = FakeAdapter([])  # a kept pass must not reach the adapter
    events = []

    report = runner.run_stage(
        project, impl, adapter, keep={"vision": {"audience": "teens"}}, progress=events.append
    )

    assert report.success
    assert [(e.name, e.status) for e in events] == [("vision", "kept")]


def test_graph_error_from_apply_is_repairable_not_a_crash(tmp_path, monkeypatch):
    """A store GraphError (duplicate id, missing edge endpoint, duplicate
    edge) must reach the repair loop like ApplyError/MutationError, not
    escape as an uncaught KeyError and crash the run — the false-branch
    id-collision class, generalized to every model-reachable graph write."""
    from questfoundry.graph.store import GraphError

    _use_test_templates(monkeypatch)
    project = _scaffold(tmp_path)

    def bad_apply(proposal, project):
        raise GraphError("id 'beat:x' is already used; coin a different one.")

    bad = PassSpec(
        name="bad",
        role="utility",
        template=TEMPLATE_NAME,
        schema=VisionProposal,
        build_context=lambda project: {"audience_hint": ""},
        apply=bad_apply,
    )
    impl = StageImpl(stage=Stage.DREAM, passes=(bad,), gate=lambda project: [])
    adapter = FakeAdapter([VisionProposal(audience="x"), VisionProposal(audience="x")])

    report = runner.run_stage(project, impl, adapter, max_repairs=0)

    assert not report.success  # reported, not raised
    assert "exhausted repairs" in report.error
