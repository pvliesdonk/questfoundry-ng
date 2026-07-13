# Greywater Docks — the `wide` narration-scope demonstration

An **LLM-generated** noir, preserved as the artifact that proves the
`narration_scope` fix end-to-end (design doc 01 §Beat annotations,
`docs/plans/pov-narration-scope.md`). This is the run where the **`wide` coda
license fires live** — the exact epilogue/POV collapse-feasibility case that
broke the pre-fix "Black Bird" run, now written cleanly.

- **Model:** `gpt-oss:120b-cloud` (Ollama), all three roles.
- **Premise:** a dying PI takes one last case in a rain-soaked port city; he
  cracks it and does not walk away, and the city goes on without him
  (`vision.yaml`). The premise *structurally* forces an out-of-horizon coda —
  which is what a `wide` beat needs.
- **Scope:** `micro`. **Reached stage:** `fill` (validates 0 errors, 2 advisory
  warnings; `uv run qf validate examples/greywater-docks`).
- **Voice:** `third person limited (Elliot March)`, past tense.

## What it demonstrates

The finale passage `p-finale` collapses the climax scenes (`limited`) **and** a
world-coda beat (`wide`) into one passage — the *exact* shape that failed twice
before (a limited-POV finale asked to narrate aftermath the viewpoint character
can't perceive). Here it writes clean, first try. The full chain works:

1. **SEED** (with the softened coda steer) generated a genuine out-of-horizon
   coda beat, `beat:city-continues` — *"the city's undercurrents shift, but life
   in Greywater Docks rolls on, indifferent to the broken myth."*
2. **GROW annotate** tagged it `narration_scope: wide` on its own (it is a
   *narrative* beat, so not the `epilogue→wide` fallback — the model judged it).
   Tally: 24 `limited`, **1 `wide`**.
3. **FILL** wrote `p-finale` in one pass: Elliot's death in **limited** POV
   (*"Elliot's breath halted, a final gasp lost to the pounding surf"*), then a
   detached **`wide`** coda narrated beyond the dead detective (*"The tide
   surged … Greywater Docks carried on, its shadows unchanged"*). No POV break;
   the reviewer did not flag the coda as a departure.

Compare with [`rain-and-jade`](../rain-and-jade), the sibling run whose
surviving-detective premise kept every beat perceivable (all `limited`, 0
`wide`) — together they show both halves: `limited` is correct when the story
stays in-frame, `wide` fires when the story steps outside it.

## Known rough edges

- **[B8]** a run of 4 consecutive `micro_beat` beats reads flat — the pacing
  report (advisory) working as intended.
- **[B7]** 2137 words vs the `micro` floor 2400 — the modulation-shortens signal,
  amplified by a terse death-noir; advisory.
- One ending briefly has the shattered figurine reassemble ("reborn in the
  rain") — a stray magical flourish against the noir register; minor, not
  systemic (no supernatural entity state).

## Regenerating exports

```
uv run qf export html -C examples/greywater-docks
```
