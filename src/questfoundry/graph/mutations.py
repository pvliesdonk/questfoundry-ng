"""The single write path to the story graph (design principle 2).

Every operation performs its *local* invariant checks before touching the
store; global invariants are the gates' job (`graph/validate.py`). LLM
proposals and hand-edited project files both land here — there is no
privileged writer.
"""

from __future__ import annotations

from questfoundry.graph import queries
from questfoundry.graph.store import FreezeRecord, StoryGraph
from questfoundry.models.base import Edge, EdgeKind
from questfoundry.models.drama import Answer, Consequence, Dilemma, DilemmaRole, Path
from questfoundry.models.presentation import Choice, Passage
from questfoundry.models.structure import Beat, BeatClass, IntersectionGroup, StateFlag
from questfoundry.models.world import Entity


class MutationError(Exception):
    """A proposal violated a local invariant; the graph is unchanged."""


def add_entity(g: StoryGraph, entity: Entity) -> None:
    g._add_node(entity)


def add_dilemma(
    g: StoryGraph,
    dilemma: Dilemma,
    answers: tuple[Answer, Answer],
    anchored_to: list[str],
) -> None:
    """I1 locally: a dilemma enters the graph with exactly two answers.
    I2 locally: it must anchor to at least one existing entity."""
    if len({a.id for a in answers}) != 2:
        raise MutationError(f"dilemma {dilemma.id} needs two distinct answers")
    if not anchored_to:
        raise MutationError(f"dilemma {dilemma.id} must anchor to >=1 entity")
    for entity_id in anchored_to:
        if not isinstance(g.get(entity_id), Entity):
            raise MutationError(f"dilemma {dilemma.id} anchored to non-entity {entity_id!r}")
    g._add_node(dilemma)
    for answer in answers:
        g._add_node(answer)
        g._add_edge(Edge(kind=EdgeKind.HAS_ANSWER, src=dilemma.id, dst=answer.id))
    for entity_id in anchored_to:
        g._add_edge(Edge(kind=EdgeKind.ANCHORED_TO, src=dilemma.id, dst=entity_id))


def set_entity_disposition(g: StoryGraph, entity_id: str, *, retained: bool) -> None:
    """SEED triage: mark an entity retained or cut. Cut entities stay in
    the graph (the record of what was considered) but stop counting for
    anchoring (I2) and cast budgets (B2)."""
    entity = g.get(entity_id)
    if not isinstance(entity, Entity):
        raise MutationError(f"{entity_id!r} is not an entity")
    entity.retained = retained


def add_dilemma_relation(g: StoryGraph, kind: EdgeKind, a: str, b: str) -> None:
    if kind not in (EdgeKind.WRAPS, EdgeKind.SERIAL, EdgeKind.CONCURRENT):
        raise MutationError(f"{kind} is not a dilemma ordering relation")
    if a == b:
        raise MutationError("a dilemma cannot relate to itself")
    for d in (a, b):
        if not isinstance(g.get(d), Dilemma):
            raise MutationError(f"{d!r} is not a dilemma")
    if kind == EdgeKind.CONCURRENT and b < a:
        a, b = b, a  # symmetric: stored once, lexicographically smaller first
    g._add_edge(Edge(kind=kind, src=a, dst=b))


def add_path(
    g: StoryGraph,
    path: Path,
    explores: str,
    consequences: list[Consequence],
) -> None:
    answer = g.get(explores)
    if not isinstance(answer, Answer):
        raise MutationError(f"path {path.id} explores non-answer {explores!r}")
    if g.in_ids(explores, EdgeKind.EXPLORES):
        raise MutationError(f"answer {explores} is already explored")
    g._add_node(path)
    g._add_edge(Edge(kind=EdgeKind.EXPLORES, src=path.id, dst=explores))
    for consequence in consequences:
        g._add_node(consequence)
        g._add_edge(Edge(kind=EdgeKind.HAS_CONSEQUENCE, src=path.id, dst=consequence.id))


def add_beat(g: StoryGraph, beat: Beat, belongs_to: list[str]) -> None:
    """I5 locally: belongs_to discipline by beat class and commit status."""
    if beat.beat_class == BeatClass.STRUCTURAL:
        if belongs_to:
            raise MutationError(f"structural beat {beat.id} must have zero belongs_to")
    else:
        if beat.commits_dilemmas and len(belongs_to) != 1:
            raise MutationError(f"commit beat {beat.id} must belong to exactly one path")
        if not 1 <= len(belongs_to) <= 2:
            raise MutationError(f"narrative beat {beat.id} must belong to one or two paths")
    for path_id in belongs_to:
        if not isinstance(g.get(path_id), Path):
            raise MutationError(f"beat {beat.id} belongs_to non-path {path_id!r}")
    if len(belongs_to) == 2:
        d1, d2 = (queries.dilemma_of_path(g, p) for p in belongs_to)
        if d1 != d2:
            raise MutationError(
                f"beat {beat.id}: cross-dilemma dual belongs_to ({d1} vs {d2}) is forbidden"
            )
    g._add_node(beat)
    for path_id in belongs_to:
        g._add_edge(Edge(kind=EdgeKind.BELONGS_TO, src=beat.id, dst=path_id))


