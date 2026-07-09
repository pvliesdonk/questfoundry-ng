"""The stage runner: context -> render -> complete -> apply (with repair)
-> gate -> checkpoint (design doc 02 §1).

Stage modules stay declarative (`PassSpec`/`StageImpl` in `pipeline/types.py`);
this module owns the only orchestration loop, so every stage behaves
identically to the engine and to tests.
"""

from __future__ import annotations

import copy
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
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


def _run_kept_pass(project: Project, spec, proposal_data: dict) -> PassReport | str:
    """Re-apply a recorded accepted proposal without an LLM call
    (`qf rerun --keep`). A kept proposal that no longer validates or
    applies is stale — that is an author-facing error, not a repair."""
    try:
        proposal = spec.schema.model_validate(proposal_data)
    except Exception as exc:  # pydantic.ValidationError, kept generic on purpose
        return f"kept proposal for pass {spec.name!r} no longer matches its schema: {exc}"
    try:
        applied = spec.apply(proposal, project)
    except (ApplyError, MutationError) as exc:
        return f"kept proposal for pass {spec.name!r} no longer applies: {exc}"
    return PassReport(
        name=spec.name,
        attempts=0,
        applied=[f"kept: {line}" for line in applied],
        proposal=proposal.model_dump(mode="json"),
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
        return PassReport(
            name=spec.name,
            attempts=1 + repairs_used,
            applied=applied,
            proposal=proposal.model_dump(mode="json"),
        )


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
    for sub in ("graph", "prose", "art", "codex"):
        if (root / sub).exists():
            shutil.copytree(root / sub, snap_dir / sub, dirs_exist_ok=True)

    proposals_dir = snap_dir / "proposals"
    for p in report.passes:
        if p.proposal is None:
            continue
        proposals_dir.mkdir(parents=True, exist_ok=True)
        payload = {"pass": p.name, "proposal": p.proposal}
        path = proposals_dir / f"{p.name.replace(':', '__')}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

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
    project: Project,
    impl: StageImpl,
    adapter: Any,
    *,
    notes: str = "",
    max_repairs: int = 2,
    keep: dict[str, dict] | None = None,
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
        if keep and spec.name in keep:
            result = _run_kept_pass(project, spec, keep[spec.name])
        else:
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


def recorded_proposals(root: Path, stage: Stage) -> dict[str, dict]:
    """Accepted proposals persisted at `stage`'s last checkpoint, keyed by
    pass name — the artifacts `qf rerun --keep` can re-apply."""
    proposals_dir = root / "snapshots" / stage.value / "proposals"
    result: dict[str, dict] = {}
    if proposals_dir.is_dir():
        for path in sorted(proposals_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            result[payload["pass"]] = payload["proposal"]
    return result


def prepare_rerun(root: Path, target: Stage) -> None:
    """Restore the on-disk project to `target`'s predecessor checkpoint so
    the stage can run again: stage artifacts (graph, prose, art, codex,
    voice) come back from the snapshot; author knobs stay current —
    project.yaml keeps its llm/steering/seeds (only `stage` is rewound)
    and vision.yaml is never restored, because editing it is a main
    reason to rerun. Reload the project after calling this."""
    predecessor = list(Stage)[target.order - 1]
    snap_dir = root / "snapshots" / predecessor.value
    if predecessor != Stage.NEW and not snap_dir.is_dir():
        raise RunnerError(
            f"cannot rerun {target.value!r}: no checkpoint for its "
            f"predecessor {predecessor.value!r} under {snap_dir}"
        )
    for sub in ("graph", "prose", "art", "codex"):
        if (root / sub).exists():
            shutil.rmtree(root / sub)
        if (snap_dir / sub).exists():
            shutil.copytree(snap_dir / sub, root / sub)
    (root / "voice.yaml").unlink(missing_ok=True)
    if (snap_dir / "voice.yaml").exists():
        shutil.copy2(snap_dir / "voice.yaml", root / "voice.yaml")

    meta_path = root / "project.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["stage"] = predecessor.value
    meta_path.write_text(
        yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


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
