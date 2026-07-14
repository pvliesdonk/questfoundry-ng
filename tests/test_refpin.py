"""The reference-pinning discipline (#40, generalized across every stage):
a proposal field that names an already-existing id is pinned to a
`Literal` enum of the real ids, so a dangling reference can't be emitted
under grammar-constrained decoding and is named back on a miss. These
tests cover the shared helper (pipeline/refpin.py) and assert every stage
builder wires the enum onto its reference fields.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from questfoundry.pipeline.refpin import entity_ref_ids, pin, retained_entity_ids
from questfoundry.pipeline.stages import dress, fill, polish, seed
from questfoundry.project import load_project
from tests.conftest import GOLDEN

# -- the shared helper --------------------------------------------------------


class _Leaf(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    tags: list[str] = []
    free: str = ""


class _Outer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_Leaf] = Field(min_length=2)
    note: str = ""


def test_pin_scalar_field_becomes_an_enum_and_rejects_dangling():
    schema = pin(_Leaf, "_Leaf", {("_Leaf", "ref"): ["a:1", "b:2"]})
    assert schema.model_json_schema()["properties"]["ref"]["enum"] == ["a:1", "b:2"]
    assert schema.model_validate({"ref": "a:1"}).ref == "a:1"
    with pytest.raises(ValidationError):
        schema.model_validate({"ref": "c:3"})


def test_pin_list_field_becomes_a_list_of_enum():
    schema = pin(_Leaf, "_Leaf", {("_Leaf", "tags"): ["x", "y"]})
    assert schema.model_json_schema()["properties"]["tags"]["items"]["enum"] == ["x", "y"]
    with pytest.raises(ValidationError):
        schema.model_validate({"ref": "r", "tags": ["z"]})


def test_pin_single_value_renders_as_const():
    schema = pin(_Leaf, "_Leaf", {("_Leaf", "ref"): ["only:1"]})
    # const is grammar-safe (test_proposal_schemas allows it) and tighter
    assert schema.model_json_schema()["properties"]["ref"]["const"] == "only:1"


def test_pin_recurses_and_preserves_field_constraints():
    schema = pin(_Outer, "_Outer", {("_Leaf", "ref"): ["a:1", "a:2"]})
    js = schema.model_json_schema()
    assert js["properties"]["items"]["minItems"] == 2  # Field(min_length=2) survives
    assert js["$defs"]["_Leaf"]["properties"]["ref"]["enum"] == ["a:1", "a:2"]
    # rebuilt schema still validates/applies as the base (subclass)
    assert issubclass(schema, _Outer)


def test_pin_empty_ids_leave_the_model_unchanged():
    assert pin(_Leaf, "_Leaf", {("_Leaf", "ref"): []}) is _Leaf
    assert pin(_Outer, "_Outer", {("_Leaf", "missing"): ["a"]}) is _Outer


def test_pin_default_preserved_for_optional_field():
    schema = pin(_Leaf, "_Leaf", {("_Leaf", "tags"): ["x"]})
    assert schema.model_validate({"ref": "r"}).tags == []  # default survives the re-type


class _Optional(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maybe: str | None = None


def test_pin_refuses_non_str_field_instead_of_silently_dropping_optional():
    # a `str | None` ref field would lose its `| None` if pinned blindly;
    # pin fails loud so the next author pins it deliberately
    with pytest.raises(TypeError, match="only str / list"):
        pin(_Optional, "_Optional", {("_Optional", "maybe"): ["a", "b"]})


# -- the entity-id helpers ----------------------------------------------------


class _Ent:
    def __init__(self, id: str, retained: bool = True):
        self.id = id
        self.retained = retained


class _Graph:
    def __init__(self, ents):
        self._ents = ents

    def nodes_of(self, _cls):
        return self._ents


def test_retained_entity_ids_are_exact_and_exclude_cut():
    g = _Graph([_Ent("character:wren"), _Ent("location:lock", retained=False)])
    assert retained_entity_ids(g) == ["character:wren"]  # exact ids, cut excluded


def test_entity_ref_ids_add_unambiguous_slugs_only():
    # two entities share the slug "twin" across kinds -> that slug is ambiguous
    g = _Graph([_Ent("character:wren"), _Ent("character:twin"), _Ent("place:twin")])
    refs = entity_ref_ids(g)
    assert "character:wren" in refs and "wren" in refs  # unambiguous slug included
    assert "twin" not in refs  # ambiguous slug excluded (resolve_entity_ref would reject it)


# -- every stage builder wires the enum (on the golden story) ------------------


@pytest.fixture()
def golden():
    return load_project(GOLDEN)


def test_seed_scaffold_pins_dispositions_and_rejects_dangling_dilemma(golden):
    defs = seed.scaffold_proposal_schema(golden).model_json_schema()["$defs"]
    assert defs["DilemmaScaffold"]["properties"]["dilemma"]["enum"] == [
        "dilemma:bargain",
        "dilemma:truth",
    ]
    assert defs["LockedScaffold"]["properties"]["dilemma"]["const"] == "dilemma:second-keeper"
    assert "enum" in defs["PathScaffold"]["properties"]["path"]
    assert "enum" in defs["BeatSpec"]["properties"]["entities"]["items"]


def test_seed_order_pins_relation_dilemmas(golden):
    schema = seed.order_proposal_schema(golden)
    props = schema.model_json_schema()["$defs"]["RelationSpec"]["properties"]
    assert "dilemma:truth" in props["a"]["enum"] and "dilemma:truth" in props["b"]["enum"]


def test_polish_finalize_rejects_the_live_invented_world(golden):
    # the gpt-oss:120b cloud failure: world='share-legend' on a single-hard
    # story whose only convergence world is "" -> now unrepresentable
    schema = polish.finalize_proposal_schema(golden)
    with pytest.raises(ValidationError):
        schema.model_validate(
            {"residue": [{"dilemma": "dilemma:truth", "world": "invented", "path": "path:tell",
                          "id": "beat:x", "summary": "s"}]}
        )
    schema.model_validate(
        {"residue": [{"dilemma": "dilemma:truth", "world": "", "path": "path:tell",
                      "id": "beat:x", "summary": "s"}]}
    )


def test_polish_finalize_forbids_false_branches_without_long_runs(golden, monkeypatch):
    # a false branch splices only into a long linear run; with none, the
    # list must be empty (the enum can't say "no items") — the live
    # gpt-oss:120b cloud failure was a proposed diamond where none fit.
    # texture_worlds gets the same list discipline when no sites are offered.
    with_runs = polish.finalize_proposal_schema(golden)
    assert "maxItems" not in with_runs.model_json_schema()["properties"]["false_branches"]

    monkeypatch.setattr(polish, "_texture_and_cadence", lambda project: ([], [], set()))
    without = polish.finalize_proposal_schema(golden)
    props = without.model_json_schema()["properties"]
    assert props["false_branches"]["maxItems"] == 0
    assert props["texture_worlds"]["maxItems"] == 0
    with pytest.raises(ValidationError):
        without.model_validate(
            {"residue": [], "false_branches": [
                {"before": "a", "after": "b", "arms": [{"id": "x", "summary": "s"}]}
            ]}
        )
    with pytest.raises(ValidationError):
        without.model_validate(
            {"texture_worlds": [
                {"site": 0, "premise": "p", "beats": [{"id": "x", "summary": "s"}]}
            ]}
        )


def test_polish_audit_pins_passages_and_flags_with_slug_affordance(golden):
    schema = polish.audit_proposal_schema(golden)
    props = schema.model_json_schema()["$defs"]["AuditEntry"]["properties"]
    passage_enum = props["passage"]["enum"]
    # both forms — the apply accepts the bare slug too
    assert "passage:p-tremor" in passage_enum and "p-tremor" in passage_enum
    assert "enum" in props["irrelevant"]["items"]


def test_dress_direction_pins_exact_entity_ids_no_slug(golden):
    # direction validates by exact membership, so the enum is exact ids only
    schema = dress._passes(golden)[0].schema
    entity = schema.model_json_schema()["$defs"]["ProfileItem"]["properties"]["entity"]
    assert "character:keeper" in entity["enum"]
    assert "keeper" not in entity["enum"]  # no bare-slug: apply uses exact `in retained`


def test_fill_write_pins_micro_detail_entity_with_slug_affordance(golden):
    write = next(s for s in fill._passes(golden) if s.name.startswith("write:"))
    entity = write.schema.model_json_schema()["$defs"]["MicroDetail"]["properties"]["entity"]
    # resolve_entity_ref set: exact id and its unambiguous slug both allowed
    assert "character:keeper" in entity["enum"] and "keeper" in entity["enum"]


def test_polish_arcs_pins_entities_beats_and_paths(golden):
    """The arcs pass (plan: docs/plans/prose-quality.md W5): `entity` is
    pinned to every retained entity (author doctrine 2026-07-12: all
    four categories are arc-eligible — unarced means scenery), plus
    unambiguous slugs; `pivots[].beat` to real beats, `ends[].path` to
    explored paths — an invented reference is unrepresentable."""
    defs = polish.arcs_proposal_schema(golden).model_json_schema()["$defs"]
    entity_enum = set(defs["ArcSpec"]["properties"]["entity"]["enum"])
    assert "character:keeper" in entity_enum and "keeper" in entity_enum
    assert "location:lighthouse" in entity_enum and "lighthouse" in entity_enum
    assert "beat:returned-boat" in set(defs["ArcPivotSpec"]["properties"]["beat"]["enum"])
    assert set(defs["PathEndSpec"]["properties"]["path"]["enum"]) == {
        "path:tell",
        "path:hide",
        "path:keep",
        "path:break",
        "path:mother-left",
    }
