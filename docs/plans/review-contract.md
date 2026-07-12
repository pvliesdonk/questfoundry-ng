# Review-contract redesign — implementation spec

> Author-directed, 2026-07-12. This is the #1b review-contract redesign
> contracted in `docs/plans/prose-quality.md`, promoted to its own spec
> because it is **pipeline-wide**, not FILL-specific. Status: **BUILT +
> partially validated live** (author signed off + implemented 2026-07-12 —
> shared `pipeline/review.py`, adopted by `fill_review` + `dress_codex_review`;
> a follow-up added the top-level `verdict` after a live gpt-oss:120b run
> confirmed the reviewer behaves). See Validation for what the live run showed
> and what it did not (DRESS codex review still unexercised — FILL now dies on
> an unrelated micro-detail guard).

## The problem — a class, not a prose bug

Every LLM **review** pass shares one shape: a reviewer judges a producer's
output against a set of contract rules and returns a verdict the engine
acts on. The current verdict is **binary `pass`/`fail` plus free-text
`issues: list[str]`**, and on a weak tier it fails in one direction —
**false positives that bind the producer**:

- FILL prose review, live on `gpt-oss:120b`, in three successive shapes as
  each was fixed: (1) it *fabricated* a rule number for a simile; (2) it
  literally enforced a voice-coined `banned` footgun; (3) it over-literalised
  Rule 2, rejecting "he wondered who had lost the garment, what secret it
  held" as not fulfilling "ponders the coat's origin." Every one is the same
  mechanism: a low-precision reviewer emits an objection, and the write
  prompt's "avoid every one of them" makes it **binding** — the producer has
  no channel to weigh or decline it.
- The class is not prose-specific. `dress_codex_review.j2` (spoiler safety)
  has the identical envelope and **never even ran** in the gpt-oss run
  (FILL died first). Structure passing on 120b says nothing about it. Any
  future review pass (SHIP/Twee lint) inherits the same exposure.

Free text also **conflates axes** heritage tells us to separate
(`semantic-conventions.md` §"Separate the Axes"): a single sentence hides
*what kind* of objection it is (a blocker? an uncertainty? a taste nit? an
inconsistency?), *how sure* the reviewer is, *which* rule, and *what to do*.

## The redesign in one line

Replace the binary verdict with a **structured, multi-axis finding schema**
shared by every review pass; the **engine** decides only *proceed vs
rework*; the **producer** receives the *full-fidelity findings* and decides
how to act.

## The schema (heritage-aligned; enums for finite sets)

```
ReviewFinding:
  rule:        enum   # WHICH contract clause — per-review enum (below)
  assessment:  enum   # heritage validation_result, restricted to what a
                      # finding can be: "fail" | "warn"
                      #   fail = an objective defect (a blocker)
                      #   warn = a concern / taste / "passes with concerns"
  confidence:  enum   # "high" | "medium" | "low"
  quote:       str    # the exact offending prose; "" when the defect is an
                      # ABSENCE (a missing beat) — then `reason` states what
  reason:      str    # why it breaks THAT rule, citing the rule's wording
  recovery_action: str  # the specific corrective the producer should make
                        # (heritage §Error Messages: how to fix it)

ReviewVerdict:
  verdict:  enum   # "approved" | "needs_work" (heritage recommendation)
  findings: list[ReviewFinding] = []   # replaces the old free-text issues
```

