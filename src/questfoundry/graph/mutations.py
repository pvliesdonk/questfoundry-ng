"""The single write path to the story graph (design principle 2).

Every operation performs its *local* invariant checks before touching the
store; global invariants are the gates' job (`graph/validate.py`). LLM
proposals and hand-edited project files both land here — there is no
privileged writer.
"""

from __future__ import annotations

import re

from questfoundry.graph import queries
from questfoundry.graph.store import FreezeRecord, StoryGraph
from questfoundry.models.base import Edge, EdgeKind
from questfoundry.models.drama import Answer, Consequence, Dilemma, DilemmaRole, Path
from questfoundry.models.presentation import Choice, Passage
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    IntersectionGroup,
    NarrationScope,
    SceneType,
    StateFlag,
)
from questfoundry.models.world import Entity, EntityArc, EntityCategory

CODEWORD_RE = re.compile(r"^[A-Z]{3,12}$")


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


def set_dilemma_disposition(g: StoryGraph, dilemma_id: str, *, reserved: bool) -> None:
    """SEED triage: mark a dilemma reserved — kept in the graph as unwoven
    texture feedstock, no path, never woven (structural-depth W2). Reserved
    dilemmas stop counting for role budgets (B1) and anchoring (I2); a
    reserved dilemma with an explored path is a gate error."""
    dilemma = g.get(dilemma_id)
    if not isinstance(dilemma, Dilemma):
        raise MutationError(f"{dilemma_id!r} is not a dilemma")
    dilemma.reserved = reserved


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
    try:
        g._add_node(beat)
    except KeyError as e:
        # The store raises a bare KeyError on a duplicate id; every other
        # guard here raises MutationError, and only MutationError/ApplyError
        # are caught as repairable by the runner. Convert it — and make the
        # message actionable (heritage semantic-conventions §Error Messages:
        # a recovery_action, not just a reason), because a model that coined
        # the colliding id needs to be told to pick a fresh one, not just
        # that this one is taken (weak-tier live run, gpt-oss:120b: a residue
        # beat reusing a commit-beat id, unrecoverable across repairs on a
        # bare "duplicate node id" message).
        raise MutationError(
            f"beat id {beat.id!r} is already used by an existing beat; a new "
            "beat needs a fresh, unique id. Choose an id no existing beat has "
            "(a more specific slug) and keep every new id in this proposal "
            "distinct from the others."
        ) from e
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


def remove_ordering(g: StoryGraph, before: str, after: str) -> None:
    """Unwire one ordering edge. GROW rewires SEED's scaffold chains when
    it splices dilemmas together; whether the resulting topology still
    honors frozen forks/convergences is the gates' job (I9)."""
    for b in (before, after):
        if not isinstance(g.get(b), Beat):
            raise MutationError(f"{b!r} is not a beat")
    if not g.has_edge(EdgeKind.PREDECESSOR, before, after):
        raise MutationError(f"no ordering {before} -> {after} to remove")
    g._remove_edge(EdgeKind.PREDECESSOR, before, after)


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


def set_passage_irrelevant_flags(g: StoryGraph, passage_id: str, flags: list[str]) -> None:
    """POLISH feasibility audit: declare flags this passage's prose must
    not address (they stop counting against the I12 cap)."""
    passage = g.get(passage_id)
    if not isinstance(passage, Passage):
        raise MutationError(f"{passage_id!r} is not a passage")
    for flag_id in flags:
        if not isinstance(g.get(flag_id), StateFlag):
            raise MutationError(f"irrelevant flag {flag_id!r} is not a flag")
    passage.irrelevant_flags = sorted(flags)


def set_passage_prose(g: StoryGraph, passage_id: str, prose: str) -> None:
    """FILL's write path: prose for one passage."""
    passage = g.get(passage_id)
    if not isinstance(passage, Passage):
        raise MutationError(f"{passage_id!r} is not a passage")
    if not prose.strip():
        raise MutationError(f"prose for {passage_id} is empty")
    passage.prose = prose


