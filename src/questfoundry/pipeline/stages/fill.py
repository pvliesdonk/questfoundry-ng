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

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import Issue, Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import Voice
from questfoundry.models.drama import Answer, Dilemma
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import StateFlag
from questfoundry.models.world import Entity
from questfoundry.pipeline.refpin import entity_ref_ids, pin
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
    rhythm: str = ""
    banned: list[str] = []
    notes: str = ""


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
    from questfoundry.models.world import EntityCategory

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


def _voice_apply(proposal: VoiceProposal, project: Project) -> list[str]:
    project.voice = Voice(**proposal.model_dump())
    return [f"voice: {proposal.pov}; {proposal.tense}; {proposal.diction}"]


# -- write passes -------------------------------------------------------------


class MicroDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    key: str
    value: str


class WriteProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prose: str
    micro_details: list[MicroDetail] = []


class ReviewVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["pass", "fail"]
    issues: list[str] = []


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
            seen.append({"passage": other, "label": e.payload.get("label", "")})
    # Canonical order, not store order: choice edges reload from disk
    # grouped by source file, so store order differs between a live run
    # and a resumed one — a shifted window changes prompt bytes and
    # breaks cache replay (STATUS 2026-07-08). Parallel neighbors are
    # alternative branches with no narrative order to preserve.
    seen.sort(key=lambda n: (n["passage"].id, n["label"]))
    return seen


def _write_context_for(passage_id: str):
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
        lo, hi = project.vision.preset.words_for(
            texture=all(b.is_texture for b in beats),
            ending=passage.ending is not None,
        )
        return {
            "vision": project.vision,
            "voice": project.voice,
            "passage": passage,
            "beats": beats,
            "entities": entities,
            "flags": flags,
            "shadows": _shadows(g),
            "window": _neighbor_prose(g, passage.id, "in"),
            "lookahead": _neighbor_prose(g, passage.id, "out"),
            "choices": [
                e.payload.get("label", "") for e in g.out_edges(passage.id, EdgeKind.CHOICE)
            ],
            "words_min": lo,
            "words_max": hi,
        }

    return build


def _resolve_entity(g, ref: str) -> str:
    """The id contract lives in the adapter's JSON instruction; engine-side
    only the provably unambiguous slug form is restored (parsing, not
    prediction — display names are rejected, see the STATUS decision log)."""
    return resolve_entity_ref(g, ref)


def _write_apply_for(passage_id: str):
    def apply(proposal: WriteProposal, project: Project) -> list[str]:
        g = project.graph
        passage = g.node(passage_id)
        assert isinstance(passage, Passage)
        beats = [g.node(b) for b in queries.beats_of_passage(g, passage_id)]
        lo, hi = project.vision.preset.words_for(
            texture=bool(beats) and all(b.is_texture for b in beats),
            ending=passage.ending is not None,
        )
        count = len(proposal.prose.split())
        # models cannot hit exact word windows: the band catches runaway
        # or skimpy prose, the review pass owns quality — repair only
        # beyond 20% slack; the exact preset range stays the prompt's
        # target and B5's advisory line
        if not lo * 0.8 <= count <= hi * 1.2:
            raise ApplyError(
                f"prose for {passage_id} is {count} words; the budget is {lo}-{hi}"
            )
        mutations.set_passage_prose(project.graph, passage_id, proposal.prose)
        lines = [f"{passage_id}: {count} words"]
        for d in proposal.micro_details:
            entity_id = _resolve_entity(project.graph, d.entity)
            mutations.add_entity_detail(project.graph, entity_id, d.key, d.value)
            lines.append(f"micro-detail: {entity_id}.{d.key} = {d.value}")
        return lines

    return apply


def _review_for(passage_id: str):
    # each round is anchored on what earlier rounds flagged: an amnesiac
    # reviewer samples fresh objections every round and never converges
    # (validation run, 2026-07-09) — persistence is signal, novelty is
    # usually taste
    prior: list[str] = []

    def review(proposal: WriteProposal, project: Project, adapter: Any) -> list[str]:
        from questfoundry.pipeline import runner

        env = runner._environment()
        context = _write_context_for(passage_id)(project)
        rendered = env.get_template("fill_review.j2").render(
            **context, prose=proposal.prose, prior_issues=list(prior), arbitration=None
        )
        verdict = adapter.complete(
            system=REVIEW_SYSTEM,
            prompt=rendered,
            schema=ReviewVerdict,
            role="utility",
        )
        if verdict.verdict != "fail":
            return []
        issues = verdict.issues or ["review failed without stating an issue"]
        if prior:
            # second strike halts the stage — but every halt so far has
            # been the cheap reviewer sampling taste, not structure. One
            # architect-tier arbitration breaks the tie (tiering policy:
            # escalate rather than improvise); its verdict is final.
            arb = env.get_template("fill_review.j2").render(
                **context,
                prose=proposal.prose,
                prior_issues=list(prior),
                arbitration=issues,
            )
            final = adapter.complete(
                system=REVIEW_SYSTEM,
                prompt=arb,
                schema=ReviewVerdict,
                role="architect",
            )
            if final.verdict != "fail":
                return []
            issues = final.issues or issues
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
        specs.append(
            PassSpec(
                name=f"write:{passage_id.split(':', 1)[1]}",
                role="writer",
                template="fill_write.j2",
                schema=write_schema,
                build_context=_write_context_for(passage_id),
                apply=_write_apply_for(passage_id),
                review=_review_for(passage_id),
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
