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
    groups = collapse_groups(g, max_beats=preset.passage_beats_max, split_viewpoints=True)
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
    # Texture arms host no independent diamonds — theirs arrive mirrored
    # from the trunk (insert_cadence_diamond), so both worlds keep the
    # same choice topology. Mirrored trunk stretches stay in capacity:
    # a diamond there is planted on both sides at once.
    arms = {b.id for b in g.nodes_of(Beat) if b.purpose == StructuralPurpose.TEXTURE_WORLD}
    capacity: dict[int, list[int]] = {}
    for i in long_linear_runs(runs):
        if arms & set(runs[i]):
            continue
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
        probe_arms = [
            Beat(
                id=f"beat:cadence-probe-{probe}-{side}",
                created_by=_beat(g, run[0]).created_by,
                summary="probe",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.FALSE_BRANCH,
            )
            for side in ("a", "b")
        ]
        # mirrored-stretch edges get the paired splice so the projection
        # counts both worlds' choices, exactly as the apply will
        insert_cadence_diamond(scratch, [probe_arms[0]], [probe_arms[1]], run[edge], run[edge + 1])
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


# -- texture worlds (structural-depth W3; invariant I15) -------------------------

# Scene-scale substance, not cadence filler: a run-scale fork is the
# cheapest choice in reader-words (the walk traverses one world), but each
# one doubles the FILL cost of its stretch, so the budget stays small.
TEXTURE_WORLDS_MAX = 3


def texture_sites(g: StoryGraph, preset) -> list[list[str]]:
    """Stretches a texture fork may parallel — v1: **cap-aligned
    sub-stretches** of maximal linear runs. Every beat in the stretch is
    ungated, commits nothing, ends nothing, and is not itself a texture
    arm (a real weave's long shared run always carries locked resolutions,
    so whole runs almost never qualify — the stretch excises around them);
    boundaries snap to the collapse cap so the trunk's passage chunking
    survives the fork edges (cadence's aligned-seam logic, run-scale); at
    least one full chunk long (scene-scale, not a graft); with a
    predecessor to fork from (a root-headed stretch would mint a second
    root, I4); and touching no soft rejoin frontier at either boundary —
    a later residue splice reroutes the trunk edges around a frontier,
    and a parallel arm's edge would bypass the memory beat (the I15
    projection rule catches that bypass loudly; the site rule avoids
    creating it). One candidate per qualifying window: its largest
    aligned stretch."""
    cap = preset.passage_beats_max
    frontier_beats = {b for need in convergence_needs(g) for b in need.rejoin}

    def qualifies(beat_id: str) -> bool:
        b = _beat(g, beat_id)
        return not (
            b.requires_flags
            or b.commits_dilemmas
            or b.is_ending
            or b.purpose == StructuralPurpose.TEXTURE_WORLD
        )

    sites = []
    for run in collapse_groups(g):
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
            if end - start + 1 >= cap:
                stretch = run[start : end + 1]
                head_frontier = stretch[0] in frontier_beats
                tail_frontier = set(queries.successors(g, stretch[-1])) & frontier_beats
                if not head_frontier and not tail_frontier:
                    sites.append(stretch)
            i = j + 1
    return sites


def insert_texture_world(g: StoryGraph, arm: Sequence[Beat], stretch: Sequence[str]) -> None:
    """Splice a parallel texture-world arm around ``stretch``: every
    predecessor of the stretch head also feeds the arm head, the arm tail
    feeds every successor of the stretch tail, and no trunk edge moves —
    additions only (I9), the trunk becomes conditionally traversed like a
    diamond arm. The engine copies each twin's *effective* annotations
    onto its arm beat (mirroring is engine work, never model-set — copied
    raw, a twin's unset annotation would fall back asymmetrically) and
    records the twin in ``mirrors``, the evidence I15 checks."""
    if not arm:
        raise mutations.MutationError("a texture arm needs at least one beat")
    if len(arm) != len(stretch):
        raise mutations.MutationError(
            f"texture arm has {len(arm)} beat(s) against a {len(stretch)}-beat "
            "stretch; the arm mirrors the trunk beat-for-beat (I15) — give "
            "every trunk beat exactly one arm twin, in order"
        )
    preds = queries.predecessors(g, stretch[0])
    succs = queries.successors(g, stretch[-1])
    if not preds or not succs:
        raise mutations.MutationError(
            f"stretch {stretch[0]} .. {stretch[-1]} has no predecessor or no "
            "successor to fork around; a root or ending stretch cannot be "
            "paralleled — pick an interior stretch"
        )
    for a, b in zip(stretch, stretch[1:], strict=False):
        if not g.has_edge(EdgeKind.PREDECESSOR, a, b):
            raise mutations.MutationError(
                f"stretch beats {a} -> {b} are not adjacent; the stretch must "
                "be a contiguous linear chain"
            )
    for beat, twin_id in zip(arm, stretch, strict=True):
        twin = _beat(g, twin_id)
        if twin.requires_flags or twin.commits_dilemmas or twin.is_ending:
            raise mutations.MutationError(
                f"stretch beat {twin_id} is gated, commits, or ends the story; "
                "a texture fork parallels only consequence-free stretches — "
                "shrink the stretch to exclude it"
            )
        if twin.purpose == StructuralPurpose.TEXTURE_WORLD:
            raise mutations.MutationError(
                f"stretch beat {twin_id} is itself a texture arm; worlds do "
                "not nest — parallel the trunk, not an arm"
            )
        if beat.purpose != StructuralPurpose.TEXTURE_WORLD:
            raise mutations.MutationError(
                f"texture arm beat {beat.id} must carry purpose texture_world"
            )
        beat.mirrors = twin.id
        beat.scene_type = effective_scene_type(twin)
        beat.narration_scope = effective_narration_scope(twin)
        beat.viewpoint = twin.viewpoint
        beat.interlude = twin.interlude
    for beat in arm:
        mutations.add_beat(g, beat, [])
    for p in sorted(preds):
        mutations.add_ordering(g, p, arm[0].id)
    for prev, beat in zip(arm, arm[1:], strict=False):
        mutations.add_ordering(g, prev.id, beat.id)
    for s in sorted(succs):
        mutations.add_ordering(g, arm[-1].id, s)


