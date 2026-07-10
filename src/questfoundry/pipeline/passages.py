"""POLISH's deterministic core: passage collapse and choice topology
(design doc 02, POLISH; 01 §6).

The engine computes everything computable — collapse boundaries, choice
endpoints, gates (`requires`), grants, residue/variant needs — and the
LLM contributes only judgment and words: beat content for residue and
false-branch insertions, passage summaries, choice labels, ending
titles, feasibility calls. Collapse groups maximal linear runs:
boundaries fall at divergences and convergences, and flag-gated beats
(residue) are always singleton passages.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind
from questfoundry.models.drama import Dilemma, DilemmaRole, ResidueWeight
from questfoundry.models.structure import Beat, StateFlag

# -- collapse ----------------------------------------------------------------


def _beat(g: StoryGraph, beat_id: str) -> Beat:
    node = g.node(beat_id)
    assert isinstance(node, Beat)
    return node


def collapse_groups(g: StoryGraph) -> list[list[str]]:
    """Maximal linear runs of beats, in topological order of their heads.

    A run extends across a -> b iff a has exactly one successor, b has
    exactly one predecessor, and both carry the same gate — usually none.
    An identically-gated linear chain (a multi-beat residue arm) is one
    passage: the gate boundary is where the passage breaks, not every
    gated beat.
    """
    order = queries.topological_order(g)
    if order is None:
        raise ValueError("beat graph has a cycle; collapse needs a DAG")

    def merges(a: str, b: str) -> bool:
        if len(queries.successors(g, a)) != 1 or len(queries.predecessors(g, b)) != 1:
            return False
        return sorted(_beat(g, a).requires_flags) == sorted(_beat(g, b).requires_flags)

    groups: list[list[str]] = []
    group_of: dict[str, int] = {}
    for b in order:
        preds = queries.predecessors(g, b)
        if len(preds) == 1 and merges(preds[0], b):
            idx = group_of[preds[0]]
            groups[idx].append(b)
            group_of[b] = idx
        else:
            group_of[b] = len(groups)
            groups.append([b])
    return groups


def group_edges(groups: list[list[str]], g: StoryGraph) -> list[tuple[int, int]]:
    """Cross-group beat edges, deduplicated, as (from_group, to_group).
    Runs guarantee cross edges leave tails and enter heads."""
    index = {b: i for i, grp in enumerate(groups) for b in grp}
    seen: set[tuple[int, int]] = set()
    result: list[tuple[int, int]] = []
    for e in g.edges:
        if e.kind != EdgeKind.PREDECESSOR:
            continue
        a, b = index[e.src], index[e.dst]
        if a != b and (a, b) not in seen:
            seen.add((a, b))
            result.append((a, b))
    return sorted(result)


def choice_requires(g: StoryGraph, target_group: list[str]) -> list[str]:
    """A choice into a gated (residue) passage carries its head's gate."""
    return sorted(_beat(g, target_group[0]).requires_flags)


def choice_grants(g: StoryGraph, target_group: list[str]) -> list[str]:
    """Entering a passage that contains a path's commit beat locks the
    choice in: the choice edge grants that path's flags. Commits are per
    world; each world's commit passage grants the same flag."""
    beats = set(target_group)
    grants = []
    for flag in g.nodes_of(StateFlag):
        if flag.path is not None and beats & set(queries.grant_beats(g, flag.id)):
            grants.append(flag.id)
    return sorted(grants)


def group_entities(g: StoryGraph, group: list[str]) -> list[str]:
    seen: list[str] = []
    for b in group:
        for entity in _beat(g, b).entities:
            if entity not in seen:
                seen.append(entity)
    return seen


def ending_beat(g: StoryGraph, group: list[str]) -> str | None:
    for b in group:
        if _beat(g, b).is_ending:
            return b
    return None


# -- residue / variant needs ---------------------------------------------------


@dataclass(frozen=True)
class ConvergenceNeed:
    """One world's rejoin frontier of a soft dilemma and what its residue
    weight demands there. `world` is '' in the shared region; the hard
    path(s) whose fork created the world otherwise (queries.world_label)."""

    dilemma: str
    weight: ResidueWeight
    world: str
    rejoin: tuple[str, ...]  # beat(s) where the paths rejoin; >1 at a hard fork
    path_flags: dict[str, str]  # path id -> dilemma flag id