**Top-level `verdict` (added 2026-07-12 after live validation, author-directed).**
The reviewer states one attestation: `approved` auto-accepts; `needs_work`
hands the proceed/rework call to the engine, which reworks only on a confident
`fail` finding and otherwise approves anyway ("a needs-work can still be
approved by the engine"). This is *not* a return of the binary verdict the
redesign removed: the reviewer can affirm a clean read but still cannot
**block** on its own say-so — a block requires `needs_work` **and** a `fail`
finding at `medium`+ confidence. The asymmetry makes it safe: a wrong
`approved` only accepts marginal prose (the deterministic echo / word-budget
checks still guard structure), whereas the danger the redesign targeted was a
wrong *block*. It also makes an empty review a deliberate act (`approved`), not
a lazy default. Banned per heritage: `green/yellow/red/success/error`.

**Per-review `rule` enums** (the envelope is shared; the clause set is
specialised — built per review type, the way proposal schemas are pinned
per project):
- **FILL prose** (`fill_review`): `voice_pov`, `voice_tense`,
  `banned_pattern`, `beat_infidelity`, `continuity`, `state_dishonesty`,
  `leakage`, `pronoun`.
- **DRESS codex** (`dress_codex_review`): `conditional_stated_as_fact`,
  `machinery_leakage`, `ending_title_named`.

Your four questions map to explicit axes: *blocker vs uncertainty* →
`assessment`; *how sure* → `confidence`; *prose vs inconsistency* → `rule`
(an inconsistency is `continuity`/`state_dishonesty`; a pure prose nit can
only be a `warn`, because the contract says taste is never a defect);
*actionable?* → `recovery_action` is now a **required field**.

## Division of labor

- **Reviewer** — emits the full `ReviewVerdict{verdict, findings}`: a
  top-level `approved`/`needs_work` attestation plus the evidence. It affirms a
  clean read but does not get to *block* — a rework requires the engine to
  agree.
- **Engine** — owns exactly one coarse decision, *"good enough, or another
  rework?"* (heritage `recommendation`: `proceed` vs `rework`), computed
  mechanically:
  ```
  needs_rework = verdict == "needs_work" and any(
      f.assessment == "fail" and f.confidence in {"high","medium"}
      for f in findings)
  ```
  `approved` → accept immediately. `needs_work` with no confident defect →
  accept anyway. Only `needs_work` **and** a confident `fail` → rework. The
  engine does **not** filter, drop, or reformat findings — it only gates the
  loop. Warns and low-confidence fails never force a rework, but they are
  **not discarded** (below).
- **Producer** (writer / codex author) — on `rework`, receives the **entire
  findings list, full fidelity**, each rendered with its labels, and
  *decides how to revise*. It must address the blocking findings; a `warn`
  or a low-confidence finding is the reviewer's concern to **weigh, not a
  mandate**. The producer holds the prose and the tradeoffs — it judges.

This is the crux and the correction to the first sketch: the false-positive
protection is **not** the engine silently dropping findings; it is
(a) the engine only *looping* on confident objective defects, and
(b) the producer *seeing every finding with its confidence label* and
exercising judgment. The reviewer cannot force a rework loop without
stamping a finding `fail` + `≥medium` confidence **and** writing a coherent
`recovery_action` — each required field makes a fabricated match costlier to
sustain.

## Producer-facing rendering

The engine renders each finding into the producer's repair block as a
labeled, uniform line (not raw reviewer prose):

```
[beat_infidelity · FAIL · high] "A navy coat hung limp" — the beat's
  snagged-coat-on-the-lock-gate discovery is absent; show the coat snagged
  on the gate and hint at the lost story.
[beat_infidelity · WARN · low]  "He wondered who had lost the garment" —
  reviewer felt "ponders origin" was thin; weigh, do not over-correct.
```

The write/codex prompt's rejection block gains one framing line: *"Findings
marked FAIL are blocking — resolve each. A WARN or a low-confidence finding
is the reviewer's concern; weigh it and decide — do not over-correct."*

## Cross-tier arbitration (the ceiling, deadlock only)

Confidence + structure lowers the false-positive rate but cannot zero it —
a weak reviewer can be *confidently* wrong. So after `max_repairs` rework
rounds still returning `rework`, escalate once to an **architect-tier**
arbiter that emits the same schema; its `proceed`/`rework` is final. On a
**mixed model map** this is a genuinely stronger judge and is the real
ceiling-raiser; on an **all-weak map** it is the same model and adds cost,
not signal — document that, and run arbitration only on the ≤N passages
that actually deadlock (cheap and targeted).

## Roll-out — one contract, every review

- Shared types `ReviewFinding` / `ReviewVerdict` and a shared
  `evaluate_review(findings) -> list[str]` gate+render helper live in one
  module (e.g. `pipeline/review.py`), used by every review.
- `PassSpec.review` keeps its `-> list[str]` shape (empty = accept), so the
  runner's repair loop is unchanged; the structure lives in the review
  function + schema + helper.
- Adopters this PR: `fill_review` (prose) and `dress_codex_review` (codex).
  Every future review inherits the envelope.

## Change surface

- `pipeline/review.py` (new): `ReviewFinding`, `ReviewVerdict`, the per-review
  `rule` enum builders, `evaluate_review`, the finding→string renderer.
- `pipeline/stages/fill.py`: `_review_for` builds the fill `rule` enum, calls
  the reviewer for the structured verdict, runs `evaluate_review`; arbitration
  path unchanged in shape.
- `pipeline/stages/dress.py`: the codex review adopts the same path.
- `fill_review.j2`, `dress_codex_review.j2`: ask for the structured verdict
  (the rule definitions stay; the "list issues as sentences + (a)(b)(c)"
  block is replaced by the finding-schema instruction, since the axes are now
  schema fields, not prose the model must remember to include).
- The producer prompts gain the one-line "weigh warns" framing.

## Acceptance / tests

- Schema + enum validation tests.
- Gate unit tests: a warn-only verdict → accept; a low-confidence-fail-only
  verdict → accept; one high/medium-confidence fail → rework; mixed → rework
  **and the producer receives every finding** (fidelity, not just blockers).
- Renderer test: the producer string carries the rule, assessment,
  confidence, quote, and recovery_action.
- Prompt-source guards for both review templates (structured-verdict ask;
  "weigh warns" framing in the producers).
- The keeper e2e's staged review-fail/revise round is re-recorded to the new
  schema; golden `qf validate` stays green.
- `uv run pytest -q`, `ruff check` green.

## Validation

**Live gpt-oss:120b run, 2026-07-12 (unbilled Ollama cloud; scratch project
`examples/thaw-between/`).** What it showed:

- **The contract holds on the weak tier.** Every FILL prose review returned a
  well-formed structured verdict; six write passes accepted first-try with no
  fabricated rule and no false-positive halt — the failure mode this redesign
  targeted (a reviewer inventing a "Rule 1" simile violation and looping the
  writer) did not recur. The voice-ban footgun is also gone: the coined
  `banned` list was all literally-matchable, no common-word ban.
- **The empty-review signal was thin**, which motivated the top-level
  `verdict` follow-up above: an `approved` attestation makes a clean read a
  deliberate act rather than a `{"findings": []}` that could be a lazy default.
- **Not yet exercised: DRESS codex review.** FILL died before DRESS again — but
  on an *unrelated* cause this time: the micro-detail single-assignment guard
  (`object:old-lens already has 'material'`) exhausted repairs when the weak
  writer kept re-observing an established fact. The error message is already
  exemplary (reason + subject + recovery_action), so this is a weak-tier
  fixation, not a message-quality defect — tracked separately in
  `docs/plans/prose-quality.md` / STATUS, not a review-contract gap.

Open: a rerun once the micro-detail blocker is addressed, to finally exercise
DRESS codex review under the contract.

## Open questions / risks

- **Two soft axes for a weak model.** `assessment` (defect vs concern) and
  `confidence` are orthogonal but subtle; a weak reviewer may fill them
  noisily. Kept separate per heritage's "separate the axes"; revisit
  collapsing to one 3-value axis if live runs show the distinction is noise.
- **Producer over-correcting on warns** despite the framing — a live risk to
  measure, not assume.
- **Threshold tuning.** `confidence in {high, medium}` blocks; may need to be
  `high` only if false positives persist — a one-line engine knob.
- **Fixture churn.** Every recorded review verdict changes shape; the e2e
  fixtures re-record in the same PR.
