"""FILL — prose (design doc 02).

The pass list is computed per project: one *voice* pass (skipped when a
voice already exists — author-provided or a re-run), then one *write*
pass per passage in reference-arc-first order. The reference arc is
FILL-internal scheduling state (design doc 01 §4): a seeded selection
whose passages are written end-to-end first so convergence-point prose
has a first author; every remaining passage is then written toward the
already-written text (window + lookahead context). Nothing about the
reference arc is stored or visible to any other stage.

Each write pass enforces the word budget deterministically (repairable,
with 20% slack — models cannot hit exact word windows; the band catches
runaway or skimpy prose, the review pass owns quality)
and then faces the automated review — an LLM judgment on voice, beat
fidelity, and continuity, run through `PassSpec.review`, so the ≤2
revision rounds and the "structure is wrong, not the words" halt are
the runner's ordinary repair contract.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import Issue, Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import Voice
from questfoundry.models.drama import Answer, Dilemma
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import (
    StateFlag,
    effective_narration_scope,
    effective_scene_type,
    passage_intensity,
    passage_viewpoint,
)
from questfoundry.models.world import Entity, EntityCategory
from questfoundry.pipeline import echo
from questfoundry.pipeline.refpin import entity_ref_ids, pin
from questfoundry.pipeline.review import (
    ReviewFinding,
    build_verdict_schema,
    evaluate_review,
    is_blocking,
    render_finding,
)
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl, resolve_entity_ref
from questfoundry.project.io import Project

REVIEW_SYSTEM = (
    "You are the reviewer for QuestFoundry, a compiler that turns a premise into a "
    "branching interactive-fiction gamebook. Judge strictly against the given voice "
    "and beats and respond only in the requested JSON format."
)


# -- work queue ---------------------------------------------------------------


def reference_selection(project: Project) -> dict[str, str]:
    """Seeded, deterministic, author-overridable via `fill_seed` in
    project.yaml. FILL-local: no other stage may depend on it."""
    selections = queries.arc_selections(project.graph)
    return selections[project.fill_seed % len(selections)]


def writing_order(project: Project) -> list[str]:
    """Reference-arc passages first (in story order), then the rest."""
    g = project.graph
    view = queries.arc_view(g, reference_selection(project))
    topo = {b: i for i, b in enumerate(queries.topological_order(g) or [])}

    def story_position(passage: Passage) -> int:
        return min(topo[b] for b in queries.beats_of_passage(g, passage.id))

    ordered = sorted(g.nodes_of(Passage), key=story_position)
    on_reference = [
        p.id for p in ordered if set(queries.beats_of_passage(g, p.id)) <= view
    ]
    rest = [p.id for p in ordered if p.id not in set(on_reference)]
    return on_reference + rest


# -- pass 1: voice ------------------------------------------------------------


class VoiceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pov: str
    # the write prompt builds sentences around this value ("narrate in
    # {tense} tense"), so it must be exactly one of the two words the
    # prompt promises — an enum, per the A11 finite-set discipline
    # (Voice itself stays open for author-provided voice.yaml files)
    tense: Literal["past", "present"]
    diction: str
    rhythm: str
    # required here though Voice defaults them empty: the pass exists to
    # give the writer a palette, and a writer short on style guidance
    # copies whatever styled text is at hand (plan W3)
    imagery: str
    dialogue: str
    banned: list[str] = []
    notes: str = ""
    # the scheme's marked deviant register ("" when the scheme has none);
    # required so the pass decides explicitly rather than omitting
    interlude: str


def _voice_skip(project: Project) -> str | None:
    return "voice already locked" if project.voice is not None else None


def _voice_context(project: Project) -> dict:
    # The pov decision names a viewpoint character, so the prompt must show
    # the cast's exact spellings: a live gpt-oss:120b run copied the prompt
    # example's name ("Maren") over the real protagonist ("Marin") and every
    # later passage failed review on the name mismatch (prompt audit
    # follow-up, 2026-07-11).
    g = project.graph
    endings = [p.ending.title for p in g.nodes_of(Passage) if p.ending]
    cast = sorted(
        (
            e
            for e in g.nodes_of(Entity)
            if e.retained and e.category == EntityCategory.CHARACTER
        ),
        key=lambda e: e.id,
    )
    return {
        "vision": project.vision,
        "dilemmas": g.nodes_of(Dilemma),
        "endings": endings,
        "passage_count": len(g.nodes_of(Passage)),
        "cast": cast,
    }


# A limited POV names its viewpoint character in parentheses. A pronoun
# ("you"/"I"/…) is not a name — only a proper name must resolve to the cast.
_POV_PAREN_RE = re.compile(r"\(([^)]+)\)")
_POV_PRONOUNS = {"you", "i", "we", "he", "she", "they", "me", "us"}
# Common connective tokens in names ("The Sleeper", "Ada of the Marsh") that
# must not, alone, make two different names look like a match.
_NAME_STOPWORDS = {"the", "a", "an", "of", "de", "van", "von"}


def _name_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if t not in _NAME_STOPWORDS}


def _check_pov_names_the_cast(pov: str, project: Project) -> None:
    """The pov string names the viewpoint character, and every later passage
    and its review are held to it verbatim — so a wrong name poisons the
    whole stage (live gpt-oss:120b: the prompt example's "Maren" copied over
    the real "Marin", every passage failed review). The cast is a finite set
    in context; validate the coined name against it rather than trusting it."""
    match = _POV_PAREN_RE.search(pov)
    if not match:
        return
    named = match.group(1).strip().strip("'\"")
    if not named[:1].isupper() or named.lower() in _POV_PRONOUNS:
        return  # a pronoun / 'you' — not a character name
    names = [
        e.name
        for e in project.graph.nodes_of(Entity)
        if e.retained and e.category == EntityCategory.CHARACTER and e.name
    ]
    # Match on whole name tokens, not raw substrings: the cast stores full
    # names ("Maren Voss") and the pov may use the short form ("Maren"), so a
    # shared token is enough — but "Maren" must not match "Marin Voss" (the
    # bug), and a short cast name like "Ann" must not match a coined "Anna"
    # (the mirror bug: substring containment would, token equality does not).
    named_tokens = _name_tokens(named)
    cast_tokens = [_name_tokens(n) for n in names]
    if named_tokens and not any(named_tokens & toks for toks in cast_tokens):
        raise ApplyError(
            f"the POV names {named!r}, who is not a character in this story; a "
            "limited POV must name its viewpoint character with the exact cast "
            f"spelling — use one of: {sorted(names)}."
        )


def _check_interlude_names_the_cast(interlude: str, project: Project) -> None:
    """The interlude register always has a narrator (unlike a pronoun POV),
    so the parenthetical is REQUIRED here — without it the pov checker's
    no-parens early return would silently skip validation for exactly the
    format the prompt teaches (PR #74 review finding)."""
    names = sorted(
        e.name
        for e in project.graph.nodes_of(Entity)
        if e.retained and e.category == EntityCategory.CHARACTER and e.name
    )
    if not _POV_PAREN_RE.search(interlude):
        raise ApplyError(
            "the interlude names no narrator; add the narrator's cast name in "
            'parentheses, as the pov does — e.g. "first-person journal entries '
            f'(NAME)" with NAME one of: {names}.'
        )
    _check_pov_names_the_cast(interlude, project)


def _voice_apply(proposal: VoiceProposal, project: Project) -> list[str]:
    _check_pov_names_the_cast(proposal.pov, project)
    if proposal.interlude:
        _check_interlude_names_the_cast(proposal.interlude, project)
    project.voice = Voice(**proposal.model_dump())
    line = f"voice: {proposal.pov}; {proposal.tense}; {proposal.diction}"
    if proposal.interlude:
        line += f"; interlude: {proposal.interlude}"
    return [line]


# -- write passes -------------------------------------------------------------


class MicroDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    key: str
    value: str


class RevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # the finding this entry answers (quote or name it), and the specific
    # change made to resolve it. On a rework the writer fills one per finding.
    finding: str
    how_addressed: str


class WriteProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prose: str
    # at most one, and only on a genuine new fact or a sharper version of a
    # listed one — the write prompt frames adding as the exception, not an
    # obligation (author-directed micro-detail redesign, 2026-07-12): a
    # standing "up to 2" invitation made a capable model coin a re-observation
    # of the story's central object every scene and hard-fail the prose.
    micro_details: list[MicroDetail] = Field(default=[], max_length=1)
    # empty on the first attempt; on a rework the writer responds to each
    # finding here (author-directed, 2026-07-12; validated on gpt-oss:120b:
    # forcing the per-finding response lifts the group-1 beat fix from 2/4 to
    # 4/4 under multi-finding load). Reviewer-facing only — not applied, so
    # replay stays deterministic.
    revision_notes: list[RevisionResponse] = []


# The prose review's clause set (docs/plans/review-contract.md): the `rule`
# axis of every finding is pinned to exactly these, so a reviewer cannot cite
# a rule the contract does not carry (the live "fabricated a rule number"
# failure). One envelope, this stage's clauses.
FILL_REVIEW_RULES = (
    "voice_pov",
    "voice_tense",
    "banned_pattern",
    "beat_infidelity",
    "continuity",
    "state_dishonesty",
    "leakage",
    "pronoun",
    # the writer may add or update a micro-detail; the reviewer judges whether
    # it holds — a contradiction of an established fact is a defect, a
    # gratuitous restatement a concern (author-directed, 2026-07-12).
    "micro_detail",
)
FILL_REVIEW_SCHEMA = build_verdict_schema("FillReview", FILL_REVIEW_RULES)


def _gate_certain_flags(g, passage_id: str) -> set[str]:
    """Flags every arriving player provably holds: a beat of the passage
    requires them (gated residue beats), or every choice into the passage
    requires them (variant passages — their gate lives on the choice
    edge, not the shared beats)."""
    certain = {
        f
        for b in queries.beats_of_passage(g, passage_id)
        for f in g.node(b).requires_flags
    }
    in_choices = g.in_edges(passage_id, EdgeKind.CHOICE)
    if in_choices:
        certain |= set.intersection(
            *[set(e.payload.get("requires", [])) for e in in_choices]
        )
    return certain


def _flag_status(g, passage_id: str, flag: StateFlag) -> str:
    """certain (granted on every route here, or gating guarantees it),
    foreclosed (the other side committed upstream, or gating guarantees
    a rival path), or possible. Grant/commit beats are per world; one in
    the ancestry decides.

    Gate certainty propagates along the dilemma: a passage only holders
    of path P reach makes every one of P's flags certain and every rival
    path's flag foreclosed — without this, a residue or variant passage's
    own truth read as merely "possible" and the write prompt ordered the
    writer to stay neutral about the very fact the passage exists to
    carry (prompt audit, 2026-07-11)."""
    grants = queries.grant_beats(g, flag.id)
    if not grants or flag.path is None:
        return "possible"
    dilemma = queries.dilemma_of_path(g, flag.path)
    flag_paths = {fl.id: fl.path for fl in g.nodes_of(StateFlag)}
    gate_paths = {flag_paths.get(f) for f in _gate_certain_flags(g, passage_id)}
    if flag.path in gate_paths:
        return "certain"
    if gate_paths & (set(queries.explored_paths(g, dilemma)) - {flag.path}):
        return "foreclosed"
    beats = queries.beats_of_passage(g, passage_id)
    ancestry = set(beats)
    for b in beats:
        ancestry |= queries.ancestors(g, b)
    other_commits = [
        c
        for p in queries.explored_paths(g, dilemma)
        if p != flag.path
        for c in queries.commit_beats(g, p)
    ]
    if any(c in ancestry for c in grants):
        if any(c in ancestry for c in other_commits):
            return "possible"  # both sides upstream: a shared passage
        return "certain"
    if any(c in ancestry for c in other_commits):
        return "foreclosed"
    return "possible"


def _arc_positions(g, passage_id: str) -> list[dict]:
    """Per on-stage arced entity (POLISH's arcs pass): the aspect in
    play now, the turn this passage itself carries, where the entity is
    heading, and the landings of paths committed upstream. "Passed" is
    plain ancestry — the same convention flag certainty uses for
    grants; a pivot on a branch-only beat may read slightly early for
    readers who skirted it, which is acceptable for a pacing channel
    (WORLD STATE, not the arc, governs what may be asserted)."""
    passage = g.node(passage_id)
    beats = set(queries.beats_of_passage(g, passage_id))
    ancestry = set(beats)
    for b in beats:
        ancestry |= queries.ancestors(g, b)
    entries = []
    for eid in passage.entities:
        e = g.get(eid)
        if not isinstance(e, Entity) or e.arc is None:
            continue
        now, turn, heading = e.arc.begins, None, None
        for p in e.arc.pivots:
            if p.beat in beats:
                turn = p.becomes
            elif p.beat in ancestry:
                now = p.becomes
            elif heading is None and queries.ancestors(g, p.beat) & beats:
                heading = p.becomes
        ends = [
            pe.state
            for pe in e.arc.ends
            if any(c in ancestry for c in queries.commit_beats(g, pe.path))
        ]
        entries.append(
            {"entity": e, "now": now, "turn": turn, "heading": heading, "ends": ends}
        )
    return entries


def _shadows(g) -> list[dict]:
    result = []
    for d in sorted(g.nodes_of(Dilemma), key=lambda n: n.id):
        answers = []
        for a in queries.answers_of(g, d.id):
            node = g.node(a)
            assert isinstance(node, Answer)
            explored = bool(g.in_ids(a, EdgeKind.EXPLORES))
            answers.append({"text": node.text, "explored": explored})
        result.append({"dilemma": d, "answers": answers})
    return result


# Late in a long story a route's summaries still grow linearly; cap the
# block so deep scopes don't rebuy the token blow-up the summaries exist
# to avoid (a route is arc-length, ~40+ passages at `long`).
STORY_SO_FAR_MAX = 40


def _story_route(project: Project, passage_id: str) -> list[str]:
    """One deterministic route from the story's root to this passage,
    walking in-choice edges backwards: prefer a reference-arc
    predecessor, else the lowest passage id. Deterministic so prompt
    bytes are stable across resumes (cache replay)."""
    g = project.graph
    view = queries.arc_view(g, reference_selection(project))
    route: list[str] = []
    seen = {passage_id}
    current = passage_id
    while True:
        preds = sorted({e.src for e in g.in_edges(current, EdgeKind.CHOICE)} - seen)
        if not preds:
            break
        on_ref = [p for p in preds if set(queries.beats_of_passage(g, p)) <= view]
        current = (on_ref or preds)[0]
        seen.add(current)
        route.append(current)
    route.reverse()
    return route


def _story_so_far(project: Project, passage_id: str) -> tuple[list[str], int]:
    """Summaries along the route, oldest first, minus the direct
    predecessors (their full prose is the window). Returns the rendered
    list and the count elided by the cap."""
    g = project.graph
    window_ids = {e.src for e in g.in_edges(passage_id, EdgeKind.CHOICE)}
    entries = [
        g.node(p).prose_summary
        for p in _story_route(project, passage_id)
        if p not in window_ids and g.node(p).prose_summary
    ]
    elided = max(0, len(entries) - STORY_SO_FAR_MAX)
    return entries[elided:], elided


def _passage_head(g, passage_id: str) -> tuple[Entity | None, bool]:
    """The passage's viewpoint entity (resolved) and interlude mark —
    (None, False) when its beats carry no head (texture/bridge passages,
    pre-annotation projects): the write prompt then degrades to the
    book-wide Voice.pov rule."""
    beats = [g.node(b) for b in queries.beats_of_passage(g, passage_id)]
    vp = passage_viewpoint(beats)
    if vp.viewpoint is None:
        return None, False
    entity = g.get(vp.viewpoint)
    assert isinstance(entity, Entity)
    return entity, vp.interlude


def _neighbor_prose(g, passage_id: str, direction: str) -> list[dict]:
    edges = (
        g.in_edges(passage_id, EdgeKind.CHOICE)
        if direction == "in"
        else g.out_edges(passage_id, EdgeKind.CHOICE)
    )
    seen = []
    for e in edges:
        other_id = e.src if direction == "in" else e.dst
        other = g.node(other_id)
        assert isinstance(other, Passage)
        if other.prose:
            head, _ = _passage_head(g, other_id)
            seen.append(
                {
                    "passage": other,
                    "label": e.payload.get("label", ""),
                    # the neighbor's head, so the writer sees a switch and does
                    # not bleed the adjacent passage's interiority across it
                    "head": head.name if head else "",
                }
            )
    # Canonical order, not store order: choice edges reload from disk
    # grouped by source file, so store order differs between a live run
    # and a resumed one — a shifted window changes prompt bytes and
    # breaks cache replay (STATUS 2026-07-08). Parallel neighbors are
    # alternative branches with no narrative order to preserve.
    seen.sort(key=lambda n: (n["passage"].id, n["label"]))
    return seen


def _write_context_for(passage_id: str, last_draft: dict | None = None):
    def build(project: Project) -> dict:
        g = project.graph
        passage = g.node(passage_id)
        assert isinstance(passage, Passage)
        beats = [g.node(b) for b in queries.beats_of_passage(g, passage.id)]
        order = {b: i for i, b in enumerate(queries.topological_order(g) or [])}
        beats.sort(key=lambda b: order[b.id])
        flags = []
        for flag in sorted(g.nodes_of(StateFlag), key=lambda f: f.id):
            if flag.id in passage.irrelevant_flags:
                continue
            status = _flag_status(g, passage.id, flag)
            if status != "foreclosed":
                flags.append({"flag": flag, "status": status})
        entities = [
            g.node(e) for e in passage.entities if isinstance(g.get(e), Entity)
        ]
        intensity = passage_intensity(beats)
        lo, hi = project.vision.preset.words_for(
            intensity=intensity,
            ending=passage.ending is not None,
        )
        story_so_far, story_elided = _story_so_far(project, passage.id)
        viewpoint, interlude = _passage_head(g, passage.id)
        return {
            "vision": project.vision,
            "voice": project.voice,
            "passage": passage,
            "beats": beats,
            # THIS passage's head (a resolved character entity, or None when
            # no beat carries one — then the prompts fall back to the
            # book-wide Voice.pov rule) and whether it is an interlude in the
            # Voice's marked deviant register (rotating-pov-build.md)
            "viewpoint": viewpoint,
            "interlude": interlude,
            # the aggregate intensity sets the band; the per-beat map lets the
            # write/review prompts mark which beat may rise and which stays plain
            # (style belongs to the story, not the paragraph — PR #64, made
            # concrete per beat by scene_type)
            "intensity": intensity.value,
            "beat_scene": {b.id: effective_scene_type(b).value for b in beats},
            # per-beat POV/coda register — most beats limited (inside the Voice's
            # POV), a wide beat is a detached coda the writer may narrate beyond the
            # viewpoint character's horizon (design doc 01 §Beat annotations)
            "beat_scope": {b.id: effective_narration_scope(b).value for b in beats},
            "entities": entities,
            "arcs": _arc_positions(g, passage.id),
            "flags": flags,
            "shadows": _shadows(g),
            "story_so_far": story_so_far,
            "story_elided": story_elided,
            "window": _neighbor_prose(g, passage.id, "in"),
            "lookahead": _neighbor_prose(g, passage.id, "out"),
            "choices": [
                e.payload.get("label", "") for e in g.out_edges(passage.id, EdgeKind.CHOICE)
            ],
            "words_min": lo,
            "words_max": hi,
            # a mutable box the review fills with the rejected draft, so the
            # next rework round shows the writer what it already tried (the
            # adapter is stateless — a fresh call each round has no memory of
            # its prior attempt, which is how it re-derives a losing draft).
            "previous_draft": last_draft,
        }

    return build


def _resolve_entity(g, ref: str) -> str:
    """The id contract lives in the adapter's JSON instruction; engine-side
    only the provably unambiguous slug form is restored (parsing, not
    prediction — display names are rejected, see the STATUS decision log)."""
    return resolve_entity_ref(g, ref)


def _check_echoes(g, passage_id: str, prose: str) -> None:
    """The deterministic floor under the input-role framing (plan W1):
    a rendered fact performed verbatim, or a run lifted from adjacent
    prose, is the stamping failure live run 8 read at book scale."""
    passage = g.node(passage_id)
    for entity_id in passage.entities:
        entity = g.get(entity_id)
        if not isinstance(entity, Entity):
            continue
        facts = dict(entity.base)
        for o in entity.overlays:
            facts.update(o.details)
        for key, value in facts.items():
            if echo.contains_phrase(prose, value, echo.FACT_ECHO_TOKENS):
                raise ApplyError(
                    f'prose restates an established fact verbatim: "{value}" '
                    f"({entity_id}.{key}). Facts are constraints, not choreography — "
                    "the reader already knows this; keep it true in fresh words or "
                    "leave it in the background"
                )
    for direction in ("in", "out"):
        for w in _neighbor_prose(g, passage_id, direction):
            run = echo.longest_shared_run(
                prose, w["passage"].prose, echo.WINDOW_ECHO_TOKENS
            )
            if run:
                raise ApplyError(
                    f'prose repeats {w["passage"].id} verbatim: "{run}". Adjacent '
                    "prose is continuity, not a style template — the reader just "
                    "read those words; write fresh ones"
                )


def _write_apply_for(
    passage_id: str,
    prior_facts: dict[tuple[str, str], str | None] | None = None,
    last_draft: dict | None = None,
):
    prior_facts = {} if prior_facts is None else prior_facts

    def apply(proposal: WriteProposal, project: Project) -> list[str]:
        g = project.graph
        # Stash this draft for the next rework round BEFORE any check can
        # raise, so an apply-stage rejection (word budget, echo) shows the
        # writer what it wrote just as a review rejection does — otherwise the
        # writer re-derives blind and re-lands the same too-short/echoing draft
        # (live gpt-oss:120b: group-9 exhausted repairs 6 words under the band).
        # Harmless on success: the box is only read on a rework of this passage.
        if last_draft is not None:
            last_draft["prose"] = proposal.prose
        passage = g.node(passage_id)
        assert isinstance(passage, Passage)
        count = len(proposal.prose.split())
        # The word budget is no longer a hard apply gate: it is a graded review
        # finding (`_word_budget_finding`), because a near-miss with good prose
        # and a real reason ("this ending's voice is terse") beats a forced
        # rework or padding — the reviewer's confidence scales with distance,
        # so only a large miss blocks (author-directed, 2026-07-12). Runaway or
        # skimpy prose is still caught, just as a finding the engine weighs.
        _check_echoes(g, passage_id, proposal.prose)
        mutations.set_passage_prose(project.graph, passage_id, proposal.prose)
        lines = [f"{passage_id}: {count} words"]
        # A micro-detail is optional enrichment, never a blocker (author-
        # directed redesign, 2026-07-12): the only apply check is the note-form
        # length cap, and an over-long one is DROPPED, not repaired — a
        # too-long value is prose, and we simply do not store prose as a fact.
        # A same-key value UPDATES the fact (a sharper version); whether an
        # update is a legitimate refinement or a contradiction, and whether an
        # add genuinely adds, is the reviewer's `micro_detail` rule to judge.
        prior_facts.clear()
        for d in proposal.micro_details:
            entity_id = _resolve_entity(project.graph, d.entity)
            words = len(d.value.split())
            if words > echo.DETAIL_VALUE_MAX_WORDS:
                lines.append(
                    f"micro-detail dropped ({words} words > "
                    f"{echo.DETAIL_VALUE_MAX_WORDS}, not note form): {entity_id}.{d.key}"
                )
                continue
            # capture the value this update overwrites (None if a new key) so
            # the reviewer can compare proposed-vs-prior — apply mutates in
            # place, so the prior is otherwise gone by review time.
            entity = project.graph.node(entity_id)
            prior_facts[(entity_id, d.key)] = entity.base.get(d.key)
            mutations.add_entity_detail(project.graph, entity_id, d.key, d.value)
            lines.append(f"micro-detail: {entity_id}.{d.key} = {d.value}")
        return lines

    return apply


# -- summarize passes (the rolling story-so-far, plan W4) ---------------------

SUMMARY_MAX_WORDS = 60


class SummaryProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str


def _summary_context_for(passage_id: str):
    def build(project: Project) -> dict:
        passage = project.graph.node(passage_id)
        assert isinstance(passage, Passage)
        return {
            "passage": passage,
            "prose": passage.prose,
            "max_words": SUMMARY_MAX_WORDS,
        }

    return build


def _summary_apply_for(passage_id: str):
    def apply(proposal: SummaryProposal, project: Project) -> list[str]:
        count = len(proposal.summary.split())
        if count > SUMMARY_MAX_WORDS:
            raise ApplyError(
                f"story-so-far summary for {passage_id} is {count} words; the "
                f"cap is {SUMMARY_MAX_WORDS} — a note for later writers, not prose"
            )
        mutations.set_passage_prose_summary(project.graph, passage_id, proposal.summary)
        return [f"{passage_id}: story-so-far entry, {count} words"]

    return apply


# The word budget is a *graded* finding, not a binary gate (author-directed,
# 2026-07-12): confidence scales with how far the prose is outside the band, so
# a near-miss with a real reason is the writer's call, not a forced rework.
# Bands: inside [lo, hi] is clean; the 20% slack margin is a low warn (was
# silently accepted before); beyond the slack, the miss fails, low/medium/high
# by distance beyond the slack edge. Thresholds are one tunable knob.
_WB_WARN, _WB_MEDIUM = 0.15, 0.40


def _word_budget_finding(project: Project, passage_id: str, prose: str) -> ReviewFinding | None:
    g = project.graph
    passage = g.node(passage_id)
    beats = [g.node(b) for b in queries.beats_of_passage(g, passage_id)]
    lo, hi = project.vision.preset.words_for(
        intensity=passage_intensity(beats),
        ending=passage.ending is not None,
    )
    count = len(prose.split())
    if lo <= count <= hi:
        return None
    slack_lo, slack_hi = lo * 0.8, hi * 1.2
    if count < lo:
        recovery = (
            f"reach at least {lo} words by deepening a beat the draft rushed "
            "(name which beat you expand and what you add — do not pad)"
        )
        reason = f"the prose is {count} words, under the {lo}-{hi} target"
        beyond = (slack_lo - count) / slack_lo if count < slack_lo else 0.0
    else:
        recovery = f"tighten to at most {hi} words; cut the least load-bearing lines"
        reason = f"the prose is {count} words, over the {lo}-{hi} target"
        beyond = (count - slack_hi) / slack_hi if count > slack_hi else 0.0
    if beyond <= 0.0:  # inside the slack margin: a weighable concern, not a block
        assessment, confidence = "warn", "low"
    elif beyond <= _WB_WARN:
        assessment, confidence = "fail", "low"
    elif beyond <= _WB_MEDIUM:
        assessment, confidence = "fail", "medium"
    else:
        assessment, confidence = "fail", "high"
    return ReviewFinding(
        rule="word_budget", assessment=assessment, confidence=confidence,
        quote="", reason=reason, recovery_action=recovery,
    )


# The overwriting guardrail (docs/plans/reading-difficulty.md): coined-compound
# density is the one modulation red flag that survived a genre-diverse study with
# zero false positives — the two published-gamebook exemplars run 1.7-3.0/1k,
# every competent work measured <= 7.2, and the worst-read story 21.2. A graded
# finding beside word_budget: warn past ~8/1k, fail past ~15/1k, low/medium/high
# by distance beyond 15 — so an egregiously over-compounded passage blocks while a
# merely rich one is weighed. Fragmentation is deliberately NOT gated (it
# false-positives on good noir, Grimnoir 49%); the modulation-variance half of the
# guardrail is the B8 pacing report over scene_type. Thresholds are one knob.
_COMPOUND_RE = re.compile(r"[A-Za-z]+-[A-Za-z]+(?:-[A-Za-z]+)*")
_OW_WARN_PER_K, _OW_FAIL_PER_K = 8.0, 15.0
_OW_MEDIUM, _OW_HIGH = 0.15, 0.40
_OW_MIN_WORDS = 40  # below this a couple of compounds is not a density


def _overwriting_finding(prose: str) -> ReviewFinding | None:
    """Graded coined-compound density (per 1k words). Register-flat by
    design: 15/1k is ~3x the literary golden and ~5x the plain exemplars,
    so even a heightened scene passage has headroom before it blocks."""
    n = len(prose.split())
    if n < _OW_MIN_WORDS:
        return None
    compounds = _COMPOUND_RE.findall(prose)
    density = 1000 * len(compounds) / n
    if density <= _OW_WARN_PER_K:
        return None
    reason = (
        f"{len(compounds)} coined hyphen-compounds in {n} words (~{density:.0f}/1k); "
        "a readable gamebook runs under ~5/1k, and relentless coinage is the "
        "over-stylization that leaves the reader lost"
    )
    recovery = (
        "keep the one or two hyphen-compounds that carry real weight and say the "
        "rest in plain words — a specific noun beats a coined compound"
    )
    if density <= _OW_FAIL_PER_K:
        assessment, confidence = "warn", "low"
    else:
        beyond = (density - _OW_FAIL_PER_K) / _OW_FAIL_PER_K
        if beyond <= _OW_MEDIUM:
            assessment, confidence = "fail", "low"
        elif beyond <= _OW_HIGH:
            assessment, confidence = "fail", "medium"
        else:
            assessment, confidence = "fail", "high"
    return ReviewFinding(
        rule="overwriting", assessment=assessment, confidence=confidence,
        quote="", reason=reason, recovery_action=recovery,
    )


def _micro_review(g, proposal: WriteProposal, prior_facts: dict) -> list[dict]:
    """What the reviewer needs to judge each proposed micro-detail: the
    proposed value, the value it replaces (from `prior_facts`, captured before
    apply overwrote it — None for a new key), and the entity's OTHER
    established facts to check a contradiction against. Over-long details were
    dropped at apply, so they carry no review."""
    out = []
    for d in proposal.micro_details:
        if len(d.value.split()) > echo.DETAIL_VALUE_MAX_WORDS:
            continue
        entity_id = _resolve_entity(g, d.entity)
        entity = g.node(entity_id)
        prior = prior_facts.get((entity_id, d.key))
        out.append(
            {
                "entity": entity_id,
                "key": d.key,
                "value": d.value,
                "prior": prior,
                "is_update": prior is not None,
                "facts": {k: v for k, v in entity.base.items() if k != d.key},
            }
        )
    return out


def _review_for(
    passage_id: str, prior_facts: dict[tuple[str, str], str | None] | None = None
):
    prior_facts = {} if prior_facts is None else prior_facts
    # each round is anchored on what earlier rounds flagged: an amnesiac
    # reviewer samples fresh objections every round and never converges
    # (validation run, 2026-07-09) — persistence is signal, novelty is
    # usually taste
    prior: list[str] = []

    def review(proposal: WriteProposal, project: Project, adapter: Any) -> list[str]:
        from questfoundry.pipeline import runner

        # the engine's own mechanical findings (word budget; the overwriting
        # guardrail — coined-compound density) ride the same findings list as the
        # reviewer's — a confident mechanical defect blocks even when the LLM
        # approves the prose, but a near-miss is a low-confidence finding that does
        # not force a rework (author-directed, 2026-07-12).
        wb = _word_budget_finding(project, passage_id, proposal.prose)
        ow = _overwriting_finding(proposal.prose)
        mech = [f for f in (wb, ow) if f is not None]
        mech_blocks = any(is_blocking(f) for f in mech)

        def rendered_findings(v: Any) -> list[str]:
            # full fidelity for the writer (and the arbiter): the reviewer's
            # findings plus the mechanical ones (word_budget, overwriting).
            return [render_finding(f) for f in [*v.findings, *mech]]

        env = runner._environment()
        context = _write_context_for(passage_id)(project)
        micro_review = _micro_review(project.graph, proposal, prior_facts)
        verdict = adapter.complete(
            system=REVIEW_SYSTEM,
            prompt=env.get_template("fill_review.j2").render(
                **context,
                prose=proposal.prose,
                micro_review=micro_review,
                revision_notes=proposal.revision_notes,
                prior_issues=list(prior),
                arbitration=None,
            ),
            schema=FILL_REVIEW_SCHEMA,
            role="utility",
        )
        # approved auto-accepts and a needs_work verdict gates on confident
        # objective defects only (review-contract); accept iff neither the
        # reviewer's findings nor a confident mechanical finding (word_budget,
        # overwriting) block.
        if not evaluate_review(verdict) and not mech_blocks:
            return []
        active = verdict
        # a persistent *reviewer* dispute escalates once to an architect arbiter,
        # shown the full finding set it rules on (mechanical findings included). A
        # mechanical-only block is deterministic — an arbiter cannot overturn it —
        # so it does not spend the frontier call (tiering policy: escalate only
        # what a stronger judge can actually change).
        if prior and evaluate_review(verdict):
            final = adapter.complete(
                system=REVIEW_SYSTEM,
                prompt=env.get_template("fill_review.j2").render(
                    **context,
                    prose=proposal.prose,
                    micro_review=micro_review,
                    revision_notes=proposal.revision_notes,
                    prior_issues=list(prior),
                    arbitration=rendered_findings(verdict),
                ),
                schema=FILL_REVIEW_SCHEMA,
                role="architect",
            )
            if not evaluate_review(final) and not mech_blocks:
                return []
            active = final
        # rework: hand the writer every finding, full fidelity (the rejected
        # draft itself is stashed by _write_apply_for, which runs before review).
        issues = rendered_findings(active)
        prior.extend(issues)
        return issues

    return review


def _passes(project: Project) -> tuple[PassSpec, ...]:
    specs: list[PassSpec] = [
        PassSpec(
            name="voice",
            role="writer",
            template="fill_voice.j2",
            schema=VoiceProposal,
            build_context=_voice_context,
            apply=_voice_apply,
            skip_if=_voice_skip,
        )
    ]
    # The retained entity set is fixed for all of FILL, so pin
    # `micro_details[].entity` to it once and share across write passes
    # (pipeline/refpin.py).
    write_schema = pin(
        WriteProposal, "WriteProposal", {("MicroDetail", "entity"): entity_ref_ids(project.graph)}
    )
    for passage_id in writing_order(project):
        slug = passage_id.split(":", 1)[1]
        # A micro-detail may UPDATE a fact, so apply overwrites base before the
        # review runs (mutations are the sole replay path — they cannot move
        # into review). This box carries the pre-apply value of each touched
        # key from apply to review, so the reviewer's `micro_detail` rule can
        # compare the proposed value against the fact it replaces (PR #59
        # review findings); shared per passage, repopulated each apply round.
        prior_facts: dict[tuple[str, str], str | None] = {}
        # carries the rejected draft from the review of one round into the
        # write prompt of the next, per passage (rework-convergence lever).
        last_draft: dict = {"prose": None}
        specs.append(
            PassSpec(
                name=f"write:{slug}",
                role="writer",
                template="fill_write.j2",
                schema=write_schema,
                build_context=_write_context_for(passage_id, last_draft),
                apply=_write_apply_for(passage_id, prior_facts, last_draft),
                review=_review_for(passage_id, prior_facts),
            )
        )
        # the rolling story-so-far entry rides right behind the accepted
        # prose, so every later write pass can read the route in notes
        # instead of re-buying a deep prose look-back (plan W4)
        specs.append(
            PassSpec(
                name=f"summarize:{slug}",
                role="utility",
                template="fill_summary.j2",
                schema=SummaryProposal,
                build_context=_summary_context_for(passage_id),
                apply=_summary_apply_for(passage_id),
            )
        )
    return tuple(specs)


def _fill_gate(project: Project) -> list[Issue]:
    issues = run_checks(project.graph, project.vision, Stage.FILL)
    if project.voice is None:
        issues.append(
            Issue("G5", Severity.ERROR, "no voice record — FILL must lock the voice first")
        )
    return issues


FILL_STAGE = StageImpl(stage=Stage.FILL, passes=_passes, gate=_fill_gate)
