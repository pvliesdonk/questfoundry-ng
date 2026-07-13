# Rain and Jade — narration-scope validation run

An **LLM-generated** noir, preserved as the live-validation artifact for the
`narration_scope` beat annotation (design doc 01 §Beat annotations,
`docs/plans/pov-narration-scope.md`). Not a hand-authored fixture and not a CI
gate — the golden [`keepers-bargain`](../keepers-bargain) is the story that must
always pass; this is a weak model's output, warts included.

- **Model:** `gpt-oss:120b-cloud` (Ollama), all three roles.
- **Premise:** a hard-boiled PI in a rain-soaked port city is hired by a woman
  who lies as she breathes to recover a jade figurine three people will kill for
  (`vision.yaml`).
- **Scope:** `micro`. **Reached stage:** `fill` (validates 0 errors, 2 advisory
  warnings; `uv run qf validate examples/rain-and-jade`).
- **Voice:** `third person limited (Sam "Rain" Marlowe)`, past tense — the same
  limited-POV shape whose finale broke the pre-fix "Black Bird" run.

## What it validates

The `narration_scope` fix targets the epilogue/POV collapse-feasibility bug: a
single limited-POV story whose endings narrate world-scope aftermath the
viewpoint character can't perceive. This run is the first weak-tier noir to
carry that shape **through FILL with no review-exhaustion halt** — every
passage landed in ≤ 2 attempts, and the endings (where the old run died) wrote
clean limited-POV prose with no head-hopping.

- **All 30 beats came out `narration_scope: limited`** — and correctly so: SEED
  produced a story where every consequence reaches Sam directly (he hands the
  jade over, hears the informant, is roared at by the antagonist), so there is
  no out-of-horizon beat to narrate `wide`. The run therefore validates
  *completion + no regression + the upstream perceivable-consequence bias*; it
  does **not** exercise the `wide` coda license (no beat deserved it). A story
  that structurally demands an out-of-horizon coda — a death ending, a time-skip
  epilogue — is what exercises `wide`.

## Known rough edges

- **Supernatural drift:** the jade figurine *pulses/glows* and a "ritual" binds
  the docks, contradicting the vision's `content_notes` (avoid supernatural).
  This is a DREAM/BRAINSTORM content-adherence issue, orthogonal to
  `narration_scope`.
- **B7** total words 2381 vs the `micro` floor 2400 (19 short) — the expected
  "modulation shortens sequels/micros" scale signal; advisory.

## Regenerating exports

Exports are not committed (regenerate on demand):

```
uv run qf export html -C examples/rain-and-jade
```
