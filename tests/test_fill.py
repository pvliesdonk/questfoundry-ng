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


def test_micro_detail_entity_resolves_names_and_slugs(golden_fill):
    """Third live-run lesson (gpt-5, 2026-07-08): models cite entities by
    display name; resolve any unambiguous reference."""
    from questfoundry.pipeline.stages.fill import _resolve_entity

    g = golden_fill.graph
    assert _resolve_entity(g, "character:keeper") == "character:keeper"
    assert _resolve_entity(g, g.node("character:keeper").name) == "character:keeper"
    assert _resolve_entity(g, "keeper") == "character:keeper"
    with pytest.raises(ApplyError, match="use one of"):
        _resolve_entity(g, "Nobody Anyone Knows")
