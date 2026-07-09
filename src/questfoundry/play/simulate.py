"""Exhaustive arc walker for QA (design doc 03 §2, 04).

M2 walks the beat DAG: one walk per computed arc selection, linearized
in topological order, checking the completeness properties gate G3
enforces (so `qf simulate` reports in story terms what `qf validate`
reports in invariant terms). Passage-graph simulation joins in M3 when
passages exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from questfoundry.graph import queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.structure import Beat, StateFlag


@dataclass
class ArcWalk:
    selection: dict[str, str]  # dilemma id -> selected path id
    beats: list[str]  # arc view in topological order
    flags: dict[str, str]  # flag id -> beat where it is granted
    ending: str | None
    problems: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return " + ".join(self.selection[d] for d in sorted(self.selection)) or "(single arc)"


def walk_arc(g: StoryGraph, selection: dict[str, str]) -> ArcWalk:
    order = queries.topological_order(g) or []
    view = queries.arc_view(g, selection)
    beats = [b for b in order if b in view]
    problems: list[str] = []

    selected = set(selection.values())
    flags: dict[str, str] = {}
    for flag in sorted(g.nodes_of(StateFlag), key=lambda f: f.id):
        if flag.path in selected:
            for grant in queries.grant_beats(g, flag.id):
                if grant in view:  # an arc reaches exactly one world's grant
                    flags[flag.id] = grant
                    break

    endings = [b for b in beats if g.node(b).is_ending]  # type: ignore[union-attr]
    if len(endings) != 1:
        problems.append(f"expected exactly one ending, found {endings or 'none'}")
    for path_id in selection.values():
        if not any(c in view for c in queries.commit_beats(g, path_id)):
            problems.append(f"never commits {path_id}")
    for b in beats:
        beat = g.node(b)
        assert isinstance(beat, Beat)
        if not any(s in view for s in queries.successors(g, b)) and not beat.is_ending:
            problems.append(f"dead-ends at non-ending beat {b}")

    return ArcWalk(
        selection=selection,
        beats=beats,
        flags=flags,
        ending=endings[0] if len(endings) == 1 else None,
        problems=problems,
    )


def walk_all_arcs(g: StoryGraph) -> list[ArcWalk]:
    return [walk_arc(g, selection) for selection in queries.arc_selections(g)]
