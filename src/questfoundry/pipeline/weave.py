"""GROW's deterministic interleaving core (design doc 02, GROW).

The weave turns SEED's disconnected scaffolds into one beat DAG. Each
branched dilemma contributes its shared pre-commit beats as movable
*units* and its fork as one atomic unit — commit beats plus post-commit
chains: a diamond that reconverges for a soft dilemma, the terminal
split for a hard one. A locked dilemma (single explored path, design
doc 01 §4) has no fork: every beat of its chain is a movable unit under
chain constraints, so the storyline threads through the whole story.
Constraints come from dilemma relations (wraps/serial — a locked
dilemma anchors at its first beat and its resolution beat), temporal
hints, and intersection adjacency; candidate interleavings are
topological orders of the units. The LLM only *chooses among* candidates
(it never invents an order); realization then recomputes the full
PREDECESSOR edge set through the mutation layer.

The weave is a tensor of Y graphs (one dimension per dilemma): soft
dimensions collapse at convergence into flags/residue; hard dimensions
stay expanded (design doc 01 §5). Realization walks the chosen order
tracking *worlds*: units before the first hard fork are placed once and
shared; every unit after it is instantiated once per world — structure
copied mechanically, world-suffixed ids, the template replaced
symmetrically so no world owns the "original" beats — and each further
hard resolve multiplies the worlds, so endings multiply (2 hard → 4).
The last unit is always the climax hard resolve; the earlier hard
forks' chain tails stop being endings (the story continues into the
climax question). Clone *content* is contextualized per world by GROW's
contextualize pass — structure is copied here, words are not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind, Stage
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
    # locked (design doc 01 §4): the single explored path's whole chain
    # lives in `chains`; there is no fork, so every beat is a movable
    # unit and the dilemma contributes no resolve unit.
    locked: bool = False


@dataclass
class WeavePlan:
    units: dict[str, Unit]
    constraints: set[tuple[str, str]]  # (before key, after key)
    shapes: list[DilemmaShape]
    unit_of_beat: dict[str, str]  # shared beat -> unit key (group-aware)
    hard_resolves: list[str] = field(default_factory=list)  # sorted resolve keys
    dropped_hints: list[str] = field(default_factory=list)
    locked_of_beat: dict[str, str] = field(default_factory=dict)  # beat -> locked dilemma


@dataclass
class RealizeReport:
    added: int
    removed: int
    clones: dict[str, list[str]]  # template beat id -> per-world clone ids
    de_ended: list[str]  # earlier hard forks' tails that stopped being endings


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
        if len(paths) == 1:
            # locked at triage: one fork-less chain on the single path
            (path,) = paths
            members = set(g.in_ids(path, EdgeKind.BELONGS_TO))
            if not members:
                raise WeaveError(f"locked dilemma {d.id} has no beats on its path")
            chain = _chain_order(g, members, f"locked storyline of {d.id}")
            commits = [b for b in chain if d.id in g.node(b).commits_dilemmas]  # type: ignore[union-attr]
            if len(commits) != 1:
                raise WeaveError(
                    f"locked storyline of {d.id} has {len(commits)} resolution "
                    "beats; the weave starts from SEED's single resolution"
                )
            result.append(
                DilemmaShape(dilemma=d.id, role=d.role, pre=[], chains={path: chain}, locked=True)
            )
            claimed.update(chain)
            continue
        if len(paths) != 2:
            raise WeaveError(
                f"dilemma {d.id} has {len(paths)} explored path(s); "
                "the weave needs both answers explored (or exactly one, locked)"
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
            commits = queries.commit_beats(g, p)
            if len(commits) != 1:
                raise WeaveError(
                    f"path {p} has {len(commits)} commit beats; the weave starts "
                    "from SEED's single Y per dilemma"
                )
            (commit,) = commits
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
    if not hard:
        raise WeaveError(
            "the weave needs at least one branched hard dilemma "
            "(the backbone whose fork ends the story)"
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

    # Locked storylines are on every arc, so their beats are groupable
    # exactly like shared pre-commit beats (groups stay pre-fork below).
    groupable = {b for s in shape_list for b in s.pre}
    locked_of_beat: dict[str, str] = {}
    for s in shape_list:
        if s.locked:
            (chain,) = s.chains.values()
            groupable.update(chain)
            for b in chain:
                locked_of_beat[b] = s.dilemma
    for beat_id in group_of_beat:
        if beat_id not in groupable:
            raise WeaveError(
                f"intersection member {beat_id} is not a shared pre-commit or "
                "locked-storyline beat; intersections group beats every player sees"
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
        if shape.locked:
            # every beat is its own movable unit on a chain of constraints:
            # the storyline threads through the story instead of lumping
            (chain,) = shape.chains.values()
            for b in chain:
                if b not in unit_of_beat:
                    key = f"pre:{b}"
                    units[key] = _linear(key, [b])
                    unit_of_beat[b] = key
            (commit,) = [
                b
                for b in chain
                if shape.dilemma in g.node(b).commits_dilemmas  # type: ignore[union-attr]
            ]
            first_pre[shape.dilemma] = unit_of_beat[chain[0]]
            resolve_key[shape.dilemma] = unit_of_beat[commit]
            for a, b in zip(chain, chain[1:], strict=False):
                constrain(unit_of_beat[a], unit_of_beat[b])
            continue
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

    hard_rkeys = sorted(
        resolve_key[s.dilemma]
        for s in shape_list
        if s.role == DilemmaRole.HARD and not s.locked
    )
    # Units after a hard fork are realized per world (cloned), so shared
    # units MAY follow it — except intersection groups, whose whole point
    # is one scene every player shares (design doc 01 §5): they stay in
    # the truly shared region, before every hard fork.
    for key in group_members:
        for rkey in hard_rkeys:
            constrain(key, rkey)
    if "setup" in units:
        for key in units:
            constrain("setup", key)

    keys = sorted(units)
    if not _climax_feasible(keys, constraints, hard_rkeys):
        raise WeaveError("ordering constraints are cyclic; the scaffolds cannot be interleaved")

    # Temporal hints are advisory: adopt each (in deterministic order)
    # unless no climax choice stays satisfiable, in which case report it.
    planned = WeavePlan(
        units=units,
        constraints=constraints,
        shapes=shape_list,
        unit_of_beat=unit_of_beat,
        hard_resolves=hard_rkeys,
        locked_of_beat=locked_of_beat,
    )
    for shape in shape_list:
        movable = next(iter(shape.chains.values())) if shape.locked else shape.pre
        for b in movable:
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
                if pair[0] == pair[1] or not _climax_feasible(
                    keys, constraints | {pair}, hard_rkeys
                ):
                    planned.dropped_hints.append(desc + " (unsatisfiable)")
                else:
                    constraints.add(pair)
    return planned


def _climax_constraints(
    keys: list[str], constraints: set[tuple[str, str]], climax: str
) -> set[tuple[str, str]]:
    """The climax hard resolve is the story's final unit: every other
    unit precedes it (nothing may follow the endings)."""
    return constraints | {(k, climax) for k in keys if k != climax}


def _climax_feasible(
    keys: list[str], constraints: set[tuple[str, str]], hard_rkeys: list[str]
) -> bool:
    return any(
        _toposort(keys, _climax_constraints(keys, constraints, h)) is not None
        for h in hard_rkeys
    )


def _orders(keys: list[str], constraints: set[tuple[str, str]], cap: int) -> list[list[str]]:
    """Topological orders of `keys` under `constraints`, in deterministic
    (lexicographic-choice DFS) order, up to `cap`."""
    succ: dict[str, set[str]] = {k: set() for k in keys}
    indeg = dict.fromkeys(keys, 0)
    for a, b in constraints:
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
    return results


def candidates(planned: WeavePlan, cap: int = CANDIDATE_CAP) -> list[list[str]]:
    """Candidate interleavings, up to `cap`. One enumeration per feasible
    climax choice (which hard dilemma resolves last — the nesting order),
    each with an even share of the cap, so multi-hard candidate lists
    always show every viable nesting."""
    keys = sorted(planned.units)
    feasible = []
    for climax in planned.hard_resolves:
        cons = _climax_constraints(keys, planned.constraints, climax)
        if _toposort(keys, cons) is not None:
            feasible.append(cons)
    if not feasible:
        raise WeaveError("no valid interleaving exists")  # plan() guarantees otherwise
    results: list[list[str]] = []
    share = max(1, cap // len(feasible))
    for cons in feasible:
        results.extend(_orders(keys, cons, share))
    return results[:cap]


@dataclass
class _World:
    suffix: str  # "" for the shared region; hard path slugs after forks
    tails: list[str]  # current attach points for the next unit


def realize(g: StoryGraph, planned: WeavePlan, order: list[str]) -> RealizeReport:
    """Rewire the beat graph to the chosen interleaving.

    The order is walked left to right tracking worlds. In the shared
    region (before the first hard resolve) a unit's beats are placed
    as-is; after it, every unit is instantiated once per world — fresh
    world-suffixed beats through the mutation layer, the template
    removed so no world owns the "original" (symmetric by design, like
    the no-canonical-answer rule) — and each hard resolve splits every
    world it is placed in. The target PREDECESSOR edge set is each
    realized unit's internal edges plus tails->heads between spine
    neighbors per world; everything else goes. Tails of every hard fork
    except the climax stop being endings — their worlds continue.
    """
    if sorted(order) != sorted(planned.units):
        raise WeaveError("order must place every unit exactly once")
    if planned.hard_resolves and order[-1] not in planned.hard_resolves:
        raise WeaveError("the last unit must be a hard resolve (the climax fork)")
    shape_of = {f"resolve:{s.dilemma}": s for s in planned.shapes}

    worlds = [_World(suffix="", tails=[])]
    target: set[tuple[str, str]] = set()
    clone_plan: list[tuple[str, str]] = []  # (template, clone id), creation order
    cloned_templates: set[str] = set()
    de_ended: list[str] = []

    for key in order:
        unit = planned.units[key]
        shape = shape_of.get(key)
        is_hard = shape is not None and shape.role == DilemmaRole.HARD
        next_worlds: list[_World] = []
        for w in worlds:
            if w.suffix:
                mapping = {b: f"{b}--{w.suffix}" for b in unit.beats}
                for b in unit.beats:
                    clone_plan.append((b, mapping[b]))
                cloned_templates.update(unit.beats)
            else:
                mapping = {b: b for b in unit.beats}
            for a, b in unit.internal:
                target.add((mapping[a], mapping[b]))
            for t in w.tails:
                for h in unit.heads:
                    target.add((t, mapping[h]))
            if is_hard:
                assert shape is not None
                for p in sorted(shape.chains):
                    tail = mapping[shape.chains[p][-1]]
                    if key != order[-1]:
                        de_ended.append(tail)
                    slug = p.split(":", 1)[1]
                    child = f"{w.suffix}--{slug}" if w.suffix else slug
                    next_worlds.append(_World(suffix=child, tails=[tail]))
            else:
                next_worlds.append(
                    _World(suffix=w.suffix, tails=[mapping[t] for t in unit.tails])
                )
        worlds = next_worlds

    clones: dict[str, list[str]] = {}
    for template_id, clone_id in clone_plan:
        template = g.node(template_id)
        assert isinstance(template, Beat)
        clone = template.model_copy(
            update={
                "id": clone_id,
                "created_by": Stage.GROW,
                # SEED's interleaving annotations are consumed by this weave
                "temporal_hints": [],
                "flexibility": "",
            }
        )
        mutations.add_beat(g, clone, queries.paths_of_beat(g, template_id))
        clones.setdefault(template_id, []).append(clone_id)
    for template_id in sorted(cloned_templates):
        mutations.remove_beat(g, template_id)

    current = {(e.src, e.dst) for e in g.edges if e.kind == EdgeKind.PREDECESSOR}
    for src, dst in sorted(current - target):
        mutations.remove_ordering(g, src, dst)
    for src, dst in sorted(target - current):
        mutations.add_ordering(g, src, dst)
    for tail in de_ended:
        beat = g.node(tail)
        assert isinstance(beat, Beat)
        if beat.is_ending:
            mutations.set_beat_ending(g, tail, is_ending=False)
    return RealizeReport(
        added=len(target - current),
        removed=len(current - target),
        clones=clones,
        de_ended=de_ended,
    )
