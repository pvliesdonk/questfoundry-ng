"""FILL: the seeded reference-arc queue, flag-status computation, word
budgets, and the review hook riding the runner's repair loop."""

from __future__ import annotations

import pytest

from questfoundry.models.concept import Voice
from questfoundry.pipeline.stages.fill import (
    ReviewVerdict,
    WriteProposal,
    _fill_gate,
    _flag_status,
    _passes,
    _review_for,
    _write_apply_for,
    _write_context_for,
    reference_selection,
    writing_order,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project import load_project
from questfoundry.project.io import Project
from tests.conftest import GOLDEN


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


def test_word_budget_is_enforced_at_apply(golden_fill):
    apply = _write_apply_for("passage:p-arrival")
    with pytest.raises(ApplyError, match="budget"):
        apply(WriteProposal(prose="far too short"), golden_fill)


def test_word_budget_has_slack_at_the_bounds(golden_fill):
    """Live medium run (2026-07-09): the writer repeatedly landed past
    the cap (553, then 613 on a climax ending against 550) and exhausted
    repairs — models cannot hit exact word windows, and the band exists
    to catch runaway or skimpy prose, not near-misses; the review pass
    owns quality. Apply repairs only beyond 20% slack; the exact range
    stays the prompt's target and B5's advisory line."""
    lo, hi = golden_fill.vision.preset.words_per_passage
    apply = _write_apply_for("passage:p-arrival")
    apply(WriteProposal(prose="w " * (hi + hi // 10)), golden_fill)  # 10% over: accepted
    with pytest.raises(ApplyError, match="budget"):
        apply(WriteProposal(prose="w " * (hi + 3 * hi // 10)), golden_fill)  # 30% over
    apply(WriteProposal(prose="w " * (lo - lo // 10)), golden_fill)  # 10% short: accepted
    with pytest.raises(ApplyError, match="budget"):
        apply(WriteProposal(prose="w " * (lo - 3 * lo // 10)), golden_fill)  # 30% short


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
    ok = review(proposal, golden_fill, FakeAdapter(ReviewVerdict(verdict="pass")))
    assert ok == []
    bad = review(
        proposal,
        golden_fill,
        FakeAdapter(ReviewVerdict(verdict="fail", issues=["voice drift"])),
    )
    assert bad == ["voice drift"]
    # round two is anchored: the earlier round's issues reach the prompt,
    # so persistence — not fresh taste — is what the reviewer judges
    # (validation run, 2026-07-09: an amnesiac reviewer found brand-new
    # complaints every round and never converged)
    adapter = FakeAdapter(ReviewVerdict(verdict="pass"))
    review(proposal, golden_fill, adapter)
    assert "prior[voice drift]" in adapter.seen


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
            ("utility", ReviewVerdict(verdict="fail", issues=["real defect"])),
            ("utility", ReviewVerdict(verdict="fail", issues=["fresh taste"])),
            ("architect", ReviewVerdict(verdict="pass")),
        ]
    )
    assert review(proposal, golden_fill, adapter) == ["real defect"]
    assert review(proposal, golden_fill, adapter) == []
    assert adapter.prompts[-1][0] == "architect"
    assert "ARB[fresh taste]" in adapter.prompts[-1][1]

    # arbitration upholds: the halt is real and carries the arbiter's issues
    review = _review_for("passage:p-arrival")
    adapter = ScriptedAdapter(
        [
            ("utility", ReviewVerdict(verdict="fail", issues=["real defect"])),
            ("utility", ReviewVerdict(verdict="fail", issues=["still broken"])),
            ("architect", ReviewVerdict(verdict="fail", issues=["confirmed: still broken"])),
        ]
    )
    assert review(proposal, golden_fill, adapter) == ["real defect"]
    assert review(proposal, golden_fill, adapter) == ["confirmed: still broken"]


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
    _check_pov_names_the_cast("second person ('you')", golden_fill)  # pronoun — not checked
    with pytest.raises(ApplyError, match="not a character"):
        _check_pov_names_the_cast("third person limited (Nadia)", golden_fill)


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
    continuity, not a style template."""
    apply = _write_apply_for("passage:p-tremor")
    lifted = "She waits for slack tide, when the water holds its breath"
    with pytest.raises(ApplyError, match="repeats passage:p-lamp-room"):
        apply(WriteProposal(prose=_padded(lifted)), golden_fill)


def test_micro_detail_value_word_cap(golden_fill):
    apply = _write_apply_for("passage:p-arrival")
    performed = "he settles into the wide lateral stance of a classical fencer once more"
    with pytest.raises(ApplyError, match="note form"):
        apply(
            WriteProposal(
                prose=_padded("A quiet scene."),
                micro_details=[
                    {"entity": "character:cartographer", "key": "stance", "value": performed}
                ],
            ),
            golden_fill,
        )


def test_micro_detail_near_duplicate_names_the_existing_key(golden_fill):
    """The fencer-stance accrual: the same fact under a new key is
    rejected naming the key that already carries it."""
    apply = _write_apply_for("passage:p-arrival")
    with pytest.raises(ApplyError, match="'appearance'"):
        apply(
            WriteProposal(
                prose=_padded("A quiet scene."),
                micro_details=[
                    {
                        "entity": "character:cartographer",
                        "key": "grooming",
                        "value": "a tidy beard going salt-and-pepper",
                    }
                ],
            ),
            golden_fill,
        )


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