def add_ordering(g: StoryGraph, before: str, after: str) -> None:
    if before == after:
        raise MutationError(f"beat {before} cannot precede itself")
    for b in (before, after):
        if not isinstance(g.get(b), Beat):
            raise MutationError(f"{b!r} is not a beat")
    if before in queries.descendants(g, after):
        raise MutationError(f"ordering {before} -> {after} would create a cycle")
    g._add_edge(Edge(kind=EdgeKind.PREDECESSOR, src=before, dst=after))


def remove_beat(g: StoryGraph, beat_id: str) -> None:
    """Beats are never removed after the freeze (I9)."""
    if not isinstance(g.get(beat_id), Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if g.frozen and beat_id in g.frozen.beats:
        raise MutationError(f"beat {beat_id} is frozen and can never be removed")
    g._remove_node(beat_id)


def add_flag(g: StoryGraph, flag: StateFlag, derived_from: list[str] | None = None) -> None:
    if flag.path is not None and not isinstance(g.get(flag.path), Path):
        raise MutationError(f"flag {flag.id} names non-path {flag.path!r}")
    g._add_node(flag)
    for consequence_id in derived_from or []:
        if not isinstance(g.get(consequence_id), Consequence):
            raise MutationError(f"flag {flag.id} derived from non-consequence {consequence_id!r}")
        g._add_edge(Edge(kind=EdgeKind.DERIVED_FROM, src=flag.id, dst=consequence_id))


def add_intersection(g: StoryGraph, group: IntersectionGroup, members: list[str]) -> None:
    """I8 locally: members must serve pairwise distinct dilemmas."""
    if len(members) < 2:
        raise MutationError(f"intersection {group.id} needs >=2 member beats")
    dilemma_sets = []
    for beat_id in members:
        beat = g.get(beat_id)
        if not isinstance(beat, Beat):
            raise MutationError(f"intersection member {beat_id!r} is not a beat")
        dilemma_sets.append({i.dilemma for i in beat.dilemma_impacts})
    for i, a in enumerate(dilemma_sets):
        for b in dilemma_sets[i + 1 :]:
            if a & b:
                raise MutationError(
                    f"intersection {group.id} groups two beats of dilemma(s) {sorted(a & b)}"
                )
    g._add_node(group)
    for beat_id in members:
        g._add_edge(Edge(kind=EdgeKind.IN_GROUP, src=beat_id, dst=group.id))


def add_passage(g: StoryGraph, passage: Passage, beats: list[str]) -> None:
    if not beats:
        raise MutationError(f"passage {passage.id} must contain >=1 beat")
    for beat_id in beats:
        if not isinstance(g.get(beat_id), Beat):
            raise MutationError(f"passage {passage.id} contains non-beat {beat_id!r}")
    g._add_node(passage)
    for beat_id in beats:
        g._add_edge(Edge(kind=EdgeKind.GROUPED_IN, src=beat_id, dst=passage.id))


def add_choice(g: StoryGraph, src: str, dst: str, choice: Choice) -> None:
    for p in (src, dst):
        if not isinstance(g.get(p), Passage):
            raise MutationError(f"{p!r} is not a passage")
    for flag_id in [*choice.requires, *choice.grants]:
        if not isinstance(g.get(flag_id), StateFlag):
            raise MutationError(f"choice {src}->{dst} references unknown flag {flag_id!r}")
    g._add_edge(Edge(kind=EdgeKind.CHOICE, src=src, dst=dst, payload=choice.model_dump()))


def add_variant(g: StoryGraph, variant: str, base: str) -> None:
    for p in (variant, base):
        if not isinstance(g.get(p), Passage):
            raise MutationError(f"{p!r} is not a passage")
    g._add_edge(Edge(kind=EdgeKind.VARIANT_OF, src=variant, dst=base))


def freeze_topology(g: StoryGraph) -> FreezeRecord:
    """Record the dilemma topology at the end of GROW (I9)."""
    forks: dict[str, list[str]] = {}
    convergences: dict[str, str] = {}
    for dilemma in g.nodes_of(Dilemma):
        paths = queries.explored_paths(g, dilemma.id)
        commits = sorted(c for p in paths if (c := queries.commit_beat(g, p)))
        if commits:
            forks[dilemma.id] = commits
        if dilemma.role == DilemmaRole.SOFT and len(commits) == 2:
            shared = queries.descendants(g, commits[0]) & queries.descendants(g, commits[1])
            order = queries.topological_order(g) or []
            first = next((b for b in order if b in shared), None)
            if first:
                convergences[dilemma.id] = first
    record = FreezeRecord(
        beats=sorted(b.id for b in g.nodes_of(Beat)),
        forks=forks,
        convergences=convergences,
    )
    g.frozen = record
    return record