def convergence_needs(g: StoryGraph) -> list[ConvergenceNeed]:
    """Light- and heavy-residue soft convergences, one need per world
    (cosmetic needs nothing structural — it is handled in prose wording
    alone)."""
    needs = []
    for d in sorted(g.nodes_of(Dilemma), key=lambda n: n.id):
        if d.role != DilemmaRole.SOFT or d.residue_weight == ResidueWeight.COSMETIC:
            continue
        for world, frontier in queries.soft_rejoin_frontiers(g, d.id):
            if not frontier:
                continue
            needs.append(
                ConvergenceNeed(
                    dilemma=d.id,
                    weight=d.residue_weight,
                    world=queries.world_label(g, world),
                    rejoin=tuple(frontier),
                    path_flags=queries.dilemma_flags(g, d.id),
                )
            )
    return needs


def insert_residue_chain(
    g: StoryGraph, chain: Sequence[Beat], path_id: str, rejoin: Sequence[str]
) -> None:
    """Splice a flag-gated residue arm between a path's exclusive tail and
    the rejoin frontier: tail -> chain -> each beat that carried the tail
    into the frontier (a frontier beat, or a GROW bridge leading there —
    the residue stays on the tail's side of the bridge). The arm is one
    or more identically gated beats — a multi-beat arm is the story
    visibly remembering, and collapses into a single gated passage. The
    frontier is one world's (a per-world need finds that world's tail —
    only it feeds the frontier); when the frontier is itself a deeper
    hard fork, the arm inherits the tail's fan-out into every sub-world,
    so no arc dead-ends at it (I6)."""
    if not chain:
        raise mutations.MutationError(f"residue arm for {path_id} is empty")
    tails = [
        b
        for b in queries.exclusive_beats(g, path_id)
        if queries.frontier_feeds(g, b, list(rejoin))
    ]
    if len(tails) != 1:
        raise mutations.MutationError(
            f"path {path_id} has {len(tails)} beat(s) feeding the rejoin "
            f"frontier {sorted(rejoin)}; residue insertion needs exactly one"
        )
    (tail,) = tails
    for beat in chain:
        mutations.add_beat(g, beat, [])
    for target in sorted(queries.frontier_feeds(g, tail, list(rejoin))):
        mutations.remove_ordering(g, tail, target)
        mutations.add_ordering(g, chain[-1].id, target)
    prev = tail
    for beat in chain:
        mutations.add_ordering(g, prev, beat.id)
        prev = beat.id


# -- false branches -------------------------------------------------------------


def long_linear_runs(groups: list[list[str]], min_beats: int = 3) -> list[int]:
    """Groups long enough that the player goes a while without a choice —
    candidate sites for cadence diamonds (the feel target is a genuine
    choice roughly every 250-800 traversed words, B6)."""
    return [i for i, grp in enumerate(groups) if len(grp) >= min_beats]


def insert_false_branch(
    g: StoryGraph, arm_a: Sequence[Beat], arm_b: Sequence[Beat], before: str, after: str
) -> None:
    """Splice a cosmetic diamond into a linear edge: before -> chain a /
    chain b -> after. Arms are short chains (1-2 beats), two flavors of
    the same forward motion."""
    if not g.has_edge(EdgeKind.PREDECESSOR, before, after):
        raise mutations.MutationError(f"no linear edge {before} -> {after} to fork")
    for chain in (arm_a, arm_b):
        for beat in chain:
            mutations.add_beat(g, beat, [])
    mutations.remove_ordering(g, before, after)
    for chain in (arm_a, arm_b):
        prev = before
        for beat in chain:
            mutations.add_ordering(g, prev, beat.id)
            prev = beat.id
        mutations.add_ordering(g, prev, after)


# -- feasibility ---------------------------------------------------------------


def active_flags(g: StoryGraph, group: list[str]) -> list[str]:
    """Flags the passage's prose must honor both values of (the I12
    computation — see queries.ambiguous_flags). Certain flags are world
    facts, not states; the audit only weighs the ambiguous ones."""
    return queries.ambiguous_flags(g, group)
