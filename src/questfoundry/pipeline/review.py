"""The shared review contract (docs/plans/review-contract.md).

Every LLM *review* pass shares one shape: a reviewer judges a producer's
output against a set of contract rules and returns findings the engine acts
on. This module owns that contract end to end — the finding schema, the
per-review rule enum, the engine gate (proceed vs rework), and the
producer-facing renderer — so every review (FILL prose, DRESS codex, any
future one) speaks it identically.

Division of labor (the spec's crux):

- The **reviewer** emits a `ReviewVerdict{verdict, findings}`: a top-level
  `verdict` (`approved` / `needs_work`) plus the evidence. `approved` is a
  positive attestation — it auto-accepts; `needs_work` hands the decision to
  the engine. The reviewer thus affirms a clean read but cannot *block* on its
  own say-so (that would restore the false-positive halt this redesign removed).
- The **engine** owns the one coarse decision on a `needs_work` verdict —
  *proceed vs rework* (`needs_rework`), computed mechanically from the
  findings. It does not filter, drop, or reformat — it only gates the runner's
  repair loop. A `needs_work` verdict with no confident objective defect is
  approved by the engine anyway (the author's rule: "a needs-work can still be
  approved by the engine").
- The **producer** receives the *full-fidelity* findings on a rework, each
  rendered with its labels, and decides how to revise: a `fail` is blocking,
  a `warn` or a low-confidence finding is the reviewer's concern to weigh.

The asymmetry that makes the top-level `approved` safe: a wrong `approved` only
accepts marginal prose (the deterministic echo / word-budget checks still
guard structure), whereas the danger this redesign targeted was a wrong *block*
— and a block still requires a `needs_work` verdict AND a `fail` finding at
`medium`+ confidence with a coherent `recovery_action`. Each required field
makes a fabricated halt costlier to sustain; the affirmation makes an empty
review a deliberate act, not a lazy default.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, create_model

# The reviewer's top-level attestation (heritage `recommendation`, restricted
# to the two outcomes a single review can reach). `approved` auto-accepts;
# `needs_work` defers the proceed/rework call to the engine.
Verdict = Literal["approved", "needs_work"]
# heritage `validation_result` (semantic-conventions.md §"Separate the Axes"),
# restricted to what a finding can be: a defect or a concern.
Assessment = Literal["fail", "warn"]
Confidence = Literal["high", "medium", "low"]

# A finding blocks — forces another rework round — only when it is an
# objective defect the reviewer is at least moderately sure of. Warns and
# low-confidence fails never loop the producer (but are not discarded). This
# is the one engine knob the spec flags for tuning: narrow to {"high"} if a
# live run shows medium-confidence false positives persist.
_BLOCKING_CONFIDENCE: frozenset[str] = frozenset({"high", "medium"})


class ReviewFinding(BaseModel):
    """One objection from a reviewer. The `rule` field is specialised per
    review into an enum of that review's clause set (`build_verdict_schema`);
    the rest of the envelope is shared across every review pass."""

    model_config = ConfigDict(extra="forbid")

    rule: str
    assessment: Assessment
    confidence: Confidence
    # the exact offending text; "" when the defect is an ABSENCE (a missing
    # beat) — then `reason` states what is missing.
    quote: str = ""
    reason: str
    recovery_action: str


class ReviewVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # required: the reviewer must state an outcome, so an empty review is a
    # deliberate `approved`, never a lazy default.
    verdict: Verdict
    findings: list[ReviewFinding] = []


def build_verdict_schema(name: str, rules: tuple[str, ...]) -> type[BaseModel]:
    """A `ReviewVerdict` whose findings' `rule` is pinned to this review's
    clause set — shared envelope, specialised enum, the way proposal schemas
    pin id references per project (`pipeline/refpin.py`). Under
    grammar-constrained decoding a reviewer cannot cite a rule outside the
    set (the live "fabricated a rule number" failure becomes unrepresentable);
    every other provider sees the constraint in the schema."""
    finding = create_model(
        f"{name}Finding",
        __base__=ReviewFinding,
        rule=(Literal[rules], ...),  # type: ignore[valid-type]
    )
    return create_model(
        f"{name}Verdict",
        __base__=ReviewVerdict,
        findings=(list[finding], []),  # type: ignore[valid-type]
    )


def needs_rework(verdict: ReviewVerdict) -> bool:
    """The engine's one decision: another rework, or good enough? An
    `approved` verdict auto-accepts. A `needs_work` verdict reworks iff some
    finding is an objective defect the reviewer is at least moderately sure of
    — otherwise the engine approves it anyway."""
    if verdict.verdict == "approved":
        return False
    return any(
        f.assessment == "fail" and f.confidence in _BLOCKING_CONFIDENCE
        for f in verdict.findings
    )


def render_finding(f: ReviewFinding) -> str:
    """One labeled line for the producer's repair block: the axes as labels,
    the offending quote, the reason, and the corrective. Uniform — the
    producer never sees raw reviewer prose, only this shape, so a FAIL and a
    WARN are told apart by their labels, not by tone."""
    head = f"[{f.rule} · {f.assessment.upper()} · {f.confidence}]"
    quote = f' "{f.quote}"' if f.quote else ""
    return f"{head}{quote} — {f.reason} Fix: {f.recovery_action}"


def evaluate_review(verdict: ReviewVerdict) -> list[str]:
    """The shared review gate. `PassSpec.review`'s contract is `-> list[str]`
    (empty = accept), so this returns `[]` when nothing blocks (an `approved`
    verdict, or a `needs_work` with no confident defect) and the full rendered
    finding list when a rework is due. Every finding reaches the producer on a
    rework — full fidelity, not just the blockers — because the engine gates
    the loop, it does not curate the evidence."""
    if not needs_rework(verdict):
        return []
    return [render_finding(f) for f in verdict.findings]
