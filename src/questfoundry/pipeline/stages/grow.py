"""GROW — weave the beat DAG (design doc 02).

Five passes sharing gate G3:

1. *intersections* — the LLM proposes co-occurrence groups over beats
   every player sees (shared pre-commit beats, locked-storyline beats)
   of different dilemmas, from shared entities and SEED's flexibility
   notes; grouped beats become one interleaving unit.
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
4. *annotate* — the LLM tags every beat with its `scene_type` (Swain
   scene/sequel/micro_beat), its `narration_scope` (limited/wide coda),
   and its `viewpoint` head (+ interlude mark) — the intrinsic per-beat
   signals FILL reads to modulate prose and frame the POV (design doc 01
   §5). Runs pre-freeze because these are intrinsic beat content (why the
   beat exists), settled at the freeze like a summary; beats a later
   stage adds (bridge here, POLISH's residue/false-branch) ride the
   purpose fallback (`effective_scene_type`) and are viewpoint wildcards.
5. *bridge* — for adjacent beats sharing no entities, the LLM writes
   structural bridge beats the engine splices in — before the whole fork
   frontier when the gap runs into a commit beat (a bridge is shared, so
   feeding it into one branch dead-ends the others, I6); seams no bridge
   can span safely are left for FILL's prose to smooth.

After a clean gate the topology freezes (I9). Scope notes (tracked in
docs/STATUS.md): intersections over shared pre-commit beats only.
"""

from __future__ import annotations

import copy

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
    NarrationScope,
    SceneType,
    StateFlag,
    StructuralPurpose,
)
from questfoundry.models.world import Entity, EntityCategory
from questfoundry.pipeline import weave
from questfoundry.pipeline.refpin import (
    entity_ref_ids,
    pin,
    retained_character_ids,
    retained_entity_ids,
)
from questfoundry.pipeline.types import (
    ApplyError,
    PassSpec,
    StageImpl,
    format_validation_error,
    resolve_entity_ref,
)
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
        # every player sees a branched dilemma's pre-commit beats and a
        # locked storyline's whole chain — both may intersect
        groupable = next(iter(shape.chains.values())) if shape.locked else shape.pre
        beats = []
        for b in groupable:
            beat = g.node(b)
            assert isinstance(beat, Beat)
            beats.append(beat)
        table.append({"dilemma": g.node(shape.dilemma), "beats": beats, "locked": shape.locked})
    return table


def _intersections_context(project: Project) -> dict:
    return {"vision": project.vision, "dilemmas": _shared_beat_table(project)}


def _intersections_apply(proposal: IntersectionProposal, project: Project) -> list[str]:
    g = project.graph
    shared = {
        b
        for shape in weave.shapes(g)[0]
        for b in (next(iter(shape.chains.values())) if shape.locked else shape.pre)
    }
    used: set[str] = set()
    for spec in proposal.groups:
        for m in spec.members:
            if m not in shared:
                raise ApplyError(
                    f"intersection {spec.id}: member {m} is not a shared pre-commit "
                    f"or locked-storyline beat; members must come from {sorted(shared)}"
                )
            if m in used:
                raise ApplyError(
                    f"beat {m} appears in more than one intersection group — "
                    "keep it in one group and drop it from the others"
                )
            used.add(m)

    def _build(spec: IntersectionSpec) -> IntersectionGroup:
        try:
            return IntersectionGroup(
                id=spec.id,
                created_by=Stage.GROW,
                location=spec.location or None,
                rationale=spec.rationale,
            )
        except ValidationError as e:
            raise ApplyError(f"invalid intersection {spec.id}: {format_validation_error(e)}") from e

    # Intersections are advisory enrichment, like temporal hints (design
    # doc 02 §2): the model proposes them before seeing the full ordering
    # web, so a group that would wedge the weave is dropped and reported,
    # never allowed to fail the stage. Each group is probed one at a time
    # so the drop note names the offending group and why — live run 7
    # burned its repair rounds twice on dense webs where the model could
    # not find satisfiable pairings at all.
    scratch = copy.deepcopy(g)
    baseline = copy.deepcopy(g)
    accepted: list[IntersectionSpec] = []
    lines = []
    for spec in proposal.groups:
        trial = copy.deepcopy(scratch)
        mutations.add_intersection(trial, _build(spec), spec.members)  # I8 locally
        try:
            weave.plan(trial)
        except weave.WeaveError:
            members = ", ".join(spec.members)
            probe = copy.deepcopy(baseline)
            try:
                mutations.add_intersection(probe, _build(spec), spec.members)
                weave.plan(probe)
            except weave.WeaveError:
                lines.append(
                    f"dropped {spec.id} ({members}): its members occupy incompatible "
                    "positions in their storylines' required order"
                )
                continue
            others = ", ".join(s.id for s in accepted)
            lines.append(f"dropped {spec.id} ({members}): cannot coexist with {others}")
            continue
        scratch = trial
        accepted.append(spec)
        lines.append(f"{spec.id}: {' + '.join(spec.members)}")
    for spec in accepted:
        mutations.add_intersection(g, _build(spec), spec.members)
    if not proposal.groups:
        return ["no intersections proposed"]
    return lines


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
    locked = planned.locked_of_beat.get(unit.beats[0])
    if locked:
        return f"({locked}, locked subplot) {summaries}"
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
    return {"vision": project.vision, "candidates": rendered, "multi_hard": multi_hard}


