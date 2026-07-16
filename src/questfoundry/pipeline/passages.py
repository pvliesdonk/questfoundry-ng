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
    SceneType,
    StateFlag,
    StructuralPurpose,
    effective_narration_scope,
    effective_scene_type,
    passage_intensity,
)

# -- collapse ----------------------------------------------------------------


def _beat(g: StoryGraph, beat_id: str) -> Beat:
    node = g.node(beat_id)
    assert isinstance(node, Beat)
    return node


def collapse_groups(
    g: StoryGraph, max_beats: int | None = None, *, split_viewpoints: bool = False
) -> list[list[str]]:
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

    ``split_viewpoints`` additionally cuts where annotated viewpoints
    conflict — one head per passage (I14; rotating-pov-build.md). Two
    beats merge unless both carry a viewpoint and disagree on
    ``(viewpoint, interlude)``; a beat without one (bridge, residue,
    false-branch, wide codas) is a wildcard and merges anywhere. Like the
    cap, this is prose chunking: passage-building call sites set it, the
    raw choice-topology mode leaves it off.
    """
    order = queries.topological_order(g)
    if order is None:
        raise ValueError("beat graph has a cycle; collapse needs a DAG")

    def head(beat_id: str) -> tuple[str, bool] | None:
        beat = _beat(g, beat_id)
        return None if beat.viewpoint is None else (beat.viewpoint, beat.interlude)

    def merges(a: str, b: str) -> bool:
        if len(queries.successors(g, a)) != 1 or len(queries.predecessors(g, b)) != 1:
            return False
        if sorted(_beat(g, a).requires_flags) != sorted(_beat(g, b).requires_flags):
            return False
        if split_viewpoints:
            # the group's head so far is a's run-head: a itself may be a
            # wildcard riding an earlier annotated beat, so compare against
            # the group's settled head, not just a's own
            ha, hb = group_head.get(group_of[a]), head(b)
            if ha is not None and hb is not None and ha != hb:
                return False
        return True

    groups: list[list[str]] = []
    group_of: dict[str, int] = {}
    group_head: dict[int, tuple[str, bool]] = {}
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
        if split_viewpoints and group_of[b] not in group_head:
            h = head(b)
            if h is not None:
                group_head[group_of[b]] = h
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


_FORK_RENDERING = (StructuralPurpose.FALSE_BRANCH, StructuralPurpose.TEXTURE_WORLD)


def cosmetic_rejoin_sources(groups: list[list[str]], g: StoryGraph) -> set[int]:
    """Source groups whose outgoing choice is a cosmetic-fork rendering
    rejoining the road the reader could have walked plainly: the group is one
    rendering of a cosmetic fork (its beats carry a false-branch or
    texture-world purpose) and it edges into a *shared rejoin* — a destination
    several parallel edges enter. Their label passes are ordered AFTER the
    parallel siblings' (`_polish_expand`) so each carries its rendering's
    residue instead of re-offering the action a sibling already labels onto
    the same destination — the confirmed exit-label convergence (01 §6;
    cosmetic-forks §5). A rendering's internal chunk seams are excluded: a
    capped arm splits into groups joined by single edges, whose destination
    has one entering edge and so nothing to differ from."""
    edges = group_edges(groups, g)
    incoming: dict[int, int] = {}
    for _, b in edges:
        incoming[b] = incoming.get(b, 0) + 1
    return {
        a
        for a, b in edges
        if incoming[b] >= 2 and any(_beat(g, x).purpose in _FORK_RENDERING for x in groups[a])
    }


def choice_requires(g: StoryGraph, target_group: list[str]) -> list[str]:
    """A choice into a gated (residue) passage carries its head's gate."""
    return sorted(_beat(g, target_group[0]).requires_flags)


