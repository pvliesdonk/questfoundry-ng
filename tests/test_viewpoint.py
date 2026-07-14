"""Rotating limited POV: the per-beat viewpoint annotation, the passage
head derivation, invariant I14, and the G3 referential check
(docs/plans/rotating-pov-build.md). GROW's annotate emission and FILL's
per-passage consumption are exercised in test_grow.py / test_fill.py /
test_prompts.py; the collapse cut in test_passages.py."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.concept import Voice
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import Beat, PassageViewpoint, passage_viewpoint
from questfoundry.models.world import Entity
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat
from tests.test_invariants import errors_for


def _annotated(slug: str, viewpoint: str | None, interlude: bool = False) -> Beat:
    beat = narrative_beat(slug, "dilemma:d")
    beat.viewpoint = viewpoint
    beat.interlude = interlude
    return beat


# -- passage_viewpoint derivation ----------------------------------------------


def test_no_annotated_beats_derives_no_head():
    beats = [narrative_beat("a", "dilemma:d"), narrative_beat("b", "dilemma:d")]
    assert passage_viewpoint(beats) == PassageViewpoint(None, False)


def test_unique_head_wins_and_unannotated_are_wildcards():
    beats = [
        _annotated("a", "character:eleanor"),
        narrative_beat("bridge", "dilemma:d"),  # wildcard: no viewpoint
        _annotated("c", "character:eleanor"),
    ]
    assert passage_viewpoint(beats) == PassageViewpoint("character:eleanor", False)


def test_interlude_head_derives_as_interlude():
    beats = [_annotated("a", "character:eleanor", interlude=True)]
    assert passage_viewpoint(beats) == PassageViewpoint("character:eleanor", True)


def test_conflicting_heads_raise():
    beats = [_annotated("a", "character:eleanor"), _annotated("b", "character:charles")]
    with pytest.raises(ValueError, match="I14"):
        passage_viewpoint(beats)


def test_same_head_mixed_interlude_raises():
    # a journal entry and base narration never share a passage, even in one head
    beats = [
        _annotated("a", "character:eleanor"),
        _annotated("b", "character:eleanor", interlude=True),
    ]
    with pytest.raises(ValueError, match="I14"):
        passage_viewpoint(beats)


# -- model ---------------------------------------------------------------------


def test_interlude_without_viewpoint_rejected():
    with pytest.raises(ValueError, match="interlude but names no viewpoint"):
        Beat.model_validate(
            {**narrative_beat("x", "dilemma:d").model_dump(), "interlude": True}
        )


def test_viewpoint_round_trips_and_default_is_omitted():
    beat = narrative_beat("x", "dilemma:d")
    dumped = beat.model_dump(mode="json", exclude_defaults=True)
    assert "viewpoint" not in dumped and "interlude" not in dumped
    beat.viewpoint = "character:eleanor"
    beat.interlude = True
    dumped = beat.model_dump(mode="json", exclude_defaults=True)
    assert dumped["viewpoint"] == "character:eleanor"
    assert dumped["interlude"] is True
    restored = Beat.model_validate(dumped)
    assert restored.viewpoint == "character:eleanor" and restored.interlude


def test_voice_interlude_defaults_empty():
    voice = Voice(pov="third limited", tense="past", diction="plain")
    assert voice.interlude == ""


# -- set_beat_viewpoint mutation -----------------------------------------------


def test_set_viewpoint_before_freeze():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.set_beat_viewpoint(g, "beat:one-pre", "character:one-anchor")
    beat = g.node("beat:one-pre")
    assert beat.viewpoint == "character:one-anchor" and beat.interlude is False


def test_set_viewpoint_rejects_frozen_beat():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.freeze_topology(g)
    with pytest.raises(MutationError, match="frozen; viewpoint is settled"):
        mutations.set_beat_viewpoint(g, "beat:one-pre", "character:one-anchor")


def test_set_viewpoint_rejects_non_beat():
    g = StoryGraph()
    make_dilemma(g, "one")
    with pytest.raises(MutationError, match="not a beat"):
        mutations.set_beat_viewpoint(g, "dilemma:one", "character:one-anchor")


def test_set_viewpoint_rejects_interlude_without_head():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    with pytest.raises(MutationError, match="interlude beat must name a viewpoint"):
        mutations.set_beat_viewpoint(g, "beat:one-pre", None, interlude=True)


# -- gate G3: referential integrity ---------------------------------------------


def test_g3_dangling_viewpoint_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.set_beat_viewpoint(g, "beat:one-pre", "character:ghost")
    issues = errors_for("G3", g, vision, Stage.GROW)
    assert any("not a character entity" in i.message for i in issues)


def test_g3_non_character_viewpoint_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.add_entity(
        g, Entity(id="location:manor", created_by=Stage.BRAINSTORM, name="Manor", concept="c")
    )
    mutations.set_beat_viewpoint(g, "beat:one-pre", "location:manor")
    issues = errors_for("G3", g, vision, Stage.GROW)
    assert any("not a character entity" in i.message for i in issues)


def test_g3_unretained_viewpoint_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.add_entity(
        g,
        Entity(
            id="character:cut",
            created_by=Stage.BRAINSTORM,
            name="Cut",
            concept="c",
            retained=False,
        ),
    )
    mutations.set_beat_viewpoint(g, "beat:one-pre", "character:cut")
    issues = errors_for("G3", g, vision, Stage.GROW)
    assert any("not retained" in i.message for i in issues)


def test_g3_valid_viewpoint_clean(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.set_beat_viewpoint(g, "beat:one-pre", "character:one-anchor")
    assert not [
        i
        for i in errors_for("G3", g, vision, Stage.GROW)
        if "viewpoint" in i.message
    ]


# -- invariant I14: one head per passage (violating construction) ---------------


def _grouped_pair(g: StoryGraph, head_a: str | None, head_b: str | None, interlude_b=False):
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    if head_a:
        mutations.set_beat_viewpoint(g, "beat:one-pre", head_a)
    if head_b:
        mutations.set_beat_viewpoint(g, "beat:one-commit-a", head_b, interlude=interlude_b)
    mutations.add_passage(
        g,
        Passage(id="passage:p1", created_by=Stage.POLISH, summary="s"),
        ["beat:one-pre", "beat:one-commit-a"],
    )


def test_i14_two_heads_in_one_passage_flagged(vision):
    g = StoryGraph()
    mutations.add_entity(
        g, Entity(id="character:other", created_by=Stage.BRAINSTORM, name="O", concept="c")
    )
    _grouped_pair(g, "character:one-anchor", "character:other")
    issues = errors_for("I14", g, vision, Stage.POLISH)
    assert any("mixes viewpoints" in i.message for i in issues)


def test_i14_interlude_mixed_with_narration_flagged(vision):
    g = StoryGraph()
    _grouped_pair(g, "character:one-anchor", "character:one-anchor", interlude_b=True)
    issues = errors_for("I14", g, vision, Stage.POLISH)
    assert any("mixes viewpoints" in i.message for i in issues)


def test_i14_one_head_plus_wildcards_clean(vision):
    g = StoryGraph()
    _grouped_pair(g, "character:one-anchor", None)
    assert not errors_for("I14", g, vision, Stage.POLISH)