def _derive_flags(g) -> list[str]:
    lines = []
    locked_paths = {
        p
        for d_id in queries.locked_dilemmas(g)
        for p in queries.explored_paths(g, d_id)
    }
    for path in sorted(g.nodes_of(Path), key=lambda p: p.id):
        if path.id in locked_paths:
            continue  # a locked outcome is a world fact, never a flag (G3-FLAGS)
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
        paths = queries.explored_paths(g, d.id)
        if len(paths) != 2:
            continue  # a locked chain interleaves; its beats are not fork tails
        for p in paths:
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
            raise ApplyError(f"{spec.beat} rewritten twice — keep one rewrite entry per beat")
        if not spec.summary.strip():
            raise ApplyError(f"summary for {spec.beat} is empty")
        seen.add(spec.beat)
    missing = expected - seen
    if missing:
        raise ApplyError(f"every listed beat needs a rewrite; missing {sorted(missing)}")
    for spec in proposal.rewrites:
        mutations.set_beat_summary(g, spec.beat, spec.summary)
    return [f"{len(seen)} beat summaries contextualized to their worlds"]


# -- pass 4: annotate ---------------------------------------------------------


class SchemeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # the head roster: the characters the narration follows (pinned to the
    # retained character ids; a single-viewpoint scheme is a roster of one)
    heads: list[str] = Field(min_length=1)
    # the deviant register's voice, when the POV hint declares one (pinned
    # to the retained character ids plus "" = no register); the carrier
    # need not be a roster head (pov-sequences.md decision 6)
    interlude_head: str = ""


def scheme_proposal_schema(project: Project) -> type[SchemeProposal]:
    """Pin `heads` and `interlude_head` to the retained character ids, so
    an off-cast head is unrepresentable (I17's schema half)."""
    ids = retained_character_ids(project.graph)
    return pin(
        SchemeProposal,
        "SchemeProposal",
        {
            ("SchemeProposal", "heads"): ids,
            ("SchemeProposal", "interlude_head"): ids + [""],
        },
    )


def _scheme_context(project: Project) -> dict:
    g = project.graph
    characters = [g.node(cid) for cid in retained_character_ids(g)]
    return {"vision": project.vision, "characters": characters}


def _scheme_apply(proposal: SchemeProposal, project: Project) -> list[str]:
    """Resolve the prose POV scheme into graph marks: `pov_head` on every
    roster character, `interlude_carrier` on the register's voice. Marks
    are RESET, not accumulated — a rerun's fresh roster replaces the old
    one entirely (stale marks would widen I17's legal set silently)."""
    g = project.graph
    heads = set(proposal.heads)
    carrier = proposal.interlude_head or None
    for entity in g.nodes_of(Entity):
        if entity.category != EntityCategory.CHARACTER:
            continue
        mutations.set_pov_head(g, entity.id, entity.id in heads)
        mutations.set_interlude_carrier(g, entity.id, entity.id == carrier)
    log = [f"head roster: {', '.join(sorted(heads))}"]
    log.append(f"interlude carrier: {carrier}" if carrier else "no interlude register")
    return log


def _scheme_roster(g) -> tuple[list[str], str | None]:
    """The declared roster and carrier, empty/None on pre-scheme graphs."""
    roster = sorted(
        e.id
        for e in g.nodes_of(Entity)
        if e.category == EntityCategory.CHARACTER and e.pov_head
    )
    carrier = next(
        (
            e.id
            for e in g.nodes_of(Entity)
            if e.category == EntityCategory.CHARACTER and e.interlude_carrier
        ),
        None,
    )
    return roster, carrier


