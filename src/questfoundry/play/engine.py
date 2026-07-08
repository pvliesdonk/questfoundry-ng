"""Flag-tracking traversal of the passage graph (design doc 04 §1).

Implements exactly the runtime semantics every player must share: state
is a set of active flags; at a passage, the choices whose `requires` are
all active are offered (unavailable choices are hidden, never disabled);
taking a choice adds its `grants` and moves on; a passage with an ending
terminates. Pre-FILL the "prose" is the passage's beat summaries, which
is what makes the structure playable before a word is written.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from questfoundry.graph import queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind
from questfoundry.models.presentation import Choice, Ending, Passage


class PlayError(Exception):
    pass


@dataclass(frozen=True)
class Offered:
    label: str
    to: str
    grants: tuple[str, ...]


@dataclass
class Player:
    """One playthrough. Deterministic and headless — the TUI and tests
    drive it the same way, by index into `choices()`."""

    g: StoryGraph
    passage_id: str = ""
    flags: set[str] = field(default_factory=set)
    visited: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.passage_id:
            starts = queries.start_passages(self.g)
            if len(starts) != 1:
                raise PlayError(f"expected exactly one start passage, found {starts}")
            self.passage_id = starts[0]
        self.visited.append(self.passage_id)

    @property
    def passage(self) -> Passage:
        node = self.g.node(self.passage_id)
        assert isinstance(node, Passage)
        return node

    @property
    def ending(self) -> Ending | None:
        return self.passage.ending

    def prose(self) -> list[str]:
        """Pre-FILL rendering: the passage's beat summaries in DAG order."""
        beats = set(queries.beats_of_passage(self.g, self.passage_id))
        order = queries.topological_order(self.g) or []
        return [self.g.node(b).summary for b in order if b in beats]  # type: ignore[union-attr]

    def choices(self) -> list[Offered]:
        """Choices whose gates the current flags satisfy, in edge order."""
        offered = []
        for e in self.g.out_edges(self.passage_id, EdgeKind.CHOICE):
            choice = Choice.model_validate(e.payload)
            if set(choice.requires) <= self.flags:
                offered.append(Offered(label=choice.label, to=e.dst, grants=tuple(choice.grants)))
        return offered

    def choose(self, index: int) -> None:
        if self.ending is not None:
            raise PlayError("the story has ended")
        offered = self.choices()
        if not 0 <= index < len(offered):
            raise PlayError(f"choice {index} out of range 0..{len(offered) - 1}")
        taken = offered[index]
        self.flags.update(taken.grants)
        self.passage_id = taken.to
        self.visited.append(taken.to)
