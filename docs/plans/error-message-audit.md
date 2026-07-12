# Error-message & prompt actionability audit — plan

> Author-directed, 2026-07-12. Root cause named during the prose-quality
> live validation: **blunt prompts and error messages propped up by model
> intelligence**. A weak-tier (`gpt-oss:120b`) run exposed three instances
> of one defect (finalize duplicate-id feedback; review-contract rule
> fabrication; write-prompt non-POV handling), and the duplicate-id case
> proved there are many more sites (~74 `ApplyError` + ~54 `MutationError`
> raises). This plan makes the audit systematic. Retires into STATUS +
> the AGENTS.md "Prompt and error-message quality" rule when complete.

## Rubric (heritage `semantic-conventions.md` §Error Messages)

A **model-facing** error — one fed back into a repair loop or a review
verdict the model must act on — is graded on three fields:

1. **reason** — what is wrong (almost all sites have this).
2. **subject/location** — which field / id / spec / rule is at fault.
3. **recovery_action** — the specific corrective the model should take,
   phrased as an imperative: *pick a fresh id*, *use one of these values*,
   *move X after Y*, *drop the assertion*. **This is the field that is
   usually missing**, and its absence is what a strong model silently
   compensates for and a weak model cannot.

A site **passes** only with all three (proportionate to the error —
a value-enum error's recovery is "use one of {…}", already common; a
novel-id collision's recovery "coin a fresh id" was absent). A site is
**out of scope** if it is an engine-internal invariant failure that
signals a code bug, not a model-repairable proposal (those should read
as engineering diagnostics, not model instructions).

## Prompt sites (same lens, structural enforcement)

- `fill_review.j2` — must **force** each objection to quote the rule
  text and the offending prose and show the match, so a rule number
  cannot be cited for an objection that rule does not cover (live:
  reviewer flagged a simile as a "Rule 1" POV violation).
- `fill_write.j2` — must instruct **how to render a beat centered on a
  non-viewpoint character**: externalize (observable action/speech),
  never state their interiority (live: writer narrated a non-POV
  character's plotting intentions, failing the POV rule on both tiers).
- The adapter's correction brief (`llm/adapter.py:_repair_feedback`) —
  already actionable for schema errors; confirm.

## Method

Story-model-semantic messages are frontier judgment (AGENTS.md model
economics — do not hand narrative/DAG semantics to a cheap tier). Grade
every raise site directly against the rubric, fix the deficient ones,
and add a violating-construction test where a message change guards a
real failure. Batch by file; keep messages terse and in-style.

## Pipeline-wide prompt sweep (2026-07-12, author-directed: "FILL was a symptom")

Five parallel graders swept every stage's prompts + context + apply against
the rubric. The dominant defect is one shape: **a rule is stated but the
enabling data is withheld from the context, or the rule is not enforced at
apply** — the model is trusted to reconstruct what a strong tier can and a
weak tier can't. Findings by stage (H/M/L severity):

- **DREAM/BRAINSTORM**: [H] `brainstorm.j2` dilemma-count conflates output
  vs post-triage count → a literal reader emits too few, passes the gate,
  starves triage of locked candidates (silent wrong output). [H]
  `brainstorm.py` raw ValidationError dump — **fixed** (Class 1). [M]
  `brainstorm.j2` VISION block unframed, "Avoid" not imperative. [M]
  `dream.j2` "2-4 themes" not schema-enforced. [M] `add_dilemma` anchor
  error lacks recovery_action. [L] `research.j2` requires a `reason` the
  engine discards.
- **SEED**: [H] `seed_triage.j2` forbids orphaning a dilemma's anchor but
  withholds the `ANCHORED_TO` bindings (the model can't obey a rule whose
  data it can't see). [L] `seed_order.j2` cycle violation gets the
  feasibility error's message (mis-attribution).
- **GROW**: [H] `grow_contextualize.j2` demands "keep the same entities"
  but never renders the beat's entities (siblings `grow_bridge`/
  `grow_intersections` do). [M] `grow_intersections.j2` "every member from
  a different dilemma" not enforced at apply. [L] contextualize doesn't
  surface which clones are per-world siblings, though it demands they differ.
- **POLISH**: [H] `polish_finalize.j2` never says coined beat ids must be
  fresh/unique — the prompt-side root cause of the live finalize collision.
  [M] false-branch arm id shows no `beat:slug` format. [M] `polish_audit.j2`
  "a granted/paid-off flag is never irrelevant" is trust-only. [M]
  `polish_passages.j2` doesn't require passage/variant ids distinct. [L]
  arcs "in story order" unenforced; cadence "fill each run's count"
  overstates an advisory budget.
- **DRESS/voice**: [H] `fill_voice.j2` pov `NAME` never validated against
  the cast (the Maren/Marin bug — prompt-fixed, not enforced; cheapest
  finite-set check in the pipeline). [H] `dress_codex_review.j2` lacks the
  `fill_review` three-part discipline (quote the rule wording + show the
  match + drop-if-no-match) on its first-line reviewer — the open
  laundering surface. [M] `dress_briefs.j2` opening-prose excerpt has no
  input-role label / no-copy ban. [L] `set_flag_codeword` reuse error
  lacks a recovery_action; `fill_summary.j2` re-implements `_summary_brief`.

Fixes applied this pass are checked below; the rest are tracked here.

## A distinct class: model-coined constraints enforced downstream (2026-07-12)

Surfaced by the full `gpt-oss:120b` run: a **new failure shape**, separate
from the sweep's withheld-data/unenforced-rule class. Here a model **coins
a value in one pass that a later pass enforces literally or structurally**,
and a weak model coins an *over-broad, vague, or unsatisfiable* one that
traps the downstream writer — the constraint becomes a footgun the pipeline
then faithfully enforces.

The live instance: FILL's **voice pass** let the model coin
`banned: ["similes using 'as' or 'like'", "direct metaphor", …]`.
`fill_review.j2` matches banned patterns **literally**, so the ban on the
word "as" outlawed ordinary prose ("as the river rose" is not a simile) and
the vague "direct metaphor" was unactionable; every passage failed review
in two rounds. Note this only surfaced *because* the review-contract fix
made the reviewer honest — the failure moved up the chain from "reviewer
fabricates" to "voice coins a bad rule the honest reviewer enforces."

**The fix pattern for the class:** at the *coining* pass, state what makes
a good vs bad constraint and *why it is enforced downstream* (so the model
feels the cost of an over-broad one); where the coined value is enumerable,
guard it structurally at apply. Free-text constraints (banned patterns) are
prompt-bounded; enumerable ones can be made unrepresentable.

**Audit list — every place a model coins a value a later pass enforces:**
- [x] voice `banned` → `fill_review` (literal) — **fixed** (`fill_voice.j2`
      forbids common-word and vague bans, states the verbatim enforcement).
- [x] voice `pov` name → `fill_review` (literal) — already guarded (the
      cast-name check, the Maren/Marin fix).
- [ ] micro-details / entity facts → the echo check (a coined fact ≥4
      tokens becomes a no-restate constraint) — partly bounded (≤12-word
      register cap); review whether an awkward coined fact over-constrains.
- [ ] POLISH `arcs` (begins/pivots/ends) → FILL renders ARC POSITION the
      writer must honor — could an over-specified arc over-constrain a scene?
- [ ] DRESS art `direction` → briefs/codex must not invent beyond it —
      an over-broad direction constrains both.
- [ ] flag `description` → `fill_review` Rule 4 (state honesty) tests it.
- [x] codewords → gate-tested; already structurally guarded (format +
      uniqueness + grant-before-test).

## Status
- [x] `mutations.add_beat` duplicate-id → actionable `MutationError`
      (+ finalize residue/false-branch repairability; tests). First fix.
- [x] Full error-site inventory graded (~74 `ApplyError` + ~54
      `MutationError`). Finding: most stage `ApplyError`s already carry a
      recovery_action (refpin-era work — they list valid values / state the
      requirement). Two systematic gaps: **Class 2** (store `KeyError`
      escapes) and **Class 1** (raw-exception dumps, `f"invalid X: {e}"`).
- [x] **Class 2 fixed at the boundary**: `store.GraphError(KeyError)` with
      recovery_action for duplicate id / missing endpoint / duplicate edge;
      the runner catches `GraphError` so every model-reachable graph write is
      repairable, not an uncaught crash (generalizes the false-branch
      id-collision fix). Tests: `test_duplicate_edge_raises_graph_error`,
      `test_graph_error_from_apply_is_repairable_not_a_crash`.
- [x] `fill_review.j2` structural rule-matching (quote the rule's wording +
      show the match; figurative language named as taste). Prompt-source test.
- [x] `fill_write.j2` non-POV-character rendering (POINT OF VIEW IS LIMITED;
      externalize non-narrator interiority). Prompt-source test.
- [x] **Class 1 (raw-exception dumps) fixed sitewide**: all eight
      `f"invalid X: {e}"` sites now route the `ValidationError` through one
      shared `format_validation_error` (owned by `llm/adapter.py`,
      re-exported by `pipeline/types.py`, so the adapter's schema-retry
      brief and the apply-layer errors share one renderer and never drift).
- [ ] Live validation of the two prompt fixes (a completing FILL run on both
      tiers; the runs that surfaced the failures died before completing).
