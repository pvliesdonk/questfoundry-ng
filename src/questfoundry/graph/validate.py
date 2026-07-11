"""The invariant registry (I1-I13) and gate runner.

Each check cites the invariant it enforces (design doc 01 §8) and the
gate it belongs to (design doc 02). `run_checks` runs every gate at or
below the project's current stage, so hand-edited files and pipeline
output pass through exactly the same wall.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from questfoundry.graph import queries
from questfoundry.graph.mutations import CODEWORD_RE
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import SCOPE_PRESETS, Vision
from questfoundry.models.drama import Dilemma, DilemmaRole, ResidueWeight
from questfoundry.models.drama import Path as StoryPath
from questfoundry.models.enrichment import Enrichment
from questfoundry.models.presentation import Choice, Passage
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    IntersectionGroup,
    StateFlag,
    StructuralPurpose,
)
from questfoundry.models.world import Entity


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Issue:
    check: str
    severity: Severity
    message: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.message}"


@dataclass
class Context:
    g: StoryGraph
    vision: Vision
    # DRESS artifacts live on the Project, not the graph; callers at or
    # past DRESS pass them in so gate G6 sees them (one validation path).
    enrichment: Enrichment = field(default_factory=Enrichment)
    issues: list[Issue] = field(default_factory=list)

    def error(self, check: str, message: str) -> None:
        self.issues.append(Issue(check, Severity.ERROR, message))

    def warn(self, check: str, message: str) -> None:
        self.issues.append(Issue(check, Severity.WARNING, message))


# --------------------------------------------------------------------------
# Gate G0 (DREAM)
# --------------------------------------------------------------------------


def check_g0_vision_complete(ctx: Context) -> None:
    v = ctx.vision
    for name in ("premise", "genre", "tone"):
        value = getattr(v, name).strip()
        if not value or value.upper().startswith("TODO"):
            ctx.error("G0", f"vision.{name} is missing or a TODO placeholder")
    if not v.themes:
        ctx.error("G0", "vision.themes is empty")
    if v.scope not in SCOPE_PRESETS:
        ctx.error("G0", f"vision.scope {v.scope!r} is not a known preset")


# --------------------------------------------------------------------------
# Gate G1 (BRAINSTORM)
# --------------------------------------------------------------------------


def check_i1_two_answers(ctx: Context) -> None:
    for d in ctx.g.nodes_of(Dilemma):
        n = len(queries.answers_of(ctx.g, d.id))
        if n != 2:
            ctx.error("I1", f"dilemma {d.id} has {n} answers; exactly 2 required")


def check_i2_anchoring(ctx: Context) -> None:
    for d in ctx.g.nodes_of(Dilemma):
        anchors = ctx.g.out_ids(d.id, EdgeKind.ANCHORED_TO)
        retained = [
            e for e in anchors if isinstance(n := ctx.g.get(e), Entity) and n.retained
        ]
        if not retained:
            ctx.error("I2", f"dilemma {d.id} is not anchored to any retained entity")


def check_g1_entity_anchoring(ctx: Context) -> None:
    """Advisory: an entity anchoring no dilemma is a triage candidate."""
    anchored = {e.dst for e in ctx.g.edges if e.kind == EdgeKind.ANCHORED_TO}
    for entity in ctx.g.nodes_of(Entity):
        if entity.retained and entity.id not in anchored:
            ctx.warn(
                "G1",
                f"entity {entity.id} anchors no dilemma — connect it or cut it at triage",
            )


def check_g1_shared_entity(ctx: Context) -> None:
    """Dilemmas that share no entities produce parallel novels, not a
    woven story (design doc 02, gate G1)."""
    dilemmas = ctx.g.nodes_of(Dilemma)
    if len(dilemmas) < 2:
        return
    anchors = {d.id: set(ctx.g.out_ids(d.id, EdgeKind.ANCHORED_TO)) for d in dilemmas}
    ids = sorted(anchors)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if anchors[a] & anchors[b]:
                return
    ctx.error("G1", "no two dilemmas share an anchored entity (parallel-novels risk)")


def check_budget_dilemmas(ctx: Context) -> None:
    """B1: branched dilemmas match the scope's role counts exactly; up to
    `locked_dilemmas` extra may be locked at triage (single explored path
    — design doc 01 §4). Before triage no path exists, so the same totals
    are checked as a range: BRAINSTORM overgenerates, triage disposes."""
    preset = ctx.vision.preset
    want = {DilemmaRole.HARD: preset.hard_dilemmas, DilemmaRole.SOFT: preset.soft_dilemmas}
    dilemmas = ctx.g.nodes_of(Dilemma)
    explored = {d.id: len(queries.explored_paths(ctx.g, d.id)) for d in dilemmas}
    if not any(explored.values()):
        by_role = {DilemmaRole.HARD: 0, DilemmaRole.SOFT: 0}
        for d in dilemmas:
            by_role[d.role] += 1
        surplus = 0
        for role, count in by_role.items():
            if count < want[role]:
                ctx.error(
                    "B1",
                    f"scope '{preset.name}' expects >={want[role]} {role.value} "
                    f"dilemma(s), found {count}",
                )
            else:
                surplus += count - want[role]
        if surplus > preset.locked_dilemmas:
            ctx.error(
                "B1",
                f"{surplus} dilemma(s) beyond the branched budget; scope "
                f"'{preset.name}' allows at most {preset.locked_dilemmas} to lock",
            )
        return
    branched = {DilemmaRole.HARD: 0, DilemmaRole.SOFT: 0}
    locked = 0
    for d in dilemmas:
        if explored[d.id] == 2:
            branched[d.role] += 1
        elif explored[d.id] == 1:
            locked += 1
        else:
            ctx.error(
                "B1",
                f"dilemma {d.id} has no explored path; triage must branch or lock "
                "every dilemma",
            )
    for role, count in branched.items():
        if count != want[role]:
            ctx.error(
                "B1",
                f"scope '{preset.name}' expects {want[role]} branched {role.value} "
                f"dilemma(s), found {count}",
            )
    if locked > preset.locked_dilemmas:
        ctx.error(
            "B1",
            f"{locked} locked dilemma(s); scope '{preset.name}' allows at most "
            f"{preset.locked_dilemmas}",
        )


def check_budget_cast(ctx: Context) -> None:
    preset = ctx.vision.preset
    cast = sum(1 for e in ctx.g.nodes_of(Entity) if e.retained)
    if not preset.cast_min <= cast <= preset.cast_max:
        ctx.error(
            "B2",
            f"scope '{preset.name}' expects {preset.cast_min}-{preset.cast_max} "
            f"retained entities, found {cast}",
        )


# --------------------------------------------------------------------------
# Gate G2 (SEED)
# --------------------------------------------------------------------------


def check_i3_scaffolds(ctx: Context) -> None:
    """I3: complete scaffold per explored path. Branched paths carry the
    Y — shared pre-commit beats, commits, exclusive post-commit beats. A
    locked path (its dilemma's only explored path, design doc 01 §4) is a
    fork-less chain: a resolution (commit) beat with >=1 lead-in beat
    before it and >=1 aftermath beat after it. Either way commit beats
    occupy pairwise distinct worlds — exactly one before any multi-hard
    expansion (every world is then the empty shared region), one per
    world once the dilemma resolves inside a hard fork (01 §5, §8)."""
    for d in ctx.g.nodes_of(Dilemma):
        paths = queries.explored_paths(ctx.g, d.id)
        locked = len(paths) == 1
        own_commits = {
            b
            for p in paths
            for b in queries.exclusive_beats(ctx.g, p)
            if d.id in ctx.g.node(b).commits_dilemmas  # type: ignore[union-attr]
        }

        def distinct_worlds(path_id: str, commits: list[str], own_commits=own_commits) -> None:
            # worlds are made by OTHER dilemmas' hard forks — a dilemma's
            # own commits are its fork, never its coordinate
            worlds: dict[frozenset[str], str] = {}
            for c in sorted(commits):
                world = queries.world_of(ctx.g, c) - own_commits
                if world in worlds:
                    ctx.error(
                        "I3",
                        f"path {path_id} has two commit beats in the same world "
                        f"({worlds[world]}, {c}); need exactly one per world",
                    )
                worlds[world] = c

        for path_id in paths:
            member_beats = ctx.g.in_ids(path_id, EdgeKind.BELONGS_TO)
            exclusive = queries.exclusive_beats(ctx.g, path_id)
            commits = [
                b
                for b in exclusive
                if d.id in ctx.g.node(b).commits_dilemmas  # type: ignore[union-attr]
            ]
            if locked:
                members = set(member_beats)
                if not commits:
                    ctx.error("I3", f"locked path {path_id} has no resolution (commit) beat")
                distinct_worlds(path_id, commits)
                for c in sorted(commits):
                    if not members & queries.ancestors(ctx.g, c):
                        ctx.error(
                            "I3",
                            f"locked path {path_id} has no lead-in beat before "
                            f"its resolution {c}",
                        )
                    if not members & queries.descendants(ctx.g, c):
                        ctx.error(
                            "I3",
                            f"locked path {path_id} has no aftermath beat after "
                            f"its resolution {c}",
                        )
                continue
            pre = [b for b in member_beats if len(queries.paths_of_beat(ctx.g, b)) == 2]
            post = [b for b in exclusive if b not in commits]
            if not commits:
                ctx.error("I3", f"path {path_id} has no commit beat")
            distinct_worlds(path_id, commits)
            if not pre:
                ctx.error("I3", f"path {path_id} has no shared pre-commit beats")
            if not post:
                ctx.error("I3", f"path {path_id} has no exclusive post-commit beats")


def check_ordering_relations(ctx: Context) -> None:
    """wraps/serial declarations must not form a cycle."""
    adjacency: dict[str, set[str]] = {}
    for kind in (EdgeKind.WRAPS, EdgeKind.SERIAL):
        for e in ctx.g.edges:
            if e.kind == kind:
                adjacency.setdefault(e.src, set()).add(e.dst)
    seen: dict[str, int] = {}  # 1 = in stack, 2 = done

    def dfs(node: str) -> bool:
        seen[node] = 1
        for nxt in adjacency.get(node, ()):
            if seen.get(nxt) == 1 or (seen.get(nxt) is None and dfs(nxt)):
                return True
        seen[node] = 2
        return False

    for node in list(adjacency):
        if seen.get(node) is None and dfs(node):
            ctx.error("G2-ORDER", "dilemma ordering relations (wraps/serial) form a cycle")
            return


# --------------------------------------------------------------------------
# Gate G3 (GROW)
# --------------------------------------------------------------------------


def check_i4_dag_shape(ctx: Context) -> None:
    if not ctx.g.nodes_of(Beat):
        return
    order = queries.topological_order(ctx.g)
    if order is None:
        ctx.error("I4", "the beat graph contains a cycle")
        return
    root_list = queries.roots(ctx.g)
    if len(root_list) != 1:
        ctx.error("I4", f"the beat DAG must have exactly one root, found {sorted(root_list)}")
        return
    reachable = {root_list[0]} | queries.descendants(ctx.g, root_list[0])
    orphans = set(queries.beat_ids(ctx.g)) - reachable
    for b in sorted(orphans):
        ctx.error("I4", f"beat {b} is unreachable from the root")


def check_i5_membership(ctx: Context) -> None:
    for beat in ctx.g.nodes_of(Beat):
        paths = queries.paths_of_beat(ctx.g, beat.id)
        if beat.beat_class == BeatClass.STRUCTURAL:
            if paths:
                ctx.error("I5", f"structural beat {beat.id} has belongs_to edges")
            continue
        if beat.commits_dilemmas and len(paths) != 1:
            ctx.error(
                "I5", f"commit beat {beat.id} must belong to exactly 1 path, has {len(paths)}"
            )
        if not 1 <= len(paths) <= 2:
            ctx.error("I5", f"narrative beat {beat.id} has {len(paths)} belongs_to edges")
        if len(paths) == 2:
            d1, d2 = (queries.dilemma_of_path(ctx.g, p) for p in paths)
            if d1 != d2:
                ctx.error("I5", f"beat {beat.id} has cross-dilemma dual belongs_to ({d1}, {d2})")
                continue
            impacted = {i.dilemma for i in beat.dilemma_impacts}
            if impacted != {d1}:
                ctx.error(
                    "I5",
                    f"dual-membership beat {beat.id} must impact only its dilemma {d1}",
                )
            for p in paths:
                for commit in queries.commit_beats(ctx.g, p):
                    if beat.id in queries.descendants(ctx.g, commit):
                        ctx.error(
                            "I5",
                            f"pre-commit beat {beat.id} lies after commit {commit} in the DAG",
                        )


def check_i6_arcs_complete(ctx: Context) -> None:
    if not ctx.g.nodes_of(Beat):
        return
    for selection in queries.arc_selections(ctx.g):
        label = "/".join(selection[d] for d in sorted(selection)) or "(single arc)"
        view = queries.arc_view(ctx.g, selection)
        endings = [b for b in view if ctx.g.node(b).is_ending]  # type: ignore[union-attr]
        if not endings:
            ctx.error("I6", f"arc {label} reaches no ending beat")
        locked_paths = [
            p
            for d_id in queries.locked_dilemmas(ctx.g)
            for p in queries.explored_paths(ctx.g, d_id)
        ]
        for path_id in [*selection.values(), *locked_paths]:
            in_view = [c for c in queries.commit_beats(ctx.g, path_id) if c in view]
            if not in_view:
                ctx.error("I6", f"arc {label} never commits path {path_id}")
            elif len(in_view) > 1:
                ctx.error(
                    "I6",
                    f"arc {label} commits path {path_id} more than once ({in_view})",
                )
        for b in sorted(view):
            is_terminal = not any(s in view for s in queries.successors(ctx.g, b))
            if is_terminal and not ctx.g.node(b).is_ending:  # type: ignore[union-attr]
                ctx.error("I6", f"arc {label} dead-ends at non-ending beat {b}")


def check_i7_convergence_by_role(ctx: Context) -> None:
    preset = ctx.vision.preset
    for d in ctx.g.nodes_of(Dilemma):
        paths = queries.explored_paths(ctx.g, d.id)
        if len(paths) != 2:
            continue
        commits = {p: queries.commit_beats(ctx.g, p) for p in paths}
        if not all(commits.values()):
            continue  # I3's problem
        if d.role == DilemmaRole.HARD:
            # never reconverge, in any world: no cross-path commit pair
            # may share a descendant
            for ca in commits[paths[0]]:
                for cb in commits[paths[1]]:
                    shared = queries.descendants(ctx.g, ca) & queries.descendants(ctx.g, cb)
                    if shared:
                        ctx.error(
                            "I7",
                            f"hard dilemma {d.id} paths reconverge at {sorted(shared)[:3]}",
                        )
        if d.role == DilemmaRole.SOFT:
            frontiers = queries.soft_rejoin_frontiers(ctx.g, d.id)
            if not frontiers:
                ctx.error("I7", f"soft dilemma {d.id} paths never reconverge")
            for world, frontier in frontiers:
                if not frontier:
                    where = queries.world_label(ctx.g, world) or "the shared region"
                    ctx.error(
                        "I7",
                        f"soft dilemma {d.id} paths never reconverge in world {where}",
                    )
            for p in paths:
                exclusive = set(queries.exclusive_beats(ctx.g, p))
                for c in commits[p]:
                    # this world's payoff: the commit's own exclusive chain
                    payoff = len(exclusive & queries.descendants(ctx.g, c))
                    if payoff < preset.min_payoff_beats:
                        ctx.error(
                            "I7",
                            f"path {p} has {payoff} payoff beat(s) after {c}; "
                            f"scope '{preset.name}' requires >={preset.min_payoff_beats}",
                        )


def check_g3_flag_derivation(ctx: Context) -> None:
    """G3: flag derivation is total over branched paths — every
    consequence of a branched explored path yields at least one state
    flag. Locked paths are exempt in both directions: their outcome is
    a world fact on every arc, so it needs no gateable flag and must
    not carry one (design doc 02, gate G3)."""
    derived = {e.dst for e in ctx.g.edges if e.kind == EdgeKind.DERIVED_FROM}
    locked_paths = {
        p
        for d_id in queries.locked_dilemmas(ctx.g)
        for p in queries.explored_paths(ctx.g, d_id)
    }
    for flag in ctx.g.nodes_of(StateFlag):
        if flag.path in locked_paths:
            ctx.error(
                "G3-FLAGS",
                f"flag {flag.id} is granted by locked path {flag.path}; a locked "
                "outcome is a world fact, never a gateable flag",
            )
    for d in ctx.g.nodes_of(Dilemma):
        for path_id in queries.explored_paths(ctx.g, d.id):
            if path_id in locked_paths:
                continue
            for cid in ctx.g.out_ids(path_id, EdgeKind.HAS_CONSEQUENCE):
                if cid not in derived:
                    ctx.error(
                        "G3-FLAGS", f"consequence {cid} of path {path_id} derives no state flag"
                    )


def check_budget_arc_beats(ctx: Context) -> None:
    preset = ctx.vision.preset
    if not ctx.g.nodes_of(Beat):
        return
    for selection in queries.arc_selections(ctx.g):
        label = "/".join(selection[d] for d in sorted(selection)) or "(single arc)"
        count = len(queries.arc_view(ctx.g, selection))
        if not preset.arc_beats_min <= count <= preset.arc_beats_max:
            ctx.warn(
                "B4",
                f"arc {label} has {count} beats; scope '{preset.name}' targets "
                f"{preset.arc_beats_min}-{preset.arc_beats_max} (advisory)",
            )


def check_i8_intersections(ctx: Context) -> None:
    for group in ctx.g.nodes_of(IntersectionGroup):
        members = ctx.g.in_ids(group.id, EdgeKind.IN_GROUP)
        seen: dict[str, str] = {}
        for beat_id in members:
            beat = ctx.g.node(beat_id)
            assert isinstance(beat, Beat)
            for impact in beat.dilemma_impacts:
                if impact.dilemma in seen and seen[impact.dilemma] != beat_id:
                    ctx.error(
                        "I8",
                        f"intersection {group.id} groups two beats of dilemma {impact.dilemma}",
                    )
                seen[impact.dilemma] = beat_id


def check_i9_freeze(ctx: Context) -> None:
    record = ctx.g.frozen
    if record is None:
        return
    for beat_id in record.beats:
        if beat_id not in ctx.g:
            ctx.error("I9", f"frozen beat {beat_id} has been deleted")
    for dilemma_id, commits in record.forks.items():
        current = sorted(
            c
            for p in queries.explored_paths(ctx.g, dilemma_id)
            for c in queries.commit_beats(ctx.g, p)
        )
        if current != sorted(commits):
            ctx.error(
                "I9",
                f"dilemma {dilemma_id} fork changed after freeze: {commits} -> {current}",
            )
    for dilemma_id, beats in record.convergences.items():
        current = sorted(
            f[0] for _, f in queries.soft_rejoin_frontiers(ctx.g, dilemma_id) if len(f) == 1
        )
        if current != sorted(beats):
            ctx.error(
                "I9",
                f"dilemma {dilemma_id} convergence moved after freeze: {beats} -> {current}",
            )


# --------------------------------------------------------------------------
# Gate G4 (POLISH)
# --------------------------------------------------------------------------


def _grant_position_ok(ctx: Context, flag_id: str, at_beats: list[str], view: set[str]) -> bool:
    """Is `flag_id` active by the time the player stands at `at_beats`?
    Grant beats are per world; one in this view's history suffices."""
    for grant in queries.grant_beats(ctx.g, flag_id):
        if grant not in view:
            continue
        if grant in at_beats or any(grant in queries.ancestors(ctx.g, b) for b in at_beats):
            return True
    return False


def check_i10_gates_satisfiable(ctx: Context) -> None:
    selections = queries.arc_selections(ctx.g)
    views = {tuple(sorted(s.items())): queries.arc_view(ctx.g, s) for s in selections}

    def satisfiable(required: list[str], at_beats: list[str]) -> bool:
        return any(
            all(_grant_position_ok(ctx, f, at_beats, view) for f in required)
            for view in views.values()
        )

    for e in ctx.g.edges:
        if e.kind == EdgeKind.CHOICE and e.payload.get("requires"):
            src_beats = queries.beats_of_passage(ctx.g, e.src)
            if not satisfiable(e.payload["requires"], src_beats):
                ctx.error(
                    "I10",
                    f"choice {e.src} -> {e.dst} requires {e.payload['requires']}, "
                    "which no arc can satisfy",
                )
    for beat in ctx.g.nodes_of(Beat):
        if beat.requires_flags and not satisfiable(beat.requires_flags, [beat.id]):
            ctx.error(
                "I10",
                f"beat {beat.id} requires {beat.requires_flags}, which no arc can satisfy",
            )


def check_i11_grouping(ctx: Context) -> None:
    if not ctx.g.nodes_of(Passage):
        return
    for beat in ctx.g.nodes_of(Beat):
        passages = queries.passages_of_beat(ctx.g, beat.id)
        if not passages:
            ctx.error("I11", f"beat {beat.id} is not grouped into any passage")
        elif len(passages) > 1:
            for p in passages:
                variant_links = set(ctx.g.out_ids(p, EdgeKind.VARIANT_OF)) | set(
                    ctx.g.in_ids(p, EdgeKind.VARIANT_OF)
                )
                if not variant_links & set(passages):
                    ctx.error(
                        "I11",
                        f"beat {beat.id} appears in unrelated passages {passages} "
                        "(only variant passages may share a beat)",
                    )
                    break


def check_i12_feasibility(ctx: Context) -> None:
    cap = 3
    for passage in ctx.g.nodes_of(Passage):
        beats = queries.beats_of_passage(ctx.g, passage.id)
        relevant = set(queries.ambiguous_flags(ctx.g, beats)) - set(passage.irrelevant_flags)
        if len(relevant) > cap:
            ctx.error(
                "I12",
                f"passage {passage.id} must honor {len(relevant)} ambiguous states "
                f"{sorted(relevant)}; cap is {cap} "
                f"(mark irrelevant flags or split into variants)",
            )


def check_i13_passage_graph(ctx: Context) -> None:
    passages = ctx.g.nodes_of(Passage)
    if not passages:
        return
    starts = queries.start_passages(ctx.g)
    if len(starts) != 1:
        ctx.error("I13", f"the passage graph must have exactly one start, found {sorted(starts)}")
        return
    start = starts[0]

    for p in passages:
        outgoing = ctx.g.out_edges(p.id, EdgeKind.CHOICE)
        if p.ending is None and not outgoing:
            ctx.error("I13", f"non-ending passage {p.id} has no outgoing choices")
        if p.ending is not None and outgoing:
            ctx.error("I13", f"ending passage {p.id} has outgoing choices")

    visited_any: set[str] = set()
    for selection in queries.arc_selections(ctx.g):
        label = "/".join(selection[d] for d in sorted(selection)) or "(single arc)"
        view = queries.arc_view(ctx.g, selection)
        reached_ending = False
        seen: set[tuple[str, frozenset[str]]] = set()
        frontier: deque[tuple[str, frozenset[str]]] = deque([(start, frozenset())])
        while frontier:
            passage_id, flags = frontier.popleft()
            if (passage_id, flags) in seen:
                continue
            seen.add((passage_id, flags))
            visited_any.add(passage_id)
            node = ctx.g.node(passage_id)
            assert isinstance(node, Passage)
            if node.ending is not None:
                reached_ending = True
                continue
            for e in ctx.g.out_edges(passage_id, EdgeKind.CHOICE):
                choice = Choice.model_validate(e.payload)
                if not set(choice.requires) <= flags:
                    continue
                if not set(queries.beats_of_passage(ctx.g, e.dst)) <= view:
                    continue
                frontier.append((e.dst, flags | set(choice.grants)))
        if not reached_ending:
            ctx.error("I13", f"arc {label} cannot reach any ending through the passage graph")
    for p in passages:
        if p.id not in visited_any:
            ctx.error("I13", f"passage {p.id} is unreachable on every arc")


def check_g4_choice_labels(ctx: Context) -> None:
    """G4: sibling choice labels are non-empty and distinct. Same-label
    siblings are allowed only behind different gates (variant passages:
    the runtime hides all but one, so the player never sees the twins)."""
    for passage in ctx.g.nodes_of(Passage):
        seen: set[tuple[str, tuple[str, ...]]] = set()
        for e in ctx.g.out_edges(passage.id, EdgeKind.CHOICE):
            label = e.payload.get("label", "")
            if not label.strip():
                ctx.error("G4", f"choice {passage.id} -> {e.dst} has an empty label")
                continue
            key = (label, tuple(sorted(e.payload.get("requires", []))))
            if key in seen:
                ctx.error(
                    "G4",
                    f"passage {passage.id} offers two choices labeled {label!r} "
                    "behind the same gate",
                )
            seen.add(key)


def check_g4_residue_coverage(ctx: Context) -> None:
    """G4: per world, every light-residue soft convergence has a residue
    arm per path in that world, gated on that path's flag (the residue
    diamond: the story remembers whichever side was chosen); every heavy
    one has variant passages at every beat of that world's rejoin
    frontier (one beat when a convergence passage exists, one per deeper
    world when the diamond feeds a hard fork — design doc 02, gate G4)."""
    if not ctx.g.nodes_of(Passage):
        return
    for d in ctx.g.nodes_of(Dilemma):
        if d.role != DilemmaRole.SOFT:
            continue
        path_flags = queries.dilemma_flags(ctx.g, d.id)
        for world, frontier in queries.soft_rejoin_frontiers(ctx.g, d.id):
            where = queries.world_label(ctx.g, world)
            suffix = f" (world {where})" if where else ""
            if d.residue_weight == ResidueWeight.LIGHT:
                for path, flags in sorted(path_flags.items()):
                    # any of the path's flags marks the same commitment, so
                    # an arm gated on any of them remembers the choice
                    covered = any(
                        b.purpose == StructuralPurpose.RESIDUE
                        and any(f in b.requires_flags for f in flags)
                        and queries.world_of(ctx.g, b.id) == world
                        for b in ctx.g.nodes_of(Beat)
                    )
                    if not covered:
                        ctx.error(
                            "G4",
                            f"light-residue dilemma {d.id} rejoins at "
                            f"{', '.join(frontier)}{suffix} with no residue beat "
                            f"gated on any of {flags} ({path}) there",
                        )
            elif d.residue_weight == ResidueWeight.HEAVY:
                for beat_id in frontier:
                    if len(queries.passages_of_beat(ctx.g, beat_id)) < 2:
                        ctx.error(
                            "G4",
                            f"heavy-residue dilemma {d.id} converges at {beat_id}"
                            f"{suffix} without variant passages",
                        )


def check_g4_arc_references(ctx: Context) -> None:
    """G4: character-arc metadata resolves — every pivot names a real
    beat, every end a real explored path. Arcs are annotations, but a
    dangling reference in one silently corrupts FILL's arc-position
    computation later (same class as G3-FLAGS: referential integrity
    fails loud at the gate, not downstream). Hand-edited files face the
    same rule as the arcs pass."""
    for e in ctx.g.nodes_of(Entity):
        if e.arc is None:
            continue
        for pivot in e.arc.pivots:
            if not isinstance(ctx.g.get(pivot.beat), Beat):
                ctx.error(
                    "G4", f"{e.id}: arc pivot {pivot.beat!r} is not a beat in the graph"
                )
        for end in e.arc.ends:
            if not isinstance(ctx.g.get(end.path), StoryPath):
                ctx.error("G4", f"{e.id}: arc end {end.path!r} is not a path")


def check_budget_passages(ctx: Context) -> None:
    preset = ctx.vision.preset
    count = len(ctx.g.nodes_of(Passage))
    if count and not preset.passages_min <= count <= preset.passages_max:
        ctx.warn(
            "B3",
            f"scope '{preset.name}' targets {preset.passages_min}-{preset.passages_max} "
            f"passages, found {count} (advisory)",
        )


# --------------------------------------------------------------------------
# Gate G5 (FILL)
# --------------------------------------------------------------------------


def check_g5_prose_presence(ctx: Context) -> None:
    for passage in ctx.g.nodes_of(Passage):
        if not passage.prose.strip():
            ctx.error("G5", f"passage {passage.id} has no prose")


def check_b5_word_budget(ctx: Context) -> None:
    preset = ctx.vision.preset
    for passage in ctx.g.nodes_of(Passage):
        beats = [ctx.g.node(b) for b in queries.beats_of_passage(ctx.g, passage.id)]
        texture = bool(beats) and all(
            isinstance(b, Beat) and b.is_texture for b in beats
        )
        lo, hi = preset.words_for(texture=texture, ending=passage.ending is not None)
        count = len(passage.prose.split())
        if passage.prose.strip() and not lo <= count <= hi:
            ctx.warn(
                "B5",
                f"passage {passage.id} has {count} words; scope '{preset.name}' "
                f"budgets {lo}-{hi}{' (texture)' if texture else ''} (advisory)",
            )


# B6: how big the story FEELS is words traversed per genuine choice, not
# passage inventory (craft-corpus guidance: 300-600 words/choice reads as
# balanced agency, 600-1000 narrative-heavy, 1000+ as reading not playing)
B6_WORDS_PER_CHOICE = (250, 800)


def check_b6_choice_cadence(ctx: Context) -> None:
    """B6 measures a playthrough, not an arc view (M8): a deterministic
    walk per arc — first live choice whose target stays on the arc —
    counting the prose words the walker traverses and the decisions
    offered (>= 2 live choices; a target off the arc is still offered —
    taking it is what makes a different arc). The pre-M8 arc-view sum
    counted both arms of every cosmetic diamond, words no single reader
    sees, which is why diamonds barely moved the measured number (live
    run 6: 'the diamonds each add prose along with their choice')."""
    passages = ctx.g.nodes_of(Passage)
    if not passages or not any(p.prose.strip() for p in passages):
        return
    lo, hi = B6_WORDS_PER_CHOICE
    starts = queries.start_passages(ctx.g)
    if not starts:
        return
    averages = []
    for selection in queries.arc_selections(ctx.g):
        view = queries.arc_view(ctx.g, selection)
        held = {
            f.id
            for f in ctx.g.nodes_of(StateFlag)
            if any(grant in view for grant in queries.grant_beats(ctx.g, f.id))
        }

        def on_arc(passage_id: str, view=view) -> bool:
            beats = queries.beats_of_passage(ctx.g, passage_id)
            return bool(beats) and all(b in view for b in beats)

        cur = next((p for p in starts if on_arc(p)), None)
        if cur is None:
            continue
        words = decisions = 0
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            node = ctx.g.node(cur)
            assert isinstance(node, Passage)
            words += len(node.prose.split())
            live = sorted(
                (
                    e
                    for e in ctx.g.out_edges(cur, EdgeKind.CHOICE)
                    if all(req in held for req in e.payload.get("requires", []))
                ),
                key=lambda e: e.dst,
            )
            if len(live) >= 2:
                decisions += 1
            cur = next((e.dst for e in live if on_arc(e.dst)), None)
        if words:
            averages.append(words / max(decisions, 1))
    if not averages:
        return
    mean = sum(averages) / len(averages)
    if not lo <= mean <= hi:
        ctx.warn(
            "B6",
            f"a playthrough averages {mean:.0f} words per genuine choice "
            f"(walk range {min(averages):.0f}-{max(averages):.0f}); the feel "
            f"target is {lo}-{hi} (advisory)",
        )


def check_b7_total_words(ctx: Context) -> None:
    """B7 (advisory): total prose words within the scope's words_total —
    the scale table's primary anchor (A19). Checked once prose exists."""
    total = sum(len(p.prose.split()) for p in ctx.g.nodes_of(Passage))
    if not total:
        return
    lo, hi = ctx.vision.preset.words_total
    if not lo <= total <= hi:
        ctx.warn(
            "B7",
            f"the story carries {total} prose words; scope "
            f"'{ctx.vision.preset.name}' targets {lo}-{hi} (advisory)",
        )


# --------------------------------------------------------------------------
# Gate G6 (DRESS)
# --------------------------------------------------------------------------


def check_g6_art_direction(ctx: Context) -> None:
    """G6.1: art direction present with non-empty style/palette; every
    retained entity has exactly one visual profile referencing a known
    retained entity."""
    direction = ctx.enrichment.direction
    if direction is None or not direction.style.strip() or not direction.palette.strip():
        ctx.error("G6", "art direction is missing, or missing a non-empty style/palette")
    retained = {e.id for e in ctx.g.nodes_of(Entity) if e.retained}
    counts: dict[str, int] = {}
    for p in ctx.enrichment.profiles:
        if p.entity not in retained:
            ctx.error("G6", f"visual profile references unknown/non-retained entity {p.entity!r}")
            continue
        counts[p.entity] = counts.get(p.entity, 0) + 1
    for entity_id in sorted(retained):
        count = counts.get(entity_id, 0)
        if count == 0:
            ctx.error("G6", f"retained entity {entity_id} has no visual profile")
        elif count > 1:
            ctx.error("G6", f"retained entity {entity_id} has {count} visual profiles, need 1")


def check_g6_briefs(ctx: Context) -> None:
    """G6.2: >=1 brief, each on a real passage, <=1 per passage, priorities
    dense 1..N, non-empty caption/prompt, and the mechanical half of
    'briefs reference only established visual facts': cited entities are
    in the passage and each has a visual profile."""
    briefs = ctx.enrichment.briefs
    if not briefs:
        ctx.error("G6", "no illustration briefs")
        return
    passages = {p.id: p for p in ctx.g.nodes_of(Passage)}
    profiled = {p.entity for p in ctx.enrichment.profiles}
    by_passage: dict[str, int] = {}
    priorities = []
    for b in briefs:
        by_passage[b.passage] = by_passage.get(b.passage, 0) + 1
        priorities.append(b.priority)
        passage = passages.get(b.passage)
        if passage is None:
            ctx.error("G6", f"brief references unknown passage {b.passage!r}")
            continue
        if not b.caption.strip() or not b.prompt.strip():
            ctx.error("G6", f"brief for {b.passage} has an empty caption or prompt")
        stray = set(b.entities) - set(passage.entities)
        if stray:
            ctx.error(
                "G6", f"brief for {b.passage} cites entities {sorted(stray)} not in that passage"
            )
        unprofiled = (set(b.entities) & set(passage.entities)) - profiled
        if unprofiled:
            ctx.error(
                "G6",
                f"brief for {b.passage} cites entities {sorted(unprofiled)} with no visual profile",
            )
    for passage_id, count in by_passage.items():
        if count > 1:
            ctx.error("G6", f"passage {passage_id} has {count} briefs, at most 1 allowed")
    if sorted(priorities) != list(range(1, len(briefs) + 1)):
        ctx.error(
            "G6", f"brief priorities must be dense 1..{len(briefs)}, got {sorted(priorities)}"
        )


def check_g6_codex(ctx: Context) -> None:
    """G6.3: >=1 entry, each on a retained entity, <=1 per entity, every
    dilemma-anchoring retained entity has an entry, titles/bodies non-empty."""
    codex = ctx.enrichment.codex
    if not codex:
        ctx.error("G6", "no codex entries")
        return
    retained = {e.id for e in ctx.g.nodes_of(Entity) if e.retained}
    anchored = {e.dst for e in ctx.g.edges if e.kind == EdgeKind.ANCHORED_TO}
    required = retained & anchored
    counts: dict[str, int] = {}
    for entry in codex:
        counts[entry.entity] = counts.get(entry.entity, 0) + 1
        if entry.entity not in retained:
            ctx.error("G6", f"codex entry references unknown/non-retained entity {entry.entity!r}")
        if not entry.title.strip():
            ctx.error("G6", f"codex entry for {entry.entity} has an empty title")
        if not entry.body.strip():
            ctx.error("G6", f"codex entry for {entry.entity} has an empty body")
    for entity_id, count in counts.items():
        if count > 1:
            ctx.error("G6", f"entity {entity_id} has {count} codex entries, at most 1 allowed")
    for entity_id in sorted(required - set(counts)):
        ctx.error("G6", f"dilemma-anchoring entity {entity_id} has no codex entry")


def check_g6_codewords(ctx: Context) -> None:
    """G6.4: every projected flag carries a codeword; codewords match
    ^[A-Z]{3,12}$ and are pairwise distinct — the mutation enforces this
    on write, this re-checks files so hand edits face the same wall."""
    seen: dict[str, str] = {}
    for flag in ctx.g.nodes_of(StateFlag):
        if flag.codeword is None:
            continue
        if not CODEWORD_RE.match(flag.codeword):
            ctx.error(
                "G6",
                f"flag {flag.id} codeword {flag.codeword!r} does not match {CODEWORD_RE.pattern}",
            )
        elif flag.codeword in seen:
            ctx.error(
                "G6",
                f"codeword {flag.codeword!r} used by both {seen[flag.codeword]} and {flag.id}",
            )
        else:
            seen[flag.codeword] = flag.id
    for flag_id in queries.projected_flags(ctx.g):
        if ctx.g.node(flag_id).codeword is None:  # type: ignore[union-attr]
            ctx.error("G6", f"projected flag {flag_id} has no codeword")


# --------------------------------------------------------------------------
# Gate registry
# --------------------------------------------------------------------------

GATES: dict[Stage, list] = {
    Stage.DREAM: [check_g0_vision_complete],
    Stage.BRAINSTORM: [
        check_i1_two_answers,
        check_i2_anchoring,
        check_g1_entity_anchoring,
        check_g1_shared_entity,
        check_budget_dilemmas,
        check_budget_cast,
    ],
    Stage.SEED: [check_i3_scaffolds, check_ordering_relations],
    Stage.GROW: [
        check_i4_dag_shape,
        check_i5_membership,
        check_i6_arcs_complete,
        check_i7_convergence_by_role,
        check_i8_intersections,
        check_i9_freeze,
        check_g3_flag_derivation,
        check_budget_arc_beats,
    ],
    Stage.POLISH: [
        check_i10_gates_satisfiable,
        check_i11_grouping,
        check_i12_feasibility,
        check_i13_passage_graph,
        check_g4_choice_labels,
        check_g4_residue_coverage,
        check_g4_arc_references,
        check_budget_passages,
    ],
    Stage.FILL: [
        check_g5_prose_presence,
        check_b5_word_budget,
        check_b6_choice_cadence,
        check_b7_total_words,
    ],
    Stage.DRESS: [
        check_g6_art_direction,
        check_g6_briefs,
        check_g6_codex,
        check_g6_codewords,
    ],
}


def run_checks(
    g: StoryGraph,
    vision: Vision,
    stage: Stage,
    *,
    enrichment: Enrichment | None = None,
) -> list[Issue]:
    """Run every gate at or below `stage` and return all issues found."""
    ctx = Context(g=g, vision=vision, enrichment=enrichment or Enrichment())
    for gate_stage, checks in GATES.items():
        if gate_stage.order <= stage.order:
            for check in checks:
                check(ctx)
    return ctx.issues
