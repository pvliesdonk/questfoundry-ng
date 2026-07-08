"""The stage runner: context -> render -> complete -> apply (with repair)
-> gate -> checkpoint (design doc 02 §1).

Stage modules stay declarative (`PassSpec`/`StageImpl` in `pipeline/types.py`);
this module owns the only orchestration loop, so every stage behaves
identically to the engine and to tests.
"""

from __future__ import annotations

import copy
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from questfoundry.graph.mutations import MutationError
from questfoundry.models.base import Stage
from questfoundry.pipeline.types import ApplyError, PassReport, StageImpl, StageReport
from questfoundry.project.io import Project, save_project

PROMPTS_DIR = Path(__file__).parent / "prompts"

SYSTEM_PROMPT = (
    "You are the {role} for QuestFoundry, a compiler that turns a premise into a "
    "branching interactive-fiction gamebook. Follow the instructions exactly and "
    "respond only in the requested JSON format."
)


class RunnerError(Exception):
    """The pipeline is wired or invoked wrong (bad stage order, missing
    impl) — distinct from `ApplyError`/gate failures, which are recorded
    on the `StageReport` instead of raised."""


def _environment() -> Environment:
    """Seam for tests: monkeypatch this to swap in a `DictLoader` without
    touching `pipeline/prompts/` (which ships no fixture templates)."""
    return Environment(
        loader=FileSystemLoader(PROMPTS_DIR),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def _require_predecessor(project: Project, impl: StageImpl) -> None:
    predecessor = list(Stage)[impl.stage.order - 1]
    if project.stage.order != predecessor.order:
        raise RunnerError(
            f"project is at {project.stage.value!r}; stage {impl.stage.value!r} "
            f"requires {predecessor.value!r}"
        )


def _run_pass(
    project: Project, spec, env: Environment, adapter: Any, notes: str, max_repairs: int
) -> PassReport | str:
    """Runs one pass to a decision: a `PassReport` on success, or a
    human-readable error string once repairs are exhausted."""
    template = env.get_template(spec.template)
    context = spec.build_context(project)
    repair_errors: list[str] = []
    repairs_used = 0
    while True:
        rendered = template.render(**context, notes=notes, repair_errors=repair_errors)
        proposal = adapter.complete(
            system=SYSTEM_PROMPT.format(role=spec.role),
            prompt=rendered,
            schema=spec.schema,
            role=spec.role,
        )
        graph_backup = copy.deepcopy(project.graph)
        vision_backup = copy.deepcopy(project.vision)
        voice_backup = copy.deepcopy(project.voice)
        try:
            applied = spec.apply(proposal, project)
        except (ApplyError, MutationError) as exc:
            project.graph = graph_backup
            project.vision = vision_backup
            project.voice = voice_backup
            repair_errors.append(str(exc))
            repairs_used += 1
            if repairs_used > max_repairs:
                return f"pass {spec.name!r} exhausted repairs: {repair_errors[-1]}"
            continue
        if spec.review is not None:
            issues = spec.review(proposal, project, adapter)
            if issues:
                project.graph = graph_backup
                project.vision = vision_backup
                project.voice = voice_backup
                repair_errors.extend(issues)
                repairs_used += 1
                if repairs_used > max_repairs:
                    return (
                        f"pass {spec.name!r} failed review {max_repairs} times — the "
                        f"structure is wrong, not the words (design doc 02, FILL): "
                        f"{'; '.join(issues)}"
                    )
                continue
        return PassReport(name=spec.name, attempts=1 + repairs_used, applied=applied)


def _checkpoint(project: Project, report: StageReport) -> None:
    """Snapshot the on-disk project and write a human-readable report.
    Called only after a successful gate, so `project.stage` is already
    the completed stage."""
    root = project.root
    snap_dir = root / "snapshots" / project.stage.value
    if snap_dir.exists():
        shutil.rmtree(snap_dir)
    snap_dir.mkdir(parents=True)
    shutil.copy2(root / "project.yaml", snap_dir / "project.yaml")
    shutil.copy2(root / "vision.yaml", snap_dir / "vision.yaml")
    if (root / "voice.yaml").exists():
        shutil.copy2(root / "voice.yaml", snap_dir / "voice.yaml")
    for sub in ("graph", "prose"):
        if (root / sub).exists():
            shutil.copytree(root / sub, snap_dir / sub, dirs_exist_ok=True)

    lines = [f"# Stage: {project.stage.value}", ""]
    for p in report.passes:
        lines.append(f"## Pass: {p.name} (attempts={p.attempts})")
        lines.extend(f"- {line}" for line in p.applied)
        lines.append("")
    if report.issues:
        lines.append("## Gate issues")
        lines.extend(f"- [{i.severity.value}] {i.check}: {i.message}" for i in report.issues)
        lines.append("")
    lines.append(f"_generated {datetime.now(UTC).isoformat()}_")

    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{project.stage.value}.md").write_text("\n".join(lines) + "\n")


def run_stage(
    project: Project, impl: StageImpl, adapter: Any, *, notes: str = "", max_repairs: int = 2
) -> StageReport:
    _require_predecessor(project, impl)
    env = _environment()

    passes = impl.passes(project) if callable(impl.passes) else impl.passes
    pass_reports: list[PassReport] = []
    for spec in passes:
        if spec.skip_if is not None and (reason := spec.skip_if(project)):
            pass_reports.append(
                PassReport(name=spec.name, attempts=0, applied=[f"skipped: {reason}"])
            )
            continue
        result = _run_pass(project, spec, env, adapter, notes, max_repairs)
        if isinstance(result, str):
            return StageReport(stage=impl.stage, passes=pass_reports, error=result)
        pass_reports.append(result)

    issues = impl.gate(project)
    report = StageReport(stage=impl.stage, passes=pass_reports, issues=issues)
    if not report.success:
        return report

    project.stage = impl.stage
    save_project(project)
    _checkpoint(project, report)
    return report


def run_pipeline(
    project: Project,
    to: Stage,
    impls: dict[Stage, StageImpl],
    adapter: Any,
    *,
    notes_by_stage: dict[Stage, str] | None = None,
    max_repairs: int = 2,
) -> list[StageReport]:
    notes_by_stage = notes_by_stage or {}
    stages = [s for s in Stage if project.stage.order < s.order <= to.order]

    reports: list[StageReport] = []
    for stage in stages:
        impl = impls.get(stage)
        if impl is None:
            raise RunnerError(
                f"no implementation registered for stage {stage.value!r} (not built yet)"
            )
        report = run_stage(
            project, impl, adapter, notes=notes_by_stage.get(stage, ""), max_repairs=max_repairs
        )
        reports.append(report)
        if not report.success:
            break
    return reports