def set_entity_arc(g: StoryGraph, entity_id: str, arc: EntityArc) -> None:
    """POLISH's arcs pass (design doc 02: "begins X, pivots at beat Y,
    ends Z per path"). Pivots anchor to real beats in story order; ends
    name explored paths. Stable once set — like a codeword, re-proposing
    the identical arc is a no-op, changing one is an error (the rewind
    machinery, not overwrite, is how an arc is revised)."""
    entity = g.get(entity_id)
    if not isinstance(entity, Entity):
        raise MutationError(f"{entity_id!r} is not an entity")
    if entity.arc is not None:
        if entity.arc == arc:
            return
        raise MutationError(f"{entity_id} already has an arc; arcs are stable once set")
    order = {b: i for i, b in enumerate(queries.topological_order(g) or [])}
    positions = []
    for pivot in arc.pivots:
        if not isinstance(g.get(pivot.beat), Beat):
            raise MutationError(f"arc pivot {pivot.beat!r} is not a beat")
        positions.append(order[pivot.beat])
    if positions != sorted(positions):
        listed = [p.beat for p in arc.pivots]
        wanted = [b for _, b in sorted(zip(positions, listed, strict=True))]
        raise MutationError(
            f"{entity_id}: arc pivots are out of story order — listed as "
            f"{listed}, but their beats occur as {wanted} (story order is the "
            f"beat-by-beat sequence shown in the prompt, which fixes the order "
            f"even between parallel branches); keep every pivot and re-list "
            f"them exactly in that second order"
        )
    for end in arc.ends:
        if not isinstance(g.get(end.path), Path):
            raise MutationError(f"arc end {end.path!r} is not a path")
    entity.arc = arc


def set_passage_prose_summary(g: StoryGraph, passage_id: str, summary: str) -> None:
    """FILL's rolling story-so-far entry: the utility-summarized note a
    later passage's write context reads instead of this passage's prose."""
    passage = g.get(passage_id)
    if not isinstance(passage, Passage):
        raise MutationError(f"{passage_id!r} is not a passage")
    if not summary.strip():
        raise MutationError(f"prose summary for {passage_id} is empty")
    passage.prose_summary = summary


def add_entity_detail(g: StoryGraph, entity_id: str, key: str, value: str) -> None:
    """A universal micro-detail written into the entity's base state, true on
    every arc (design doc 01 §3). Adds a new fact, or UPDATES an existing one
    with a sharper version — a re-used key overwrites (author-directed
    redesign, 2026-07-12). Whether an update is a legitimate refinement or a
    contradiction is the FILL reviewer's `micro_detail` rule to judge; the
    single-assignment hard guard was removed because it turned a capable
    writer's natural re-observation of a recurring entity into a prose-blocking
    failure."""
    entity = g.get(entity_id)
    if not isinstance(entity, Entity):
        raise MutationError(f"{entity_id!r} is not an entity")
    entity.base[key] = value


def add_choice(g: StoryGraph, src: str, dst: str, choice: Choice) -> None:
    for p in (src, dst):
        if not isinstance(g.get(p), Passage):
            raise MutationError(f"{p!r} is not a passage")
    for flag_id in [*choice.requires, *choice.grants]:
        if not isinstance(g.get(flag_id), StateFlag):
            raise MutationError(f"choice {src}->{dst} references unknown flag {flag_id!r}")
    g._add_edge(Edge(kind=EdgeKind.CHOICE, src=src, dst=dst, payload=choice.model_dump()))


def relabel_choice(g: StoryGraph, src: str, dst: str, label: str) -> None:
    """FILL's writer may rewrite a choice label so it names what the prose
    it just wrote actually shows (author request, in-session 2026-07-14:
    "can we have the writer *also* rewrite the choice labels?"). Text only:
    the destination, gate, and grants were fixed at POLISH — the label is
    the one presentation field the finished prose knows better."""
    for p in (src, dst):
        if not isinstance(g.get(p), Passage):
            raise MutationError(f"{p!r} is not a passage")
    label = label.strip()
    if not label:
        raise MutationError(
            f"choice {src} -> {dst}: a rewritten label must be non-empty — "
            "keep the existing label (omit the rewrite) instead of blanking it"
        )
    edges = [e for e in g.out_edges(src, EdgeKind.CHOICE) if e.dst == dst]
    if not edges:
        raise MutationError(f"no choice {src} -> {dst} to relabel")
    for e in edges:
        e.payload["label"] = label


