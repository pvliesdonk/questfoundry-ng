"""The shared review contract (docs/plans/review-contract.md): the finding
schema and its per-review rule enum, the engine gate (proceed vs rework), and
the producer-facing renderer. The gate loops only on confident objective
defects; every finding still reaches the producer on a rework (full fidelity)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from questfoundry.pipeline.review import (
    ReviewFinding,
    ReviewVerdict,
    build_verdict_schema,
    evaluate_review,
    needs_rework,
    render_finding,
)


def _f(
    assessment: str, confidence: str, *, rule: str = "beat_infidelity", quote: str = "q"
) -> ReviewFinding:
    return ReviewFinding(
        rule=rule,
        assessment=assessment,
        confidence=confidence,
        quote=quote,
        reason="it breaks the rule",
        recovery_action="rewrite the line",
    )


def _needs_work(*findings: ReviewFinding) -> ReviewVerdict:
    return ReviewVerdict(verdict="needs_work", findings=list(findings))


# -- schema ------------------------------------------------------------------


def test_assessment_and_confidence_are_finite_enums():
    with pytest.raises(ValidationError):
        _f("broken", "high")  # not a valid assessment
    with pytest.raises(ValidationError):
        _f("fail", "certain")  # not a valid confidence


def test_quote_defaults_empty_for_absence_defects():
    # a missing beat has no offending text to quote; reason carries it
    f = ReviewFinding(
        rule="beat_infidelity",
        assessment="fail",
        confidence="high",
        reason="the discovery beat never happens",
        recovery_action="stage the discovery",
    )
    assert f.quote == ""


def test_build_verdict_schema_pins_rule_to_the_review_clause_set():
    schema = build_verdict_schema("FillReview", ("voice_pov", "leakage"))
    ok = schema.model_validate({"verdict": "needs_work", "findings": [{
        "rule": "leakage", "assessment": "fail", "confidence": "high",
        "quote": "flag:x", "reason": "names machinery", "recovery_action": "drop it",
    }]})
    assert ok.findings[0].rule == "leakage"
    with pytest.raises(ValidationError):
        schema.model_validate({"verdict": "needs_work", "findings": [{
            "rule": "banned_pattern",  # not in this review's clause set
            "assessment": "fail", "confidence": "high",
            "quote": "x", "reason": "y", "recovery_action": "z",
        }]})


def test_verdict_is_required():
    # the reviewer must state an outcome — an empty review is a deliberate
    # "approved", never a lazy default
    with pytest.raises(ValidationError):
        ReviewVerdict(findings=[])
    with pytest.raises(ValidationError):
        ReviewVerdict(verdict="clean")  # not a valid verdict value


# -- gate --------------------------------------------------------------------


def test_approved_auto_accepts_even_with_findings():
    # the top-level approval short-circuits; a wrong accept is the safe
    # asymmetry (deterministic checks still guard structure)
    v = ReviewVerdict(verdict="approved", findings=[_f("fail", "high")])
    assert needs_rework(v) is False
    assert evaluate_review(v) == []


def test_approved_empty_accepts():
    v = ReviewVerdict(verdict="approved", findings=[])
    assert needs_rework(v) is False
    assert evaluate_review(v) == []


def test_needs_work_with_warns_only_is_approved_by_the_engine():
    v = _needs_work(_f("warn", "high"), _f("warn", "low"))
    assert needs_rework(v) is False
    assert evaluate_review(v) == []


def test_needs_work_with_low_confidence_fail_only_is_approved():
    v = _needs_work(_f("fail", "low"))
    assert needs_rework(v) is False
    assert evaluate_review(v) == []


@pytest.mark.parametrize("confidence", ["high", "medium"])
def test_needs_work_with_a_confident_fail_reworks(confidence):
    assert needs_rework(_needs_work(_f("fail", confidence))) is True


def test_rework_returns_every_finding_full_fidelity():
    # one blocking fail forces the rework; the producer still receives the
    # warns and the low-confidence fail — the engine gates, it does not curate
    v = _needs_work(
        _f("fail", "high", rule="voice_pov"),
        _f("warn", "medium", rule="leakage"),
        _f("fail", "low", rule="continuity"),
    )
    rendered = evaluate_review(v)
    assert len(rendered) == 3
    assert any("voice_pov" in r for r in rendered)
    assert any("leakage" in r and "WARN" in r for r in rendered)
    assert any("continuity" in r and "low" in r for r in rendered)


# -- renderer ----------------------------------------------------------------


def test_render_carries_every_axis():
    line = render_finding(_f("fail", "high", rule="beat_infidelity", quote="a limp coat"))
    for token in ("beat_infidelity", "FAIL", "high", "a limp coat", "rewrite the line"):
        assert token in line


def test_render_omits_empty_quote():
    f = ReviewFinding(
        rule="beat_infidelity",
        assessment="fail",
        confidence="high",
        reason="the discovery never happens",
        recovery_action="stage it",
    )
    line = render_finding(f)
    assert '""' not in line
    assert "the discovery never happens" in line and "stage it" in line
