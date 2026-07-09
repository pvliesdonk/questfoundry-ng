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
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import SCOPE_PRESETS, Vision
from questfoundry.models.drama import Dilemma, DilemmaRole, ResidueWeight
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
    preset = ctx.vision.preset
    by_role = {DilemmaRole.HARD: 0, DilemmaRole.SOFT: 0}
    for d in ctx.g.nodes_of(Dilemma):
        by_role[d.role] += 1
    want = {DilemmaRole.HARD: preset.hard_dilemmas, DilemmaRole.SOFT: preset.soft_dilemmas}
    for role, count in by_role.items():
        if count != want[role]:
            ctx.error(
                "B1",
                f"scope '{preset.name}' expects {want[role]} {role.value} "
                f"dilemma(s), found {count}",
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
    for d in ctx.g.nodes_of(Dilemma):
        for path_id in queries.explored_paths(ctx.g, d.id):
            member_beats = ctx.g.in_ids(path_id, EdgeKind.BELONGS_TO)
            pre = [b for b in member_beats if len(queries.paths_of_beat(ctx.g, b)) == 2]
            exclusive = queries.exclusive_beats(ctx.g, path_id)
            commits = [
                b
                for b in exclusive
                if d.id in ctx.g.node(b).commits_dilemmas  # type: ignore[union-attr]
            ]
            post = [b for b in exclusive if b not in commits]
            if len(commits) != 1:
                ctx.error("I3", f"path {path_id} has {len(commits)} commit beats; need exactly 1")
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
                commit = queries.commit_beat(ctx.g, p)
                if commit and beat.id in queries.descendants(ctx.g, commit):
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
        for path_id in selection.values():
            commit = queries.commit_beat(ctx.g, path_id)
            if commit is None or commit not in view:
                ctx.error("I6", f"arc {label} never commits path {path_id}")
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
        commits = [queries.commit_beat(ctx.g, p) for p in paths]
        if None in commits:
            continue  # I3's problem
        shared = queries.descendants(ctx.g, commits[0]) & queries.descendants(ctx.g, commits[1])
        if d.role == DilemmaRole.HARD and shared:
            ctx.error(
                "I7",
                f"hard dilemma {d.id} paths reconverge at {sorted(shared)[:3]}",
            )
        if d.role == DilemmaRole.SOFT:
            if not shared:
                ctx.error("I7", f"soft dilemma {d.id} paths never reconverge")
            for p in paths:
                payoff = len(queries.exclusive_beats(ctx.g, p)) - 1  # minus the commit
                if payoff < preset.min_payoff_beats:
                    ctx.error(
                        "I7",
                        f"path {p} has {payoff} payoff beat(s); "
                        f"scope '{preset.name}' requires >={preset.min_payoff_beats}",
                    )


def check_g3_flag_derivation(ctx: Context) -> None:
    """G3: flag derivation is total — every consequence of an explored
    path yields at least one state flag (design doc 02, gate G3)."""
    derived = {e.dst for e in ctx.g.edges if e.kind == EdgeKind.DERIVED_FROM}
    for d in ctx.g.nodes_of(Dilemma):
        for path_id in queries.explored_paths(ctx.g, d.id):
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
            if (c := queries.commit_beat(ctx.g, p))
        )
        if current != sorted(commits):
            ctx.error(
                "I9",
                f"dilemma {dilemma_id} fork changed after freeze: {commits} -> {current}",
            )
    for dilemma_id, beat_id in record.convergences.items():
        commits = record.forks.get(dilemma_id, [])
        if len(commits) == 2:
            shared = queries.descendants(ctx.g, commits[0]) & queries.descendants(
                ctx.g, commits[1]
            )
            if beat_id not in shared:
                ctx.error(
                    "I9",
                    f"dilemma {dilemma_id} convergence at {beat_id} broken after freeze",
                )


# --------------------------------------------------------------------------
# Gate G4 (POLISH)
# --------------------------------------------------------------------------


def _grant_position_ok(ctx: Context, flag_id: str, at_beats: list[str], view: set[str]) -> bool:
    """Is `flag_id` active by the time the player stands at `at_beats`?"""
    grant = queries.grant_beat(ctx.g, flag_id)
    if grant is None or grant not in view:
        return False
    if grant in at_beats:
        return True
    return any(grant in queries.ancestors(ctx.g, b) for b in at_beats)


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
        active = set()
        for flag in ctx.g.nodes_of(StateFlag):
            grant = queries.grant_beat(ctx.g, flag.id)
            if grant is None:
                continue
            if grant in beats or any(grant in queries.ancestors(ctx.g, b) for b in beats):
                active.add(flag.id)
        relevant = active - set(passage.irrelevant_flags)
        if len(relevant) > cap:
            ctx.error(
                "I12",
                f"passage {passage.id} must honor {len(relevant)} states {sorted(relevant)}; "
                f"cap is {cap} (mark irrelevant flags or split into variants)",
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
    """G4: every light-residue soft convergence has a residue beat gated
    on one of the dilemma's flags; every heavy one has variant passages
    at the convergence (design doc 02, gate G4)."""
    if not ctx.g.nodes_of(Passage):
        return
    for d in ctx.g.nodes_of(Dilemma):
        if d.role != DilemmaRole.SOFT:
            continue
        frontier = queries.soft_rejoin_frontier(ctx.g, d.id)
        if not frontier:
            continue
        flags = set(queries.dilemma_flags(ctx.g, d.id).values())
        if d.residue_weight == ResidueWeight.LIGHT:
            covered = any(
                b.purpose == StructuralPurpose.RESIDUE and set(b.requires_flags) & flags
                for b in ctx.g.nodes_of(Beat)
            )
            if not covered:
                ctx.error(
                    "G4",
                    f"light-residue dilemma {d.id} rejoins at {', '.join(frontier)} "
                    "with no residue beat gated on its flags",
                )
        elif d.residue_weight == ResidueWeight.HEAVY:
            if len(frontier) > 1:
                ctx.error(
                    "G4",
                    f"heavy-residue dilemma {d.id} rejoins inside a hard fork "
                    f"({', '.join(frontier)}); per-world variant passages are "
                    "not built yet (M5 multi-hard work)",
                )
            elif len(queries.passages_of_beat(ctx.g, frontier[0])) < 2:
                ctx.error(
                    "G4",
                    f"heavy-residue dilemma {d.id} converges at {frontier[0]} "
                    "without variant passages",
                )


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
    lo, hi = preset.words_per_passage
    for passage in ctx.g.nodes_of(Passage):
        count = len(passage.prose.split())
        if passage.prose.strip() and not lo <= count <= hi:
            ctx.warn(
                "B5",
                f"passage {passage.id} has {count} words; scope '{preset.name}' "
                f"budgets {lo}-{hi} (advisory)",
            )


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
        check_budget_passages,
    ],
    Stage.FILL: [
        check_g5_prose_presence,
        check_b5_word_budget,
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
