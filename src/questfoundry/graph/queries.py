"""Read-only graph queries: DAG walks, arc views, drama-layer lookups.

Arcs are computed, never stored (design doc 01 §5): an arc view is the
beat subgraph reachable under one selection of a path per branched
dilemma, with flag-gated structural beats included only when their
flags' grant beats are in view.
"""

from __future__ import annotations

from collections import deque
from itertools import product

from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind
from questfoundry.models.drama import Dilemma, DilemmaRole, Path
from questfoundry.models.structure import Beat, BeatClass, StateFlag, StructuralPurpose

# -- beat DAG basics -------------------------------------------------------


def beat_ids(g: StoryGraph) -> list[str]:
    return [b.id for b in g.nodes_of(Beat)]


def successors(g: StoryGraph, beat_id: str) -> list[str]:
    return g.out_ids(beat_id, EdgeKind.PREDECESSOR)


def predecessors(g: StoryGraph, beat_id: str) -> list[str]:
    return g.in_ids(beat_id, EdgeKind.PREDECESSOR)


def roots(g: StoryGraph) -> list[str]:
    return [b for b in beat_ids(g) if not predecessors(g, b)]


def topological_order(g: StoryGraph) -> list[str] | None:
    """Kahn's algorithm. Returns None if the beat graph has a cycle."""
    indeg = {b: len(predecessors(g, b)) for b in beat_ids(g)}
    queue = deque(sorted(b for b, d in indeg.items() if d == 0))
    order: list[str] = []
    while queue:
        b = queue.popleft()
        order.append(b)
        for s in successors(g, b):
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)
    return order if len(order) == len(indeg) else None


def _closure(start: set[str], step) -> set[str]:
    seen = set(start)
    frontier = deque(start)
    while frontier:
        for nxt in step(frontier.popleft()):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen


def descendants(g: StoryGraph, beat_id: str) -> set[str]:
    return _closure(set(successors(g, beat_id)), lambda b: successors(g, b))


def ancestors(g: StoryGraph, beat_id: str) -> set[str]:
    return _closure(set(predecessors(g, beat_id)), lambda b: predecessors(g, b))


# -- drama-layer lookups ---------------------------------------------------


def answers_of(g: StoryGraph, dilemma_id: str) -> list[str]:
    return g.out_ids(dilemma_id, EdgeKind.HAS_ANSWER)


def explored_paths(g: StoryGraph, dilemma_id: str) -> list[str]:
    """Paths exploring this dilemma's answers, in stable order."""
    result = []
    for answer in answers_of(g, dilemma_id):
        result.extend(g.in_ids(answer, EdgeKind.EXPLORES))
    return sorted(result)


def dilemma_of_path(g: StoryGraph, path_id: str) -> str:
    (answer,) = g.out_ids(path_id, EdgeKind.EXPLORES)
    (dilemma,) = g.in_ids(answer, EdgeKind.HAS_ANSWER)
    return dilemma


def paths_of_beat(g: StoryGraph, beat_id: str) -> list[str]:
    return sorted(g.out_ids(beat_id, EdgeKind.BELONGS_TO))


def exclusive_beats(g: StoryGraph, path_id: str) -> list[str]:
    """Beats belonging to exactly this path (commit + post-commit)."""
    return [b for b in g.in_ids(path_id, EdgeKind.BELONGS_TO) if paths_of_beat(g, b) == [path_id]]


def commit_beats(g: StoryGraph, path_id: str) -> list[str]:
    """A path's commit beats, sorted. Exactly one absent multi-hard
    expansion; one per world once the path's dilemma resolves inside a
    hard fork (the tensor model, design doc 01 §5 — invariant I3)."""
    dilemma = dilemma_of_path(g, path_id)
    result = []
    for b in exclusive_beats(g, path_id):
        beat = g.node(b)
        assert isinstance(beat, Beat)
        if dilemma in beat.commits_dilemmas:
            result.append(b)
    return sorted(result)


def grant_beats(g: StoryGraph, flag_id: str) -> list[str]:
    """The beats at which a dilemma flag becomes active (the path's
    commits — one per world). A flag is active once ANY of them is in a
    walk's history; an arc only ever reaches one."""
    flag = g.node(flag_id)
    assert isinstance(flag, StateFlag)
    if flag.path is None:
        return []
    return commit_beats(g, flag.path)


