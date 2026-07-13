"""narration_scope: the per-beat POV/coda annotation (design doc 01
§Beat annotations). Covers the model fallback, the freeze-respecting
mutation, and serialization. FILL's per-beat consumption is exercised
through the prompt-source tests in test_prompts.py."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    NarrationScope,
    StructuralPurpose,
    effective_narration_scope,
)
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat


def _structural(slug: str, purpose: StructuralPurpose, **kw) -> Beat:
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.GROW,
        summary=slug,
        beat_class=BeatClass.STRUCTURAL,
        purpose=purpose,
        **kw,
    )


# -- effective_narration_scope fallback ---------------------------------------


def test_annotation_wins_over_fallback():
    # a wide-tagged narrative beat stays wide even though narrative beats
    # otherwise fall back to limited.
    beat = narrative_beat("x", "dilemma:d")
    beat.narration_scope = NarrationScope.WIDE
    assert effective_narration_scope(beat) == NarrationScope.WIDE


def test_epilogue_falls_back_to_wide():
    # the sanctioned coda site: an unannotated epilogue is wide by default.
    assert effective_narration_scope(_structural("end", StructuralPurpose.EPILOGUE)) == (
        NarrationScope.WIDE
    )


@pytest.mark.parametrize(
    "purpose",
    [
        StructuralPurpose.SETUP,
        StructuralPurpose.BRIDGE,
        StructuralPurpose.RESIDUE,
        StructuralPurpose.FALSE_BRANCH,
    ],
)
def test_non_epilogue_structural_falls_back_to_limited(purpose):
    assert effective_narration_scope(_structural("s", purpose)) == NarrationScope.LIMITED


def test_unannotated_narrative_falls_back_to_limited():
    # wide is always the marked exception; an unannotated narrative beat is
    # inside the Voice's POV.
    assert effective_narration_scope(narrative_beat("x", "dilemma:d")) == NarrationScope.LIMITED


# -- set_beat_narration_scope mutation ----------------------------------------


def test_set_narration_scope_before_freeze():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.set_beat_narration_scope(g, "beat:one-pre", NarrationScope.WIDE)
    assert g.node("beat:one-pre").narration_scope == NarrationScope.WIDE


def test_set_narration_scope_rejects_frozen_beat():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.freeze_topology(g)
    with pytest.raises(MutationError, match="frozen; narration_scope is settled"):
        mutations.set_beat_narration_scope(g, "beat:one-pre", NarrationScope.WIDE)


def test_set_narration_scope_rejects_non_beat():
    g = StoryGraph()
    make_dilemma(g, "one")
    with pytest.raises(MutationError, match="not a beat"):
        mutations.set_beat_narration_scope(g, "dilemma:one", NarrationScope.WIDE)


# -- serialization ------------------------------------------------------------


def test_narration_scope_round_trips_and_default_is_omitted():
    beat = narrative_beat("x", "dilemma:d")
    assert "narration_scope" not in beat.model_dump(mode="json", exclude_defaults=True)
    beat.narration_scope = NarrationScope.WIDE
    dumped = beat.model_dump(mode="json", exclude_defaults=True)
    assert dumped["narration_scope"] == "wide"
    assert Beat.model_validate(dumped).narration_scope == NarrationScope.WIDE
