import pytest
from pydantic import ValidationError

from questfoundry.models.base import Stage
from questfoundry.models.structure import Beat, BeatClass, DilemmaImpact, ImpactEffect
from questfoundry.models.world import Entity


def test_node_id_must_be_namespaced():
    with pytest.raises(ValidationError):
        Entity(id="keeper", created_by=Stage.BRAINSTORM, name="x", concept="c")


def test_entity_category_comes_from_id_prefix():
    entity = Entity(id="location:dock", created_by=Stage.BRAINSTORM, name="Dock", concept="c")
    assert entity.category == "location"
    with pytest.raises(ValidationError):
        Entity(id="widget:dock", created_by=Stage.BRAINSTORM, name="Dock", concept="c")


def test_structural_beat_rejects_impacts():
    with pytest.raises(ValidationError):
        Beat(
            id="beat:x",
            created_by=Stage.SEED,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose="bridge",
            dilemma_impacts=[DilemmaImpact(dilemma="dilemma:d", effect=ImpactEffect.ADVANCES)],
        )


def test_structural_beat_requires_purpose():
    with pytest.raises(ValidationError):
        Beat(id="beat:x", created_by=Stage.SEED, summary="s", beat_class=BeatClass.STRUCTURAL)


def test_narrative_beat_requires_impacts():
    with pytest.raises(ValidationError):
        Beat(id="beat:x", created_by=Stage.SEED, summary="s", beat_class=BeatClass.NARRATIVE)
