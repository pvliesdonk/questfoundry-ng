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
