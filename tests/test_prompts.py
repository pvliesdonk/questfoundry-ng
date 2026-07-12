"""M6 prompt injection (design doc 02 §1): `_craft.j2`'s advisory block
renders through the real prompts directory via `runner._environment()`
— no `DictLoader` swap, because the contract under test IS which
shipped templates include the partial and which don't.
"""

from __future__ import annotations

from pathlib import Path

from questfoundry.pipeline import runner
from questfoundry.pipeline.stages.dream import _context as dream_context
from questfoundry.pipeline.stages.fill import _write_context_for
from questfoundry.project.io import scaffold_project

PROMPTS_DIR = Path(runner.PROMPTS_DIR)

SENTINEL = "CRAFT SENTINEL"


def _render(env, template_name: str, research: str, **context) -> str:
    template = env.get_template(template_name)
    return template.render(**context, notes="", repair_errors=[], research=research)


# ---------------------------------------------------------------------------
# dream.j2 — a plain advisory-partial consumer
# ---------------------------------------------------------------------------


def test_dream_prompt_includes_advisory_frame_and_sentinel_when_research_set(tmp_path):
    env = runner._environment()
    project = scaffold_project(tmp_path, "t", "micro")
    context = dream_context(project)

    rendered = _render(env, "dream.j2", SENTINEL, **context)

    assert "CRAFT NOTES" in rendered
    assert "reference only" in rendered
    assert SENTINEL in rendered


def test_dream_prompt_omits_craft_block_when_research_empty(tmp_path):
    env = runner._environment()
    project = scaffold_project(tmp_path, "t", "micro")
    context = dream_context(project)

    rendered = _render(env, "dream.j2", "", **context)

    assert "CRAFT NOTES" not in rendered
    assert "reference only" not in rendered


# ---------------------------------------------------------------------------
# fill_write.j2 — the fade guard (only while no neighboring prose exists)
# ---------------------------------------------------------------------------


def test_fill_write_omits_craft_block_when_window_is_non_empty(golden):
    env = runner._environment()
    context = _write_context_for("passage:p-arrival")(golden)
    # Force the guard's condition regardless of what this golden passage
    # naturally borders: a non-empty window alone must suppress the block.
    context["window"] = [{"passage": golden.graph.node("passage:p-arrival"), "label": "go"}]
    context["lookahead"] = []

    rendered = _render(env, "fill_write.j2", SENTINEL, **context)

    assert SENTINEL not in rendered
    assert "CRAFT NOTES" not in rendered


def test_fill_write_includes_craft_block_when_window_and_lookahead_empty(golden):
    env = runner._environment()
    context = _write_context_for("passage:p-arrival")(golden)
    context["window"] = []
    context["lookahead"] = []

    rendered = _render(env, "fill_write.j2", SENTINEL, **context)

    assert SENTINEL in rendered
    assert "CRAFT NOTES" in rendered


def test_fill_write_omits_craft_block_when_only_lookahead_is_non_empty(golden):
    env = runner._environment()
    context = _write_context_for("passage:p-arrival")(golden)
    context["window"] = []
    context["lookahead"] = [
        {"passage": golden.graph.node("passage:p-arrival"), "label": "go"}
    ]

    rendered = _render(env, "fill_write.j2", SENTINEL, **context)

    assert SENTINEL not in rendered
    assert "CRAFT NOTES" not in rendered


# ---------------------------------------------------------------------------
# Review templates are structurally immune (iron rule: never launder
# taste through a channel the author can't see) — checked at the
# template-source level since their review functions build their own
# context and never receive `research` (runner.py's `_run_pass` never
# renders them; `PassSpec.review` does its own rendering).
# ---------------------------------------------------------------------------


def test_fill_review_template_has_no_craft_include_or_research_reference():
    source = (PROMPTS_DIR / "fill_review.j2").read_text(encoding="utf-8")
    assert "_craft.j2" not in source
    assert "research" not in source


def test_dress_codex_review_template_has_no_craft_include_or_research_reference():
    source = (PROMPTS_DIR / "dress_codex_review.j2").read_text(encoding="utf-8")
    assert "_craft.j2" not in source
    assert "research" not in source


