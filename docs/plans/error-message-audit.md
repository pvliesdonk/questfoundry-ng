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
- [ ] **Class 1 (raw-exception dumps)** graded acceptable-but-improvable:
      the interpolated `{e}` is a pydantic `ValidationError` (semi-structured,
      names the field/constraint), not a bare KeyError. Lower priority than
      Class 2; render via a correction-brief helper when touched next.
- [ ] Live validation of the two prompt fixes (a completing FILL run on both
      tiers; the runs that surfaced the failures died before completing).
