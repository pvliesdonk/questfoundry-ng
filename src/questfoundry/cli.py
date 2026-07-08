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
    from questfoundry.llm import (
        AnthropicProvider,
        GeminiProvider,
        LLMAdapter,
        MockProvider,
        OpenAIProvider,
    )
    from questfoundry.models.base import Stage as StageEnum
    from questfoundry.pipeline.runner import RunnerError, run_pipeline
    from questfoundry.pipeline.stages import IMPLS

    if bool(stage) == bool(to):
        console.print("[red]specify exactly one of a stage name or --to <stage>[/red]")
        raise typer.Exit(2)
    project = load_project(directory)
    target = StageEnum(to or stage)

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
        provider = AnthropicProvider(api_key=os.environ.get("QF_ANTHROPIC_API_KEY"))
        cache_dir = project.root / "cache" / "llm"
    elif provider_name == "openai":
        provider = OpenAIProvider()
        cache_dir = project.root / "cache" / "llm"
    elif provider_name == "gemini":
        provider = GeminiProvider()
        cache_dir = project.root / "cache" / "llm"
    else:
        console.print(
            f"[red]unknown llm.provider {provider_name!r}; "
            "use 'anthropic', 'openai', 'gemini', or 'mock'[/red]"
        )
        raise typer.Exit(2)
    adapter = LLMAdapter(
        provider,
        project.llm.get("models", {}),
        cache_dir=cache_dir,
        ledger_path=project.root / "reports" / "ledger.jsonl",
    )
    try:
        notes = {StageEnum(k): v for k, v in project.steering.items()}
    except ValueError as e:
        console.print(f"[red]bad stage name in project.yaml steering: {e}[/red]")
        raise typer.Exit(2) from e
    try:
        reports = run_pipeline(project, target, IMPLS, adapter, notes_by_stage=notes)
    except RunnerError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    failed = False
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
        failed = failed or not report.success
    if failed:
        raise typer.Exit(1)
    console.print(f"[green]project is now at stage {project.stage.value}[/green]")


@app.command()
def validate(directory: FSPath = typer.Argument(FSPath("."))) -> None:
    """Load a project and run every gate at or below its current stage."""
    project = load_project(directory)
    issues = run_checks(project.graph, project.vision, project.stage)
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
    fmt: str = typer.Argument(..., help="'json', 'html', or 'twee' ('pdf' arrives with M5)"),
    directory: FSPath = typer.Option(FSPath("."), "--dir", "-C", help="Project directory"),
    out: FSPath | None = typer.Option(None, "--out", help="Output file (default: exports/)"),
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
        console.print("[red]the print gamebook pipeline arrives with M5[/red]")
        raise typer.Exit(2)
    else:
        console.print(f"[red]unknown format {fmt!r}; use json, html, or twee[/red]")
        raise typer.Exit(2)

    slug = project.name.lower().replace(" ", "-").replace("'", "")
    target = out or (project.root / "exports" / f"{slug}.{suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    console.print(f"[green]exported[/green] {target} (round-trip check: 0 problems)")


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
    """Show a project's stage and node counts."""
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