def test_fill_review_asks_for_the_structured_finding_schema():
    """The review-contract redesign (docs/plans/review-contract.md): the
    reviewer reports structured FINDINGS (rule / assessment / confidence /
    quote / reason / recovery_action), not a binary verdict + free-text
    issues. Taste is a warn, never a fail — figurative language cannot block."""
    source = (PROMPTS_DIR / "fill_review.j2").read_text(encoding="utf-8")
    assert "findings" in source
    for axis in ('"rule"', '"assessment"', '"confidence"', '"recovery_action"'):
        assert axis in source
    # the top-level verdict: approved auto-accepts, needs_work defers to engine
    assert '"approved"' in source and '"needs_work"' in source
    assert "TASTE IS A WARN, NEVER A FAIL" in source
    assert "simile" in source  # figurative language named as taste, not a rule
    # every stage rule name is offered to the reviewer as an enumerable clause
    for rule in ("voice_pov", "beat_infidelity", "state_dishonesty", "leakage"):
        assert rule in source


def test_fill_write_frames_micro_detail_as_exceptional_and_updatable():
    """The micro-detail redesign (author-directed, 2026-07-12): the write
    prompt must defuse the 'obliged to add something' reflex — at most one,
    only on a genuine addition, and a re-used key is an update, not a
    forbidden duplicate."""
    source = " ".join((PROMPTS_DIR / "fill_write.j2").read_text(encoding="utf-8").split())
    assert "not expected to add a micro_detail" in source
    assert "AT MOST ONE" in source
    assert "UPDATE, not a duplicate" in source


def test_fill_review_has_the_micro_detail_rule():
    """The redesign moves the 'does it add / does it conflict' judgment to the
    reviewer: a contradiction of an established fact is a defect, a gratuitous
    restatement a concern."""
    source = " ".join((PROMPTS_DIR / "fill_review.j2").read_text(encoding="utf-8").split())
    assert "micro_detail" in source
    assert "CONTRADICTS an established fact" in source


def test_fill_write_requires_per_item_notes_and_shows_prior_draft():
    """Rework-convergence lever (validated on gpt-oss:120b): on a repair the
    write prompt shows the rejected draft (the adapter is stateless) and
    requires a revision_notes entry for EVERY rejection item — a reviewer
    finding OR a mechanical requirement (the word-budget account that lifts a
    stuck ending from ~114 to ~200 words: treat mechanical == reviewed)."""
    source = " ".join((PROMPTS_DIR / "fill_write.j2").read_text(encoding="utf-8").split())
    assert "PREVIOUS DRAFT WAS REJECTED" in source
    assert "revision_notes" in source
    assert "For EVERY item in the list" in source
    # the word-budget miss must force a planned expansion, not blind re-derivation
    assert "name WHICH beat or moment you expand" in source


def test_fill_review_verifies_the_writers_revision_notes():
    """The reviewer must check the writer's per-finding account against the
    prose — a claimed fix absent from the text is itself a defect."""
    source = " ".join((PROMPTS_DIR / "fill_review.j2").read_text(encoding="utf-8").split())
    assert "WRITER'S ACCOUNT OF THIS REVISION" in source
    assert "Verify each claim against" in source


def test_fill_write_states_pov_externalization():
    """The prompt-quality fix (live: both tiers narrated a non-viewpoint
    character's plotting interiority, failing the POV rule): the write
    prompt must instruct that only the narrator's interiority may be
    stated and others are rendered through observable behavior."""
    source = (PROMPTS_DIR / "fill_write.j2").read_text(encoding="utf-8")
    assert "POINT OF VIEW IS LIMITED" in source
    assert "observable behavior" in source


# ---------------------------------------------------------------------------
# Deliberate exclusions named in the M6 contract (design doc 02 §1):
# review-shaped and mechanical passes never see craft notes either.
# ---------------------------------------------------------------------------


def test_polish_audit_template_has_no_craft_include():
    source = (PROMPTS_DIR / "polish_audit.j2").read_text(encoding="utf-8")
    assert "_craft.j2" not in source


def test_seed_order_template_has_no_craft_include():
    source = (PROMPTS_DIR / "seed_order.j2").read_text(encoding="utf-8")
    assert "_craft.j2" not in source


def test_dress_codewords_template_has_no_craft_include():
    source = (PROMPTS_DIR / "dress_codewords.j2").read_text(encoding="utf-8")
    assert "_craft.j2" not in source


