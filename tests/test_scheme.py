"""The POV scheme roster (docs/plans/pov-sequences.md PR-A): the
`pov_head`/`interlude_carrier` entity marks and their mutations, the GROW
scheme pass (schema pins + apply), invariant I17 (declared-scheme
conformance), the roster-pinned annotate schema, and the annotate apply's
interlude-carrier rule. Failure modes 3/7/8/10/12/15/16 of the plan's
table live here; the sequence-unit machinery (PR-B) does not."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from questfoundry.graph import mutations
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.world import Entity
from questfoundry.pipeline.stages.grow import (
    SchemeProposal,
    _scheme_apply,
    _scheme_context,
    annotate_proposal_schema,
    scheme_proposal_schema,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.conftest import make_dilemma, narrative_beat
from tests.test_invariants import errors_for


def _character(g: StoryGraph, slug: str, retained: bool = True) -> Entity:
    e = Entity(
        id=f"character:{slug}",
        created_by=Stage.BRAINSTORM,
        name=slug.title(),
        concept="c",
        retained=retained,
    )
    mutations.add_entity(g, e)
    return e


def _location(g: StoryGraph, slug: str) -> Entity:
    e = Entity(id=f"location:{slug}", created_by=Stage.BRAINSTORM, name=slug, concept="c")
    mutations.add_entity(g, e)
    return e


@pytest.fixture()
def story(vision):
    """A minimal annotated story: one dilemma, three characters, one beat."""
    g = StoryGraph()
    _, path_a, _ = make_dilemma(g, "d")
    _character(g, "eleanor")
    _character(g, "charles")
    _character(g, "milo")
    _location(g, "manor")
    beat = narrative_beat("b1", "dilemma:d")
    mutations.add_beat(g, beat, [path_a])
    return g


@pytest.fixture()
def project(tmp_path, vision, story) -> Project:
    return Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=story)


# -- mutations -----------------------------------------------------------------


def test_set_pov_head_marks_a_character(story):
    mutations.set_pov_head(story, "character:eleanor", True)
    assert story.node("character:eleanor").pov_head is True
    mutations.set_pov_head(story, "character:eleanor", False)
    assert story.node("character:eleanor").pov_head is False


def test_set_pov_head_rejects_non_character(story):
    with pytest.raises(MutationError, match="not a character"):
        mutations.set_pov_head(story, "location:manor", True)


def test_set_interlude_carrier_marks_a_character(story):
    mutations.set_interlude_carrier(story, "character:milo", True)
    assert story.node("character:milo").interlude_carrier is True


def test_set_interlude_carrier_rejects_non_character(story):
    with pytest.raises(MutationError, match="not a character"):
        mutations.set_interlude_carrier(story, "location:manor", True)


# -- I17: declared-scheme conformance ------------------------------------------


def _head(g: StoryGraph, beat_id: str, viewpoint: str, interlude: bool = False) -> None:
    beat = g.node(beat_id)
    beat.viewpoint = viewpoint
    beat.interlude = interlude


def test_i17_off_roster_head_is_an_error(story, vision):
    mutations.set_pov_head(story, "character:eleanor", True)
    _head(story, "beat:b1", "character:charles")
    issues = errors_for("I17", story, vision)
    assert any("character:charles" in i.message for i in issues)


def test_i17_roster_head_is_clean(story, vision):
    mutations.set_pov_head(story, "character:eleanor", True)
    _head(story, "beat:b1", "character:eleanor")
    assert errors_for("I17", story, vision) == []


def test_i17_skips_entirely_without_a_roster(story, vision):
    # pre-roster projects: any head is legal (graceful degradation)
    _head(story, "beat:b1", "character:charles")
    assert errors_for("I17", story, vision) == []


def test_i17_interlude_head_is_the_carrier_even_off_roster(story, vision):
    mutations.set_pov_head(story, "character:eleanor", True)
    mutations.set_interlude_carrier(story, "character:milo", True)
    _head(story, "beat:b1", "character:milo", interlude=True)
    assert errors_for("I17", story, vision) == []


def test_i17_interlude_head_not_the_carrier_is_an_error(story, vision):
    mutations.set_pov_head(story, "character:eleanor", True)
    mutations.set_interlude_carrier(story, "character:milo", True)
    _head(story, "beat:b1", "character:eleanor", interlude=True)
    issues = errors_for("I17", story, vision)
    assert any("carrier" in i.message for i in issues)


def test_i17_interlude_without_any_carrier_is_an_error(story, vision):
    mutations.set_pov_head(story, "character:eleanor", True)
    _head(story, "beat:b1", "character:eleanor", interlude=True)
    issues = errors_for("I17", story, vision)
    assert any("carrier" in i.message for i in issues)


def test_i17_two_carriers_is_an_error(story, vision):
    # only reachable by hand edit: the scheme schema carries one interlude_head
    mutations.set_pov_head(story, "character:eleanor", True)
    mutations.set_interlude_carrier(story, "character:milo", True)
    mutations.set_interlude_carrier(story, "character:charles", True)
    issues = errors_for("I17", story, vision)
    assert any("carrier" in i.message for i in issues)


# -- the scheme pass -----------------------------------------------------------


def test_scheme_schema_pins_heads_to_retained_characters(project):
    _character(project.graph, "ghost", retained=False)
    schema = scheme_proposal_schema(project)
    fields = schema.model_fields
    # enum-pinned: an off-cast or unretained id is unrepresentable
    with pytest.raises(ValidationError):
        schema.model_validate({"heads": ["character:ghost"], "interlude_head": ""})
    with pytest.raises(ValidationError):
        schema.model_validate({"heads": ["location:manor"], "interlude_head": ""})
    ok = schema.model_validate(
        {"heads": ["character:eleanor"], "interlude_head": "character:milo"}
    )
    assert ok.heads == ["character:eleanor"]
    assert "heads" in fields


def test_scheme_schema_requires_at_least_one_head(project):
    schema = scheme_proposal_schema(project)
    with pytest.raises(ValidationError):
        schema.model_validate({"heads": [], "interlude_head": ""})


def test_scheme_apply_sets_marks_and_logs(project):
    proposal = SchemeProposal(
        heads=["character:eleanor", "character:charles"], interlude_head="character:milo"
    )
    log = _scheme_apply(proposal, project)
    g = project.graph
    assert g.node("character:eleanor").pov_head is True
    assert g.node("character:charles").pov_head is True
    assert g.node("character:milo").pov_head is False
    assert g.node("character:milo").interlude_carrier is True
    assert any("eleanor" in line for line in log)


def test_scheme_apply_clears_stale_marks_on_rerun(project):
    g = project.graph
    mutations.set_pov_head(g, "character:charles", True)
    mutations.set_interlude_carrier(g, "character:charles", True)
    _scheme_apply(SchemeProposal(heads=["character:eleanor"], interlude_head=""), project)
    assert g.node("character:charles").pov_head is False
    assert g.node("character:charles").interlude_carrier is False
    assert g.node("character:eleanor").pov_head is True


def test_scheme_context_renders_hint_and_cast(project):
    ctx = _scheme_context(project)
    assert "characters" in ctx
    ids = [c.id for c in ctx["characters"]]
    assert "character:eleanor" in ids and "location:manor" not in ids


# -- the roster pins the (per-beat, PR-A interim) annotate schema --------------


def test_annotate_viewpoint_enum_shrinks_to_roster_plus_carrier(project):
    g = project.graph
    mutations.set_pov_head(g, "character:eleanor", True)
    mutations.set_interlude_carrier(g, "character:milo", True)
    schema = annotate_proposal_schema(project)
    ann = {
        "beat": "beat:b1",
        "scene_type": "sequel",
        "narration_scope": "limited",
        "interlude": False,
    }
    ok = schema.model_validate({"annotations": [{**ann, "viewpoint": "character:eleanor"}]})
    assert ok.annotations[0].viewpoint == "character:eleanor"
    # the carrier is representable (interlude beats need it)...
    schema.model_validate({"annotations": [{**ann, "viewpoint": "character:milo"}]})
    # ...an off-roster head is not
    with pytest.raises(ValidationError):
        schema.model_validate({"annotations": [{**ann, "viewpoint": "character:charles"}]})


def test_annotate_viewpoint_enum_without_roster_is_all_retained(project):
    schema = annotate_proposal_schema(project)
    ann = {
        "beat": "beat:b1",
        "scene_type": "sequel",
        "narration_scope": "limited",
        "interlude": False,
    }
    ok = schema.model_validate({"annotations": [{**ann, "viewpoint": "character:charles"}]})
    assert ok.annotations[0].viewpoint == "character:charles"


def test_annotate_apply_holds_interlude_beats_to_the_carrier(project):
    # failure mode 15: an interlude beat's head is the carrier, mechanically
    from questfoundry.pipeline.stages.grow import _annotate_apply

    g = project.graph
    mutations.set_pov_head(g, "character:eleanor", True)
    mutations.set_interlude_carrier(g, "character:milo", True)
    schema = annotate_proposal_schema(project)
    proposal = schema.model_validate(
        {
            "annotations": [
                {
                    "beat": "beat:b1",
                    "scene_type": "sequel",
                    "narration_scope": "limited",
                    "viewpoint": "character:eleanor",
                    "interlude": True,
                }
            ]
        }
    )
    with pytest.raises(ApplyError, match="carrier"):
        _annotate_apply(proposal, project)