def set_flag_codeword(g: StoryGraph, flag_id: str, codeword: str) -> None:
    """DRESS pass 4: assign a flag's print codeword. Codewords are stable
    once set — a print run may already reference the old word, so changing
    one is an error, not an overwrite; re-proposing the same word is a
    harmless no-op (idempotent reruns)."""
    flag = g.get(flag_id)
    if not isinstance(flag, StateFlag):
        raise MutationError(f"{flag_id!r} is not a flag")
    if not CODEWORD_RE.match(codeword):
        raise MutationError(
            f"codeword {codeword!r} for {flag_id} must match {CODEWORD_RE.pattern} "
            "(3-12 uppercase letters A-Z)"
        )
    if flag.codeword == codeword:
        return
    if flag.codeword is not None:
        raise MutationError(
            f"flag {flag_id} already has codeword {flag.codeword!r}; codewords are "
            "stable once set and cannot be changed (print stability)"
        )
    taken = {f.codeword for f in g.nodes_of(StateFlag) if f.codeword and f.id != flag_id}
    if codeword in taken:
        raise MutationError(f"codeword {codeword!r} is already used by another flag")
    flag.codeword = codeword


def add_variant(g: StoryGraph, variant: str, base: str) -> None:
    for p in (variant, base):
        if not isinstance(g.get(p), Passage):
            raise MutationError(f"{p!r} is not a passage")
    g._add_edge(Edge(kind=EdgeKind.VARIANT_OF, src=variant, dst=base))


def split_passage(g: StoryGraph, passage_id: str, gate_sets: list[list[str]]) -> list[str]:
    """POLISH audit's I12 escape valve (structural-depth follow-up,
    author-directed 2026-07-14): split a wired passage into flag-gated
    variants — the same moment re-presented behind disjoint gates, so
    each variant's arrivals hold a KNOWN side of the keyed dilemma(s) and
    that state honestly stops counting against the prose (I12), instead
    of being marked irrelevant to satisfy a budget.

    ``gate_sets`` is one flag-set per variant (the caller enumerates the
    keyed dilemmas' path-flag combinations — every arriving reader holds
    exactly one combination). The passage itself becomes the first
    variant: its in-choices gain that gate; each additional set gets a
    sibling passage (same beats, same summary — FILL differentiates from
    flag context, like any variant) with copies of every in-choice
    (gate added) and out-choice, linked ``variant_of`` the original.
    Returns the variant ids, original first."""
    passage = g.get(passage_id)
    if not isinstance(passage, Passage):
        raise MutationError(f"{passage_id!r} is not a passage")
    if len(gate_sets) < 2:
        raise MutationError(f"splitting {passage_id} needs >=2 gate sets, got {len(gate_sets)}")
    seen_sets = [tuple(sorted(s)) for s in gate_sets]
    if len(set(seen_sets)) != len(seen_sets) or any(not s for s in seen_sets):
        raise MutationError(f"splitting {passage_id} needs distinct, non-empty gate sets")
    for flag_id in {f for s in gate_sets for f in s}:
        if not isinstance(g.get(flag_id), StateFlag):
            raise MutationError(f"split gate references unknown flag {flag_id!r}")
    if passage.ending is not None:
        raise MutationError(
            f"{passage_id} is an ending; endings are not split — variants "
            "would multiply the story's ending set, fixed at the freeze"
        )
    beats = [e.src for e in g.in_edges(passage_id, EdgeKind.GROUPED_IN)]
    in_choices = list(g.in_edges(passage_id, EdgeKind.CHOICE))
    out_choices = list(g.out_edges(passage_id, EdgeKind.CHOICE))

    ids = [passage_id]
    for k, gates in enumerate(gate_sets[1:], start=1):
        sibling = Passage(
            id=f"{passage_id}--s{k}",
            created_by=passage.created_by,
            summary=passage.summary,
            entities=list(passage.entities),
            variant_flag=sorted(gates)[0],
            irrelevant_flags=list(passage.irrelevant_flags),
        )
        add_passage(g, sibling, beats)
        add_variant(g, sibling.id, passage_id)
        for e in in_choices:
            choice = Choice(**e.payload)
            choice.requires = sorted({*choice.requires, *gates})
            add_choice(g, e.src, sibling.id, choice)
        for e in out_choices:
            add_choice(g, sibling.id, e.dst, Choice(**e.payload))
        ids.append(sibling.id)
    # the original takes the first gate set: its existing in-choices are
    # narrowed in place (edge payloads are the mutation layer's surface)
    passage.variant_flag = passage.variant_flag or sorted(gate_sets[0])[0]
    for e in in_choices:
        e.payload["requires"] = sorted({*e.payload.get("requires", []), *gate_sets[0]})
    return ids


