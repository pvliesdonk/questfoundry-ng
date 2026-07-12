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
    ok = schema.model_validate({"findings": [{
        "rule": "leakage", "assessment": "fail", "confidence": "high",
        "quote": "flag:x", "reason": "names machinery", "recovery_action": "drop it",
    }]})
    assert ok.findings[0].rule == "leakage"
    with pytest.raises(ValidationError):
        schema.model_validate({"findings": [{
            "rule": "banned_pattern",  # not in this review's clause set
            "assessment": "fail", "confidence": "high",
            "quote": "x", "reason": "y", "recovery_action": "z",
        }]})


def test_verdict_defaults_to_no_findings():
    assert ReviewVerdict().findings == []


# -- gate --------------------------------------------------------------------


def test_empty_verdict_accepts():
    assert needs_rework([]) is False
    assert evaluate_review([]) == []


def test_warn_only_accepts():
    findings = [_f("warn", "high"), _f("warn", "low")]
    assert needs_rework(findings) is False
    assert evaluate_review(findings) == []


def test_low_confidence_fail_only_accepts():
    findings = [_f("fail", "low")]
    assert needs_rework(findings) is False
    assert evaluate_review(findings) == []


@pytest.mark.parametrize("confidence", ["high", "medium"])
def test_a_confident_fail_reworks(confidence):
    assert needs_rework([_f("fail", confidence)]) is True


def test_rework_returns_every_finding_full_fidelity():
    # one blocking fail forces the rework; the producer still receives the
    # warns and the low-confidence fail — the engine gates, it does not curate
    findings = [
        _f("fail", "high", rule="voice_pov"),
        _f("warn", "medium", rule="leakage"),
        _f("fail", "low", rule="continuity"),
    ]
    rendered = evaluate_review(findings)
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
