import pytest
from pydantic import ValidationError

from questfoundry.models.base import Stage
from questfoundry.models.craft import CraftConfig
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


def test_craft_config_defaults():
    cfg = CraftConfig(corpus="corpus/")
    assert cfg.folders == []
    assert cfg.top_k == 4
    assert cfg.max_queries == 5
    assert cfg.words_per_query == 200
    assert cfg.search_mode == "hybrid"
    assert cfg.embedding_model == "BAAI/bge-small-en-v1.5"


def test_craft_config_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CraftConfig(corpus="corpus/", vector_store="pinecone")


def test_craft_config_rejects_bad_search_mode():
    with pytest.raises(ValidationError):
        CraftConfig(corpus="corpus/", search_mode="semantic")