def grow_sequences(g) -> list[list[str]]:
    """The engine's sequence computation (pov-sequences.md): the maximal
    choice-free linear runs of the current beat graph, in topological
    order of their heads — the unit of viewpoint assignment. Computed,
    never stored (iron rule 2's spirit); the annotate schema, apply, and
    the B11 gate all call this, so they can never disagree."""
    from questfoundry.pipeline.passages import collapse_groups

    return collapse_groups(g, max_beats=None, split_viewpoints=False)


class BeatScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat: str
    scene_type: SceneType
    narration_scope: NarrationScope
    # the beat belongs to the scheme's deviant register (its head is the
    # declared carrier — engine-expanded, never named per beat)
    interlude: bool


class SequenceSplit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # the beat AFTER which the head changes (inside the sequence, never
    # its last beat) and the new head for the rest of the sequence
    after: str
    head: str
    # the dramatic-center shift that earns the page-turn — required
    why: str = Field(min_length=1)


class SequenceHead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # a sequence is named by its first beat (pinned to the engine's list)
    sequence: str
    # pinned to the head roster plus "" (= a justified wide cutaway); the
    # carrier is NOT a legal base-register head (I17)
    head: str
    splits: list[SequenceSplit] = []


class AnnotateProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annotations: list[BeatScene]
    heads: list[SequenceHead]


def _annotate_beats(project: Project) -> list[dict]:
    g = project.graph
    rows = []
    for bid in queries.topological_order(g) or []:
        beat = g.node(bid)
        assert isinstance(beat, Beat)
        rows.append(
            {"beat": beat, "effects": sorted({i.effect.value for i in beat.dilemma_impacts})}
        )
    return rows


def _annotate_context(project: Project) -> dict:
    g = project.graph
    characters = [g.node(cid) for cid in retained_character_ids(g)]
    roster, carrier = _scheme_roster(g)
    rows = {r["beat"].id: r for r in _annotate_beats(project)}
    sequences = []
    for seq in grow_sequences(g):
        # roster heads on the page in this sequence, with presence counts —
        # advisory (a head may witness without being listed); an empty list
        # is the split-or-wide signal, stated in the prompt
        present: dict[str, int] = {}
        for bid in seq:
            beat = g.node(bid)
            assert isinstance(beat, Beat)
            for eid in beat.entities:
                if eid in roster:
                    present[eid] = present.get(eid, 0) + 1
        sequences.append(
            {
                "head_beat": seq[0],
                "beats": [rows[bid] for bid in seq],
                "candidates": [
                    (eid, n, len(seq)) for eid, n in sorted(present.items(), key=lambda x: -x[1])
                ],
            }
        )
    return {
        "vision": project.vision,
        "sequences": sequences,
        "characters": characters,
        "roster": [g.node(r) for r in roster],
        "carrier": g.node(carrier) if carrier else None,
    }


