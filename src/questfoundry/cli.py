"""The `qf` command-line interface (M0 subset: new, validate, graph, status)."""

from __future__ import annotations

from pathlib import Path as FSPath

import typer
from rich.console import Console
from rich.table import Table

from questfoundry.graph import queries
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import EdgeKind
from questfoundry.models.concept import SCOPE_PRESETS
from questfoundry.models.drama import Dilemma
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import Beat, StateFlag
from questfoundry.models.world import Entity
from questfoundry.project import load_project, scaffold_project

app = typer.Typer(help="QuestFoundry NG — a story compiler for branching gamebooks.")
console = Console()


@app.command()
def new(
    name: str,
    scope: str = typer.Option("micro", help=f"One of {sorted(SCOPE_PRESETS)}"),
    directory: FSPath | None = typer.Option(None, help="Target directory (default: ./NAME)"),
) -> None:
    """Scaffold a new story project."""
    if scope not in SCOPE_PRESETS:
        console.print(f"[red]unknown scope {scope!r}; pick one of {sorted(SCOPE_PRESETS)}[/red]")
        raise typer.Exit(2)
    root = directory or FSPath(name)
    scaffold_project(root, name=name, scope=scope)
    console.print(f"[green]created[/green] {root}/ (scope: {scope}, stage: new)")
    console.print("next: edit the premise in vision.yaml, then: qf run --to seed")


@app.command()
def run(
    stage: str = typer.Argument("", help="Stage to run, or empty with --to"),
    directory: FSPath = typer.Option(FSPath("."), "--dir", "-C", help="Project directory"),
    to: str = typer.Option("", "--to", help="Run every remaining stage up to this one"),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Batch mode. Currently the only mode: interactive checkpoint"
        " pauses are deferred (see docs/STATUS.md), so this flag is accepted"
        " for forward compatibility and has no effect yet.",
    ),
) -> None:
    """Run pipeline stage(s) against the project's configured LLM provider."""
    from questfoundry.models.base import Stage as StageEnum
    from questfoundry.pipeline.runner import RunnerError, run_pipeline
    from questfoundry.pipeline.stages import IMPLS

    if bool(stage) == bool(to):
        console.print("[red]specify exactly one of a stage name or --to <stage>[/red]")
        raise typer.Exit(2)
    project = load_project(directory)
    target = StageEnum(to or stage)
    adapter = _adapter_for(project)
    try:
        notes = {StageEnum(k): v for k, v in project.steering.items()}
    except ValueError as e:
        console.print(f"[red]bad stage name in project.yaml steering: {e}[/red]")
        raise typer.Exit(2) from e
    try:
        reports = run_pipeline(
            project,
            target,
            IMPLS,
            adapter,
            notes_by_stage=notes,
            progress=_heartbeat(project.root / "reports" / "ledger.jsonl"),
        )
    except RunnerError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    if not _print_reports(reports):
        raise typer.Exit(1)
    console.print(f"[green]project is now at stage {project.stage.value}[/green]")


def _adapter_for(project):
    from questfoundry.llm import (
        AnthropicProvider,
        GeminiProvider,
        LLMAdapter,
        MockProvider,
        OllamaProvider,
        OpenAIProvider,
    )

    provider_name = project.llm.get("provider", "anthropic")
    if provider_name == "mock":
        fixtures = project.root / project.llm.get("fixtures", "fixtures")
        provider = MockProvider(fixtures)
        cache_dir = None  # replay is already deterministic
    elif provider_name == "anthropic":
        import os

        # Hosted Claude Code environments strip the reserved name
        # ANTHROPIC_API_KEY from sessions; QF_ANTHROPIC_API_KEY passes
        # through and wins when set.
        provider = AnthropicProvider(
            api_key=os.environ.get("QF_ANTHROPIC_API_KEY"),
            thinking=project.llm.get("thinking"),
        )
        cache_dir = project.root / "cache" / "llm"
    elif provider_name == "openai":
        provider = OpenAIProvider()
        cache_dir = project.root / "cache" / "llm"
    elif provider_name == "gemini":
        provider = GeminiProvider()
        cache_dir = project.root / "cache" / "llm"
    elif provider_name == "ollama":
        # host=None follows OLLAMA_HOST (default localhost); cloud models
        # need OLLAMA_API_KEY (and host https://ollama.com when daemon-less).
        provider = OllamaProvider(
            host=project.llm.get("host"),
            num_ctx=int(project.llm.get("num_ctx", 32768)),
            temperature=project.llm.get("temperature"),
            keep_alive=project.llm.get("keep_alive"),
            think=project.llm.get("think"),
        )
        cache_dir = project.root / "cache" / "llm"
    else:
        console.print(
            f"[red]unknown llm.provider {provider_name!r}; "
            "use 'anthropic', 'openai', 'gemini', 'ollama', or 'mock'[/red]"
        )
        raise typer.Exit(2)
    return LLMAdapter(
        provider,
        project.llm.get("models", {}),
        cache_dir=cache_dir,
        ledger_path=project.root / "reports" / "ledger.jsonl",
    )