# ---------------------------------------------------------------------------
# fill_write.j2 — input-role framing + the voice palette (plan: docs/plans/
# prose-quality.md W2/W3). The framing phrases are load-bearing prompt
# contract, so pin them: facts are constraints, the window is continuity,
# micro-details are notes.
# ---------------------------------------------------------------------------


def test_fill_write_states_the_input_roles(golden):
    env = runner._environment()
    # p-tremor borders written prose on both sides, so every framed
    # block renders
    context = _write_context_for("passage:p-tremor")(golden)
    rendered = _render(env, "fill_write.j2", "", **context)
    assert "CONSTRAINTS, not choreography" in rendered
    assert "continuity, not a style template" in rendered
    assert "note form" in rendered


def test_fill_write_renders_the_voice_palette_only_when_set(golden):
    env = runner._environment()
    context = _write_context_for("passage:p-arrival")(golden)
    rendered = _render(env, "fill_write.j2", "", **context)
    assert "- Imagery: tide, weather" in rendered
    assert "- Dialogue: brief and unornamented" in rendered
    golden.voice.imagery = ""
    golden.voice.dialogue = ""
    rendered = _render(env, "fill_write.j2", "", **_write_context_for("passage:p-arrival")(golden))
    assert "- Imagery:" not in rendered and "- Dialogue:" not in rendered


# ---------------------------------------------------------------------------
# Pipeline-wide prompt-quality sweep (2026-07-12): each landed fix makes a
# checkable promise in the template source.
# ---------------------------------------------------------------------------


def test_finalize_states_coined_ids_must_be_fresh():
    """POLISH F1 (the live finalize collision root cause): the model must be
    told its coined beat ids are NEW and must be unique."""
    source = (PROMPTS_DIR / "polish_finalize.j2").read_text(encoding="utf-8")
    assert "names a NEW beat" in source
    assert "colliding id is rejected" in source


def test_contextualize_renders_the_entities_it_requires():
    """GROW HIGH: the rule 'keep the exact entities' now has the entities in
    context, not withheld."""
    source = (PROMPTS_DIR / "grow_contextualize.j2").read_text(encoding="utf-8")
    assert "t.beat.entities" in source
    assert "exact entities listed with it above" in source


def test_codex_review_asks_for_the_structured_finding_schema():
    """The review-contract redesign: the codex reviewer shares FILL's
    structured-finding envelope (its own rule enum), so spoiler safety is
    reported as findings, not a binary verdict + free-text issues."""
    source = (PROMPTS_DIR / "dress_codex_review.j2").read_text(encoding="utf-8")
    assert "findings" in source
    for axis in ('"rule"', '"assessment"', '"confidence"', '"recovery_action"'):
        assert axis in source
    assert '"approved"' in source and '"needs_work"' in source
    assert "TASTE IS A WARN, NEVER A FAIL" in source
    for rule in ("conditional_stated_as_fact", "machinery_leakage", "ending_title_named"):
        assert rule in source


def test_producers_frame_how_to_weigh_review_findings():
    """The review-contract redesign puts judgment with the producer: on a
    rework the write/codex prompt must tell the writer FAIL findings are
    blocking while WARN / low-confidence ones are weighed, not mandated."""
    for name in ("fill_write.j2", "dress_codex.j2"):
        source = (PROMPTS_DIR / name).read_text(encoding="utf-8")
        assert "marked FAIL is blocking" in source
        assert "weigh and decide, not a mandate" in source
        assert "do not over-correct" in source


def test_brainstorm_states_the_output_count_plainly():
    """BRAINSTORM H2: the output total is stated as a generate-now constraint,
    not conflated with the post-triage branched count."""
    source = (PROMPTS_DIR / "brainstorm.j2").read_text(encoding="utf-8")
    assert "Output exactly" in source and "this total, not fewer" in source


def test_voice_banned_field_forbids_word_and_vague_bans():
    """The model-coined-constraint class (live gpt-oss:120b): the voice's
    banned patterns are enforced literally by fill_review, so the voice
    prompt must forbid coining a common-word ban ("as"/"like") or a vague
    label ("direct metaphor") that traps every passage."""
    source = (PROMPTS_DIR / "fill_voice.j2").read_text(encoding="utf-8")
    assert "enforces these VERBATIM" in source
    assert "ban a common word" in source
    assert "not a simile" in source  # the "as" example
