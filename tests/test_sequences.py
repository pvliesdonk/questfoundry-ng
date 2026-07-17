"""Sequence-unit viewpoint annotation (docs/plans/pov-sequences.md PR-B):
the engine-computed sequences in annotate's context/schema, the heads
section (one head per sequence, justified splits, wide cutaways), the
per-beat expansion, and the B11 sequence-health advisory. Failure modes
1/2/4/5/6/9/11/13/14/17 of the plan's table live here; the roster
machinery (PR-A) is exercised in test_scheme.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import Stage
from questfoundry.models.structure import NarrationScope, SceneType
from questfoundry.pipeline.stages.grow import (
    AnnotateProposal,
    _annotate_apply,
    _annotate_context,
    annotate_proposal_schema,
    grow_sequences,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat
from tests.test_scheme import _character


@pytest.fixture()
def story(vision):
    """setup-1 -> setup-2 -> y-pre -> (y-commit-a -> y-post-a[end],
    y-commit-b -> y-post-b[end]): three sequences —
    [setup-1, setup-2, y-pre], [y-commit-a, y-post-a], [y-commit-b, y-post-b]."""
    g = StoryGraph()
    _, path_a, path_b = make_dilemma(g, "d", explore=2)
    _character(g, "eleanor")
    _character(g, "charles")
    _character(g, "milo")
    mutations.add_beat(g, narrative_beat("setup-1", "dilemma:d"), [path_a, path_b])
    mutations.add_beat(g, narrative_beat("setup-2", "dilemma:d"), [path_a, path_b])
    make_y_scaffold(g, "y", "dilemma:d", path_a, path_b)
    mutations.add_ordering(g, "beat:setup-1", "beat:setup-2")
    mutations.add_ordering(g, "beat:setup-2", "beat:y-pre")
    mutations.set_pov_head(g, "character:eleanor", True)
    mutations.set_pov_head(g, "character:charles", True)
    mutations.set_interlude_carrier(g, "character:milo", True)
    return g


@pytest.fixture()
def project(tmp_path, vision, story) -> Project:
    return Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=story)


SEQ_TRUNK = "beat:setup-1"
SEQ_A = "beat:y-commit-a"
SEQ_B = "beat:y-commit-b"


def _ann(beat: str, scope=NarrationScope.LIMITED, interlude: bool = False) -> dict:
    return {
        "beat": beat,
        "scene_type": SceneType.SEQUEL.value,
        "narration_scope": scope.value,
        "interlude": interlude,
    }


def _proposal(project, heads, overrides: dict | None = None) -> AnnotateProposal:
    overrides = overrides or {}
    beats = queries.topological_order(project.graph) or []
    return AnnotateProposal.model_validate(
        {
            "annotations": [overrides.get(b, _ann(b)) for b in beats],
            "heads": heads,
        }
    )


def _entry(sequence: str, head: str = "character:eleanor", splits: list | None = None) -> dict:
    return {"sequence": sequence, "head": head, "splits": splits or []}


def _full_heads(a="character:eleanor", b="character:charles") -> list[dict]:
    return [_entry(SEQ_TRUNK, a), _entry(SEQ_A, b), _entry(SEQ_B, b)]


# -- the engine's sequences ----------------------------------------------------


def test_sequences_are_the_choice_free_runs(story):
    seqs = grow_sequences(story)
    assert [s[0] for s in seqs] == [SEQ_TRUNK, SEQ_A, SEQ_B]
    assert seqs[0] == ["beat:setup-1", "beat:setup-2", "beat:y-pre"]


def test_annotate_context_carries_sequences_and_candidates(project):
    ctx = _annotate_context(project)
    assert len(ctx["sequences"]) == 3
    assert ctx["roster"] and ctx["carrier"] is not None


# -- schema pins (failure modes 2/3/5) -----------------------------------------


def test_heads_sequence_key_is_enum_pinned(project):
    schema = annotate_proposal_schema(project)
    with pytest.raises(ValidationError):
        schema.model_validate(
            {"annotations": [], "heads": [_entry("beat:setup-2")]}  # not a sequence head
        )


def test_segment_head_is_enum_pinned_to_roster(project):
    schema = annotate_proposal_schema(project)
    # the carrier is NOT a legal base-register segment head (off-roster)
    with pytest.raises(ValidationError):
        schema.model_validate(
            {"annotations": [], "heads": [_entry(SEQ_TRUNK, "character:milo")]}
        )


def test_split_without_justification_is_unrepresentable(project):
    schema = annotate_proposal_schema(project)
    with pytest.raises(ValidationError):
        schema.model_validate(
            {
                "annotations": [],
                "heads": [
                    _entry(
                        SEQ_TRUNK,
                        splits=[{"after": "beat:setup-1", "head": "character:charles", "why": ""}],
                    )
                ],
            }
        )


# -- apply: coverage and splits (failure modes 1/4/11) -------------------------


def test_apply_expands_one_head_per_sequence(project):
    _annotate_apply(_proposal(project, _full_heads()), project)
    g = project.graph
    assert g.node("beat:setup-1").viewpoint == "character:eleanor"
    assert g.node("beat:y-pre").viewpoint == "character:eleanor"
    assert g.node("beat:y-post-a").viewpoint == "character:charles"


def test_apply_rejects_a_missing_sequence(project):
    with pytest.raises(ApplyError, match="beat:y-commit-b"):
        _annotate_apply(_proposal(project, _full_heads()[:2]), project)


def test_apply_rejects_a_duplicated_sequence(project):
    heads = _full_heads() + [_entry(SEQ_A)]
    with pytest.raises(ApplyError, match="once"):
        _annotate_apply(_proposal(project, heads), project)


def test_split_assigns_the_tail_segment_to_the_new_head(project):
    heads = [
        _entry(
            SEQ_TRUNK,
            splits=[{"after": "beat:setup-2", "head": "character:charles", "why": "shift"}],
        ),
        _entry(SEQ_A),
        _entry(SEQ_B),
    ]
    lines = _annotate_apply(_proposal(project, heads), project)
    g = project.graph
    assert g.node("beat:setup-1").viewpoint == "character:eleanor"
    assert g.node("beat:setup-2").viewpoint == "character:eleanor"
    assert g.node("beat:y-pre").viewpoint == "character:charles"
    assert any("shift" in line for line in lines)  # the justification is logged


def test_split_after_the_last_beat_is_rejected(project):
    heads = [
        _entry(
            SEQ_TRUNK,
            splits=[{"after": "beat:y-pre", "head": "character:charles", "why": "w"}],
        ),
        _entry(SEQ_A),
        _entry(SEQ_B),
    ]
    with pytest.raises(ApplyError, match="last"):
        _annotate_apply(_proposal(project, heads), project)


def test_split_outside_the_sequence_is_rejected(project):
    heads = [
        _entry(
            SEQ_TRUNK,
            splits=[{"after": "beat:y-commit-a", "head": "character:charles", "why": "w"}],
        ),
        _entry(SEQ_A),
        _entry(SEQ_B),
    ]
    with pytest.raises(ApplyError, match="inside"):
        _annotate_apply(_proposal(project, heads), project)


def test_duplicate_split_points_are_rejected(project):
    heads = [
        _entry(
            SEQ_TRUNK,
            splits=[
                {"after": "beat:setup-1", "head": "character:charles", "why": "w"},
                {"after": "beat:setup-1", "head": "character:eleanor", "why": "w"},
            ],
        ),
        _entry(SEQ_A),
        _entry(SEQ_B),
    ]
    with pytest.raises(ApplyError, match="order|duplicate"):
        _annotate_apply(_proposal(project, heads), project)


# -- apply: expansion (failure modes 6/9/15) -----------------------------------


def test_wide_beats_expand_to_no_head(project):
    overrides = {"beat:y-post-a": _ann("beat:y-post-a", scope=NarrationScope.WIDE)}
    _annotate_apply(_proposal(project, _full_heads(), overrides), project)
    assert project.graph.node("beat:y-post-a").viewpoint is None


def test_wide_cutaway_segment_needs_wide_beats(project):
    # a ""-headed segment whose beats are limited is unresolvable
    heads = [_entry(SEQ_TRUNK), _entry(SEQ_A, ""), _entry(SEQ_B)]
    with pytest.raises(ApplyError, match="wide"):
        _annotate_apply(_proposal(project, heads), project)


def test_wide_cutaway_segment_expands_headless(project):
    heads = [_entry(SEQ_TRUNK), _entry(SEQ_A, ""), _entry(SEQ_B)]
    overrides = {
        SEQ_A: _ann(SEQ_A, scope=NarrationScope.WIDE),
        "beat:y-post-a": _ann("beat:y-post-a", scope=NarrationScope.WIDE),
    }
    _annotate_apply(_proposal(project, heads, overrides), project)
    assert project.graph.node(SEQ_A).viewpoint is None


def test_interlude_beats_expand_to_the_carrier(project):
    overrides = {"beat:setup-2": _ann("beat:setup-2", interlude=True)}
    _annotate_apply(_proposal(project, _full_heads(), overrides), project)
    beat = project.graph.node("beat:setup-2")
    assert beat.viewpoint == "character:milo" and beat.interlude is True


def test_interlude_without_a_carrier_is_rejected(project):
    mutations.set_interlude_carrier(project.graph, "character:milo", False)
    overrides = {"beat:setup-2": _ann("beat:setup-2", interlude=True)}
    with pytest.raises(ApplyError, match="register|carrier"):
        _annotate_apply(_proposal(project, _full_heads(), overrides), project)


# -- B11: sequence health (failure modes 14/17) --------------------------------


def _b11(g, vision):
    issues = run_checks(g, vision, Stage.GROW)
    return [i for i in issues if i.check == "B11"]


def test_b11_reports_a_mid_sequence_head_switch(project, vision):
    _annotate_apply(_proposal(project, _full_heads()), project)
    # hand-edit a hop inside the trunk sequence (post-annotate state)
    project.graph.node("beat:setup-2").viewpoint = "character:charles"
    issues = _b11(project.graph, vision)
    assert any("beat:setup-2" in i.message for i in issues)


def test_b11_is_quiet_on_clean_sequences(project, vision):
    _annotate_apply(_proposal(project, _full_heads()), project)
    issues = _b11(project.graph, vision)
    assert all("switch" not in i.message for i in issues)


def test_b11_justified_splits_still_count_as_switches(project, vision):
    # visibility is the contract: a justified split is still a page cost
    heads = [
        _entry(
            SEQ_TRUNK,
            splits=[{"after": "beat:setup-2", "head": "character:charles", "why": "shift"}],
        ),
        _entry(SEQ_A),
        _entry(SEQ_B),
    ]
    _annotate_apply(_proposal(project, heads), project)
    issues = _b11(project.graph, vision)
    assert any("switch" in i.message for i in issues)


def test_b11_reports_a_silent_register(project, vision):
    # carrier declared, zero interlude beats marked — the live gap
    _annotate_apply(_proposal(project, _full_heads()), project)
    issues = _b11(project.graph, vision)
    assert any("register" in i.message and "interlude" in i.message for i in issues)


def test_b11_register_line_is_quiet_when_an_interlude_fires(project, vision):
    overrides = {"beat:setup-2": _ann("beat:setup-2", interlude=True)}
    _annotate_apply(_proposal(project, _full_heads(), overrides), project)
    issues = _b11(project.graph, vision)
    assert not any("register" in i.message and "zero" in i.message for i in issues)


def test_b11_reports_a_non_coda_wide(project, vision):
    overrides = {"beat:setup-2": _ann("beat:setup-2", scope=NarrationScope.WIDE)}
    _annotate_apply(_proposal(project, _full_heads(), overrides), project)
    issues = _b11(project.graph, vision)
    assert any("wide" in i.message for i in issues)


def test_b11_reports_head_shares_for_a_rotating_roster(project, vision):
    _annotate_apply(_proposal(project, _full_heads()), project)
    issues = _b11(project.graph, vision)
    assert any("share" in i.message for i in issues)


def test_b11_skips_without_a_roster(story, vision):
    for cid in ("character:eleanor", "character:charles"):
        mutations.set_pov_head(story, cid, False)
    mutations.set_interlude_carrier(story, "character:milo", False)
    assert _b11(story, vision) == []


def test_b11_is_advisory_only(project, vision):
    _annotate_apply(_proposal(project, _full_heads()), project)
    issues = run_checks(project.graph, project.vision, Stage.GROW)
    assert all(i.severity != Severity.ERROR for i in issues if i.check == "B11")