def _ledger_totals(ledger_path: FSPath) -> dict:
    """Aggregate the spend ledger: call counts and token totals. Token
    counts are the honest unit — the ledger records no prices, and a
    price table here would rot (design doc 03 §5)."""
    from questfoundry.llm import ledger

    entries = ledger.read(ledger_path)
    return {
        "calls": len(entries),
        "cached": sum(1 for e in entries if e.get("cached")),
        "input_tokens": sum(e.get("input_tokens", 0) for e in entries),
        "output_tokens": sum(e.get("output_tokens", 0) for e in entries),
        "last_ts": entries[-1].get("ts") if entries else None,
    }


def _tokens(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 10_000 else str(n)


def _heartbeat(ledger_path: FSPath):
    """A flushed one-line-per-pass heartbeat on stderr (roadmap §M10):
    stdout stays the report stream, and stderr writes are unbuffered, so
    a piped or logged run still shows its pulse pass by pass."""
    import sys

    def emit(ev) -> None:
        if ev.status == "start":
            line = f"{ev.stage.value} [{ev.index}/{ev.total}] {ev.name} ..."
        else:
            attempts = f" attempts={ev.attempts}" if ev.attempts > 1 else ""
            t = _ledger_totals(ledger_path)
            spend = (
                f" | {t['calls']} calls ({t['cached']} cached), "
                f"{_tokens(t['input_tokens'])} in / {_tokens(t['output_tokens'])} out"
                if t["calls"]
                else ""
            )
            line = (
                f"{ev.stage.value} [{ev.index}/{ev.total}] "
                f"{ev.name} {ev.status}{attempts}{spend}"
            )
        print(line, file=sys.stderr, flush=True)

    return emit


def _print_reports(reports) -> bool:
    """Render stage reports; returns True when every stage succeeded."""
    ok = True
    for report in reports:
        status = "[green]ok[/green]" if report.success else "[red]FAILED[/red]"
        console.print(f"{report.stage.value}: {status}")
        for p in report.passes:
            attempts = f" ({p.attempts} attempts)" if p.attempts > 1 else ""
            console.print(f"  {p.name}{attempts}: " + "; ".join(p.applied))
        for issue in report.issues:
            color = "red" if issue.severity == Severity.ERROR else "yellow"
            console.print(f"  [{color}]{issue}[/{color}]")
        if report.error:
            console.print(f"  [red]{report.error}[/red]")
        ok = ok and report.success
    return ok


@app.command()
def rerun(
    stage: str = typer.Argument(..., help="Stage to run again from its predecessor's checkpoint"),
    directory: FSPath = typer.Option(FSPath("."), "--dir", "-C", help="Project directory"),
    keep: list[str] = typer.Option(
        [],
        "--keep",
        help="Pass name whose accepted proposal is re-applied without an LLM call"
        " (repeatable; names as shown in the stage report, e.g. 'triage', 'write:the-lamp')",
    ),
) -> None:
    """Partial regeneration (design doc 02 §3): rewind to the stage's
    predecessor checkpoint, then run the stage again — regenerating
    everything except the passes named with --keep. Downstream stages
    are rewound with it and need re-running. The stage's own research
    digest survives the rewind and is reused while fresh (mini-ADR
    A17); delete research/<stage>.md first to force re-retrieval."""
    from questfoundry.models.base import Stage as StageEnum
    from questfoundry.pipeline.runner import (
        RunnerError,
        prepare_rerun,
        recorded_proposals,
        run_stage,
    )
    from questfoundry.pipeline.stages import IMPLS

    target = StageEnum(stage)
    project = load_project(directory)
    if project.stage.order < target.order:
        console.print(
            f"[red]stage {target.value!r} has not been run yet "
            f"(project is at {project.stage.value!r}) — use qf run[/red]"
        )
        raise typer.Exit(2)
    impl = IMPLS.get(target)
    if impl is None:
        console.print(f"[red]no implementation registered for stage {target.value!r}[/red]")
        raise typer.Exit(2)

    recorded = recorded_proposals(project.root, target)
    missing = [name for name in keep if name not in recorded]
    if missing:
        console.print(
            f"[red]no recorded proposal for {missing}; available: {sorted(recorded)}[/red]"
        )
        raise typer.Exit(2)

    try:
        prepare_rerun(project.root, target)
    except RunnerError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    project = load_project(directory)  # reload: the files just rewound
    adapter = _adapter_for(project)
    report = run_stage(
        project,
        impl,
        adapter,
        notes=project.steering.get(target.value, ""),
        keep={name: recorded[name] for name in keep},
        progress=_heartbeat(project.root / "reports" / "ledger.jsonl"),
    )
    if not _print_reports([report]):
        raise typer.Exit(1)
    console.print(f"[green]project is now at stage {project.stage.value}[/green]")


@app.command()
def validate(directory: FSPath = typer.Argument(FSPath("."))) -> None:
    """Load a project and run every gate at or below its current stage."""
    project = load_project(directory)
    issues = run_checks(
        project.graph, project.vision, project.stage, enrichment=project.enrichment
    )
    errors = [i for i in issues if i.severity == Severity.ERROR]
    warnings = [i for i in issues if i.severity == Severity.WARNING]
    for issue in issues:
        color = "red" if issue.severity == Severity.ERROR else "yellow"
        console.print(f"[{color}]{issue}[/{color}]")
    console.print(
        f"\n{project.name} @ {project.stage.value}: "
        f"[red]{len(errors)} error(s)[/red], [yellow]{len(warnings)} warning(s)[/yellow]"
    )
    if errors:
        raise typer.Exit(1)
    console.print("[green]all gates pass[/green]")


@app.command()
def export(
    fmt: str = typer.Argument(..., help="'json', 'html', 'twee', or 'pdf'"),
    directory: FSPath = typer.Option(FSPath("."), "--dir", "-C", help="Project directory"),
    out: FSPath | None = typer.Option(None, "--out", help="Output file (default: exports/)"),
    seed: int | None = typer.Option(
        None, "--seed", help="Section-numbering seed for 'pdf' (default: project.print_seed or 1)"
    ),
) -> None:
    """Export the story (design doc 04). The runtime JSON is canonical;
    HTML and Twee are derived from it."""
    import json as jsonlib
    import uuid

    from questfoundry.export.html import build_html
    from questfoundry.export.runtime_json import build_runtime, validate_runtime
    from questfoundry.export.twee import build_twee

    project = load_project(directory)
    problems = validate_runtime(build_runtime(project))
    if problems:
        for problem in problems:
            console.print(f"[red]{problem}[/red]")
        console.print("[red]export blocked: the runtime round-trip check failed[/red]")
        raise typer.Exit(1)

    if fmt == "json":
        content = jsonlib.dumps(build_runtime(project), indent=2, ensure_ascii=False) + "\n"
        suffix = "json"
    elif fmt == "html":
        content = build_html(project)
        suffix = "html"
    elif fmt == "twee":
        if not project.ifid:
            # persist just the IFID — an export must not rewrite the project
            project.ifid = str(uuid.uuid4()).upper()
            meta_path = project.root / "project.yaml"
            import yaml as yamllib

            meta = yamllib.safe_load(meta_path.read_text())
            meta["ifid"] = project.ifid
            meta_path.write_text(yamllib.safe_dump(meta, sort_keys=False, allow_unicode=True))
        content = build_twee(project, project.ifid)
        suffix = "twee"
    elif fmt == "pdf":
        from questfoundry.export.gamebook import build_gamebook, compile_pdf, lint_gamebook

        print_seed = seed if seed is not None else (
            project.print_seed if project.print_seed is not None else 1
        )
        if project.print_seed is None:
            # persist just the seed — an export must not rewrite the project
            project.print_seed = print_seed
            meta_path = project.root / "project.yaml"
            import yaml as yamllib

            meta = yamllib.safe_load(meta_path.read_text())
            meta["print_seed"] = print_seed
            meta_path.write_text(yamllib.safe_dump(meta, sort_keys=False, allow_unicode=True))

        images_dir = project.root / "art" / "images"
        book = build_gamebook(
            build_runtime(project),
            seed=print_seed,
            images_dir=images_dir if images_dir.is_dir() else None,
            root=project.root,
        )
        lint_errors = lint_gamebook(book)
        if lint_errors:
            for problem in lint_errors:
                console.print(f"[red]{problem}[/red]")
            console.print("[red]export blocked: print gamebook lint failed[/red]")
            raise typer.Exit(1)
        for warning in book.warnings:
            console.print(f"[yellow]{warning}[/yellow]")

        slug = project.name.lower().replace(" ", "-").replace("'", "")
        typ_target = out or (project.root / "exports" / f"{slug}.typ")
        pdf_target = typ_target.with_suffix(".pdf")
        typ_target.parent.mkdir(parents=True, exist_ok=True)
        typ_target.write_text(book.typst, encoding="utf-8")
        pdf_target.write_bytes(compile_pdf(book.typst, root=project.root))
        console.print(f"[green]exported[/green] {typ_target} and {pdf_target}")
        return
    else:
        console.print(f"[red]unknown format {fmt!r}; use json, html, twee, or pdf[/red]")
        raise typer.Exit(2)

    slug = project.name.lower().replace(" ", "-").replace("'", "")
    target = out or (project.root / "exports" / f"{slug}.{suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    console.print(f"[green]exported[/green] {target} (round-trip check: 0 problems)")


@app.command()
def illustrate(
    directory: FSPath = typer.Option(FSPath("."), "--dir", "-C", help="Project directory"),
    provider: str = typer.Option(
        "", "--provider", help="Override images.provider (placeholder, openai, gemini)"
    ),
    budget: int | None = typer.Option(
        None, "--budget", help="Maximum renders this invocation (sample included)"
    ),
    priority: int | None = typer.Option(
        None, "--priority", help="Only render briefs with priority <= this floor"
    ),
    force: bool = typer.Option(
        False, "--force", help="Re-render briefs whose image file already exists"
    ),
    yes: bool = typer.Option(
        False, "--yes", help="Skip the sample-first confirmation and render the whole batch"
    ),
) -> None:
    """Render DRESS illustration briefs to art/images/<slug>.png
    (mini-ADR A18: a post-DRESS command, not a stage — cloud providers
    expose no seeds, so idempotence is by file presence; re-running
    costs zero API calls)."""
    from questfoundry.illustrate import (
        IllustrateError,
        RenderOutcome,
        build_service,
        image_path,
        plan_renders,
        render_briefs,
    )

    project = load_project(directory)
    if not project.enrichment.briefs:
        console.print("[red]no illustration briefs — run the pipeline through dress first[/red]")
        raise typer.Exit(1)

    plan = plan_renders(project, force=force, priority_floor=priority, budget=budget)
    if plan.skipped_existing:
        console.print(
            f"[dim]{len(plan.skipped_existing)} image(s) already rendered "
            "(use --force to re-render)[/dim]"
        )
    if plan.skipped_priority:
        console.print(f"[dim]{len(plan.skipped_priority)} brief(s) below the priority floor[/dim]")
    if plan.skipped_budget:
        console.print(f"[dim]{len(plan.skipped_budget)} brief(s) beyond the render budget[/dim]")
    if not plan.to_render:
        console.print("[green]nothing to render[/green]")
        return

    try:
        service, provider_name, generate_kwargs = build_service(project, provider or None)
    except IllustrateError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2) from e

    def on_rendered(outcome: RenderOutcome) -> None:
        console.print(f"[green]rendered[/green] {outcome.path}")

    def confirm_batch(sample: RenderOutcome, remaining: int) -> bool:
        if remaining <= 0:
            return True
        console.print(f"sample rendered — inspect {sample.path}")
        return typer.confirm(f"continue with the remaining {remaining} brief(s)?")

    def reformulate(prompt: str, refusal: str) -> str:
        # built lazily: only a live content-policy refusal pays this call
        from pydantic import BaseModel

        from questfoundry.illustrate import REFORMULATE_SYSTEM, reformulate_prompt_text

        class Reformulated(BaseModel):
            prompt: str

        console.print("[yellow]content policy refusal — attempting one reformulation[/yellow]")
        adapter = _adapter_for(project)
        return adapter.complete(
            system=REFORMULATE_SYSTEM,
            prompt=reformulate_prompt_text(prompt, refusal),
            schema=Reformulated,
            role="utility",
        ).prompt

    try:
        outcomes = render_briefs(
            project,
            service,
            provider_name,
            plan.to_render,
            generate_kwargs=generate_kwargs,
            reformulate=reformulate,
            on_rendered=on_rendered,
            confirm_batch=None if yes else confirm_batch,
        )
    except IllustrateError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e

    refused = [o for o in outcomes if o.path is None]
    for o in refused:
        console.print(f"[red]refused by content policy: {image_path(project.root, o.brief)}[/red]")
        console.print(f"  [dim]{o.refusal}[/dim]")
    rendered = sum(1 for o in outcomes if o.path is not None)
    console.print(f"[green]{rendered} image(s) rendered[/green] ({provider_name})")
    if len(outcomes) < len(plan.to_render):
        remaining = len(plan.to_render) - len(outcomes)
        console.print(
            f"[yellow]stopped after the sample — {remaining} brief(s) not rendered[/yellow]"
        )
    if refused:
        raise typer.Exit(1)


@app.command()
def play(
    directory: FSPath = typer.Argument(FSPath(".")),
    show_state: bool = typer.Option(
        False, "--show-state", help="Reveal passage ids and active flags while playing."
    ),
) -> None:
    """Play the story in the terminal (beat summaries before FILL, prose after)."""
    from questfoundry.models.presentation import Passage as PassageNode
    from questfoundry.play.tui import play as run_tui

    project = load_project(directory)
    if not project.graph.nodes_of(PassageNode):
        console.print("[red]no passages yet — run the pipeline through polish first[/red]")
        raise typer.Exit(1)
    console.print(f"[bold]{project.name}[/bold]")
    run_tui(project.graph, console, show_state=show_state)


@app.command()
def simulate(
    directory: FSPath = typer.Argument(FSPath(".")),
    all_arcs: bool = typer.Option(
        True,
        "--all-arcs",
        help="Walk every computed arc (the only mode until targeted walks land).",
    ),
) -> None:
    """Walk every arc of the beat DAG and report completeness."""
    from questfoundry.play import walk_all_arcs

    project = load_project(directory)
    walks = walk_all_arcs(project.graph)
    names = queries.path_names(project.graph)
    failed = False
    for walk in walks:
        title = " + ".join(names.get(p, p) for _, p in sorted(walk.selection.items()))
        console.print(f"\n[bold]{title or '(single arc)'}[/bold]  ({walk.label})")
        for b in walk.beats:
            beat = project.graph.node(b)
            markers = []
            if getattr(beat, "commits_dilemmas", []):
                markers.append("[magenta]commit[/magenta]")
            for flag_id, grant in walk.flags.items():
                if grant == b:
                    markers.append(f"[cyan]+{flag_id}[/cyan]")
            if beat.is_ending:  # type: ignore[union-attr]
                markers.append("[green]ending[/green]")
            suffix = f"  ({', '.join(markers)})" if markers else ""
            console.print(f"  {b}{suffix}")
        for problem in walk.problems:
            console.print(f"  [red]{problem}[/red]")
            failed = True
    console.print(
        f"\n{len(walks)} arc(s): "
        + ("[red]incomplete[/red]" if failed else "[green]all complete[/green]")
    )
    if failed:
        raise typer.Exit(1)


@app.command()
def status(directory: FSPath = typer.Argument(FSPath("."))) -> None:
    """Show a project's stage, node counts, LLM spend, and any
    interrupted in-flight run (roadmap §M10 progress reporting)."""
    project = load_project(directory)
    g = project.graph
    table = Table(title=f"{project.name} — stage: {project.stage.value}")
    table.add_column("layer")
    table.add_column("count", justify="right")
    table.add_row("entities (retained)", str(sum(1 for e in g.nodes_of(Entity) if e.retained)))
    table.add_row("dilemmas", str(len(g.nodes_of(Dilemma))))
    table.add_row("beats", str(len(g.nodes_of(Beat))))
    table.add_row("state flags", str(len(g.nodes_of(StateFlag))))
    table.add_row("passages", str(len(g.nodes_of(Passage))))
    table.add_row("arcs (computed)", str(len(queries.arc_selections(g))))
    table.add_row("topology frozen", "yes" if g.frozen else "no")
    console.print(table)

    t = _ledger_totals(project.root / "reports" / "ledger.jsonl")
    if t["calls"]:
        console.print(
            f"llm spend: {t['calls']} calls ({t['cached']} cached), "
            f"{_tokens(t['input_tokens'])} in / {_tokens(t['output_tokens'])} out"
            + (f" — last call {t['last_ts']}" if t["last_ts"] else "")
        )

    # An inflight/<stage>/ directory is an interrupted run: the ledger
    # is consumed at the gate-passing checkpoint (mini-ADR A16), so its
    # presence means the stage started and never checkpointed. Re-running
    # `qf run` resumes the journaled passes without new LLM calls.
    inflight_root = project.root / "inflight"
    if inflight_root.is_dir():
        from datetime import UTC, datetime

        for stage_dir in sorted(p for p in inflight_root.iterdir() if p.is_dir()):
            proposals = sorted(
                (stage_dir / "proposals").glob("*.json"), key=lambda p: p.stat().st_mtime
            )
            if proposals:
                import json as jsonlib

                last = proposals[-1]
                try:
                    last_name = jsonlib.loads(last.read_text(encoding="utf-8"))["pass"]
                except (ValueError, KeyError, TypeError, OSError):
                    # torn ledger entry (crash mid-write): best-effort name
                    last_name = last.stem.replace("__", ":")
                last_ts = datetime.fromtimestamp(last.stat().st_mtime, tz=UTC).isoformat(
                    timespec="seconds"
                )
                detail = f"{len(proposals)} pass(es) journaled, last {last_name!r} at {last_ts}"
            else:
                detail = "no passes journaled yet"
            console.print(
                f"[yellow]in-flight: {stage_dir.name} — {detail}; "
                "re-run qf run to resume free[/yellow]"
            )


@app.command()
def graph(
    directory: FSPath = typer.Argument(FSPath(".")),
    layer: str = typer.Option("beats", help="'beats' or 'passages'"),
) -> None:
    """Render the beat DAG or passage graph as Mermaid (stdout)."""
    project = load_project(directory)
    g = project.graph
    lines = ["flowchart TD"]
    if layer == "beats":
        for beat in sorted(g.nodes_of(Beat), key=lambda b: b.id):
            slug = beat.id.split(":", 1)[1]
            shape = ("([", "])") if beat.is_ending else ("[", "]")
            label = beat.summary[:40].replace('"', "'")
            lines.append(f'    {slug}{shape[0]}"{label}"{shape[1]}')
        for e in g.edges:
            if e.kind == EdgeKind.PREDECESSOR:
                lines.append(
                    f"    {e.src.split(':', 1)[1]} --> {e.dst.split(':', 1)[1]}"
                )
    elif layer == "passages":
        for passage in sorted(g.nodes_of(Passage), key=lambda p: p.id):
            slug = passage.id.split(":", 1)[1]
            shape = ("([", "])") if passage.ending else ("[", "]")
            label = passage.summary[:40].replace('"', "'")
            lines.append(f'    {slug}{shape[0]}"{label}"{shape[1]}')
        for e in g.edges:
            if e.kind == EdgeKind.CHOICE:
                label = e.payload.get("label", "")[:30].replace('"', "'")
                gate = f" 🔒{','.join(e.payload['requires'])}" if e.payload.get("requires") else ""
                lines.append(
                    f'    {e.src.split(":", 1)[1]} -->|"{label}{gate}"| {e.dst.split(":", 1)[1]}'
                )
    else:
        console.print(f"[red]unknown layer {layer!r}[/red]")
        raise typer.Exit(2)
    print("\n".join(lines))


if __name__ == "__main__":
    app()
