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
    console.print(f"[green]created[/green] {root}/ (scope: {scope}, stage: dream)")
    console.print("next: edit vision.yaml, then run the pipeline (M1+).")


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
