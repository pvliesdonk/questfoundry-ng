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
    assert len(order) == 7
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


def test_word_budget_is_enforced_at_apply(golden_fill):
    apply = _write_apply_for("passage:p-arrival")
    with pytest.raises(ApplyError, match="budget"):
        apply(WriteProposal(prose="far too short"), golden_fill)


def test_write_context_carries_the_contract(golden_fill):
    golden_fill.voice = golden_fill.voice or Voice(
        pov="third", tense="present", diction="spare"
    )
    ctx = _write_context_for("passage:p-tremor")(golden_fill)
    assert ctx["voice"] is golden_fill.voice
    assert [b.id for b in ctx["beats"]] == ["beat:tremor", "beat:offer"]
    # the truth flags are merely possible here — the prose must stay honest
    statuses = {f["flag"].id: f["status"] for f in ctx["flags"]}
    assert statuses["flag:elias-knows"] == "possible"
    assert len(ctx["choices"]) == 3
    assert ctx["words_min"] == 150 and ctx["words_max"] == 450


def test_review_hook_translates_verdicts(golden_fill, monkeypatch):
    class FakeAdapter:
        def __init__(self, verdict):
            self.verdict = verdict

        def complete(self, *, system, prompt, schema, role):
            assert role == "utility"
            return self.verdict

    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner

    env = Environment(loader=DictLoader({"fill_review.j2": "review {{ passage.id }}"}))
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


def test_fill_pass_list_is_voice_plus_one_write_per_passage(golden_fill):
    passes = _passes(golden_fill)
    assert passes[0].name == "voice"
    assert passes[0].skip_if is not None
    assert passes[0].skip_if(golden_fill)  # golden already carries a voice
    write_passes = [p for p in passes[1:]]
    assert len(write_passes) == 7
    assert all(p.review is not None for p in write_passes)


def test_gate_requires_voice(golden_fill):
    golden_fill.voice = None
    issues = _fill_gate(golden_fill)
    assert any("no voice record" in i.message for i in issues)


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