def hard_commit_beats(g: StoryGraph) -> set[str]:
    """Commit beats of every explored hard-dilemma path — the beats that
    create worlds."""
    commits: set[str] = set()
    for d in g.nodes_of(Dilemma):
        if d.role == DilemmaRole.HARD:
            for p in explored_paths(g, d.id):
                commits.update(commit_beats(g, p))
    return commits


def world_of(g: StoryGraph, beat_id: str) -> frozenset[str]:
    """A beat's hard-fork coordinate: the hard commit beats among its
    ancestors. Empty in the shared region before any hard fork."""
    return frozenset(hard_commit_beats(g) & ancestors(g, beat_id))


def soft_rejoin_frontiers(g: StoryGraph, dilemma_id: str) -> list[tuple[frozenset[str], list[str]]]:
    """Per-world rejoin frontiers of a soft dilemma, as (world, frontier)
    pairs sorted by world.

    The two paths' commits are paired by world (equal hard-commit
    ancestry); each pair's frontier is the minimal shared descendants of
    the two commits. A frontier is usually a single convergence beat; it
    is one beat per (deeper) world when the diamond feeds a hard fork
    directly (the soft coordinate collapses into each world separately —
    design doc 01 §5)."""
    paths = explored_paths(g, dilemma_id)
    if len(paths) != 2:
        return []
    a_commits = {world_of(g, c): c for c in commit_beats(g, paths[0])}
    b_commits = {world_of(g, c): c for c in commit_beats(g, paths[1])}
    result = []
    for world in sorted(set(a_commits) & set(b_commits), key=sorted):
        shared = descendants(g, a_commits[world]) & descendants(g, b_commits[world])
        interior: set[str] = set()
        for b in shared:
            interior |= descendants(g, b)
        result.append((world, sorted(shared - interior)))
    return result


def frontier_feeds(g: StoryGraph, beat_id: str, frontier: list[str]) -> list[str]:
    """Direct successors of ``beat_id`` that carry it into ``frontier``:
    frontier beats themselves, or bridge beats whose bridge-only chains
    reach one. GROW may splice a bridge between a tail and the frontier
    it feeds (before the whole fork when the frontier is one); for
    arrival questions the bridge is transparent — the drama is the
    tail's, the bridge belongs to no path."""
    targets = set(frontier)

    def is_bridge(b: str) -> bool:
        node = g.node(b)
        return (
            isinstance(node, Beat)
            and node.beat_class == BeatClass.STRUCTURAL
            and node.purpose == StructuralPurpose.BRIDGE
        )

    feeds = []
    for s in successors(g, beat_id):
        hit = s in targets
        if not hit and is_bridge(s):
            seen, stack = {s}, [s]
            while stack and not hit:
                for nxt in successors(g, stack.pop()):
                    if nxt in targets:
                        hit = True
                    elif is_bridge(nxt) and nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
        if hit:
            feeds.append(s)
    return feeds


def world_label(g: StoryGraph, world: frozenset[str]) -> str:
    """Human-readable world name: the path(s) whose hard commits define
    it, e.g. 'path:bargain-keep'. Empty for the shared region."""
    return "+".join(sorted(paths_of_beat(g, c)[0] for c in world))


def dilemma_flags(g: StoryGraph, dilemma_id: str) -> dict[str, str]:
    """path id -> the dilemma flag granted at that path's commit."""
    paths = set(explored_paths(g, dilemma_id))
    return {f.path: f.id for f in g.nodes_of(StateFlag) if f.path in paths}


# -- arc views -------------------------------------------------------------


def branched_dilemmas(g: StoryGraph) -> list[str]:
    """Dilemmas with two explored paths — the ones that fork the DAG."""
    return sorted(d.id for d in g.nodes_of(Dilemma) if len(explored_paths(g, d.id)) == 2)


def arc_selections(g: StoryGraph) -> list[dict[str, str]]:
    """Cartesian product of one explored path per branched dilemma."""
    dilemmas = branched_dilemmas(g)
    if not dilemmas:
        return [{}]
    options = [explored_paths(g, d) for d in dilemmas]
    return [dict(zip(dilemmas, combo, strict=True)) for combo in product(*options)]


