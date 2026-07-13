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

import copy
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind
from questfoundry.models.drama import Dilemma, DilemmaRole, ResidueWeight
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    StateFlag,
    StructuralPurpose,
    passage_intensity,
)

# -- collapse ----------------------------------------------------------------


def _beat(g: StoryGraph, beat_id: str) -> Beat:
    node = g.node(beat_id)
    assert isinstance(node, Beat)
    return node


def collapse_groups(g: StoryGraph, max_beats: int | None = None) -> list[list[str]]:
    """Maximal linear runs of beats, in topological order of their heads.

    A run extends across a -> b iff a has exactly one successor, b has
    exactly one predecessor, and both carry the same gate — usually none.
    An identically-gated linear chain (a multi-beat residue arm) is one
    passage: the gate boundary is where the passage breaks, not every
    gated beat.

    ``max_beats`` caps a passage's beat count (scope preset,
    ``passage_beats_max``): a run longer than the cap splits front-to-back
    into cap-sized passages. Every beat is a story moment with a prose
    claim, but a passage's word budget is fixed per scope — unbounded
    collapse crushes a deep run into one passage and the story mints no
    pages from its added structure. The cap is the choice-free cutter;
    cadence diamonds meter *choices* (B6), never words. Pass None for the
    raw choice-topology runs (cadence site detection wants the true
    choice-less stretch, however it is chunked into prose).
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
        if (
            len(preds) == 1
            and merges(preds[0], b)
            and not (max_beats and len(groups[group_of[preds[0]]]) >= max_beats)
        ):
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
    path_flags: dict[str, list[str]]  # path id -> that path's dilemma flags, sorted


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
    _splice_residue(g, [chain], path_id, rejoin)


def insert_residue_diamond(
    g: StoryGraph,
    branch_a: Sequence[Beat],
    branch_b: Sequence[Beat],
    path_id: str,
    rejoin: Sequence[str],
) -> None:
    """Splice a tensored residue arm (M8): two identically gated branches
    forking at the path's exclusive tail and rejoining at the frontier —
    the story remembers the choice AND hands the reader a choice that
    exists only on this side of it. Each branch collapses into its own
    gated passage (the fork and rejoin are boundaries); both count as the
    path's arm for G4's coverage."""
    _splice_residue(g, [branch_a, branch_b], path_id, rejoin)


def _splice_residue(
    g: StoryGraph, branches: Sequence[Sequence[Beat]], path_id: str, rejoin: Sequence[str]
) -> None:
    if not all(branches) or not branches:
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
    for branch in branches:
        for beat in branch:
            mutations.add_beat(g, beat, [])
    for target in sorted(queries.frontier_feeds(g, tail, list(rejoin))):
        mutations.remove_ordering(g, tail, target)
        for branch in branches:
            mutations.add_ordering(g, branch[-1].id, target)
    for branch in branches:
        prev = tail
        for beat in branch:
            mutations.add_ordering(g, prev, beat.id)
            prev = beat.id


# -- false branches -------------------------------------------------------------


def long_linear_runs(groups: list[list[str]], min_beats: int = 3) -> list[int]:
    """Groups long enough that the player goes a while without a choice —
    candidate sites for cadence diamonds (the feel target is a genuine
    choice roughly every 250-800 traversed words, B6). Detect on the
    uncapped collapse: the choice-less stretch is a topology fact,
    however the cap chunks it into prose."""
    return [i for i, grp in enumerate(groups) if len(grp) >= min_beats]


def projected_group_words(g: StoryGraph, group: list[str], preset) -> int:
    """Projected prose words for a passage group: models write near a
    band's cap — every measured live run averaged ~0.9x of it (400/450
    micro, 440-460/500 short, 529 medium) — so a group projects at 0.9x
    the cap of its aggregate-intensity band (scene / sequel / micro; a
    texture arm falls back to micro_beat, keeping the pre-scene_type
    short-band projection)."""
    intensity = passage_intensity(_beat(g, b) for b in group)
    ending = any(_beat(g, b).is_ending for b in group)
    return round(preset.words_for(intensity=intensity, ending=ending)[1] * 0.9)


def projected_walks(g: StoryGraph, preset) -> list[tuple[int, int]]:
    """Per arc selection, a deterministic playthrough over the capped
    collapse groups: (projected walk words, decisions offered). At every
    step the walk counts a decision when >= 2 choices are live (gate
    satisfiable on this arc's history — target in view or not, B6
    semantics) and follows the first live in-view successor. One diamond
    arm is traversed, not both — the projection measures what a reader
    experiences, which is what the arc view over-counted."""
    groups = collapse_groups(g, max_beats=preset.passage_beats_max)
    edges = group_edges(groups, g)
    succ: dict[int, list[int]] = {}
    for a, b in edges:
        succ.setdefault(a, []).append(b)
    group_of = {b: i for i, grp in enumerate(groups) for b in grp}
    root_groups = {group_of[r] for r in queries.roots(g)}
    results = []
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        held = {
            f.id
            for f in g.nodes_of(StateFlag)
            if any(grant in view for grant in queries.grant_beats(g, f.id))
        }
        in_view = [all(b in view for b in grp) for grp in groups]
        cur = min(i for i in root_groups if in_view[i])
        words = decisions = 0
        while True:
            words += projected_group_words(g, groups[cur], preset)
            live = [
                t
                for t in succ.get(cur, [])
                if all(req in held for req in choice_requires(g, groups[t]))
            ]
            if len(live) >= 2:
                decisions += 1
            nxt = [t for t in live if in_view[t]]
            if not nxt:
                break
            cur = nxt[0]
        results.append((words, decisions))
    return results


def _bisection_order(n: int) -> list[int]:
    """Indices 0..n-1 in binary-subdivision order (middle first, then the
    quarters, ...), so the k-th pick is always maximally spread."""
    order: list[int] = []
    intervals = deque([(0, n - 1)])
    seen: set[int] = set()
    while intervals:
        lo, hi = intervals.popleft()
        if lo > hi:
            continue
        mid = (lo + hi) // 2
        if mid not in seen:
            seen.add(mid)
            order.append(mid)
        intervals.append((lo, mid - 1))
        intervals.append((mid + 1, hi))
    return order


def cadence_plan(g: StoryGraph, preset) -> dict[int, list[tuple[str, str]]]:
    """Words-aware diamond budget (M8): uncapped-run index -> the edges
    to fork, sized by iterated projection rather than a closed form.

    Only cap-aligned edges are offered — the seams between complete
    passage chunks — so a diamond costs the reader one arm's words and
    yields one offered choice; a mid-chunk split would mint a whole
    extra passage per choice, a marginal cost so close to the target
    that sizing saturates instead of converging. Probe diamonds go into
    a scratch copy (largest runs first, each run's aligned edges in
    bisection order) and the playthrough is re-projected until its mean
    words-per-choice reaches the B6 band's upper middle — low enough to
    feel played, no denser — or aligned capacity runs out (the band is
    advisory; the cap owns prose volume, this budget owns choices).
    Scratch insertion prices for free what closed forms undercount: a
    diamond in a per-world run is only met by that world's readers.
    """
    from questfoundry.graph.validate import B6_WORDS_PER_CHOICE

    lo, hi = B6_WORDS_PER_CHOICE
    target = (lo + 2 * hi) // 3
    cap = preset.passage_beats_max
    runs = collapse_groups(g)
    capacity: dict[int, list[int]] = {}
    for i in long_linear_runs(runs):
        aligned = [e for e in range(len(runs[i]) - 1) if (e + 1) % cap == 0]
        if aligned:
            capacity[i] = [aligned[j] for j in _bisection_order(len(aligned))]
    if not capacity:
        return {}

    def projected_mean(scratch: StoryGraph) -> float:
        walks = projected_walks(scratch, preset)
        return sum(w for w, _ in walks) / max(sum(d for _, d in walks), 1)

    scratch = copy.deepcopy(g)
    taken: dict[int, int] = dict.fromkeys(capacity, 0)
    probe = 0
    while projected_mean(scratch) > target:
        open_runs = [i for i in capacity if taken[i] < len(capacity[i])]
        if not open_runs:
            break
        run_idx = max(open_runs, key=lambda i: (len(capacity[i]) - taken[i], -i))
        run = runs[run_idx]
        edge = capacity[run_idx][taken[run_idx]]
        arms = [
            Beat(
                id=f"beat:cadence-probe-{probe}-{side}",
                created_by=_beat(g, run[0]).created_by,
                summary="probe",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.FALSE_BRANCH,
            )
            for side in ("a", "b")
        ]
        insert_false_branch(scratch, [arms[0]], [arms[1]], run[edge], run[edge + 1])
        taken[run_idx] += 1
        probe += 1
    return {
        i: [(runs[i][e], runs[i][e + 1]) for e in sorted(capacity[i][: taken[i]])]
        for i in capacity
        if taken[i]
    }


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


def insert_sidetrack(g: StoryGraph, arm: Sequence[Beat], before: str, after: str) -> None:
    """Splice a cosmetic sidetrack onto a linear edge (01 §6): the direct
    edge stays, and a short detour forks off and rejoins — the reader may
    decline it, which is a choice that costs no words."""
    if not g.has_edge(EdgeKind.PREDECESSOR, before, after):
        raise mutations.MutationError(f"no linear edge {before} -> {after} to fork")
    if not arm:
        raise mutations.MutationError("a sidetrack needs at least one detour beat")
    for beat in arm:
        mutations.add_beat(g, beat, [])
    prev = before
    for beat in arm:
        mutations.add_ordering(g, prev, beat.id)
        prev = beat.id
    mutations.add_ordering(g, prev, after)


# -- feasibility ---------------------------------------------------------------


def active_flags(g: StoryGraph, group: list[str]) -> list[str]:
    """Flags the passage's prose must honor both values of (the I12
    computation — see queries.ambiguous_flags). Certain flags are world
    facts, not states; the audit only weighs the ambiguous ones."""
    return queries.ambiguous_flags(g, group)