def choice_grants(g: StoryGraph, target_group: list[str]) -> list[str]:
    """Entering a passage that contains a flag's grant beat locks the choice
    in: the choice edge grants that flag. A dilemma flag's grant is its path's
    commit (per world; each world's commit passage grants the same flag); a
    cosmetic flag's grant is a rendering head that lists it in `grants_flags`
    (cosmetic-forks PR-4) — the entry choice into that rendering carries it, so
    the play engine and exports (which already honor edge grants) hold it for
    exactly the readers who took the rendering."""
    beats = set(target_group)
    grants = [
        flag.id
        for flag in g.nodes_of(StateFlag)
        if beats & set(queries.grant_beats(g, flag.id))
    ]
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
    groups = collapse_groups(g, max_beats=preset.passage_beats_max, split_viewpoints=True)
    edges = group_edges(groups, g)
    succ: dict[int, list[int]] = {}
    for a, b in edges:
        succ.setdefault(a, []).append(b)
    group_of = {b: i for i, grp in enumerate(groups) for b in grp}
    root_groups = {group_of[r] for r in queries.roots(g)}
    results = []
    # Cosmetic grants are per-walk, not per-view: a rendering head sits in
    # every arc view, so view-derived holding counted keywords from detours a
    # walk never took (cosmetic-forks §4, open question 5 — resolved). A
    # cosmetic flag accrues when the walk traverses its granting group.
    cosmetic_grants: dict[int, set[str]] = {}
    for f in g.nodes_of(StateFlag):
        if f.path is None:
            for grant in queries.grant_beats(g, f.id):
                if grant in group_of:
                    cosmetic_grants.setdefault(group_of[grant], set()).add(f.id)
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        # Dilemma flags stay view-derived: a commit is on exactly the arcs
        # the view selects, so view membership IS the walk's holding.
        held = {
            f.id
            for f in g.nodes_of(StateFlag)
            if f.path is not None
            and any(grant in view for grant in queries.grant_beats(g, f.id))
        }
        in_view = [all(b in view for b in grp) for grp in groups]
        cur = min(i for i in root_groups if in_view[i])
        words = decisions = 0
        while True:
            held |= cosmetic_grants.get(cur, set())
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


