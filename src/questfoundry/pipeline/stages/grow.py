"""GROW — weave the beat DAG (design doc 02).

Four passes sharing gate G3:

1. *intersections* — the LLM proposes co-occurrence groups over shared
   pre-commit beats of different dilemmas (from shared entities and
   SEED's flexibility notes); grouped beats become one interleaving unit.
2. *weave* — the engine enumerates valid interleavings (relations +
   temporal hints + intersection adjacency; with several hard dilemmas,
   one enumeration per viable nesting order); the LLM only chooses among
   them; the engine rewires the DAG — instantiating every unit after the
   first hard fork once per world (design doc 01 §5) — and derives state
   flags from consequences (deterministic, one flag per consequence,
   granted at the path's commits).
3. *contextualize* — structure was copied per world mechanically; here
   the LLM rewrites each cloned beat's summary for its world, and the
   earlier hard forks' de-ended tails to leave the climax question open.
   Skipped when nothing was cloned (single hard dilemma).
4. *bridge* — for adjacent beats sharing no entities, the LLM writes
   structural bridge beats the engine splices in — before the whole fork
   frontier when the gap runs into a commit beat (a bridge is shared, so
   feeding it into one branch dead-ends the others, I6); seams no bridge
   can span safely are left for FILL's prose to smooth.

After a clean gate the topology freezes (I9). Scope notes (tracked in
docs/STATUS.md): intersections over shared pre-commit beats only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import Issue, Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Answer, Dilemma, DilemmaRole, Path
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    FlagSource,
    IntersectionGroup,
    StateFlag,
    StructuralPurpose,
)
from questfoundry.pipeline import weave
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl
from questfoundry.project.io import Project

MAX_CANDIDATES_SHOWN = 8


# -- pass 1: intersections ----------------------------------------------------


class IntersectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    location: str = ""  # entity id of the shared place, if one anchors the scene
    rationale: str = ""
    members: list[str] = Field(min_length=2)


class IntersectionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    groups: list[IntersectionSpec] = []


def _shared_beat_table(project: Project) -> list[dict]:
    g = project.graph
    table = []
    for shape in weave.shapes(g)[0]:
        beats = []
        for b in shape.pre:
            beat = g.node(b)
            assert isinstance(beat, Beat)
            beats.append(beat)
        table.append({"dilemma": g.node(shape.dilemma), "beats": beats})
    return table


def _intersections_context(project: Project) -> dict:
    return {"vision": project.vision, "dilemmas": _shared_beat_table(project)}


def _intersections_apply(proposal: IntersectionProposal, project: Project) -> list[str]:
    g = project.graph
    shared = {b for shape in weave.shapes(g)[0] for b in shape.pre}
    used: set[str] = set()
    for spec in proposal.groups:
        for m in spec.members:
            if m not in shared:
                raise ApplyError(
                    f"intersection {spec.id}: member {m} is not a shared pre-commit beat"
                )
            if m in used:
                raise ApplyError(f"beat {m} appears in more than one intersection group")
            used.add(m)
        try:
            group = IntersectionGroup(
                id=spec.id,
                created_by=Stage.GROW,
                location=spec.location or None,
                rationale=spec.rationale,
            )
        except ValidationError as e:
            raise ApplyError(f"invalid intersection {spec.id}: {e}") from e
        mutations.add_intersection(g, group, spec.members)  # I8 locally
    try:
        weave.plan(g)
    except weave.WeaveError as exc:
        raise ApplyError(f"these intersections make the interleave unsatisfiable: {exc}") from exc
    if not proposal.groups:
        return ["no intersections proposed"]
    return [f"{s.id}: {' + '.join(s.members)}" for s in proposal.groups]


# -- pass 2: weave ------------------------------------------------------------


class WeaveChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: int
    rationale: str = ""


def _spread(items: list, cap: int) -> list:
    """Up to `cap` items spread evenly across the list (always keeps the
    first and last), preserving order."""
    if len(items) <= cap:
        return items
    idx = sorted({round(i * (len(items) - 1) / (cap - 1)) for i in range(cap)})
    return [items[i] for i in idx]


def _unit_label(g, planned: weave.WeavePlan, key: str) -> str:
    unit = planned.units[key]
    if key.startswith("resolve:"):
        dilemma = g.node(key.removeprefix("resolve:"))
        rejoin = "branches rejoin after payoff" if dilemma.role == "soft" else "final fork"
        return f"[{dilemma.id} COMMITS — {rejoin}]"
    summaries = "; ".join(
        g.node(b).summary.split(".")[0][:80] for b in unit.beats  # type: ignore[union-attr]
    )
    if key.startswith("group:"):
        return f"[one scene: {summaries}]"
    return summaries


def _shown_candidates(project: Project) -> tuple[weave.WeavePlan, list[list[str]]]:
    planned = weave.plan(project.graph)
    return planned, _spread(weave.candidates(planned), MAX_CANDIDATES_SHOWN)


def _weave_context(project: Project) -> dict:
    g = project.graph
    planned, shown = _shown_candidates(project)
    multi_hard = len(planned.hard_resolves) > 1
    rendered = []
    for i, order in enumerate(shown):
        steps = []
        in_worlds = False
        for key in order:
            label = _unit_label(g, planned, key)
            if multi_hard and key in planned.hard_resolves:
                dilemma = g.node(key.removeprefix("resolve:"))
                if key == order[-1]:
                    label = (
                        f"[{dilemma.id} COMMITS in each world — the final fork; "
                        "endings multiply]"
                    )
                elif not in_worlds:
                    label = f"[{dilemma.id} COMMITS — the story forks into worlds]"
            elif multi_hard and in_worlds:
                label = "(in each world) " + label
            steps.append(label)
            if key in planned.hard_resolves:
                in_worlds = True
        rendered.append({"index": i, "steps": steps})
    return {"vision": project.vision, "candidates": rendered}


def _derive_flags(g) -> list[str]:
    lines = []
    for path in sorted(g.nodes_of(Path), key=lambda p: p.id):
        for cid in g.out_ids(path.id, EdgeKind.HAS_CONSEQUENCE):
            flag = StateFlag(
                id="flag:" + cid.split(":", 1)[1],
                created_by=Stage.GROW,
                description=g.node(cid).text,
                source=FlagSource.DILEMMA,
                path=path.id,
            )
            mutations.add_flag(g, flag, derived_from=[cid])
            lines.append(f"{flag.id} <- {cid} (granted at {path.id}'s commit)")
    return lines


def _weave_apply(proposal: WeaveChoice, project: Project) -> list[str]:
    g = project.graph
    planned, shown = _shown_candidates(project)
    if not 0 <= proposal.choice < len(shown):
        raise ApplyError(f"choice {proposal.choice} is out of range 0..{len(shown) - 1}")
    order = shown[proposal.choice]
    report = weave.realize(g, planned, order)
    lines = [
        f"interleaving #{proposal.choice}: " + " -> ".join(order),
        f"orderings rewired: +{report.added} -{report.removed}",
    ]
    for template, ids in sorted(report.clones.items()):
        lines.append(f"{template} instantiated per world: {', '.join(ids)}")
    if report.de_ended:
        lines.append(
            "no longer endings (their worlds continue into the climax fork): "
            + ", ".join(report.de_ended)
        )
    lines.extend(_derive_flags(g))
    if planned.dropped_hints:
        lines.append("dropped temporal hints: " + "; ".join(planned.dropped_hints))
    return lines


# -- pass 3: contextualize ------------------------------------------------------


class RewriteSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat: str
    summary: str


class ContextualizeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rewrites: list[RewriteSpec]


def _world_facts(g, world: frozenset[str]) -> list[dict]:
    """What is true in a world: for each hard commit defining it, the
    question, the answer taken, and its consequences."""
    facts = []
    for commit_id in sorted(world):
        (path_id,) = queries.paths_of_beat(g, commit_id)
        (answer_id,) = g.out_ids(path_id, EdgeKind.EXPLORES)
        answer = g.node(answer_id)
        assert isinstance(answer, Answer)
        (dilemma_id,) = g.in_ids(answer_id, EdgeKind.HAS_ANSWER)
        facts.append(
            {
                "dilemma": g.node(dilemma_id),
                "answer": answer.text,
                "consequences": [
                    g.node(c).text  # type: ignore[union-attr]
                    for c in g.out_ids(path_id, EdgeKind.HAS_CONSEQUENCE)
                ],
                "committed_at": g.node(commit_id).summary,  # type: ignore[union-attr]
            }
        )
    return facts


def _clone_targets(g) -> list[Beat]:
    """The weave's per-world instances: narrative beats created by GROW
    (the bridge pass, GROW's only other beat source, runs after this one
    and writes structural beats)."""
    return sorted(
        (
            b
            for b in g.nodes_of(Beat)
            if b.beat_class == BeatClass.NARRATIVE and b.created_by == Stage.GROW
        ),
        key=lambda b: b.id,
    )


def _de_ended_tails(g) -> list[Beat]:
    """Hard-path chain tails that feed a deeper fork: realization cleared
    their is_ending, but their summaries still read as story-final."""
    tails = []
    for d in sorted(g.nodes_of(Dilemma), key=lambda n: n.id):
        if d.role != DilemmaRole.HARD:
            continue
        for p in queries.explored_paths(g, d.id):
            exclusive = set(queries.exclusive_beats(g, p))
            for b in sorted(exclusive):
                succs = set(queries.successors(g, b))
                if succs and not succs & exclusive:
                    beat = g.node(b)
                    assert isinstance(beat, Beat)
                    tails.append(beat)
    return tails


def _contextualize_targets(project: Project) -> list[dict]:
    g = project.graph
    targets = []
    for beat in _clone_targets(g):
        world = queries.world_of(g, beat.id)
        targets.append(
            {
                "beat": beat,
                "kind": "clone",
                "world": queries.world_label(g, world),
                "facts": _world_facts(g, world),
                "open_questions": [],
            }
        )
    for beat in _de_ended_tails(g):
        below = queries.descendants(g, beat.id)
        open_questions = [
            d.question
            for d in sorted(g.nodes_of(Dilemma), key=lambda n: n.id)
            if d.role == DilemmaRole.HARD
            and any(
                c in below
                for p in queries.explored_paths(g, d.id)
                for c in queries.commit_beats(g, p)
            )
        ]
        targets.append(
            {
                "beat": beat,
                "kind": "tail",
                "world": "",
                "facts": [],
                "open_questions": open_questions,
            }
        )
    return targets


def _contextualize_skip(project: Project) -> str | None:
    if _contextualize_targets(project):
        return None
    return "no per-world beat instances (single hard dilemma)"


def _contextualize_context(project: Project) -> dict:
    return {"vision": project.vision, "targets": _contextualize_targets(project)}


def _contextualize_apply(proposal: ContextualizeProposal, project: Project) -> list[str]:
    g = project.graph
    expected = {t["beat"].id for t in _contextualize_targets(project)}
    seen: set[str] = set()
    for spec in proposal.rewrites:
        if spec.beat not in expected:
            raise ApplyError(
                f"{spec.beat} is not a rewrite target; rewrite exactly these "
                f"beats: {sorted(expected)}"
            )
        if spec.beat in seen:
            raise ApplyError(f"{spec.beat} rewritten twice")
        if not spec.summary.strip():
            raise ApplyError(f"summary for {spec.beat} is empty")
        seen.add(spec.beat)
    missing = expected - seen
    if missing:
        raise ApplyError(f"every listed beat needs a rewrite; missing {sorted(missing)}")
    for spec in proposal.rewrites:
        mutations.set_beat_summary(g, spec.beat, spec.summary)
    return [f"{len(seen)} beat summaries contextualized to their worlds"]


# -- pass 4: bridge -----------------------------------------------------------


class BridgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap: int
    id: str
    summary: str
    entities: list[str] = []


class BridgeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bridges: list[BridgeSpec]


def _splice_targets(g, src: str, dst: str) -> tuple[str, ...]:
    """Beats the bridge is spliced before. A gap into a fork commit is a
    gap into the fork: the bridge must precede the whole frontier slice
    src feeds (cf. the residue splice at a fork rejoin), else every arc
    taking a sibling commit reaches the bridge and dead-ends (I6)."""
    dst_beat = g.node(dst)
    assert isinstance(dst_beat, Beat)
    committed = set(dst_beat.commits_dilemmas)
    if not committed:
        return (dst,)
    group = []
    for s in queries.successors(g, src):
        beat = g.node(s)
        assert isinstance(beat, Beat)
        if set(beat.commits_dilemmas) & committed:
            group.append(s)
    return tuple(sorted(group))


def _gaps(g) -> list[tuple[str, tuple[str, ...]]]:
    """Adjacent beats that share no entities — each needs a bridge.

    A gap is (src, targets): the bridge replaces src's edges into the
    targets (one beat, or a whole fork frontier — `_splice_targets`).
    A gap is bridgeable only if every arc reaching src reaches a target:
    a bridge is a shared structural beat, on every arc that reaches it,
    so an uncovered arc would dead-end at it (I6). Unbridgeable seams
    are not gaps — FILL smooths them in prose."""
    views = [queries.arc_view(g, sel) for sel in queries.arc_selections(g)]
    gaps: list[tuple[str, tuple[str, ...]]] = []
    for e in sorted(g.edges, key=lambda e: (e.src, e.dst)):
        if e.kind != EdgeKind.PREDECESSOR:
            continue
        a, b = g.node(e.src), g.node(e.dst)
        if not a.entities or not b.entities or set(a.entities) & set(b.entities):
            continue
        gap = (e.src, _splice_targets(g, e.src, e.dst))
        if gap in gaps:
            continue
        if any(e.src in v and not any(t in v for t in gap[1]) for v in views):
            continue
        gaps.append(gap)
    return gaps


def _bridge_skip(project: Project) -> str | None:
    return None if _gaps(project.graph) else "no entity-disjoint adjacencies"


def _bridge_context(project: Project) -> dict:
    g = project.graph
    rendered = []
    for i, (src, targets) in enumerate(_gaps(g)):
        rendered.append({"index": i, "src": g.node(src), "dsts": [g.node(t) for t in targets]})
    return {"vision": project.vision, "gaps": rendered}


def _bridge_apply(proposal: BridgeProposal, project: Project) -> list[str]:
    g = project.graph
    gaps = _gaps(g)
    covered = sorted(b.gap for b in proposal.bridges)
    if covered != list(range(len(gaps))):
        raise ApplyError(f"bridges must cover each gap 0..{len(gaps) - 1} exactly once")
    lines = []
    for spec in proposal.bridges:
        src, targets = gaps[spec.gap]
        try:
            bridge = Beat(
                id=spec.id,
                created_by=Stage.GROW,
                summary=spec.summary,
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.BRIDGE,
                entities=spec.entities,
            )
        except ValidationError as e:
            raise ApplyError(f"invalid bridge beat {spec.id}: {e}") from e
        mutations.add_beat(g, bridge, [])
        for dst in targets:
            mutations.remove_ordering(g, src, dst)
        mutations.add_ordering(g, src, bridge.id)
        for dst in targets:
            mutations.add_ordering(g, bridge.id, dst)
        lines.append(f"{spec.id} bridges {src} -> {' + '.join(targets)}")
    return lines


# -- gate ---------------------------------------------------------------------


def _grow_gate(project: Project) -> list[Issue]:
    """G3, then the freeze: after a clean gate the dilemma topology is
    frozen (I9) — the pipeline's central commitment point."""
    issues = run_checks(project.graph, project.vision, Stage.GROW)
    if not any(i.severity == Severity.ERROR for i in issues):
        mutations.freeze_topology(project.graph)
    return issues


GROW_STAGE = StageImpl(
    stage=Stage.GROW,
    passes=(
        PassSpec(
            name="intersections",
            role="architect",
            template="grow_intersections.j2",
            schema=IntersectionProposal,
            build_context=_intersections_context,
            apply=_intersections_apply,
        ),
        PassSpec(
            name="weave",
            role="architect",
            template="grow_weave.j2",
            schema=WeaveChoice,
            build_context=_weave_context,
            apply=_weave_apply,
        ),
        PassSpec(
            name="contextualize",
            role="writer",
            template="grow_contextualize.j2",
            schema=ContextualizeProposal,
            build_context=_contextualize_context,
            apply=_contextualize_apply,
            skip_if=_contextualize_skip,
        ),
        PassSpec(
            name="bridge",
            role="writer",
            template="grow_bridge.j2",
            schema=BridgeProposal,
            build_context=_bridge_context,
            apply=_bridge_apply,
            skip_if=_bridge_skip,
        ),
    ),
    gate=_grow_gate,
)