def _annotate_apply(proposal: AnnotateProposal, project: Project) -> list[str]:
    g = project.graph
    expected = set(queries.topological_order(g) or [])
    roster, carrier = _scheme_roster(g)
    sequences = grow_sequences(g)
    seq_by_head = {seq[0]: seq for seq in sequences}

    # -- beat coverage (validate everything before mutating anything) --------
    seen: set[str] = set()
    specs: dict[str, BeatScene] = {}
    for spec in proposal.annotations:
        if spec.beat not in expected:
            raise ApplyError(
                f"{spec.beat} is not a beat to annotate; annotate exactly these "
                f"beats: {sorted(expected)}"
            )
        if spec.beat in seen:
            raise ApplyError(f"{spec.beat} annotated twice — keep one entry per beat")
        seen.add(spec.beat)
        specs[spec.beat] = spec
        if spec.narration_scope == NarrationScope.WIDE and spec.interlude:
            raise ApplyError(
                f"{spec.beat} is marked both wide and interlude — an interlude is "
                "narrated inside one head; make it limited, or drop the interlude mark"
            )
        if spec.interlude and carrier is None:
            raise ApplyError(
                f"{spec.beat} is marked interlude but the scheme declares no "
                "deviant register — drop the interlude mark"
            )
    missing = expected - seen
    if missing:
        raise ApplyError(
            "every beat needs a scene_type and narration_scope — the writer "
            f"paces and frames the whole story from them; missing {sorted(missing)}"
        )

    # -- sequence coverage and split validation ------------------------------
    covered: set[str] = set()
    for entry in proposal.heads:
        if entry.sequence in covered:
            raise ApplyError(
                f"sequence {entry.sequence} is assigned twice — assign each "
                "sequence exactly once"
            )
        covered.add(entry.sequence)
        seq = seq_by_head[entry.sequence]
        last_idx = -1
        for split in entry.splits:
            if split.after not in seq:
                raise ApplyError(
                    f"split point {split.after} is not inside the sequence at "
                    f"{entry.sequence}; valid split points are "
                    f"{seq[:-1]} (never the last beat)"
                )
            idx = seq.index(split.after)
            if idx == len(seq) - 1:
                raise ApplyError(
                    f"split after {split.after} is the sequence's last beat — "
                    "a split needs a non-empty tail; use an earlier beat"
                )
            if idx <= last_idx:
                raise ApplyError(
                    f"split points at {entry.sequence} repeat or run out of "
                    "order — list each once, in story order"
                )
            last_idx = idx
    missing_seqs = set(seq_by_head) - covered
    if missing_seqs:
        raise ApplyError(
            "every sequence needs a head (one entry per sequence, keyed by its "
            f"first beat); missing {sorted(missing_seqs)}"
        )

    # -- expansion: sequence heads -> per-beat viewpoints --------------------
    beat_head: dict[str, str | None] = {}
    cutaways = 0
    for entry in proposal.heads:
        seq = seq_by_head[entry.sequence]
        bounds = {seq.index(s.after): s.head for s in entry.splits}
        head: str | None = entry.head or None
        for i, bid in enumerate(seq):
            spec = specs[bid]
            if spec.interlude:
                # the register's voice is scheme-level (I17); pre-roster
                # graphs have no carrier and no interludes reach here
                beat_head[bid] = carrier
            elif spec.narration_scope == NarrationScope.WIDE:
                beat_head[bid] = None  # a coda has no head, ever
            elif head is None:
                raise ApplyError(
                    f'{bid} is limited inside a ""-headed segment — a headless '
                    "segment is a wide CUTAWAY: mark its beats wide, or give "
                    "the segment a head from the roster"
                )
            else:
                beat_head[bid] = head
            if i in bounds:
                head = bounds[i] or None
                if head is None:
                    cutaways += 1
        if entry.head == "":
            cutaways += 1

    # -- write ---------------------------------------------------------------
    counts = {SceneType.SCENE: 0, SceneType.SEQUEL: 0, SceneType.MICRO_BEAT: 0}
    scopes = {NarrationScope.LIMITED: 0, NarrationScope.WIDE: 0}
    heads: dict[str, int] = {}
    interludes = 0
    for spec in proposal.annotations:
        mutations.set_beat_scene_type(g, spec.beat, spec.scene_type)
        mutations.set_beat_narration_scope(g, spec.beat, spec.narration_scope)
        viewpoint = beat_head.get(spec.beat)
        mutations.set_beat_viewpoint(g, spec.beat, viewpoint, interlude=spec.interlude)
        counts[spec.scene_type] += 1
        scopes[spec.narration_scope] += 1
        if viewpoint is not None:
            heads[viewpoint.split(":", 1)[1]] = heads.get(viewpoint.split(":", 1)[1], 0) + 1
        interludes += spec.interlude
    head_note = ", ".join(f"{h} {n}" for h, n in sorted(heads.items(), key=lambda x: -x[1]))
    lines = [
        f"annotated {len(seen)} beats over {len(sequences)} sequences: "
        f"{counts[SceneType.SCENE]} scene, "
        f"{counts[SceneType.SEQUEL]} sequel, {counts[SceneType.MICRO_BEAT]} micro_beat; "
        f"{scopes[NarrationScope.LIMITED]} limited, {scopes[NarrationScope.WIDE]} wide; "
        f"heads: {head_note or 'none'}"
        + (f"; {interludes} interlude{'s' if interludes != 1 else ''}" if interludes else "")
        + (f"; {cutaways} wide cutaway{'s' if cutaways != 1 else ''}" if cutaways else "")
    ]
    for entry in proposal.heads:
        for split in entry.splits:
            lines.append(
                f"split at {entry.sequence} after {split.after} -> "
                f"{split.head or 'wide cutaway'}: {split.why}"
            )
    return lines


