"""scene_type: the intrinsic prose-intensity beat annotation (design doc
01 §10.3). Covers the model fallback, the intensity rank, and the
freeze-respecting mutation. FILL's band consumption is in test_fill.py."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    SceneType,
    StructuralPurpose,
    effective_scene_type,
    intensity_rank,
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


# -- effective_scene_type fallback --------------------------------------------


def test_annotation_wins_over_fallback():
    beat = narrative_beat("x", "dilemma:d")
    beat.scene_type = SceneType.SEQUEL
    assert effective_scene_type(beat) == SceneType.SEQUEL


@pytest.mark.parametrize(
    "purpose",
    [StructuralPurpose.BRIDGE, StructuralPurpose.RESIDUE, StructuralPurpose.FALSE_BRANCH],
)
def test_unannotated_texture_and_bridge_fall_back_to_micro(purpose):
    # residue/false-branch preserve today's short band; bridge is a
    # transition and now shortens too (a documented behavior change).
    assert effective_scene_type(_structural("b", purpose)) == SceneType.MICRO_BEAT


def test_unannotated_narrative_falls_back_to_scene():
    # heritage R-4b.1: absent -> scene, conservative, never starves prose.
    assert effective_scene_type(narrative_beat("x", "dilemma:d")) == SceneType.SCENE


@pytest.mark.parametrize("purpose", [StructuralPurpose.SETUP, StructuralPurpose.EPILOGUE])
def test_unannotated_setup_epilogue_fall_back_to_scene(purpose):
    # setup/epilogue are LLM-classified at annotate time; the fallback only
    # fires on partial coverage, and then stays conservative (scene).
    assert effective_scene_type(_structural("s", purpose)) == SceneType.SCENE


def test_is_texture_consistent_with_effective_type():
    for purpose in (StructuralPurpose.RESIDUE, StructuralPurpose.FALSE_BRANCH):
        beat = _structural("t", purpose)
        assert beat.is_texture
        assert effective_scene_type(beat) == SceneType.MICRO_BEAT


# -- intensity rank -----------------------------------------------------------


def test_intensity_rank_orders_scene_above_sequel_above_micro():
    assert (
        intensity_rank(SceneType.SCENE)
        > intensity_rank(SceneType.SEQUEL)
        > intensity_rank(SceneType.MICRO_BEAT)
    )


def test_rank_inverts_lexicographic_stringenum_order():
    # a bare max() over the StrEnum would pick "sequel" (lexicographic max);
    # the rank map is what makes scene dominate a mixed passage.
    types = [SceneType.SCENE, SceneType.SEQUEL, SceneType.MICRO_BEAT]
    assert max(types) == SceneType.SEQUEL  # the trap
    assert max(types, key=intensity_rank) == SceneType.SCENE  # the fix


# -- set_beat_scene_type mutation ---------------------------------------------


def test_set_scene_type_before_freeze():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.set_beat_scene_type(g, "beat:one-pre", SceneType.SCENE)
    assert g.node("beat:one-pre").scene_type == SceneType.SCENE


def test_set_scene_type_rejects_frozen_beat():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.freeze_topology(g)
    with pytest.raises(MutationError, match="frozen; scene_type is settled"):
        mutations.set_beat_scene_type(g, "beat:one-pre", SceneType.SCENE)


def test_set_scene_type_rejects_non_beat():
    g = StoryGraph()
    make_dilemma(g, "one")
    with pytest.raises(MutationError, match="not a beat"):
        mutations.set_beat_scene_type(g, "dilemma:one", SceneType.SCENE)


# -- serialization ------------------------------------------------------------


def test_scene_type_round_trips_and_default_is_omitted():
    beat = narrative_beat("x", "dilemma:d")
    assert "scene_type" not in beat.model_dump(mode="json", exclude_defaults=True)
    beat.scene_type = SceneType.SEQUEL
    dumped = beat.model_dump(mode="json", exclude_defaults=True)
    assert dumped["scene_type"] == "sequel"
    assert Beat.model_validate(dumped).scene_type == SceneType.SEQUEL
