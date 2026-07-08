"""GROW's deterministic interleaving core (design doc 02, GROW).

The weave turns SEED's disconnected Y scaffolds into one beat DAG. Each
dilemma contributes its shared pre-commit beats as movable *units* and
its fork as one atomic unit — commit beats plus post-commit chains: a
diamond that reconverges for a soft dilemma, the terminal split for the
hard one. Constraints come from dilemma relations (wraps/serial),
temporal hints, and intersection adjacency; candidate interleavings are
topological orders of the units. The LLM only *chooses among* candidates
(it never invents an order); realization then recomputes the full
PREDECESSOR edge set through the mutation layer.

M2 scope: exactly one hard dilemma and both answers of every dilemma
explored. Multi-hard weaving nests forks — the remaining hard dilemma
forks again on each branch of the first, with per-world *authored*
beats (different worlds, different scenes — never copies), so endings
multiply (design doc 01 §5). That per-world authorship is M5 work,
see docs/STATUS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind
from questfoundry.models.drama import Dilemma, DilemmaRole
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    HintPosition,
    IntersectionGroup,
    StructuralPurpose,
)

CANDIDATE_CAP = 64


class WeaveError(Exception):
    """The graph is not weavable as-is (scaffold shape, cyclic
    constraints). Callers that own a proposal (the intersections pass)
    translate this into a repairable ApplyError; anywhere else it is an
    engine bug and should stay loud."""


@dataclass(frozen=True)
class Unit:
    """An atomic placement unit on the spine."""

    key: str
    heads: tuple[str, ...]  # entry beats (predecessors attach here)
    tails: tuple[str, ...]  # exit beats (successors attach here)
    internal: tuple[tuple[str, str], ...]  # ordering edges inside the unit
    beats: tuple[str, ...]


def _linear(key: str, beats: list[str]) -> Unit:
    return Unit(
        key=key,
        heads=(beats[0],),
        tails=(beats[-1],),
        internal=tuple(zip(beats, beats[1:], strict=False)),
        beats=tuple(beats),
    )


@dataclass
class DilemmaShape:
    dilemma: str
    role: DilemmaRole
    pre: list[str]  # shared pre-commit beats in scaffold chain order
    chains: dict[str, list[str]]  # path id -> [commit, post-commit...]


@dataclass
class WeavePlan:
    units: dict[str, Unit]
    constraints: set[tuple[str, str]]  # (before key, after key)
    shapes: list[DilemmaShape]
    unit_of_beat: dict[str, str]  # shared beat -> unit key (group-aware)
    dropped_hints: list[str] = field(default_factory=list)


def _chain_order(g: StoryGraph, beats: set[str], what: str) -> list[str]:
    """Order `beats` by the PREDECESSOR edges among them; they must form
    a single chain (SEED wires scaffolds that way)."""
    if not beats:
        return []
    succ: dict[str, str] = {}
    heads = set(beats)
    for b in beats:
        nxts = [s for s in queries.successors(g, b) if s in beats]
        if len(nxts) > 1:
            raise WeaveError(f"{what}: beat {b} has {len(nxts)} successors inside its chain")
        if nxts:
            succ[b] = nxts[0]
            heads.discard(nxts[0])
    if len(heads) != 1:
        raise WeaveError(f"{what}: expected one chain, found chain heads {sorted(heads)}")
    (cur,) = heads
    order = [cur]
    while cur in succ:
        cur = succ[cur]
        order.append(cur)
    if len(order) != len(beats):
        raise WeaveError(f"{what}: beats do not form a single chain")
    return order


def shapes(g: StoryGraph) -> tuple[list[DilemmaShape], list[str]]:
    """Decompose the beat graph into per-dilemma Y shapes plus the setup
    chain. Raises WeaveError for anything the weave cannot place."""
    result: list[DilemmaShape] = []
    hard: list[str] = []
    claimed: set[str] = set()
    for d in sorted(g.nodes_of(Dilemma), key=lambda n: n.id):
        paths = queries.explored_paths(g, d.id)
        if len(paths) != 2:
            raise WeaveError(
                f"dilemma {d.id} has {len(paths)} explored path(s); "
                "the weave needs both answers explored"
            )
        pre = {
            b
            for p in paths
            for b in g.in_ids(p, EdgeKind.BELONGS_TO)
            if queries.paths_of_beat(g, b) == sorted(paths)
        }
        if not pre:
            raise WeaveError(f"dilemma {d.id} has no shared pre-commit beats")
        chains: dict[str, list[str]] = {}
        for p in paths:
            commit = queries.commit_beat(g, p)
            if commit is None:
                raise WeaveError(f"path {p} has no commit beat")
            exclusive = set(queries.exclusive_beats(g, p))
            post = _chain_order(g, exclusive - {commit}, f"post-commit chain of {p}")
            chains[p] = [commit, *post]
        result.append(
            DilemmaShape(
                dilemma=d.id,
                role=d.role,
                pre=_chain_order(g, pre, f"pre-commit chain of {d.id}"),
                chains=chains,
            )
        )
        if d.role == DilemmaRole.HARD:
            hard.append(d.id)
        claimed.update(pre)
        for chain in chains.values():
            claimed.update(chain)
    if len(hard) != 1:
        raise WeaveError(
            f"the weave needs exactly one hard dilemma, found {len(hard)} "
            "(multi-hard topology is a later milestone)"
        )
    setup = {
        b.id
        for b in g.nodes_of(Beat)
        if b.beat_class == BeatClass.STRUCTURAL and b.purpose == StructuralPurpose.SETUP
    }
    setup_chain = _chain_order(g, setup, "setup chain")
    unclaimed = set(queries.beat_ids(g)) - claimed - setup
    if unclaimed:
        raise WeaveError(f"beats outside any weavable unit: {sorted(unclaimed)}")
    return result, setup_chain


def _resolve_unit(shape: DilemmaShape) -> Unit:
    internal: list[tuple[str, str]] = []
    tails: list[str] = []
    beats: list[str] = []
    for p in sorted(shape.chains):
        chain = shape.chains[p]
        internal.extend(zip(chain, chain[1:], strict=False))
        tails.append(chain[-1])
        beats.extend(chain)
    return Unit(
        key=f"resolve:{shape.dilemma}",
        heads=tuple(sorted(chain[0] for chain in shape.chains.values())),
        tails=tuple(sorted(tails)),
        internal=tuple(internal),
        beats=tuple(beats),
    )


def _toposort(keys: list[str], constraints: set[tuple[str, str]]) -> list[str] | None:
    indeg = dict.fromkeys(keys, 0)
    succ: dict[str, list[str]] = {k: [] for k in keys}
    for a, b in constraints:
        succ[a].append(b)
        indeg[b] += 1
    order: list[str] = []
    ready = sorted(k for k, d in indeg.items() if d == 0)
    while ready:
        k = ready.pop(0)
        order.append(k)
        for s in succ[k]:
            indeg[s] -= 1
            if indeg[s] == 0:
                ready.append(s)
        ready.sort()
    return order if len(order) == len(keys) else None


def plan(g: StoryGraph) -> WeavePlan:
    """Build units and ordering constraints. Deterministic: context
    building and proposal application both call this and must agree."""
    shape_list, setup_chain = shapes(g)

    # Intersection groups merge their member beats into one unit.
    group_of_beat: dict[str, str] = {}
    group_members: dict[str, list[str]] = {}
    for group in sorted(g.nodes_of(IntersectionGroup), key=lambda n: n.id):
        members = sorted(g.in_ids(group.id, EdgeKind.IN_GROUP))
        key = f"group:{group.id}"
        group_members[key] = members
        for m in members:
            if m in group_of_beat:
                raise WeaveError(f"beat {m} is a member of more than one intersection group")
            group_of_beat[m] = key

    units: dict[str, Unit] = {}
    unit_of_beat: dict[str, str] = {}
    constraints: set[tuple[str, str]] = set()

    if setup_chain:
        units["setup"] = _linear("setup", setup_chain)

    shared_beats = {b for s in shape_list for b in s.pre}
    for beat_id in group_of_beat:
        if beat_id not in shared_beats:
            raise WeaveError(
                f"intersection member {beat_id} is not a shared pre-commit beat; "
                "M2 intersections group shared beats only"
            )
    for key, members in group_members.items():
        units[key] = _linear(key, members)
        for m in members:
            unit_of_beat[m] = key

    first_pre: dict[str, str] = {}
    resolve_key: dict[str, str] = {}

    def constrain(a: str, b: str) -> None:
        if a != b:
            constraints.add((a, b))

    for shape in shape_list:
        for b in shape.pre:
            if b not in unit_of_beat:
                key = f"pre:{b}"
                units[key] = _linear(key, [b])
                unit_of_beat[b] = key
        rkey = f"resolve:{shape.dilemma}"
        units[rkey] = _resolve_unit(shape)
        resolve_key[shape.dilemma] = rkey
        first_pre[shape.dilemma] = unit_of_beat[shape.pre[0]]
        for a, b in zip(shape.pre, shape.pre[1:], strict=False):
            constrain(unit_of_beat[a], unit_of_beat[b])
        constrain(unit_of_beat[shape.pre[-1]], rkey)

    for e in g.edges:
        if e.kind == EdgeKind.WRAPS and e.src in first_pre and e.dst in first_pre:
            constrain(first_pre[e.src], first_pre[e.dst])
            constrain(resolve_key[e.dst], resolve_key[e.src])
        elif e.kind == EdgeKind.SERIAL and e.src in first_pre and e.dst in first_pre:
            constrain(resolve_key[e.src], first_pre[e.dst])

    # Nothing shared may follow the hard fork (its branches never rejoin,
    # so a later single-node beat would reconverge them — I7).
    (hard_rkey,) = [resolve_key[s.dilemma] for s in shape_list if s.role == DilemmaRole.HARD]
    for key in units:
        constrain(key, hard_rkey)
    if "setup" in units:
        for key in units:
            constrain("setup", key)

    keys = sorted(units)
    if _toposort(keys, constraints) is None:
        raise WeaveError("ordering constraints are cyclic; the scaffolds cannot be interleaved")

    # Temporal hints are advisory: adopt each (in deterministic order)
    # unless it makes the constraints cyclic, in which case report it.
    planned = WeavePlan(
        units=units, constraints=constraints, shapes=shape_list, unit_of_beat=unit_of_beat
    )
    for shape in shape_list:
        for b in shape.pre:
            beat = g.node(b)
            assert isinstance(beat, Beat)
            for hint in beat.temporal_hints:
                rkey = resolve_key.get(hint.dilemma)
                desc = f"{b}: {hint.position.value} {hint.dilemma}"
                if rkey is None:
                    planned.dropped_hints.append(desc + " (unknown or unbranched dilemma)")
                    continue
                ukey = unit_of_beat[b]
                pair = (ukey, rkey) if hint.position == HintPosition.BEFORE_COMMIT else (rkey, ukey)
                if pair[0] == pair[1] or _toposort(keys, constraints | {pair}) is None:
                    planned.dropped_hints.append(desc + " (unsatisfiable)")
                else:
                    constraints.add(pair)
    return planned


def candidates(planned: WeavePlan, cap: int = CANDIDATE_CAP) -> list[list[str]]:
    """Topological orders of the units under the constraints, in
    deterministic (lexicographic-choice DFS) order, up to `cap`."""
    keys = sorted(planned.units)
    succ: dict[str, set[str]] = {k: set() for k in keys}
    indeg = dict.fromkeys(keys, 0)
    for a, b in planned.constraints:
        if b not in succ[a]:
            succ[a].add(b)
            indeg[b] += 1
    results: list[list[str]] = []
    order: list[str] = []
    placed: set[str] = set()

    def dfs() -> None:
        if len(results) >= cap:
            return
        if len(order) == len(keys):
            results.append(list(order))
            return
        for k in keys:
            if k in placed or indeg[k] != 0:
                continue
            placed.add(k)
            order.append(k)
            for s in succ[k]:
                indeg[s] -= 1
            dfs()
            for s in succ[k]:
                indeg[s] += 1
            placed.discard(k)
            order.pop()
            if len(results) >= cap:
                return

    dfs()
    if not results:
        raise WeaveError("no valid interleaving exists")  # plan() guarantees otherwise
    return results


def realize(g: StoryGraph, planned: WeavePlan, order: list[str]) -> tuple[int, int]:
    """Rewire the beat graph to the chosen interleaving: the target edge
    set is each unit's internal edges plus tails->heads between spine
    neighbors; everything else goes. Returns (added, removed)."""
    if sorted(order) != sorted(planned.units):
        raise WeaveError("order must place every unit exactly once")
    target: set[tuple[str, str]] = set()
    for key in order:
        target.update(planned.units[key].internal)
    for a, b in zip(order, order[1:], strict=False):
        for t in planned.units[a].tails:
            for h in planned.units[b].heads:
                target.add((t, h))
    current = {(e.src, e.dst) for e in g.edges if e.kind == EdgeKind.PREDECESSOR}
    for src, dst in sorted(current - target):
        mutations.remove_ordering(g, src, dst)
    for src, dst in sorted(target - current):
        mutations.add_ordering(g, src, dst)
    return len(target - current), len(current - target)