class _Rendering:
    """A non-fresh rendering of a cosmetic fork (a sentinel, not a beat chain)."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return self._name


EMPTY_RENDERING = _Rendering("EMPTY_RENDERING")  # the direct before->after edge (walk-on)
SEGMENT_RENDERING = _Rendering("SEGMENT_RENDERING")  # the trunk segment itself (rendering 0)


def insert_cosmetic_fork(
    g: StoryGraph,
    renderings: Sequence[Sequence[Beat] | _Rendering],
    *,
    before: str | None = None,
    after: str | None = None,
    segment: Sequence[str] = (),
) -> None:
    """The one cosmetic-fork splice (01 §6): k ≥ 2 *renderings* of a trunk
    *segment*, all rejoining where it ends. Each rendering is
    ``EMPTY_RENDERING`` (the direct ``before -> after`` edge — a walk-on),
    ``SEGMENT_RENDERING`` (the trunk segment's own beats — rendering 0), or a
    fresh ``list[Beat]`` chain. ``segment`` is the trunk beats between the
    boundary: empty for an *edge-scale* fork (diamond / sidetrack, where
    ``before``/``after`` name the edge), non-empty for a *segment-scale* fork
    (texture world / small two-worlds, where the boundary is the segment's
    predecessors and successors and the trunk stays put). A fresh chain over a
    non-empty segment mirrors it beat-for-beat (I15); over an empty segment it
    invents a breath of texture. The direct edge is kept iff an
    ``EMPTY_RENDERING`` is offered. Additions only, save the diamond's spine
    removal (I9). The three shipped shapes are adapters below."""
    renderings = list(renderings)
    fresh = [list(r) for r in renderings if not isinstance(r, _Rendering)]
    segment = list(segment)
    if len(renderings) < 2:
        raise mutations.MutationError("a cosmetic fork needs at least two renderings")
    if not fresh:
        raise mutations.MutationError("a cosmetic fork needs at least one fresh rendering")
    for chain in fresh:
        if not chain:
            raise mutations.MutationError("a fresh rendering needs at least one beat")
    # There is one trunk segment and one direct edge, so at most one of each
    # marker; and the two scales are exclusive — a segment-scale fork's
    # rendering 0 IS the segment (no walk-on edge), an edge-scale fork has no
    # segment to render 0 (PR-5's loop will call this with looser inputs).
    n_empty = sum(1 for r in renderings if r is EMPTY_RENDERING)
    n_segment = sum(1 for r in renderings if r is SEGMENT_RENDERING)
    if n_empty > 1 or n_segment > 1:
        raise mutations.MutationError(
            "a cosmetic fork offers at most one EMPTY_RENDERING and one SEGMENT_RENDERING"
        )
    if segment:
        if n_segment != 1:
            raise mutations.MutationError(
                "a segment-scale fork's rendering 0 is the trunk segment — offer "
                "exactly one SEGMENT_RENDERING"
            )
        if n_empty:
            raise mutations.MutationError(
                "a segment-scale fork has no walk-on edge; EMPTY_RENDERING is edge-scale only"
            )
    elif n_segment:
        raise mutations.MutationError(
            "an edge-scale fork has no trunk segment; SEGMENT_RENDERING needs a non-empty segment"
        )

    if segment:
        # Segment-scale: the trunk stays (rendering 0), each fresh chain mirrors
        # it. Check order matches the shipped texture splice so its message
        # tests hold: length -> boundary -> contiguity -> per-beat.
        for chain in fresh:
            if len(chain) != len(segment):
                raise mutations.MutationError(
                    f"texture arm has {len(chain)} beat(s) against a {len(segment)}-beat "
                    "stretch; the arm mirrors the trunk beat-for-beat (I15) — give "
                    "every trunk beat exactly one arm twin, in order"
                )
        entry = queries.predecessors(g, segment[0])
        exit_ = queries.successors(g, segment[-1])
        if not entry or not exit_:
            raise mutations.MutationError(
                f"stretch {segment[0]} .. {segment[-1]} has no predecessor or no "
                "successor to fork around; a root or ending stretch cannot be "
                "paralleled — pick an interior stretch"
            )
        for a, b in zip(segment, segment[1:], strict=False):
            if not g.has_edge(EdgeKind.PREDECESSOR, a, b):
                raise mutations.MutationError(
                    f"stretch beats {a} -> {b} are not adjacent; the stretch must "
                    "be a contiguous linear chain"
                )
        for chain in fresh:
            _mirror_onto_segment(g, chain, segment)
    else:
        # Edge-scale: the direct before->after edge is the spine; keep it iff a
        # walk-on (EMPTY) rendering is offered.
        if before is None or after is None:
            raise mutations.MutationError("an edge-scale cosmetic fork needs `before` and `after`")
        if not g.has_edge(EdgeKind.PREDECESSOR, before, after):
            raise mutations.MutationError(f"no linear edge {before} -> {after} to fork")
        if EMPTY_RENDERING not in renderings:
            mutations.remove_ordering(g, before, after)
        entry, exit_ = [before], [after]

    for chain in fresh:
        for beat in chain:
            mutations.add_beat(g, beat, [])
        for p in sorted(entry):
            mutations.add_ordering(g, p, chain[0].id)
        prev = chain[0].id
        for beat in chain[1:]:
            mutations.add_ordering(g, prev, beat.id)
            prev = beat.id
        for s in sorted(exit_):
            mutations.add_ordering(g, prev, s)


def _mirror_onto_segment(g: StoryGraph, arm: Sequence[Beat], segment: Sequence[str]) -> None:
    """Texture mirroring (I15): each fresh arm beat twins the segment beat at
    its position — the twin's *effective* annotations engine-copied,
    ``mirrors`` recorded — and the segment must be consequence-free and
    non-nesting. ``entities`` is deliberately NOT copied: the arm's whole point
    is a different backdrop (01 §6), so its entities belong to whoever words
    the arm. Length was checked by the caller (message order)."""
    for beat, twin_id in zip(arm, segment, strict=True):
        twin = _beat(g, twin_id)
        if twin.requires_flags or twin.commits_dilemmas or twin.is_ending:
            raise mutations.MutationError(
                f"stretch beat {twin_id} is gated, commits, or ends the story; "
                "a texture fork parallels only consequence-free stretches — "
                "shrink the stretch to exclude it"
            )
        # the twin may itself be a mirror beat: worlds nest (cosmetic-forks
        # §3) — mirror chains ground out in trunk beats transitively (I15)
        if beat.purpose != StructuralPurpose.TEXTURE_WORLD:
            raise mutations.MutationError(
                f"texture arm beat {beat.id} must carry purpose texture_world"
            )
        beat.mirrors = twin.id
        beat.scene_type = effective_scene_type(twin)
        beat.narration_scope = effective_narration_scope(twin)
        beat.viewpoint = twin.viewpoint
        beat.interlude = twin.interlude


def insert_false_branch(
    g: StoryGraph, arm_a: Sequence[Beat], arm_b: Sequence[Beat], before: str, after: str
) -> None:
    """Cosmetic diamond — edge-scale, two fresh renderings, no walk-on: the
    direct edge is removed and two flavors of the same forward motion fork and
    rejoin. Adapter over ``insert_cosmetic_fork``."""
    insert_cosmetic_fork(g, [list(arm_a), list(arm_b)], before=before, after=after)


def insert_sidetrack(g: StoryGraph, arm: Sequence[Beat], before: str, after: str) -> None:
    """Cosmetic sidetrack — edge-scale, walk-on + one fresh rendering: the
    direct edge stays and a short detour forks off and rejoins, the reader free
    to decline it. Adapter over ``insert_cosmetic_fork``."""
    if not arm:
        raise mutations.MutationError("a sidetrack needs at least one detour beat")
    insert_cosmetic_fork(g, [EMPTY_RENDERING, list(arm)], before=before, after=after)


# -- texture worlds (structural-depth W3; invariant I15) -------------------------

# Scene-scale substance, not cadence filler: a run-scale fork is the
# cheapest choice in reader-words (the walk traverses one world), but each
# one doubles the FILL cost of its stretch, so the budget stays small.
TEXTURE_WORLDS_MAX = 3


def fork_segments(
    g: StoryGraph, preset
) -> tuple[list[list[str]], list[list[tuple[str, str]]]]:
    """One round's candidate cosmetic-fork sites (cosmetic-forks §1, §6), as
    ``(segments, seam_edges)`` — the segment tiers and the edge tier of the
    unified table.

    Segments generalize the one-shot texture-sites aligned-window walk: a window's
    seam-aligned span of >= cap beats is a *scene* segment (texture world);
    a run-tail span of 1..cap-1 beats — seam-aligned start, ending at a run
    end that has an exit — is a *small two-worlds* segment, the admission of
    shorter segments into the same machinery (interior spans snap to seams
    on both sides, so they are always cap-multiples; only a run tail can be
    small). ``qualifies`` drops the texture-arm exclusion — a segment inside
    a rendering is just a segment the next round may fork (recursion, §3) —
    and excludes FALSE_BRANCH decoration, which is never re-rendered.

    Seam edges are the cap-aligned interior edges of long linear runs
    (today's cadence capacity), arm runs included: with the mirrored-cadence
    machinery retired, a detour inside one rendering is simply budgeted on
    that rendering's own walks (per-walk B6 owns choice fairness)."""
    cap = preset.passage_beats_max
    frontier_beats = {b for need in convergence_needs(g) for b in need.rejoin}

    def qualifies(beat_id: str) -> bool:
        b = _beat(g, beat_id)
        return not (
            b.requires_flags
            or b.commits_dilemmas
            or b.is_ending
            or b.purpose == StructuralPurpose.FALSE_BRANCH
        )

    segments: list[list[str]] = []
    runs = collapse_groups(g)
    for run in runs:
        i = 0
        while i < len(run):
            if not qualifies(run[i]):
                i += 1
                continue
            j = i
            while j + 1 < len(run) and qualifies(run[j + 1]):
                j += 1
            start = i if i % cap == 0 else i + (cap - i % cap)
            if start == 0 and not queries.predecessors(g, run[0]):
                start = cap
            end = j if j == len(run) - 1 else (j + 1) // cap * cap - 1
            if end == len(run) - 1 and not queries.successors(g, run[-1]):
                end = (j + 1) // cap * cap - 1
            if end >= start:
                stretch = run[start : end + 1]
                head_frontier = stretch[0] in frontier_beats
                tail_frontier = set(queries.successors(g, stretch[-1])) & frontier_beats
                if not head_frontier and not tail_frontier:
                    segments.append(stretch)
            i = j + 1

    seam_edges: list[list[tuple[str, str]]] = []
    for idx in long_linear_runs(runs):
        run = runs[idx]
        aligned = [
            (run[e], run[e + 1]) for e in range(len(run) - 1) if (e + 1) % cap == 0
        ]
        if aligned:
            seam_edges.append(aligned)
    return segments, seam_edges


def scene_fork_count(g: StoryGraph, cap: int) -> int:
    """Existing scene-scale renderings — maximal mirror-beat chains of
    >= cap beats — so the story-total ``TEXTURE_WORLDS_MAX`` holds across
    finalize rounds as a pure function of the graph (resume determinism).
    Chain steps skip through un-mirrored FALSE_BRANCH decoration on either
    side (the same contraction the I15 shape rule applies), so a diamond a
    later round spliced inside a rendering does not split the count."""
    beats = {b.id: b for b in g.nodes_of(Beat)}
    mirror = {bid: b.mirrors for bid, b in beats.items() if b.mirrors}
    twins = set(mirror.values())

    def effective_successors(bid: str) -> list[str]:
        out, stack, seen = [], list(queries.successors(g, bid)), set()
        while stack:
            s = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            b = beats.get(s)
            if (
                b is not None
                and b.purpose == StructuralPurpose.FALSE_BRANCH
                and b.mirrors is None
                and s not in twins
            ):
                stack.extend(queries.successors(g, s))
            else:
                out.append(s)
        return out

    def effective_predecessors(bid: str) -> set[str]:
        out, stack, seen = set(), list(queries.predecessors(g, bid)), set()
        while stack:
            s = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            b = beats.get(s)
            if (
                b is not None
                and b.purpose == StructuralPurpose.FALSE_BRANCH
                and b.mirrors is None
                and s not in twins
            ):
                stack.extend(queries.predecessors(g, s))
            else:
                out.add(s)
        return out

    def chain_next(bid: str) -> str | None:
        # a chain step stays inside ONE fresh rendering: the twins are
        # consecutive AND the current beat is the candidate's only effective
        # predecessor — a rendering head inherits its segment entry's fan-in
        # (adjacent constructs' tails included), which marks the boundary
        twin_succ = set(effective_successors(mirror[bid]))
        for s in effective_successors(bid):
            nb = beats.get(s)
            if (
                nb is not None
                and nb.mirrors
                and nb.mirrors in twin_succ
                and effective_predecessors(s) == {bid}
            ):
                return s
        return None

    heads = set(mirror)
    for bid in mirror:
        nxt = chain_next(bid)
        if nxt is not None:
            heads.discard(nxt)
    count = 0
    for head in sorted(heads):
        length, cur = 1, head
        while (cur := chain_next(cur)) is not None:
            length += 1
        if length >= cap:
            count += 1
    return count


@dataclass(frozen=True)
class ForkSite:
    """One admitted cosmetic-fork site of a finalize round (cosmetic-forks
    §6). Edge-scale: ``segment`` is empty and ``(before, after)`` names the
    seam edge; ``arms`` is the engine-assigned fresh-rendering count (1 =
    sidetrack, 2-3 = diamond). Segment-scale: ``segment`` carries the trunk
    beats, ``before`` doubles as the sort anchor (the segment head), ``after``
    is empty, and ``arms`` is 1 (two-worlds: the segment itself + one fresh
    rendering). ``keywords`` are the holdable, unconsumed cosmetic flags the
    site's call may let one gated extra rendering consume — pinned at
    round-plan time, so offers are strictly from earlier rounds; empty for
    segment-scale sites (a keyword never gates a scene-scale world; the v1
    gated rendering is edge-scale only)."""

    before: str
    after: str
    segment: tuple[str, ...]
    arms: int
    keywords: tuple[str, ...]


def offered_keywords(g: StoryGraph, before_id: str, limit: int = 8) -> list[str]:
    """Cosmetic keywords a fork at ``before_id``'s outgoing edge may consume:
    unconsumed (no beat requires them — one consumer per keyword), every
    grant strictly upstream of ``before_id`` (so a holder provably made the
    granting choice before reaching the fork; I10 by construction), capped
    at ``limit`` as a context-bloat guard (cosmetic-forks §6)."""
    consumed = {f for b in g.nodes_of(Beat) for f in b.requires_flags}
    upstream = queries.ancestors(g, before_id)
    out = []
    for flag in sorted(g.nodes_of(StateFlag), key=lambda f: f.id):
        if flag.path is not None or flag.id in consumed:
            continue
        grants = queries.grant_beats(g, flag.id)
        if grants and all(b in upstream for b in grants):
            out.append(flag.id)
    return out[:limit]


def fork_plan(g: StoryGraph, preset, words_target: int | None = None) -> list[ForkSite]:
    """One finalize round's admissions (cosmetic-forks §3, §6): recompute the
    qualifying sites and both budgets on the *current* graph and assign shape
    and arm count per admitted site — the same graph-pure machinery the
    one-shot pass used (``fork_segments`` for the tiers, ``projected_walks``
    for the B6 projection, the one-shot texture plan's words-admission
    rule), iterated to a fixed point by the round loop.

    Admission order follows marginal story-words per decision: scene
    segments first (near-zero traversed words; capped story-total at
    ``TEXTURE_WORLDS_MAX`` — existing worlds counted via ``scene_fork_count``,
    so the cap holds across rounds), then seam edges (a micro chunk per arm,
    the cheapest tier), then small two-worlds segments last (a re-printed
    chunk buys one decision — real substance, but the dearest ratio, so they
    take only the budget the cheaper tiers leave). Edges go
    largest-remaining-run first in bisection order, shapes cycled from the
    scope's ``cadence_arm_cycle`` offset by the cosmetic flags already
    minted (the cycle position stays a pure function of the graph — resume
    determinism).
    Every site's marginal story words must fit the headroom (``words_target``
    or the band top). An empty plan is the loop's terminal round: the B6 mean
    is at target, or no site fits the remaining words, or capacity is out.
    Deterministic: same graph, same plan."""
    from questfoundry.graph.validate import B6_WORDS_PER_CHOICE

    lo, hi = B6_WORDS_PER_CHOICE
    target = (lo + 2 * hi) // 3
    cap = preset.passage_beats_max
    limit = words_target if words_target is not None else preset.words_total[1]
    segments, edge_runs = fork_segments(g, preset)

    def projected_worst(scratch: StoryGraph) -> float:
        walks = projected_walks(scratch, preset)
        return max(w / max(d, 1) for w, d in walks)

    scratch = copy.deepcopy(g)
    total = projected_total_words(g, preset)
    scenes = scene_fork_count(g, cap)
    sites: list[ForkSite] = []
    admitted_beats: set[str] = set()
    probe = 0

    def admit_segment(seg: list[str]) -> None:
        nonlocal probe, total, scenes
        marginal = _stretch_words(g, seg, preset)
        if total + marginal > limit:
            return  # a shorter site may still fit the words budget
        arm = [
            Beat(
                id=f"beat:fork-probe-{probe}-{i}",
                created_by=_beat(g, seg[0]).created_by,
                summary="probe",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.TEXTURE_WORLD,
            )
            for i in range(len(seg))
        ]
        insert_texture_world(scratch, arm, seg)
        probe += 1
        total += marginal
        scenes += len(seg) >= cap
        admitted_beats.update(seg)
        sites.append(
            ForkSite(before=seg[0], after="", segment=tuple(seg), arms=1, keywords=())
        )

    ordered = sorted(segments, key=lambda run: (-len(run), run[0]))
    for seg in ordered:
        if len(seg) < cap or scenes >= TEXTURE_WORLDS_MAX:
            continue
        if projected_worst(scratch) <= target:
            break
        admit_segment(seg)

    # Edge tier: skip seams touching an admitted segment (its fork boundaries
    # land there this round; next round they are ordinary run seams again).
    capacity = [
        [e for e in run if e[0] not in admitted_beats and e[1] not in admitted_beats]
        for run in edge_runs
    ]
    capacity = [
        [run[j] for j in _bisection_order(len(run))] for run in capacity if run
    ]
    taken = [0] * len(capacity)
    cycle = preset.cadence_arm_cycle
    offset = sum(1 for f in g.nodes_of(StateFlag) if f.path is None)
    k = 0
    arm_words = round(preset.words_for(intensity=SceneType.MICRO_BEAT)[1] * 0.9)
    while projected_worst(scratch) > target:
        open_runs = [i for i in range(len(capacity)) if taken[i] < len(capacity[i])]
        if not open_runs:
            break
        run_idx = max(open_runs, key=lambda i: (len(capacity[i]) - taken[i], -i))
        before, after = capacity[run_idx][taken[run_idx]]
        taken[run_idx] += 1
        arms = cycle[(offset + k) % len(cycle)]
        if total + arms * arm_words > limit:
            # degrade to the cheapest shape at the budget boundary: a
            # sidetrack site beats no site (the mix is taste, the words
            # ceiling is a contract)
            arms = 1
        if total + arms * arm_words > limit:
            continue  # no shape fits here; cheaper sites may remain elsewhere
        probe_arms = [
            Beat(
                id=f"beat:fork-probe-{probe}-{side}",
                created_by=_beat(g, before).created_by,
                summary="probe",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.FALSE_BRANCH,
            )
            for side in ("a", "b")[: min(arms, 2)]
        ]
        if arms == 1:
            insert_sidetrack(scratch, probe_arms, before, after)
        else:
            # a 2-arm probe sizes the choice budget for any diamond (the walk
            # traverses one arm; one decision per site regardless of count)
            insert_cosmetic_fork(
                scratch, [[b] for b in probe_arms], before=before, after=after
            )
        probe += 1
        k += 1
        total += arms * arm_words
        sites.append(
            ForkSite(
                before=before,
                after=after,
                segment=(),
                arms=arms,
                keywords=tuple(offered_keywords(g, before)),
            )
        )

    edge_beats = {b for site in sites if not site.segment for b in (site.before, site.after)}
    for seg in ordered:
        if len(seg) >= cap or set(seg) & edge_beats:
            continue
        if projected_worst(scratch) <= target:
            break
        admit_segment(seg)

    return sorted(sites, key=lambda s: s.before)


def insert_texture_world(g: StoryGraph, arm: Sequence[Beat], stretch: Sequence[str]) -> None:
    """Splice a parallel texture-world arm around ``stretch``: every
    predecessor of the stretch head also feeds the arm head, the arm tail
    feeds every successor of the stretch tail, and no trunk edge moves —
    additions only (I9), the trunk becomes conditionally traversed like a
    diamond arm. The engine copies each twin's *effective* annotations
    onto its arm beat (mirroring is engine work, never model-set — copied
    raw, a twin's unset annotation would fall back asymmetrically) and
    records the twin in ``mirrors``, the evidence I15 checks. ``entities``
    is deliberately NOT copied: the arm's whole point is a different
    backdrop — a different place, company, or detail of things and people
    (any consequence-free axis; 01 §6) — so its entities belong to
    whoever words the arm (the fork pass's proposal)."""
    if not arm:
        raise mutations.MutationError("a texture arm needs at least one beat")
    insert_cosmetic_fork(g, [SEGMENT_RENDERING, list(arm)], segment=list(stretch))


def projected_total_words(g: StoryGraph, preset) -> int:
    """Projected prose words for the whole story: every passage group's
    projection summed — the structural estimate of what B7 will measure."""
    groups = collapse_groups(g, max_beats=preset.passage_beats_max, split_viewpoints=True)
    return sum(projected_group_words(g, group, preset) for group in groups)


def _stretch_words(g: StoryGraph, stretch: Sequence[str], preset) -> int:
    """What one texture arm adds to the story's projected words: the
    stretch's own projection, chunked at the cap like the arm will be."""
    cap = preset.passage_beats_max
    chunks = [list(stretch[i : i + cap]) for i in range(0, len(stretch), cap)]
    return sum(projected_group_words(g, chunk, preset) for chunk in chunks)


