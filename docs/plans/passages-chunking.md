# POLISH `passages` pass chunking — Plan

> Status: **PLANNED** (2026-07-13). Fixes the medium-scale `AdapterError` the
> narration_scope live runs surfaced (STATUS decision log): the POLISH *passages*
> pass emits the whole passage layer in one LLM call and overruns the context
> window at medium scope. Frontier-authored; the design has fixture/doc blast
> radius, so it lands after author sign-off.

## Root cause (confirmed, not assumed)

The *passages* pass (`pipeline/stages/polish.py`, pass 2) makes **one** LLM call
that must return a `PassagesProposal` covering **every** collapse group and
**every** choice edge at once — the apply enforces full coverage
(`"passages must cover each group 0..N exactly once"`, `"labels must cover each
choice edge exactly once"`). At medium scope (~90–160 passages + a similar number
of edges) the output alone is ~15–17k tokens, and for Ollama `num_ctx` is the
**total** input+output window (`options = {"num_ctx", "num_predict": max_tokens}`,
`ollama.py`). With `num_ctx = 32768` and a ~10–15k-token input (all groups' beats
+ edges), input + output overflow and the JSON truncates → schema-invalid →
`AdapterError` after repair.

This is **not** a prompt-wording defect (the rules are clear and the engine, not
the model, computes the structure) and **not** model weakness — it is a
one-giant-call output-size limit. Raising `num_ctx` (the model supports 128k)
would unblock medium but only defers the same failure at long scope and inflates
every call; **chunking is the durable fix** (author decision B, 2026-07-13).

## What the LLM actually produces (so we know what to chunk)

The engine computes collapse groups, choice topology, gates, grants, variant
needs, and does all wiring. The LLM contributes **content only**, per item:

- per group: a `summary`, an `ending_title` (only if the group ends the story),
  and `variants[].summary` (only for heavy-residue frontier groups);
- per edge: a choice `label`.

There is almost no cross-item dependency — a passage summary is derived from its
own beats, a label from its own edge — so the content is safely batchable.

## Design

Make POLISH's pass list **computed from the project** (like FILL's per-passage
queue — `StageImpl.passes` already accepts a callable). Replace the single
`passages` pass with:

1. **`passages:batch-K`** — one pass per batch of `B` collapse groups. Context:
   only that batch's groups (their beats, ending flag, variant flags). Schema: a
   batch-scoped `PassagesBatchProposal` (`passages: list[PassageSpec]` for this
   batch's group indices only — refpin/validation pins `group` to the batch's
   indices). Apply: build the `Passage` nodes (+ variants) for this batch's groups
   via the mutation layer, exactly as today's apply does per group; check the
   batch covered its assigned groups exactly once. No edges yet.
2. **`labels`** — one pass after all passage nodes exist. Context: the choice
   edges (source/dest passage ids + summaries now available) — a *small* input,
   and the output (~1 short label per edge) is well within budget even at medium.
   Apply: the current edge-wiring (labels + gates + grants + holdability, I10/I13).
   (If a future *long*-scope run shows the label output overflowing, batch this
   pass the same way — deferred until measured, not preempted.)

**Batch size `B`:** a scope-independent constant sized so `B` groups' output stays
well under the window — **`B = 30`**. Effect by scope: micro (≤24 groups) → **1**
passages batch; short → 1–3; medium → 3–6; long → 5–10. `B` lives as a module
constant with a comment tying it to the window budget, not a scope-preset field
(it is an engine safety limit, not story scale).

**Coverage / gate:** each batch checks it covered its own groups; the stage gate
G4 already enforces I11 (every beat in exactly one passage) across the whole
graph, so total coverage is still gate-guaranteed. A batch that drops a group
fails its own apply (repairable) before the gate.

**Determinism (ledger/replay):** batches are a deterministic function of
`collapse_groups(...)` order (already deterministic), so the computed pass list is
stable across replay/resume — required for A16. Group→batch assignment is
`groups[K*B : (K+1)*B]`.

## Decisions to confirm

1. **Split summaries (batched) from labels (one pass)** — vs. keeping them in one
   combined call. Recommended: split. Labels need *all* passages to exist first
   (edges cross batches), so they can't ride the per-batch passage calls; a
   separate labels pass is the clean seam. **Consequence:** even micro goes from
   **1 call → 2 calls** (1 passages batch + 1 labels), so the keeper e2e fixtures
   re-record (below). The alternative — a "single-call fast path" when everything
   fits one batch (preserving micro's one call and its fixtures) — keeps two code
   paths; I recommend against it (complexity > the one-time fixture edit).
2. **`B = 30`** as the batch constant (vs. a smaller/larger value). 30 keeps
   per-call output ~3–4k tokens with comfortable head-room under 32k.

## Fixture / doc blast radius

- **Keeper e2e** (`tests/fixtures/keeper/…`, `test_pipeline_e2e.py`): the single
  recorded `passages` call splits into `passages:batch-0` + `labels`. Re-record
  by hand (the content is identical, re-partitioned into the two new schemas) and
  refresh POLISH snapshots. Micro is one passages batch, so exactly two calls
  replace one — a bounded, mechanical edit. Golden story (`keepers-bargain`) is a
  *static* project (no pass execution), so it is **unaffected**.
- **Unit tests** (`test_polish.py`): the passages-apply tests move to the batched
  apply + the labels apply; add a batch-boundary test (a synthetic >B-group graph
  splits into the right batches and still covers every group), and a
  batch-coverage repairable-error test.
- **Docs:** 02 §POLISH — the *passages* pass is described as a batched
  content-gather (summaries per batch of groups) + a labels pass; note the window
  motivation. 03 §9 mini-ADR — record the batched-pass decision (A2x). STATUS
  decision log + retire this plan's "next up" line.

## Build order

1. `passages.py`/`polish.py`: the batch split (constant `B`, `_passages_batches`
   computing the pass list, `PassagesBatchProposal` schema + per-batch context +
   apply), and the separate `labels` pass (schema + context + wiring apply). Wire
   POLISH's `passes` to the computed list. + unit tests.
2. Re-record the keeper e2e passages/labels calls; refresh snapshots;
   `pytest`/`ruff`/golden green.
3. Docs (02, 03 mini-ADR, STATUS).
4. (Follow-up, unbilled) a live medium `--to polish` on `gpt-oss:120b-cloud` to
   confirm the pass now completes where it truncated before — the acceptance test.

## Risks / follow-ups

- **Cross-batch summary coherence:** passage summaries are brief and beat-derived,
  so per-batch context is enough; if a live run shows tonal drift across batches, a
  small "story premise + voice-of-the-whole" header in each batch context is the
  fix (cheap, no restructure).
- **Labels at long scope:** if the single labels pass ever overflows at long, batch
  it identically (the seam is already there). Deferred until measured.
- **Not a `num_ctx` change:** this fix leaves `num_ctx` alone; a separate, optional
  config bump for long scope remains available but is not this plan.