def set_beat_summary(g: StoryGraph, beat_id: str, summary: str) -> None:
    """GROW's contextualize write path: rewrite a beat's summary for its
    world (per-world clones, de-ended first-fork tails). Frozen beats'
    content is settled — POLISH and later never rewrite what happens."""
    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if not summary.strip():
        raise MutationError(f"summary for {beat_id} is empty")
    if g.frozen and beat_id in g.frozen.beats:
        raise MutationError(f"beat {beat_id} is frozen; summaries are settled at the freeze")
    beat.summary = summary


def set_beat_scene_type(g: StoryGraph, beat_id: str, scene_type: SceneType) -> None:
    """GROW's annotate write path: a beat's prose-intensity type (Swain
    scene/sequel/micro_beat). Like a summary, ``scene_type`` is intrinsic
    beat content settled at the freeze — it names *why the beat exists*
    dramatically, which POLISH never restates — so a frozen beat is
    rejected. Pre-freeze it is settable (repair may re-run the pass)."""
    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if g.frozen and beat_id in g.frozen.beats:
        raise MutationError(f"beat {beat_id} is frozen; scene_type is settled at the freeze")
    beat.scene_type = scene_type


def set_beat_narration_scope(g: StoryGraph, beat_id: str, scope: NarrationScope) -> None:
    """GROW's annotate write path: a beat's POV/coda register (limited vs
    wide). Like ``scene_type``, ``narration_scope`` is intrinsic beat content
    settled at the freeze — POLISH never restates whether a beat is a coda —
    so a frozen beat is rejected. Pre-freeze it is settable (repair may
    re-run the pass)."""
    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if g.frozen and beat_id in g.frozen.beats:
        raise MutationError(f"beat {beat_id} is frozen; narration_scope is settled at the freeze")
    beat.narration_scope = scope


def set_beat_viewpoint(
    g: StoryGraph, beat_id: str, viewpoint: str | None, *, interlude: bool = False
) -> None:
    """GROW's annotate write path: the character entity whose head narrates
    this beat, plus its interlude mark (the two travel together —
    rotating-pov-build.md). Like the other annotations, intrinsic beat
    content settled at the freeze, so a frozen beat is rejected. Referential
    existence of the id is the gate's job (G3), not the mutation's."""
    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if g.frozen and beat_id in g.frozen.beats:
        raise MutationError(f"beat {beat_id} is frozen; viewpoint is settled at the freeze")
    if interlude and viewpoint is None:
        raise MutationError(f"beat {beat_id}: an interlude beat must name a viewpoint")
    beat.viewpoint = viewpoint
    beat.interlude = interlude


def set_pov_head(g: StoryGraph, entity_id: str, flag: bool) -> None:
    """GROW's scheme write path: mark a character as a followed POV head
    (the roster; pov-sequences.md). Characters only — a head is always a
    character (rotating-pov-build.md). Entity annotation, no freeze
    interaction; scheme conformance of beat heads is I17's job."""
    entity = g.get(entity_id)
    if not isinstance(entity, Entity) or entity.category != EntityCategory.CHARACTER:
        raise MutationError(f"{entity_id!r} is not a character; only characters head a POV")
    entity.pov_head = flag


