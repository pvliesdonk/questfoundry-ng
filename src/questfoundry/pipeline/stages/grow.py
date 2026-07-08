"""GROW — weave the beat DAG (design doc 02).

Three passes sharing gate G3:

1. *intersections* — the LLM proposes co-occurrence groups over shared
   pre-commit beats of different dilemmas (from shared entities and
   SEED's flexibility notes); grouped beats become one interleaving unit.
2. *weave* — the engine enumerates valid interleavings (relations +
   temporal hints + intersection adjacency); the LLM only chooses among
   them; the engine rewires the DAG and derives state flags from
   consequences (deterministic, one flag per consequence, granted at the
   path's commit).
3. *bridge* — for adjacent beats sharing no entities, the LLM writes
   structural bridge beats the engine splices in.

After a clean gate the topology freezes (I9). M2 scope notes (tracked in
docs/STATUS.md): intersections over shared pre-commit beats only;
exactly one hard dilemma.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.graph import mutations
from questfoundry.graph.validate import Issue, Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Path
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
    rendered = [
        {"index": i, "steps": [_unit_label(g, planned, key) for key in order]}
        for i, order in enumerate(shown)
    ]
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
    added, removed = weave.realize(g, planned, order)
    lines = [
        f"interleaving #{proposal.choice}: " + " -> ".join(order),
        f"orderings rewired: +{added} -{removed}",
        *_derive_flags(g),
    ]
    if planned.dropped_hints:
        lines.append("dropped temporal hints: " + "; ".join(planned.dropped_hints))
    return lines


# -- pass 3: bridge -----------------------------------------------------------


class BridgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap: int
    id: str
    summary: str
    entities: list[str] = []


class BridgeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bridges: list[BridgeSpec]


def _gaps(g) -> list[tuple[str, str]]:
    """Adjacent beats that share no entities — each needs a bridge."""
    gaps = []
    for e in sorted(g.edges, key=lambda e: (e.src, e.dst)):
        if e.kind != EdgeKind.PREDECESSOR:
            continue
        a, b = g.node(e.src), g.node(e.dst)
        if a.entities and b.entities and not set(a.entities) & set(b.entities):
            gaps.append((e.src, e.dst))
    return gaps


def _bridge_skip(project: Project) -> str | None:
    return None if _gaps(project.graph) else "no entity-disjoint adjacencies"


def _bridge_context(project: Project) -> dict:
    g = project.graph
    rendered = []
    for i, (src, dst) in enumerate(_gaps(g)):
        rendered.append({"index": i, "src": g.node(src), "dst": g.node(dst)})
    return {"vision": project.vision, "gaps": rendered}


def _bridge_apply(proposal: BridgeProposal, project: Project) -> list[str]:
    g = project.graph
    gaps = _gaps(g)
    covered = sorted(b.gap for b in proposal.bridges)
    if covered != list(range(len(gaps))):
        raise ApplyError(f"bridges must cover each gap 0..{len(gaps) - 1} exactly once")
    lines = []
    for spec in proposal.bridges:
        src, dst = gaps[spec.gap]
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
        mutations.remove_ordering(g, src, dst)
        mutations.add_ordering(g, src, bridge.id)
        mutations.add_ordering(g, bridge.id, dst)
        lines.append(f"{spec.id} bridges {src} -> {dst}")
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