# -- pass 5: bridge -----------------------------------------------------------


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
                entities=[resolve_entity_ref(g, e) for e in spec.entities],
            )
        except ValidationError as e:
            raise ApplyError(f"invalid bridge beat {spec.id}: {format_validation_error(e)}") from e
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


def _shared_beats(g) -> list[str]:
    """Beats every player sees — a branched dilemma's pre-commit beats and
    a locked storyline's whole chain — the only beats an intersection may
    group (mirrors `_intersections_apply`'s `shared` set, in shape order)."""
    return [
        b
        for shape in weave.shapes(g)[0]
        for b in (next(iter(shape.chains.values())) if shape.locked else shape.pre)
    ]


def intersections_proposal_schema(project: Project) -> type[IntersectionProposal]:
    """Pin `members` to the shared/lockable beats and `location` to the
    entity ids (plus "" — no anchor, its default); closes the previously
    unchecked `location` dangling-reference hole (pipeline/refpin.py)."""
    g = project.graph
    # `location` is stored raw (`IntersectionGroup.location`), so pin it to
    # exact entity ids — plus "" (its default: no anchoring place).
    return pin(
        IntersectionProposal,
        "IntersectionProposal",
        {
            ("IntersectionSpec", "members"): _shared_beats(g),
            ("IntersectionSpec", "location"): retained_entity_ids(g) + [""],
        },
    )


def contextualize_proposal_schema(project: Project) -> type[ContextualizeProposal]:
    """Pin `rewrites[].beat` to the per-world clone / de-ended tail beats
    the weave produced (resolved after weave rewires the graph)."""
    targets = [t["beat"].id for t in _contextualize_targets(project)]
    return pin(
        ContextualizeProposal, "ContextualizeProposal", {("RewriteSpec", "beat"): targets}
    )


def annotate_proposal_schema(project: Project) -> type[AnnotateProposal]:
    """Pin `annotations[].beat` to every beat present pre-freeze (the
    annotatable set — SEED scaffold + GROW clones; bridge/residue/
    false-branch are added later and ride the purpose fallback),
    `heads[].sequence` to the engine's sequence heads, and every head
    field to the roster plus "" (an off-scheme segment head is
    unrepresentable — I17's schema half; the carrier is deliberately NOT
    in the segment-head enum, interlude beats reach it per beat). A
    pre-roster graph falls back to the retained character ids — the
    legal degenerate case. Resolved after scheme/weave/contextualize
    rewire the graph (PassSpec.schema_for)."""
    g = project.graph
    beats = queries.topological_order(g) or []
    roster, _carrier = _scheme_roster(g)
    heads = list(roster) if roster else retained_character_ids(g)
    seq_heads = [seq[0] for seq in grow_sequences(g)]
    return pin(
        AnnotateProposal,
        "AnnotateProposal",
        {
            ("BeatScene", "beat"): beats,
            ("SequenceHead", "sequence"): seq_heads,
            ("SequenceHead", "head"): heads + [""],
            ("SequenceSplit", "after"): beats,
            ("SequenceSplit", "head"): heads + [""],
        },
    )


def bridge_proposal_schema(project: Project) -> type[BridgeProposal]:
    """Pin `bridges[].entities` to the entity ids."""
    return pin(
        BridgeProposal,
        "BridgeProposal",
        {("BridgeSpec", "entities"): entity_ref_ids(project.graph)},
    )


GROW_STAGE = StageImpl(
    stage=Stage.GROW,
    passes=(
        PassSpec(
            name="intersections",
            role="architect",
            template="grow_intersections.j2",
            schema=intersections_proposal_schema,
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
            schema=contextualize_proposal_schema,
            build_context=_contextualize_context,
            apply=_contextualize_apply,
            skip_if=_contextualize_skip,
        ),
        PassSpec(
            name="scheme",
            role="utility",
            template="grow_scheme.j2",
            schema=scheme_proposal_schema,
            build_context=_scheme_context,
            apply=_scheme_apply,
        ),
        PassSpec(
            name="annotate",
            role="writer",
            template="grow_annotate.j2",
            schema=annotate_proposal_schema,
            build_context=_annotate_context,
            apply=_annotate_apply,
        ),
        PassSpec(
            name="bridge",
            role="writer",
            template="grow_bridge.j2",
            schema=bridge_proposal_schema,
            build_context=_bridge_context,
            apply=_bridge_apply,
            skip_if=_bridge_skip,
        ),
    ),
    gate=_grow_gate,
)