def set_interlude_carrier(g: StoryGraph, entity_id: str, flag: bool) -> None:
    """GROW's scheme write path: mark the character whose voice carries the
    scheme's deviant register (journal entries, letters). At most one
    carrier per story — the scheme schema makes a second unrepresentable,
    I17 catches a hand edit. Roster membership is not required (the
    *Closed Circle* investigator carries the journal without being a
    rotating head)."""
    entity = g.get(entity_id)
    if not isinstance(entity, Entity) or entity.category != EntityCategory.CHARACTER:
        raise MutationError(
            f"{entity_id!r} is not a character; only a character's voice carries a register"
        )
    entity.interlude_carrier = flag


def set_beat_texture_premise(g: StoryGraph, beat_id: str, premise: str) -> None:
    """POLISH's finalize write path: the consequence-free axis a cosmetic-fork
    rendering varies, named on each of its beats so FILL grounds the prose and
    the fork's entry label can name it (01 §6). Unlike ``scene_type`` and the
    other beat annotations, this is a presentation *addition*, not intrinsic
    content — a rendering-0 premise lands on the *frozen* trunk beats it
    describes, and the freeze (I9) is topological (no beat deleted, no fork or
    convergence moved), so an added annotation is legal. Engine-set only: the
    finalize apply derives the premise, models never set it directly."""
    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if not premise.strip():
        raise MutationError(f"texture_premise for {beat_id} is empty")
    beat.texture_premise = premise


def add_beat_flag_grant(g: StoryGraph, beat_id: str, flag_id: str) -> None:
    """POLISH's fork-splice write path (cosmetic-forks PR-5): record on a
    rendering's head beat that walking it grants ``flag_id`` — the beat-layer
    cosmetic grant `grant_beats` reads. Like ``set_beat_texture_premise``, a
    presentation *addition*: rendering 0's head is a frozen beat and the
    freeze (I9) is topological, so no freeze check. Engine-set only; kept
    sorted and idempotent (re-applying a recorded proposal is a no-op)."""
    from questfoundry.models.structure import FlagSource

    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    flag = g.get(flag_id)
    if not isinstance(flag, StateFlag):
        raise MutationError(f"{flag_id!r} is not a flag")
    if flag.source != FlagSource.COSMETIC:
        raise MutationError(
            f"flag {flag_id} is not cosmetic; only cosmetic flags are granted "
            "via grants_flags — a dilemma flag is granted at its path's commit "
            "beat, never annotated onto one"
        )
    if flag_id not in beat.grants_flags:
        beat.grants_flags = sorted([*beat.grants_flags, flag_id])


def set_beat_ending(g: StoryGraph, beat_id: str, *, is_ending: bool) -> None:
    """GROW's realization: a nested hard fork de-ends the first-forking
    dilemma's tails (the story continues into the climax fork)."""
    beat = g.get(beat_id)
    if not isinstance(beat, Beat):
        raise MutationError(f"{beat_id!r} is not a beat")
    if g.frozen and beat_id in g.frozen.beats:
        raise MutationError(f"beat {beat_id} is frozen; endings cannot move after the freeze")
    beat.is_ending = is_ending


def freeze_topology(g: StoryGraph) -> FreezeRecord:
    """Record the dilemma topology at the end of GROW (I9)."""
    forks: dict[str, list[str]] = {}
    convergences: dict[str, list[str]] = {}
    for dilemma in g.nodes_of(Dilemma):
        paths = queries.explored_paths(g, dilemma.id)
        commits = sorted(c for p in paths for c in queries.commit_beats(g, p))
        if commits:
            forks[dilemma.id] = commits
        if dilemma.role == DilemmaRole.SOFT and commits:
            # A multi-beat frontier is a deeper hard fork's commits, already
            # frozen under forks — record only single-beat convergences.
            beats = sorted(
                f[0] for _, f in queries.soft_rejoin_frontiers(g, dilemma.id) if len(f) == 1
            )
            if beats:
                convergences[dilemma.id] = beats
    record = FreezeRecord(
        beats=sorted(b.id for b in g.nodes_of(Beat)),
        forks=forks,
        convergences=convergences,
    )
    g.frozen = record
    return record
