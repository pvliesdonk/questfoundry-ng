"""FILL: the seeded reference-arc queue, flag-status computation, word
budgets, and the review hook riding the runner's repair loop."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from questfoundry.models.concept import Voice
from questfoundry.pipeline.review import ReviewFinding, ReviewVerdict
from questfoundry.pipeline.stages.fill import (
    VoiceProposal,
    WriteProposal,
    _fill_gate,
    _flag_status,
    _passes,
    _review_for,
    _voice_apply,
    _write_apply_for,
    _write_context_for,
    reference_selection,
    writing_order,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project import load_project
from questfoundry.project.io import Project
from tests.conftest import GOLDEN


def _finding(
    reason: str, *, assessment: str = "fail", confidence: str = "high"
) -> ReviewFinding:
    return ReviewFinding(
        rule="beat_infidelity",
        assessment=assessment,
        confidence=confidence,
        quote="the offending line",
        reason=reason,
        recovery_action="rewrite it",
    )


def _verdict(*findings: ReviewFinding) -> ReviewVerdict:
    # empty = a clean "approved"; any finding = "needs_work" (the engine still
    # decides whether it blocks)
    verdict = "needs_work" if findings else "approved"
    return ReviewVerdict(verdict=verdict, findings=list(findings))


@pytest.fixture()
def golden_fill() -> Project:
    return load_project(GOLDEN)


def test_reference_arc_is_seeded_and_local(golden_fill):
    first = reference_selection(golden_fill)
    golden_fill.fill_seed = 1
    second = reference_selection(golden_fill)
    assert first != second  # the seed genuinely selects a different arc
    assert set(first) == {"dilemma:bargain", "dilemma:truth"}


def test_writing_order_is_reference_arc_first(golden_fill):
    order = writing_order(golden_fill)
    assert len(order) == 9
    selection = reference_selection(golden_fill)
    from questfoundry.graph import queries

    view = queries.arc_view(golden_fill.graph, selection)
    on_ref = [
        p
        for p in order
        if set(queries.beats_of_passage(golden_fill.graph, p)) <= view
    ]
    # every reference passage precedes every off-reference passage
    assert order[: len(on_ref)] == on_ref
    assert order[0] == "passage:p-arrival"


def test_flag_status_certain_possible_foreclosed(golden_fill):
    g = golden_fill.graph
    flag = g.node("flag:elias-knows")
    assert _flag_status(g, "passage:p-counsel", flag) == "certain"
    assert _flag_status(g, "passage:p-lamp-room", flag) == "certain"
    assert _flag_status(g, "passage:p-fair-weather", flag) == "foreclosed"
    assert _flag_status(g, "passage:p-tremor", flag) == "possible"
    assert _flag_status(g, "passage:p-arrival", flag) == "possible"


def test_flag_status_gate_forecloses_the_rival_path(golden_fill):
    """A gated residue passage sits at a convergence — both commits are
    upstream, so ancestry alone reads the rival path's flag as possible.
    But only holders of the gate's path arrive: the rival is settled, and
    calling it possible ordered the writer (and the review's rule 4) to
    stay neutral about a fact the passage exists to carry (prompt audit,
    2026-07-11)."""
    g = golden_fill.graph
    # p-unspoken is gated on flag:lie-between (path:hide); the tell path's
    # flag cannot hold there
    assert _flag_status(g, "passage:p-unspoken", g.node("flag:elias-knows")) == "foreclosed"
    # p-counsel is the tell-side arm (gated on flag:elias-knows)
    assert _flag_status(g, "passage:p-counsel", g.node("flag:lie-between")) == "foreclosed"


def test_flag_status_choice_gate_makes_a_variant_certain(golden_fill):
    """A variant passage's gate lives on its choice edges, not its
    (shared) beats: every way in requires the flag, so it is certain
    there — and the same dilemma's rival path is foreclosed. Simulated by
    moving p-unspoken's gate from its beat onto its incoming choices."""
    from questfoundry.models.base import EdgeKind

    g = golden_fill.graph
    g.node("beat:unspoken").requires_flags = []
    for e in g.edges:
        if e.kind == EdgeKind.CHOICE and e.dst == "passage:p-unspoken":
            e.payload["requires"] = ["flag:lie-between"]
    assert _flag_status(g, "passage:p-unspoken", g.node("flag:lie-between")) == "certain"
    assert _flag_status(g, "passage:p-unspoken", g.node("flag:elias-knows")) == "foreclosed"


def _arrival_band(golden_fill):
    from questfoundry.graph import queries
    from questfoundry.models.structure import passage_intensity

    g = golden_fill.graph
    pg = g.node("passage:p-arrival")
    beats = [g.node(b) for b in queries.beats_of_passage(g, "passage:p-arrival")]
    return golden_fill.vision.preset.words_for(
        intensity=passage_intensity(beats), ending=pg.ending is not None
    )


def test_word_budget_is_no_longer_a_hard_apply_gate(golden_fill):
    """Author-directed (2026-07-12): the word budget is a graded review
    finding, not a binary ApplyError — a near-miss with good prose beats a
    forced rework or padding. Apply stores even a too-short draft."""
    apply = _write_apply_for("passage:p-arrival")
    lines = apply(WriteProposal(prose="far too short"), golden_fill)
    assert any("p-arrival" in ln for ln in lines)


def test_word_budget_finding_grades_by_distance(golden_fill):
    """Confidence scales with how far outside the band the prose is: in-band is
    clean, the slack margin a non-blocking warn, a near-miss a low fail
    (accepted), a large miss a high fail (blocks)."""
    from questfoundry.pipeline.review import ReviewVerdict, needs_rework
    from questfoundry.pipeline.stages.fill import _word_budget_finding

    lo, hi = _arrival_band(golden_fill)

    def wb(n):
        return _word_budget_finding(golden_fill, "passage:p-arrival", "w " * n)

    assert wb((lo + hi) // 2) is None  # in band
    assert wb(int(lo * 0.9)).assessment == "warn"  # slack margin: weighable
    near = wb(int(lo * 0.8) - max(1, int(lo * 0.8 * 0.05)))  # ~5% beyond slack (group-9)
    assert near.rule == "word_budget" and near.assessment == "fail" and near.confidence == "low"
    assert needs_rework(ReviewVerdict(verdict="needs_work", findings=[near])) is False
    far = wb(lo // 4)  # far short
    assert far.assessment == "fail" and far.confidence == "high"
    assert needs_rework(ReviewVerdict(verdict="needs_work", findings=[far])) is True


def test_write_context_carries_the_contract(golden_fill):
    golden_fill.voice = golden_fill.voice or Voice(
        pov="third", tense="present", diction="spare"
    )
    ctx = _write_context_for("passage:p-tremor")(golden_fill)
    assert ctx["voice"] is golden_fill.voice
    assert [b.id for b in ctx["beats"]] == [
        "beat:tremor",
        "beat:returned-boat",
        "beat:inherited-watch",
        "beat:offer",
    ]
    # the truth flags are merely possible here — the prose must stay honest
    statuses = {f["flag"].id: f["status"] for f in ctx["flags"]}
    assert statuses["flag:elias-knows"] == "possible"
    assert len(ctx["choices"]) == 5
    assert ctx["words_min"] == 150 and ctx["words_max"] == 450


def test_review_hook_translates_verdicts(golden_fill, monkeypatch):
    class FakeAdapter:
        def __init__(self, verdict):
            self.verdict = verdict
            self.seen = ""

        def complete(self, *, system, prompt, schema, role):
            assert role == "utility"
            self.seen = prompt
            return self.verdict

    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner

    env = Environment(
        loader=DictLoader(
            {"fill_review.j2": "review {{ passage.id }} prior[{{ prior_issues | join(';') }}]"}
        )
    )
    monkeypatch.setattr(runner, "_environment", lambda: env)
    review = _review_for("passage:p-arrival")
    proposal = WriteProposal(prose="x " * 200)
    # an empty findings list accepts; so does a warn-only or a low-confidence
    # verdict — the engine loops only on confident objective defects
    assert review(proposal, golden_fill, FakeAdapter(_verdict())) == []
    warn = _verdict(_finding("taste", assessment="warn"))
    assert review(proposal, golden_fill, FakeAdapter(warn)) == []
    low = _verdict(_finding("reach", confidence="low"))
    assert review(proposal, golden_fill, FakeAdapter(low)) == []
    # an explicit "approved" auto-accepts even if a fail finding slipped in
    approved = ReviewVerdict(verdict="approved", findings=[_finding("ignored")])
    assert review(proposal, golden_fill, FakeAdapter(approved)) == []
    # a high-confidence fail reworks; the returned string is the rendered
    # finding (labels + quote + recovery), carrying the reviewer's reason
    bad = review(proposal, golden_fill, FakeAdapter(_verdict(_finding("voice drift"))))
    assert len(bad) == 1 and "voice drift" in bad[0] and "FAIL" in bad[0]
    # round two is anchored: the earlier round's finding reaches the prompt,
    # so persistence — not fresh taste — is what the reviewer judges
    # (validation run, 2026-07-09: an amnesiac reviewer found brand-new
    # complaints every round and never converged)
    adapter = FakeAdapter(_verdict())
    review(proposal, golden_fill, adapter)
    assert "voice drift" in adapter.seen


def test_double_fail_escalates_to_architect_arbitration(golden_fill, monkeypatch):
    """Every stage halt so far has been the utility reviewer sampling
    taste, never real structural wrongness (validation run, 2026-07-09).
    A second failure escalates once to an architect-tier arbitration
    whose verdict is final — pass accepts the prose, fail halts for real."""
    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner

    class ScriptedAdapter:
        def __init__(self, script):
            self.script = list(script)
            self.prompts: list[tuple[str, str]] = []

        def complete(self, *, system, prompt, schema, role):
            expected_role, verdict = self.script.pop(0)
            assert role == expected_role
            self.prompts.append((role, prompt))
            return verdict

    env = Environment(
        loader=DictLoader(
            {"fill_review.j2": "{% if arbitration %}ARB[{{ arbitration | join(';') }}]{% endif %}r"}
        )
    )
    monkeypatch.setattr(runner, "_environment", lambda: env)
    proposal = WriteProposal(prose="x " * 200)

    # arbitration overturns the second strike: prose accepted
    review = _review_for("passage:p-arrival")
    adapter = ScriptedAdapter(
        [
            ("utility", _verdict(_finding("real defect"))),
            ("utility", _verdict(_finding("fresh taste"))),
            ("architect", _verdict()),
        ]
    )
    assert "real defect" in review(proposal, golden_fill, adapter)[0]
    assert review(proposal, golden_fill, adapter) == []
    assert adapter.prompts[-1][0] == "architect"
    # the arbiter sees the second-strike finding, rendered
    assert "ARB[" in adapter.prompts[-1][1] and "fresh taste" in adapter.prompts[-1][1]

    # arbitration upholds: the halt is real and carries the arbiter's finding
    review = _review_for("passage:p-arrival")
    adapter = ScriptedAdapter(
        [
            ("utility", _verdict(_finding("real defect"))),
            ("utility", _verdict(_finding("still broken"))),
            ("architect", _verdict(_finding("confirmed: still broken"))),
        ]
    )
    assert "real defect" in review(proposal, golden_fill, adapter)[0]
    assert "confirmed: still broken" in review(proposal, golden_fill, adapter)[0]


def test_word_budget_only_block_reworks_without_spending_arbitration(golden_fill, monkeypatch):
    """A word_budget-only block is deterministic — an architect cannot overturn
    it — so a second strike must NOT spend the frontier arbitration call
    (PR #61 review)."""
    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner

    class Scripted:
        def __init__(self, script):
            self.script = list(script)
            self.roles: list[str] = []

        def complete(self, *, system, prompt, schema, role):
            self.roles.append(role)
            return self.script.pop(0)

    env = Environment(loader=DictLoader({"fill_review.j2": "r"}))
    monkeypatch.setattr(runner, "_environment", lambda: env)
    review = _review_for("passage:p-arrival")
    too_short = WriteProposal(prose="w " * 5)  # far under the band → confident word_budget fail
    # the LLM approves both rounds; only the mechanical word budget blocks
    adapter = Scripted([_verdict(), _verdict()])  # two utility calls, NO architect scripted
    assert any("word_budget" in i for i in review(too_short, golden_fill, adapter))
    assert any("word_budget" in i for i in review(too_short, golden_fill, adapter))  # 2nd strike
    assert adapter.roles == ["utility", "utility"]  # no architect call was spent


def test_arbitration_render_includes_the_word_budget_finding(golden_fill, monkeypatch):
    """When a persistent reviewer dispute DOES escalate, the architect is shown
    the full finding set it rules on — word_budget included, not just the LLM's
    own findings (PR #61 review)."""
    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner

    class Scripted:
        def __init__(self, script):
            self.script = list(script)
            self.prompts: list[tuple[str, str]] = []

        def complete(self, *, system, prompt, schema, role):
            expected_role, verdict = self.script.pop(0)
            assert role == expected_role
            self.prompts.append((role, prompt))
            return verdict

    env = Environment(
        loader=DictLoader(
            {"fill_review.j2": "{% if arbitration %}ARB[{{ arbitration | join(';') }}]{% endif %}r"}
        )
    )
    monkeypatch.setattr(runner, "_environment", lambda: env)
    review = _review_for("passage:p-arrival")
    too_short = WriteProposal(prose="w " * 5)
    adapter = Scripted(
        [
            ("utility", _verdict(_finding("real defect"))),
            ("utility", _verdict(_finding("still disputed"))),
            ("architect", _verdict()),  # architect clears the prose dispute...
        ]
    )
    review(too_short, golden_fill, adapter)
    out = review(too_short, golden_fill, adapter)  # second strike escalates
    assert adapter.prompts[-1][0] == "architect"
    assert "word_budget" in adapter.prompts[-1][1]  # arbiter is shown the finding
    assert any("word_budget" in i for i in out)  # ...but the mechanical miss still blocks


def test_fill_pass_list_is_voice_plus_write_and_summarize_per_passage(golden_fill):
    passes = _passes(golden_fill)
    assert passes[0].name == "voice"
    assert passes[0].skip_if is not None
    assert passes[0].skip_if(golden_fill)  # golden already carries a voice
    write_passes = [p for p in passes[1:] if p.name.startswith("write:")]
    summarize_passes = [p for p in passes[1:] if p.name.startswith("summarize:")]
    assert len(write_passes) == 9 and len(summarize_passes) == 9
    assert all(p.review is not None for p in write_passes)
    # each summary rides right behind its write pass, at utility tier
    names = [p.name for p in passes[1:]]
    assert all(
        names[i + 1] == "summarize:" + n.split(":", 1)[1]
        for i, n in enumerate(names)
        if n.startswith("write:")
    )
    assert all(p.role == "utility" and p.review is None for p in summarize_passes)


def test_gate_requires_voice(golden_fill):
    golden_fill.voice = None
    issues = _fill_gate(golden_fill)
    assert any("no voice record" in i.message for i in issues)


def test_voice_prompt_shows_the_cast_and_plants_no_example_name(golden_fill):
    """The pov decision names a viewpoint character, so the prompt must show
    the cast's exact spellings — and must not carry a concrete example name
    for it: a live gpt-oss:120b run copied the example's "(Maren)" over the
    real protagonist "Marin", and every later passage failed review on the
    name mismatch (prompt audit follow-up, 2026-07-11)."""
    from questfoundry.pipeline import runner
    from questfoundry.pipeline.stages.fill import _voice_context

    context = _voice_context(golden_fill)
    assert [e.name for e in context["cast"]] == ["Elias Wren", "Maren Voss", "The Sleeper"]
    rendered = runner._environment().get_template("fill_voice.j2").render(
        **context, notes="", repair_errors=[], research=""
    )
    assert "THE CAST" in rendered
    assert "Maren" in rendered  # from the cast list, the only legitimate source
    source = (runner.PROMPTS_DIR / "fill_voice.j2").read_text(encoding="utf-8")
    assert "limited (NAME)" in source and "(Maren)" not in source


def test_voice_pov_name_is_validated_against_the_cast(golden_fill):
    """The prompt-quality sweep: the pov name is now enforced, not merely
    trusted (the Maren-over-Marin bug). A limited POV naming a non-cast
    character is a repairable ApplyError; the short form of a real cast name
    passes, and a pronoun POV is not name-checked."""
    from questfoundry.pipeline import ApplyError
    from questfoundry.pipeline.stages.fill import _check_pov_names_the_cast

    # golden cast: "Elias Wren", "Maren Voss", "The Sleeper"
    _check_pov_names_the_cast("third person limited (Maren)", golden_fill)  # short form OK
    _check_pov_names_the_cast("third person limited (Elias Wren)", golden_fill)  # full name OK
    _check_pov_names_the_cast("second person ('you')", golden_fill)  # pronoun — not checked
    with pytest.raises(ApplyError, match="not a character"):
        _check_pov_names_the_cast("third person limited (Nadia)", golden_fill)
    # token matching, not substring: a coined name must not pass merely because
    # a real name is a substring of it (the mirror of the Maren/Marin bug).
    with pytest.raises(ApplyError, match="not a character"):
        _check_pov_names_the_cast("third person limited (Marenda)", golden_fill)


def test_pov_name_check_token_match_avoids_short_name_false_positive(tmp_path):
    """A short cast name ('Ada') must not validate a coined 'Adam' for a
    different character — substring containment would, token equality does
    not (the review's short-name mirror bug)."""
    from questfoundry.graph import mutations
    from questfoundry.graph.store import StoryGraph
    from questfoundry.models.base import Stage
    from questfoundry.models.concept import Vision
    from questfoundry.models.world import Entity
    from questfoundry.pipeline import ApplyError
    from questfoundry.pipeline.stages.fill import _check_pov_names_the_cast
    from questfoundry.project.io import Project

    g = StoryGraph()
    # category is derived from the id's kind prefix (character:…)
    mutations.add_entity(
        g, Entity(id="character:ada", created_by=Stage.BRAINSTORM, name="Ada", concept="c")
    )
    vision = Vision(premise="p", genre="g", tone="t")
    project = Project(root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g)
    _check_pov_names_the_cast("third person limited (Ada)", project)  # the real character
    with pytest.raises(ApplyError, match="not a character"):
        _check_pov_names_the_cast("third person limited (Adam)", project)


def _diamond_graph(reverse_wiring: bool):
    """A fork into two prose-bearing passages converging on a fourth,
    wired through the mutation layer in either order."""
    from questfoundry.graph import mutations
    from questfoundry.graph.store import StoryGraph
    from questfoundry.models.base import Stage
    from questfoundry.models.presentation import Choice, Passage
    from tests.conftest import make_dilemma, narrative_beat

    g = StoryGraph()
    d, pa, _pb = make_dilemma(g, "d")
    for slug in ("start", "left", "right", "join"):
        mutations.add_beat(g, narrative_beat(slug, d), [pa])
        mutations.add_passage(
            g,
            Passage(id=f"passage:p-{slug}", created_by=Stage.POLISH, summary=slug),
            [f"beat:{slug}"],
        )
    branches = ["passage:p-left", "passage:p-right"]
    if reverse_wiring:
        branches.reverse()
    for branch in branches:
        mutations.add_choice(g, "passage:p-start", branch, Choice(label=f"to {branch}"))
        mutations.add_choice(g, branch, "passage:p-join", Choice(label=f"via {branch}"))
        mutations.set_passage_prose(g, branch, f"prose of {branch}")
    return g


def test_window_order_is_canonical_not_wiring_order():
    """Crash-resume replay (STATUS, 2026-07-08): a reloaded project
    rebuilds choice edges grouped by source file, not in wiring order,
    so any store-order dependence in the write context shifts prompt
    bytes and invalidates the call cache on resume. The window must
    come out identical however the edges were inserted."""
    from questfoundry.pipeline.stages.fill import _neighbor_prose

    windows = [
        _neighbor_prose(_diamond_graph(rev), "passage:p-join", "in") for rev in (False, True)
    ]
    assert [n["passage"].id for n in windows[0]] == [n["passage"].id for n in windows[1]]
    assert windows[0] == windows[1]


def test_write_context_survives_a_save_load_round_trip(tmp_path, vision):
    """The stronger form: the write context built from the live in-memory
    graph must equal the one built after save + reload, or resuming a
    crashed FILL re-spends the cache. Wiring order is deliberately the
    reverse of filename order so the reload genuinely reorders edges."""
    from questfoundry.models.base import Stage
    from questfoundry.project.io import save_project

    project = Project(
        root=tmp_path, name="t", stage=Stage.FILL, vision=vision,
        graph=_diamond_graph(reverse_wiring=True),
    )
    # p-join exercises the window (two in-edges); p-start exercises
    # lookahead and choices (two out-edges).
    builders = [_write_context_for(p) for p in ("passage:p-join", "passage:p-start")]
    before = [b(project) for b in builders]
    save_project(project)
    reloaded = load_project(tmp_path)
    after = [b(reloaded) for b in builders]
    for b, a in zip(before, after, strict=True):
        for key in ("window", "lookahead", "choices"):
            assert b[key] == a[key], key
        assert [x.id for x in b["beats"]] == [x.id for x in a["beats"]]
    assert len(before[0]["window"]) == 2 and len(before[1]["choices"]) == 2


def test_micro_detail_entity_resolves_ids_and_slugs_only(golden_fill):
    """Id-contract decision (STATUS, 2026-07-08): the adapter states the
    contract once; the engine restores only the unambiguous slug form.
    Display names are rejected — fuzzy acceptance converts loud failures
    into quiet wrong answers."""
    from questfoundry.pipeline.stages.fill import _resolve_entity

    g = golden_fill.graph
    assert _resolve_entity(g, "character:keeper") == "character:keeper"
    assert _resolve_entity(g, "keeper") == "character:keeper"
    with pytest.raises(ApplyError, match="use one of"):
        _resolve_entity(g, g.node("character:keeper").name)
    with pytest.raises(ApplyError, match="use one of"):
        _resolve_entity(g, "Nobody Anyone Knows")


# -- echo checks (plan: docs/plans/prose-quality.md W1) ------------------------


def _padded(prose: str, words: int = 200) -> str:
    return prose + " " + "filler " * words


def test_fact_echo_fails_apply(golden_fill):
    """Live run 8's stamp: a rendered fact performed verbatim. Elias's
    base appearance is on stage in p-arrival; restating it fails the
    apply with the constraints-not-choreography framing."""
    apply = _write_apply_for("passage:p-arrival")
    fact = golden_fill.graph.node("character:cartographer").base["appearance"]
    with pytest.raises(ApplyError, match="restates an established fact"):
        apply(WriteProposal(prose=_padded(f"He arrives, all {fact}, smiling.")), golden_fill)


def test_fact_echo_allows_fresh_wording(golden_fill):
    apply = _write_apply_for("passage:p-arrival")
    apply(
        WriteProposal(prose=_padded("His cuffs carry old ink; the beard is going grey.")),
        golden_fill,
    )


def test_window_echo_fails_apply(golden_fill):
    """A run lifted verbatim from adjacent prose: the window is
    continuity, not a style template. The message carries the restated-
    dialogue corrective (Closed Circle live run, 2026-07-14: a character
    repeating their theory to the room re-transcribed the line and
    exhausted repairs on a generic 'write fresh ones')."""
    apply = _write_apply_for("passage:p-tremor")
    lifted = "She waits for slack tide, when the water holds its breath"
    with pytest.raises(ApplyError, match="repeats passage:p-lamp-room") as exc:
        apply(WriteProposal(prose=_padded(lifted)), golden_fill)
    assert "say it in NEW words" in str(exc.value)


def test_micro_detail_capped_at_one(golden_fill):
    """At most one micro-detail per passage (author-directed redesign): the
    standing 'up to 2' invitation made a capable writer coin a re-observation
    of the story's central entity every scene."""
    with pytest.raises(ValidationError):
        WriteProposal(
            prose=_padded("A quiet scene."),
            micro_details=[
                {"entity": "character:cartographer", "key": "a", "value": "one"},
                {"entity": "character:cartographer", "key": "b", "value": "two"},
            ],
        )


def test_micro_detail_over_long_value_is_dropped_not_fatal(golden_fill):
    """A micro-detail is optional enrichment (author-directed redesign): an
    over-long value is prose, not a note, so it is DROPPED — never a repair
    that blocks the required prose. The passage still applies without it."""
    apply = _write_apply_for("passage:p-arrival")
    performed = "he settles into the wide lateral stance of a classical fencer once more"
    lines = apply(
        WriteProposal(
            prose=_padded("A quiet scene."),
            micro_details=[
                {"entity": "character:cartographer", "key": "stance", "value": performed}
            ],
        ),
        golden_fill,
    )
    assert any("dropped" in line for line in lines)
    assert "stance" not in golden_fill.graph.node("character:cartographer").base


def test_micro_detail_same_key_updates_the_fact(golden_fill):
    """A re-used key is an UPDATE (a sharper version), not a hard failure —
    the single-assignment guard was removed because it turned a capable
    writer's natural re-observation of a recurring entity into a
    prose-blocking failure; the reviewer now judges refinement vs
    contradiction."""
    apply = _write_apply_for("passage:p-arrival")
    e = "character:cartographer"
    before = golden_fill.graph.node(e).base["appearance"]
    lines = apply(
        WriteProposal(
            prose=_padded("A quiet scene."),
            micro_details=[{"entity": e, "key": "appearance", "value": "weathered, salt-grey"}],
        ),
        golden_fill,
    )
    assert golden_fill.graph.node(e).base["appearance"] == "weathered, salt-grey"
    assert before != "weathered, salt-grey"
    assert any("appearance" in line for line in lines)


def test_review_sees_entity_facts_and_the_prior_value_of_an_update(golden_fill):
    """The `micro_detail` rule can only judge a contradiction if the reviewer
    is shown (a) the entity's other established facts and (b), for a same-key
    update, the prior value apply overwrote — captured through the shared
    prior_facts box (PR #59 review findings: facts weren't rendered and the
    prior was gone by review time). Uses the real fill_review.j2 template."""
    prior_facts: dict = {}
    apply = _write_apply_for("passage:p-arrival", prior_facts)
    review = _review_for("passage:p-arrival", prior_facts)
    e = "character:cartographer"
    old_appearance = golden_fill.graph.node(e).base["appearance"]
    other_key = next(k for k in golden_fill.graph.node(e).base if k != "appearance")
    proposal = WriteProposal(
        prose=_padded("A quiet scene."),
        micro_details=[{"entity": e, "key": "appearance", "value": "weathered, salt-grey"}],
    )
    # apply overwrites base and stashes the prior value into the shared box
    apply(proposal, golden_fill)

    class Capture:
        def complete(self, *, system, prompt, schema, role):
            self.prompt = prompt
            return schema(verdict="approved", findings=[])

    cap = Capture()
    assert review(proposal, golden_fill, cap) == []
    # the prior value (overwritten in the graph) still reaches the reviewer,
    # alongside the entity's other facts and the proposed value
    assert old_appearance in cap.prompt
    assert "weathered, salt-grey" in cap.prompt
    assert other_key in cap.prompt


def test_write_proposal_carries_per_finding_revision_notes():
    """The rework-convergence lever: on a rework the writer responds to each
    finding; empty on the first attempt."""
    p = WriteProposal(
        prose="x",
        revision_notes=[{"finding": "beat_infidelity", "how_addressed": "added 'toward'"}],
    )
    assert p.revision_notes[0].finding == "beat_infidelity"
    assert p.revision_notes[0].how_addressed == "added 'toward'"
    assert WriteProposal(prose="x").revision_notes == []


def test_rejected_draft_reaches_the_next_write_prompt(golden_fill):
    """The adapter is stateless — each rework is a fresh call with no memory of
    the prior attempt — so apply stashes the attempted draft into a shared box
    the next write render surfaces. It stashes as its FIRST statement, so the
    draft reaches the next round whether the rework was triggered by an apply
    check or a review finding (e.g. the word-budget finding that halted
    group-9)."""
    from questfoundry.pipeline import runner

    env = runner._environment()
    last_draft: dict = {"prose": None}
    apply = _write_apply_for("passage:p-arrival", {}, last_draft)
    ctx = _write_context_for("passage:p-arrival", last_draft)(golden_fill)

    # round 1: no previous draft yet
    r1 = env.get_template("fill_write.j2").render(
        **ctx, notes="", repair_errors=["a finding"], research=""
    )
    assert "PREVIOUS DRAFT WAS REJECTED" not in r1

    # applying a draft stashes it (the word budget no longer raises here; it is
    # a review finding), so a later rework surfaces it
    draft = "A rejected two-line draft about the arrival on the cold rock."
    apply(WriteProposal(prose=draft), golden_fill)
    assert last_draft["prose"] == draft

    # round 2: the same context (holding the live box) now surfaces the draft
    r2 = env.get_template("fill_write.j2").render(
        **ctx, notes="", repair_errors=["a finding"], research=""
    )
    assert "PREVIOUS DRAFT WAS REJECTED" in r2
    assert draft in r2


def test_review_renders_the_writers_revision_notes(golden_fill):
    """The reviewer receives the writer's per-finding account to verify against
    the prose (uses the real fill_review.j2 template)."""
    review = _review_for("passage:p-arrival")
    proposal = WriteProposal(
        prose="x " * 200,
        revision_notes=[
            {"finding": "beat_infidelity", "how_addressed": "she now steps toward the log"}
        ],
    )

    class Capture:
        def complete(self, *, system, prompt, schema, role):
            self.prompt = prompt
            return schema(verdict="approved", findings=[])

    cap = Capture()
    review(proposal, golden_fill, cap)
    assert "she now steps toward the log" in cap.prompt
    assert "WRITER'S ACCOUNT OF THIS REVISION" in cap.prompt


def test_micro_detail_fresh_fact_is_accepted(golden_fill):
    apply = _write_apply_for("passage:p-arrival")
    lines = apply(
        WriteProposal(
            prose=_padded("A quiet scene."),
            micro_details=[
                {
                    "entity": "character:cartographer",
                    "key": "habit",
                    "value": "hums off-key over charts",
                }
            ],
        ),
        golden_fill,
    )
    assert any("habit" in line for line in lines)


# -- rolling story-so-far (plan: docs/plans/prose-quality.md W4) ---------------


def test_summary_apply_enforces_the_cap_and_stores(golden_fill):
    from questfoundry.pipeline.stages.fill import (
        SUMMARY_MAX_WORDS,
        SummaryProposal,
        _summary_apply_for,
    )

    apply = _summary_apply_for("passage:p-arrival")
    with pytest.raises(ApplyError, match="cap"):
        apply(SummaryProposal(summary="w " * (SUMMARY_MAX_WORDS + 1)), golden_fill)
    apply(SummaryProposal(summary="Elias lands; the soundings are wrong."), golden_fill)
    assert (
        golden_fill.graph.node("passage:p-arrival").prose_summary
        == "Elias lands; the soundings are wrong."
    )


def test_story_so_far_is_route_notes_minus_the_window(golden_fill):
    """p-tremor's direct predecessors are the window (full prose shown);
    the story-so-far carries the route's earlier passages as notes."""
    from questfoundry.pipeline.stages.fill import _story_so_far

    entries, elided = _story_so_far(golden_fill, "passage:p-tremor")
    assert elided == 0
    assert entries == [golden_fill.graph.node("passage:p-arrival").prose_summary]
    # an ending passage sees the whole route
    entries, _ = _story_so_far(golden_fill, "passage:p-long-watch")
    assert golden_fill.graph.node("passage:p-arrival").prose_summary in entries
    assert len(entries) >= 2


def test_story_route_is_deterministic_and_prefers_the_reference_arc(golden_fill):
    from questfoundry.graph import queries
    from questfoundry.models.base import EdgeKind
    from questfoundry.pipeline.stages.fill import _story_route

    route = _story_route(golden_fill, "passage:p-long-watch")
    assert route == _story_route(golden_fill, "passage:p-long-watch")
    view = queries.arc_view(golden_fill.graph, reference_selection(golden_fill))
    for p in route:
        beats = set(queries.beats_of_passage(golden_fill.graph, p))
        # every hop with a reference-arc alternative takes it
        assert beats <= view or not any(
            set(queries.beats_of_passage(golden_fill.graph, q)) <= view
            for q in {e.src for e in golden_fill.graph.in_edges(p, EdgeKind.CHOICE)}
        )


def test_prose_summary_round_trips(tmp_path, golden_fill):
    from questfoundry.project import save_project

    golden_fill.root = tmp_path / "golden"
    save_project(golden_fill)
    reloaded = load_project(golden_fill.root)
    assert (
        reloaded.graph.node("passage:p-tremor").prose_summary
        == golden_fill.graph.node("passage:p-tremor").prose_summary
    )
    assert reloaded.graph.node("passage:p-tremor").prose_summary


# -- arc positions (plan: docs/plans/prose-quality.md W5) ----------------------


def test_arc_positions_track_now_turn_heading_and_ends(golden_fill):
    """Maren's golden arc pivots at beat:returned-boat (in p-tremor):
    before it she is at `begins` and heading toward the pivot; the
    pivot's own passage carries the turn; downstream of a commit the
    path's landing appears."""
    from questfoundry.pipeline.stages.fill import _arc_positions

    g = golden_fill.graph

    def keeper(passage_id):
        return next(
            a for a in _arc_positions(g, passage_id) if a["entity"].id == "character:keeper"
        )

    before = keeper("passage:p-arrival")
    assert before["now"].startswith("keeper by inheritance")
    assert before["turn"] is None
    assert before["heading"] is not None and "question" in before["heading"]
    assert before["ends"] == []

    at = keeper("passage:p-tremor")
    assert at["turn"] is not None and "question" in at["turn"]

    after = keeper("passage:p-long-watch")
    assert after["now"] == at["turn"]  # the pivot has passed
    assert after["turn"] is None and after["heading"] is None
    assert after["ends"] == [
        "chooses the watch with open eyes; the light is hers, not her family's"
    ]


def test_arc_positions_skip_unarced_entities(golden_fill):
    from questfoundry.pipeline.stages.fill import _arc_positions

    entries = _arc_positions(golden_fill.graph, "passage:p-tremor")
    ids = {a["entity"].id for a in entries}
    assert "character:sleeper" not in ids  # no arc in the golden fixture
    assert "character:keeper" in ids and "character:cartographer" in ids


def test_write_context_and_prompt_carry_the_arc_position(golden_fill):
    from questfoundry.pipeline import runner

    ctx = _write_context_for("passage:p-tremor")(golden_fill)
    assert any(a["entity"].id == "character:keeper" for a in ctx["arcs"])
    env = runner._environment()
    rendered = env.get_template("fill_write.j2").render(
        **ctx, notes="", repair_errors=[], research=""
    )
    assert "ARC POSITION" in rendered
    assert "THIS SCENE TURNS IT" in rendered


# -- overwriting guardrail (coined-compound density) --------------------------


def _prose(total_words: int, compounds: int) -> str:
    """`compounds` hyphen-compounds among `total_words` words — a density
    the overwriting finding measures (density = 1000 * compounds / total)."""
    return " ".join(["salt-worn"] * compounds + ["grey"] * (total_words - compounds))


def test_overwriting_finding_grades_by_density():
    from questfoundry.pipeline.review import ReviewVerdict, needs_rework
    from questfoundry.pipeline.stages.fill import _overwriting_finding

    assert _overwriting_finding(_prose(240, 0)) is None  # plain: no finding
    warn = _overwriting_finding(_prose(300, 3))  # ~10/1k: past warn, under fail
    assert warn.rule == "overwriting" and warn.assessment == "warn"
    assert not needs_rework(ReviewVerdict(verdict="needs_work", findings=[warn]))
    # just past the 15/1k fail line: a fail but LOW confidence, so it does NOT
    # block (mirrors word_budget's near-miss; a threshold tweak must not silently
    # flip this boundary from weighed to forced-rework)
    near = _overwriting_finding(_prose(1000, 16))  # ~16/1k
    assert near.assessment == "fail" and near.confidence == "low"
    assert not needs_rework(ReviewVerdict(verdict="needs_work", findings=[near]))
    mid = _overwriting_finding(_prose(1000, 19))  # ~19/1k: fail/medium, blocks
    assert mid.assessment == "fail" and mid.confidence == "medium"
    assert needs_rework(ReviewVerdict(verdict="needs_work", findings=[mid]))
    flood = _overwriting_finding(_prose(200, 6))  # ~30/1k: egregious
    assert flood.assessment == "fail" and flood.confidence == "high"
    assert needs_rework(ReviewVerdict(verdict="needs_work", findings=[flood]))
    assert "plain words" in flood.recovery_action


def test_overwriting_finding_ignores_a_tiny_sample():
    from questfoundry.pipeline.stages.fill import _overwriting_finding

    # two compounds in a handful of words is not a density (the min-words floor)
    assert _overwriting_finding("salt-worn brine-lamp grey sea") is None


def test_overwriting_blocks_a_compound_flood_even_when_approved(golden_fill, monkeypatch):
    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner

    class FakeAdapter:
        def complete(self, *, system, prompt, schema, role):
            return _verdict()  # the LLM approves — an empty-findings verdict

    env = Environment(loader=DictLoader({"fill_review.j2": "review {{ passage.id }}"}))
    monkeypatch.setattr(runner, "_environment", lambda: env)
    review = _review_for("passage:p-arrival")
    # ~30/1k compounds in 200 words: inside p-arrival's 150-450 band, so the block
    # is purely the overwriting guardrail, not word_budget
    issues = review(WriteProposal(prose=_prose(200, 6)), golden_fill, FakeAdapter())
    assert issues and any("overwriting" in i for i in issues)


# -- per-passage viewpoint + interludes (rotating-pov-build.md) ----------------


def _render_write(project, passage_id):
    from questfoundry.pipeline import runner

    context = _write_context_for(passage_id)(project)
    template = runner._environment().get_template("fill_write.j2")
    return context, template.render(**context, notes="", repair_errors=[], research="")


def _render_review(project, passage_id):
    from questfoundry.pipeline import runner

    context = _write_context_for(passage_id)(project)
    template = runner._environment().get_template("fill_review.j2")
    return template.render(
        **context, prose="p", micro_review=[], revision_notes=[], prior_issues=[],
        arbitration=None,
    )


def _set_passage_head(g, passage_id, viewpoint, interlude=False):
    # in-memory annotation for consumption tests (the golden is frozen; the
    # GROW-time write path is covered in test_grow / test_viewpoint)
    from questfoundry.graph import queries

    for bid in queries.beats_of_passage(g, passage_id):
        beat = g.node(bid)
        beat.viewpoint = viewpoint
        beat.interlude = interlude


def test_write_context_degrades_without_annotations(golden_fill):
    # no beat carries a head -> the book-wide Voice.pov semantics
    # (strip the golden's annotation: this is the pre-migration shape)
    _set_passage_head(golden_fill.graph, "passage:p-arrival", None)
    context, rendered = _render_write(golden_fill, "passage:p-arrival")
    assert context["viewpoint"] is None and context["interlude"] is False
    assert "THIS passage's viewpoint character" not in rendered
    assert "TENSE IS ABSOLUTE" in rendered


def test_write_prompt_names_the_passage_head(golden_fill):
    _set_passage_head(golden_fill.graph, "passage:p-arrival", "character:keeper")
    context, rendered = _render_write(golden_fill, "passage:p-arrival")
    assert context["viewpoint"].id == "character:keeper"
    assert "THIS passage's viewpoint character is\n   Maren Voss" in rendered or (
        "THIS passage's viewpoint character is" in rendered and "Maren Voss" in rendered
    )


def test_write_prompt_marks_a_neighbor_head_switch(golden_fill):
    g = golden_fill.graph
    _set_passage_head(g, "passage:p-arrival", "character:keeper")
    context = _write_context_for("passage:p-arrival")(golden_fill)
    context["window"] = [
        {"passage": g.node("passage:p-tremor"), "label": "go", "head": "Elias Wren"},
        {"passage": g.node("passage:p-chart"), "label": "on", "head": "Maren Voss"},
    ]
    from questfoundry.pipeline import runner

    rendered = (
        runner._environment()
        .get_template("fill_write.j2")
        .render(**context, notes="", repair_errors=[], research="")
    )
    # a different head is flagged; the same head is not
    assert "told from Elias Wren's viewpoint" in rendered
    assert "told from Maren Voss's viewpoint" not in rendered


def test_write_prompt_renders_the_interlude_register(golden_fill):
    golden_fill.voice.interlude = (
        "first-person past-tense journal entries in Maren Voss's voice"
    )
    _set_passage_head(
        golden_fill.graph, "passage:p-arrival", "character:keeper", interlude=True
    )
    context, rendered = _render_write(golden_fill, "passage:p-arrival")
    assert context["interlude"] is True
    assert "THIS PASSAGE IS AN INTERLUDE" in rendered
    assert "journal entries in Maren Voss's voice" in rendered
    # the interlude register owns person/tense for this passage
    assert "TENSE IS ABSOLUTE" not in rendered


def test_review_prompt_keys_pov_to_the_passage_head(golden_fill):
    _set_passage_head(golden_fill.graph, "passage:p-arrival", "character:keeper")
    rendered = _render_review(golden_fill, "passage:p-arrival")
    assert "viewpoint character: Maren Voss" in rendered


def test_review_prompt_judges_an_interlude_against_its_register(golden_fill):
    golden_fill.voice.interlude = "first-person journal entries in Maren Voss's voice"
    _set_passage_head(
        golden_fill.graph, "passage:p-arrival", "character:keeper", interlude=True
    )
    rendered = _render_review(golden_fill, "passage:p-arrival")
    assert "THIS PASSAGE IS AN INTERLUDE" in rendered
    assert "required POV:" not in rendered


# -- choice grounding (author finding, 2026-07-14) -----------------------------


def test_write_prompt_demands_planted_choice_referents(golden_fill):
    # labels are minted at POLISH from beat summaries, so without this
    # contract they read as connective tissue to the NEXT passage ("open the
    # door" with no door on the page)
    context, rendered = _render_write(golden_fill, "passage:p-arrival")
    assert context["choices"], "p-arrival should have outgoing choices"
    assert "PLANT THEIR REFERENTS" in rendered
    for label in context["choices"]:
        assert f'"{label}"' in rendered


def test_write_prompt_ending_lands_instead_of_planting(golden_fill):
    context, rendered = _render_write(golden_fill, "passage:p-long-watch")
    assert not context["choices"]
    assert "PLANT THEIR REFERENTS" not in rendered
    assert "This is an ending: land it completely." in rendered


def test_review_prompt_carries_the_choice_grounding_rule(golden_fill):
    rendered = _render_review(golden_fill, "passage:p-arrival")
    assert "choice_grounding" in rendered
    assert "QUOTE them in `quote`" in rendered
    # the corrective goes to the prose, never the label
    assert "never a change to the label" in rendered


def test_review_prompt_omits_choice_grounding_on_endings(golden_fill):
    rendered = _render_review(golden_fill, "passage:p-long-watch")
    assert "choice_grounding" not in rendered


def test_review_rules_pin_choice_grounding():
    from questfoundry.pipeline.stages.fill import FILL_REVIEW_RULES

    assert "choice_grounding" in FILL_REVIEW_RULES


def test_voice_proposal_requires_an_interlude_decision(golden_fill):
    with pytest.raises(ValidationError):
        VoiceProposal(
            pov="third person limited (Maren)", tense="past", diction="d",
            rhythm="r", imagery="i", dialogue="g",
        )
    proposal = VoiceProposal(
        pov="third person limited (Maren)", tense="past", diction="d",
        rhythm="r", imagery="i", dialogue="g",
        interlude="first-person past-tense journal entries (Elias Wren)",
    )
    golden_fill.voice = None
    lines = _voice_apply(proposal, golden_fill)
    assert golden_fill.voice.interlude.startswith("first-person")
    assert "interlude:" in lines[0]


def _interlude_proposal(interlude: str) -> VoiceProposal:
    return VoiceProposal(
        pov="third person limited (Maren)", tense="past", diction="d",
        rhythm="r", imagery="i", dialogue="g", interlude=interlude,
    )


def test_voice_interlude_narrator_is_validated_against_the_cast(golden_fill):
    golden_fill.voice = None
    with pytest.raises(ApplyError, match="not a character"):
        _voice_apply(_interlude_proposal("first-person journal entries (Nadia)"), golden_fill)


def test_voice_interlude_without_a_parenthetical_narrator_is_repairable(golden_fill):
    # the pov checker's no-parens early return must not silently skip the
    # interlude (PR #74 review finding): an interlude always has a narrator,
    # so the parenthetical is required, and the prompted paren-free phrasing
    # is exactly the case that used to slip through
    golden_fill.voice = None
    with pytest.raises(ApplyError, match="names no narrator"):
        _voice_apply(
            _interlude_proposal("first-person journal entries in Maren Voss's voice"),
            golden_fill,
        )


def test_review_prompt_renders_the_cast_for_actor_resolution(golden_fill):
    """PR #74 review finding on 6dd9aca: the fidelity rule said 'resolve the
    role against the cast below' but the template rendered no cast — the only
    entity listing was gated on pronouns being set (never true for the
    golden). The roster now renders unconditionally beside the rule, proven
    on the rendered template, not the source."""
    rendered = _render_review(golden_fill, "passage:p-arrival")
    assert "THE CAST ON THIS PAGE" in rendered
    assert "Maren Voss (character:keeper)" in rendered
    assert "resolve the role against the cast" in rendered