def _arm_pairs(g: StoryGraph, before: str, after: str) -> list[tuple[str, str]]:
    """Texture-arm beat pairs mirroring the trunk edge (before, after) —
    one per arm paralleling that stretch."""
    by_mirror: dict[str, list[str]] = {}
    for b in g.nodes_of(Beat):
        if b.mirrors:
            by_mirror.setdefault(b.mirrors, []).append(b.id)
    return sorted(
        (a, z)
        for a in by_mirror.get(before, [])
        for z in by_mirror.get(after, [])
        if g.has_edge(EdgeKind.PREDECESSOR, a, z)
    )


def _twin_chain(g: StoryGraph, chain: Sequence[Beat], k: int) -> list[Beat]:
    """Texture twins of freshly spliced trunk false-branch beats: same
    summary for now (words for texture worlds are the wording pass's job —
    structure is copied by the engine, words are rewritten per world,
    A14's doctrine), mirrored annotations, engine-suffixed ids."""
    return [
        Beat(
            id=f"{fb.id}--tw{k}",
            created_by=fb.created_by,
            summary=fb.summary,
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.TEXTURE_WORLD,
            entities=list(fb.entities),
            mirrors=fb.id,
            scene_type=effective_scene_type(fb),
            narration_scope=effective_narration_scope(fb),
            viewpoint=fb.viewpoint,
            interlude=fb.interlude,
        )
        for fb in chain
    ]


def insert_cadence_diamond(
    g: StoryGraph, arm_a: Sequence[Beat], arm_b: Sequence[Beat], before: str, after: str
) -> None:
    """The cadence splice finalize applies: a plain diamond on an ordinary
    edge; on a trunk edge inside a mirrored stretch, the same diamond is
    additionally mirrored into every texture arm paralleling it —
    engine-suffixed twins of the fresh arms, wired identically — so both
    worlds keep the same choice topology and the I15 projection stays
    edge-exact (a one-sided diamond would remove the trunk edge the arm's
    edge projects onto, and hand the trunk world choices the parallel
    world lacks)."""
    pairs = _arm_pairs(g, before, after)
    insert_false_branch(g, arm_a, arm_b, before, after)
    for k, (ai, aj) in enumerate(pairs):
        twins = [_twin_chain(g, chain, k) for chain in (arm_a, arm_b)]
        for chain in twins:
            for beat in chain:
                mutations.add_beat(g, beat, [])
        mutations.remove_ordering(g, ai, aj)
        for chain in twins:
            prev = ai
            for beat in chain:
                mutations.add_ordering(g, prev, beat.id)
                prev = beat.id
            mutations.add_ordering(g, prev, aj)


def insert_cadence_sidetrack(g: StoryGraph, arm: Sequence[Beat], before: str, after: str) -> None:
    """Sidetrack counterpart of ``insert_cadence_diamond``: the direct
    edge stays on both sides; the detour is mirrored into every arm."""
    pairs = _arm_pairs(g, before, after)
    insert_sidetrack(g, arm, before, after)
    for k, (ai, aj) in enumerate(pairs):
        twins = _twin_chain(g, arm, k)
        for beat in twins:
            mutations.add_beat(g, beat, [])
        prev = ai
        for beat in twins:
            mutations.add_ordering(g, prev, beat.id)
            prev = beat.id
        mutations.add_ordering(g, prev, aj)


def texture_plan(g: StoryGraph, preset) -> list[list[str]]:
    """Run-scale fork budget: the stretches finalize parallels, sized by
    the same iterated projection as ``cadence_plan`` but budgeted FIRST —
    a texture fork adds a decision at near-zero traversed words, so it
    takes the cheap wins before beat diamonds spend arm-words on the
    rest. Longest qualifying runs first (the most scene-scale substance),
    until the projected mean reaches the same upper-middle B6 target,
    the cap (TEXTURE_WORLDS_MAX) is hit, or sites run out."""
    from questfoundry.graph.validate import B6_WORDS_PER_CHOICE

    lo, hi = B6_WORDS_PER_CHOICE
    target = (lo + 2 * hi) // 3
    sites = sorted(texture_sites(g, preset), key=lambda run: (-len(run), run[0]))
    if not sites:
        return []

    def projected_mean(scratch: StoryGraph) -> float:
        walks = projected_walks(scratch, preset)
        return sum(w for w, _ in walks) / max(sum(d for _, d in walks), 1)

    scratch = copy.deepcopy(g)
    chosen: list[list[str]] = []
    for run in sites:
        if len(chosen) >= TEXTURE_WORLDS_MAX or projected_mean(scratch) <= target:
            break
        arm = [
            Beat(
                id=f"beat:texture-probe-{len(chosen)}-{i}",
                created_by=_beat(g, run[0]).created_by,
                summary="probe",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.TEXTURE_WORLD,
            )
            for i in range(len(run))
        ]
        insert_texture_world(scratch, arm, run)
        chosen.append(run)
    return chosen


# -- feasibility ---------------------------------------------------------------


def active_flags(g: StoryGraph, group: list[str]) -> list[str]:
    """Flags the passage's prose must honor both values of (the I12
    computation — see queries.ambiguous_flags). Certain flags are world
    facts, not states; the audit only weighs the ambiguous ones."""
    return queries.ambiguous_flags(g, group)