def arc_view(g: StoryGraph, selection: dict[str, str]) -> set[str]:
    """Beats reachable from the root under `selection`.

    Excluded along the walk:
    - beats belonging exclusively to a non-selected path of a branched
      dilemma;
    - flag-gated beats whose required flags' grant beats are not in view
      (grants happen at commit beats, which the walk has already decided).
    """
    selected = set(selection.values())
    branched = set(selection.keys())

    def admitted(beat_id: str, in_view: set[str]) -> bool:
        beat = g.node(beat_id)
        assert isinstance(beat, Beat)
        beat_paths = paths_of_beat(g, beat_id)
        for p in beat_paths:
            if dilemma_of_path(g, p) in branched and p in selected:
                break
        else:
            if beat_paths and any(dilemma_of_path(g, p) in branched for p in beat_paths):
                return False
        for flag_id in beat.requires_flags:
            if not any(grant in in_view for grant in grant_beats(g, flag_id)):
                return False
        return True

    # Admit beats in topological order so a flag-gated beat is always
    # decided after its grant beat (commits are ancestors of their gates).
    view: set[str] = set()
    root_set = set(roots(g))
    for b in topological_order(g) or []:
        if b not in root_set and not any(p in view for p in predecessors(g, b)):
            continue
        if admitted(b, view):
            view.add(b)
    return view


def ambiguous_flags(g: StoryGraph, group: list[str]) -> list[str]:
    """Flags whose value varies among readers arriving at a passage
    holding ``group`` — the I12 computation. A flag is ambiguous when
    its grant is upstream on some route while the opposing path's
    commit is also upstream (a reconverged soft dilemma): prose must
    then honor both values. A flag granted on every route (only its
    own side upstream — a world fact) is certain, costs the writer
    nothing, and does not count; nor do flags of a dilemma the group
    is gated on (arrivals are conditioned: one side certain, the
    other foreclosed)."""
    ancestry = set(group)
    for b in group:
        ancestry |= ancestors(g, b)
    gated_dilemmas = set()
    for b in group:
        beat = g.node(b)
        assert isinstance(beat, Beat)
        for flag_id in beat.requires_flags:
            flag = g.node(flag_id)
            if isinstance(flag, StateFlag) and flag.path is not None:
                gated_dilemmas.add(dilemma_of_path(g, flag.path))
    result = []
    for flag in g.nodes_of(StateFlag):
        if flag.path is None:
            continue  # cosmetic flags have no structural grant
        dilemma = dilemma_of_path(g, flag.path)
        if dilemma in gated_dilemmas:
            continue
        if not any(c in ancestry for c in grant_beats(g, flag.id)):
            continue
        others = [
            c
            for p in explored_paths(g, dilemma)
            if p != flag.path
            for c in commit_beats(g, p)
        ]
        if any(c in ancestry for c in others):
            result.append(flag.id)
    return sorted(result)


def projected_flags(g: StoryGraph) -> list[str]:
    """Flags the print reader must track: every flag some choice gate
    tests (design doc 04 §4). Hard-dilemma flags never appear in gates —
    their worlds are disjoint pages — so this selects soft routing flags
    plus any cosmetic flag a later passage actually tests."""
    tested: set[str] = set()
    for e in g.edges:
        if e.kind == EdgeKind.CHOICE:
            tested.update(e.payload.get("requires", []))
    return sorted(tested)


# -- passage layer ---------------------------------------------------------


def beats_of_passage(g: StoryGraph, passage_id: str) -> list[str]:
    return sorted(g.in_ids(passage_id, EdgeKind.GROUPED_IN))


def passages_of_beat(g: StoryGraph, beat_id: str) -> list[str]:
    return sorted(g.out_ids(beat_id, EdgeKind.GROUPED_IN))


def start_passages(g: StoryGraph) -> list[str]:
    """Passages with no incoming choice edge."""
    from questfoundry.models.presentation import Passage

    return sorted(p.id for p in g.nodes_of(Passage) if not g.in_edges(p.id, EdgeKind.CHOICE))


def path_names(g: StoryGraph) -> dict[str, str]:
    return {p.id: p.name or p.id for p in g.nodes_of(Path)}
