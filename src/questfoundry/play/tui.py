"""`qf play` — the terminal player (design doc 04 §5).

A thin interactive loop over `play.engine.Player`: renders the passage
(beat summaries pre-FILL), numbers the available choices, reads one, and
walks on until an ending. `--show-state` reveals the machinery (passage
id, active flags) for structural debugging.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt

from questfoundry.graph.store import StoryGraph
from questfoundry.play.engine import Player


def play(g: StoryGraph, console: Console, *, show_state: bool = False) -> None:
    player = Player(g)
    while True:
        console.print()
        for paragraph in player.prose():
            console.print(paragraph)
        if show_state:
            console.print(
                f"[dim]@{player.passage_id}"
                f"  flags: {', '.join(sorted(player.flags)) or '(none)'}[/dim]"
            )
        if player.ending is not None:
            console.print()
            console.print(Panel(f"[bold]{player.ending.title}[/bold]", expand=False))
            console.print(f"[dim]{len(player.visited)} passages — the end.[/dim]")
            return
        console.print()
        offered = player.choices()
        for i, choice in enumerate(offered, start=1):
            console.print(f"  [cyan]{i}.[/cyan] {choice.label}")
        pick = IntPrompt.ask("choice", choices=[str(i) for i in range(1, len(offered) + 1)])
        player.choose(pick - 1)
