"""DRESS — art and codex (design doc 02, 01 §7) and gate G6.

Violating constructions first (AGENTS.md iron rule 6): every mutation
guard and every G6 check gets a construction that trips it, plus the
apply-level repair messages that must let a model converge from the
message alone.
"""

from __future__ import annotations

import copy

import pytest

from questfoundry.graph import mutations
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import Stage
from questfoundry.pipeline.stages.dress import (
    CodewordItem,
    CodewordsProposal,
    CodexItem,
    CodexProposal,
    DirectionProposal,
    ProfileItem,
    _codewords_apply,
    _codex_apply,
    _direction_apply,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project


def g6_errors(g, vision, enrichment):
    issues = run_checks(g, vision, Stage.DRESS, enrichment=enrichment)
    return [i for i in issues if i.check == "G6" and i.severity == Severity.ERROR]


# -- mutations.set_flag_codeword -----------------------------------------------


def test_set_flag_codeword_rejects_bad_format(golden):
    with pytest.raises(MutationError, match="A-Z"):
        mutations.set_flag_codeword(golden.graph, "flag:bound-to-light", "lowercase")


def test_set_flag_codeword_rejects_too_short_or_too_long(golden):
    with pytest.raises(MutationError):
        mutations.set_flag_codeword(golden.graph, "flag:bound-to-light", "AB")
    with pytest.raises(MutationError):
        mutations.set_flag_codeword(golden.graph, "flag:bound-to-light", "A" * 13)


def test_set_flag_codeword_rejects_duplicate(golden):
    with pytest.raises(MutationError, match="already used"):
        mutations.set_flag_codeword(golden.graph, "flag:bound-to-light", "CONFESSED")


def test_set_flag_codeword_rejects_changing_existing_value(golden):
    with pytest.raises(MutationError, match="stable"):
        mutations.set_flag_codeword(golden.graph, "flag:elias-knows", "DIFFERENT")


def test_set_flag_codeword_same_value_is_a_noop(golden):
    mutations.set_flag_codeword(golden.graph, "flag:elias-knows", "CONFESSED")
    assert golden.graph.node("flag:elias-knows").codeword == "CONFESSED"


def test_set_flag_codeword_rejects_non_flag():
    from questfoundry.graph.store import StoryGraph

    with pytest.raises(MutationError, match="not a flag"):
        mutations.set_flag_codeword(StoryGraph(), "flag:nope", "WORD")


# -- gate G6 ---------------------------------------------------------------------


def test_g6_missing_profile_flagged(golden):
    enrichment = golden.enrichment.model_copy(deep=True)
    enrichment.profiles = [p for p in enrichment.profiles if p.entity != "character:sleeper"]
    errors = g6_errors(golden.graph, golden.vision, enrichment)
    assert any(
        "character:sleeper" in i.message and "no visual profile" in i.message for i in errors
    )


def test_g6_brief_entity_outside_passage_flagged(golden):
    enrichment = golden.enrichment.model_copy(deep=True)
    brief = enrichment.briefs[0]
    passage = golden.graph.node(brief.passage)
    assert "character:sleeper" not in passage.entities  # the fixture's own assumption
    brief.entities = [*brief.entities, "character:sleeper"]
    errors = g6_errors(golden.graph, golden.vision, enrichment)
    assert any("not in that passage" in i.message for i in errors)


def test_g6_nondense_priorities_flagged(golden):
    enrichment = golden.enrichment.model_copy(deep=True)
    enrichment.briefs[0].priority = 5
    errors = g6_errors(golden.graph, golden.vision, enrichment)
    assert any("dense" in i.message for i in errors)


def test_g6_missing_codex_entry_for_anchoring_entity_flagged(golden):
    enrichment = golden.enrichment.model_copy(deep=True)
    enrichment.codex = [c for c in enrichment.codex if c.entity != "character:sleeper"]
    errors = g6_errors(golden.graph, golden.vision, enrichment)
    assert any("character:sleeper" in i.message and "no codex entry" in i.message for i in errors)


def test_g6_projected_flag_without_codeword_flagged(golden):
    g = copy.deepcopy(golden.graph)
    g.node("flag:elias-knows").codeword = None
    errors = g6_errors(g, golden.vision, golden.enrichment)
    assert any("flag:elias-knows" in i.message and "no codeword" in i.message for i in errors)


def test_g6_duplicate_codewords_flagged(golden):
    # simulate a hand-edited flags.yaml: two flags share a codeword, which
    # only the gate catches (the loader doesn't route through the
    # mutation layer's uniqueness check field-by-field).
    g = copy.deepcopy(golden.graph)
    g.node("flag:bound-to-light").codeword = "CONFESSED"
    errors = g6_errors(g, golden.vision, golden.enrichment)
    assert any("used by both" in i.message for i in errors)


def test_g6_malformed_codeword_flagged(golden):
    g = copy.deepcopy(golden.graph)
    g.node("flag:bound-to-light").codeword = "not-uppercase"
    errors = g6_errors(g, golden.vision, golden.enrichment)
    assert any("flag:bound-to-light" in i.message for i in errors)


def test_golden_enrichment_passes_g6_cleanly(golden):
    assert g6_errors(golden.graph, golden.vision, golden.enrichment) == []


# -- apply-level repairs: messages must name the expected ids -------------------


def test_direction_apply_rejects_unknown_entity(golden):
    proposal = DirectionProposal(
        style="s",
        palette="p",
        profiles=[ProfileItem(entity="character:nope", appearance="x")],
    )
    with pytest.raises(ApplyError) as exc:
        _direction_apply(proposal, golden)
    message = str(exc.value)
    assert "character:nope" in message
    for entity_id in (
        "character:cartographer",
        "character:keeper",
        "character:sleeper",
        "location:lighthouse",
    ):
        assert entity_id in message


def test_direction_apply_rejects_duplicate_profile(golden):
    from questfoundry.models.world import Entity

    all_ids = [e.id for e in golden.graph.nodes_of(Entity) if e.retained]
    profiles = [ProfileItem(entity=eid, appearance="x") for eid in all_ids]
    profiles.append(ProfileItem(entity=all_ids[0], appearance="y"))
    proposal = DirectionProposal(style="s", palette="p", profiles=profiles)
    with pytest.raises(ApplyError, match="more than one profile"):
        _direction_apply(proposal, golden)


def test_codex_apply_rejects_wrong_entity_set(golden):
    proposal = CodexProposal(
        entries=[CodexItem(entity="character:cartographer", title="T", body="word " * 70)]
    )
    with pytest.raises(ApplyError) as exc:
        _codex_apply(proposal, golden)
    message = str(exc.value)
    assert "character:keeper" in message
    assert "character:sleeper" in message
    assert "location:lighthouse" in message


def test_codex_apply_rejects_out_of_range_body_length(golden):
    from questfoundry.models.base import EdgeKind
    from questfoundry.models.world import Entity

    anchored = {e.dst for e in golden.graph.edges if e.kind == EdgeKind.ANCHORED_TO}
    required = sorted(
        e.id for e in golden.graph.nodes_of(Entity) if e.retained and e.id in anchored
    )
    entries = [CodexItem(entity=eid, title="T", body="word " * 70) for eid in required]
    entries[0].body = "too short"
    proposal = CodexProposal(entries=entries)
    with pytest.raises(ApplyError, match="60-200 words"):
        _codex_apply(proposal, golden)


def test_codewords_apply_rejects_coverage_mismatch(golden):
    golden.graph.node("flag:elias-knows").codeword = None  # reopen it for this test
    proposal = CodewordsProposal(
        codewords=[CodewordItem(flag="flag:bound-to-light", codeword="HUSH")]
    )
    with pytest.raises(ApplyError) as exc:
        _codewords_apply(proposal, golden)
    assert "flag:elias-knows" in str(exc.value)


# -- round-trip: enrichment + codewords are lossless -----------------------------


def test_enrichment_and_codewords_roundtrip(golden, tmp_path):
    from questfoundry.project import load_project, save_project

    save_project(
        Project(
            root=tmp_path,
            name=golden.name,
            stage=golden.stage,
            vision=golden.vision,
            graph=golden.graph,
            voice=golden.voice,
            ifid=golden.ifid,
            enrichment=golden.enrichment,
        )
    )
    reloaded = load_project(tmp_path)
    assert reloaded.enrichment.direction == golden.enrichment.direction
    # file-per-item collections reload in filename order, not list order —
    # compare by content, keyed the way the model itself is keyed
    assert sorted(reloaded.enrichment.briefs, key=lambda b: b.priority) == sorted(
        golden.enrichment.briefs, key=lambda b: b.priority
    )
    assert sorted(reloaded.enrichment.codex, key=lambda c: c.entity) == sorted(
        golden.enrichment.codex, key=lambda c: c.entity
    )
    assert reloaded.graph.node("flag:elias-knows").codeword == "CONFESSED"
    issues = run_checks(
        reloaded.graph, reloaded.vision, reloaded.stage, enrichment=reloaded.enrichment
    )
    assert [i for i in issues if i.severity == Severity.ERROR] == []


# -- runtime_json: codex/art -------------------------------------------------------


def test_runtime_json_codex_populated(golden):
    from questfoundry.export.runtime_json import build_runtime, validate_runtime

    data = build_runtime(golden)
    assert data["codex"]
    assert {c["entity"] for c in data["codex"]} == {c.entity for c in golden.enrichment.codex}
    assert validate_runtime(data) == []


def test_runtime_json_art_empty_without_images_on_disk(golden):
    from questfoundry.export.runtime_json import build_runtime

    # the golden fixture ships no rendered art/images/*.png, so no brief
    # is eligible to ship yet (design doc 04 §1: emitted only if the file exists)
    data = build_runtime(golden)
    assert data["art"] == []


def test_runtime_json_art_populated_when_image_exists(golden, tmp_path):
    from questfoundry.export.runtime_json import build_runtime

    brief = golden.enrichment.briefs[0]
    slug = brief.passage.split(":", 1)[1]
    image_dir = tmp_path / "art" / "images"
    image_dir.mkdir(parents=True)
    (image_dir / f"{slug}.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    project = Project(
        root=tmp_path,
        name=golden.name,
        stage=golden.stage,
        vision=golden.vision,
        graph=golden.graph,
        voice=golden.voice,
        enrichment=golden.enrichment,
    )
    data = build_runtime(project)
    assert data["art"] == [
        {"passage": slug, "image": f"art/images/{slug}.png", "caption": brief.caption}
    ]


def test_runtime_json_validate_rejects_codex_for_unknown_entity(golden):
    from questfoundry.export.runtime_json import build_runtime, validate_runtime

    data = build_runtime(golden)
    data["codex"].append({"entity": "character:nope", "title": "t", "body": "b"})
    problems = validate_runtime(data)
    assert any("character:nope" in p for p in problems)


def test_runtime_json_validate_rejects_art_for_unknown_passage(golden):
    from questfoundry.export.runtime_json import build_runtime, validate_runtime

    data = build_runtime(golden)
    data["art"].append(
        {"passage": "p-nowhere", "image": "art/images/p-nowhere.png", "caption": "x"}
    )
    problems = validate_runtime(data)
    assert any("p-nowhere" in p for p in problems)


# -- html: the codex panel --------------------------------------------------------


def test_html_contains_codex_panel_when_entries_exist(golden):
    from questfoundry.export.html import build_html

    html = build_html(golden)
    assert 'id="codex"' in html
    assert "The Stilt Light" in html  # one of the codex entry titles, rendered


def test_html_omits_codex_panel_when_no_entries(golden):
    from questfoundry.export.html import build_html

    enrichment = golden.enrichment.model_copy(deep=True)
    enrichment.codex = []
    project = Project(
        root=golden.root,
        name=golden.name,
        stage=golden.stage,
        vision=golden.vision,
        graph=golden.graph,
        voice=golden.voice,
        enrichment=enrichment,
    )
    html = build_html(project)
    assert 'id="codex"' not in html


def test_codex_double_fail_escalates_to_architect_arbitration(golden, monkeypatch):
    """DRESS's codex review shares FILL's anchored + arbitrated contract
    (validation run, 2026-07-09: the reviewer quoted the conditional-
    material list from its own context as 'the entry's assertion'). A
    second failure is architect-arbitrated; the arbiter's verdict is
    final in both directions."""
    from jinja2 import DictLoader, Environment

    from questfoundry.pipeline import runner
    from questfoundry.pipeline.review import ReviewFinding, ReviewVerdict
    from questfoundry.pipeline.stages.dress import _codex_review_for

    def _fail(reason):
        return ReviewVerdict(
            verdict="needs_work",
            findings=[
                ReviewFinding(
                    rule="conditional_stated_as_fact",
                    assessment="fail",
                    confidence="high",
                    quote="the entry sentence",
                    reason=reason,
                    recovery_action="pose it as an open question",
                )
            ],
        )

    class ScriptedAdapter:
        def __init__(self, script):
            self.script = list(script)
            self.prompts: list[tuple[str, str]] = []

        def complete(self, *, system, prompt, schema, role):
            expected_role, verdict = self.script.pop(0)
            assert role == expected_role
            self.prompts.append((role, prompt))
            return verdict

    env = Environment(
        loader=DictLoader(
            {
                "dress_codex_review.j2": (
                    "{% if arbitration %}ARB[{{ arbitration | join(';') }}]{% endif %}"
                    "prior[{{ prior_issues | join(';') }}]"
                )
            }
        )
    )
    monkeypatch.setattr(runner, "_environment", lambda: env)
    proposal = CodexProposal(entries=[CodexItem(entity="entity:x", title="t", body="b")])

    # a needs_work verdict carrying only a warn is approved by the engine
    review = _codex_review_for()
    warn = ReviewVerdict(
        verdict="needs_work",
        findings=[
            ReviewFinding(
                rule="machinery_leakage",
                assessment="warn",
                confidence="low",
                quote="x",
                reason="taste",
                recovery_action="consider",
            )
        ],
    )
    assert review(proposal, golden, ScriptedAdapter([("utility", warn)])) == []

    # arbitration overturns the second strike: entries accepted
    review = _codex_review_for()
    adapter = ScriptedAdapter(
        [
            ("utility", _fail("real defect")),
            ("utility", _fail("fresh taste")),
            ("architect", ReviewVerdict(verdict="approved", findings=[])),
        ]
    )
    assert "real defect" in review(proposal, golden, adapter)[0]
    assert review(proposal, golden, adapter) == []
    assert adapter.prompts[-1][0] == "architect"
    assert "ARB[" in adapter.prompts[-1][1] and "fresh taste" in adapter.prompts[-1][1]
    assert "prior[" in adapter.prompts[-1][1] and "real defect" in adapter.prompts[-1][1]

    # arbitration upholds: the halt is real and carries the arbiter's finding
    review = _codex_review_for()
    adapter = ScriptedAdapter(
        [
            ("utility", _fail("real defect")),
            ("utility", _fail("still broken")),
            ("architect", _fail("confirmed")),
        ]
    )
    assert "real defect" in review(proposal, golden, adapter)[0]
    assert "confirmed" in review(proposal, golden, adapter)[0]
