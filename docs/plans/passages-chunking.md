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
the model, computes the structure) and **not** model weakness. The deeper
diagnosis (author, 2026-07-13) is a **prompt-engineering** one: the pass **greedily
stuffs the entire passage layer + all edges into one call** because a large model
tolerates "context is free" — but that context gives *no per-item benefit* (a
passage summary is derived from its own beats alone), and it breaks a weak model
for nothing. Raising `num_ctx` (the model supports 128k) would paper over it and
inflate every call; the fix is to **decompose the pass into genuinely independent
calls, each carrying only the context it needs** (author decision B). Call count
is not a cost we optimize against — FILL already runs ~150 calls per medium run;
right-sized independent calls are strictly better for weak tiers.

## What the LLM actually produces (so we know what to chunk)

The engine computes collapse groups, choice topology, gates, grants, variant
needs, and does all wiring. The LLM contributes **content only**, per item:

- per group: a `summary`, an `ending_title` (only if the group ends the story),
  and `variants[].summary` (only for heavy-residue frontier groups);
- per edge: a choice `label`.

Independence analysis (the seam this design turns on — author, 2026-07-13: prefer
*independent* calls with minimal context, however many, over any batching for its
own sake):

- **Summaries are independent per collapse group.** A passage summary is a brief
  derived from that group's own beats; no other passage's content bears on it. A
  group's *variants* (heavy-residue: same moment, different prose per world-state)
  must contrast with each other, so they generate **together within their group's
  call** — still per-group independence.
- **Labels are independent per *source passage*, not per edge.** A single label
  needs its source + destination, but the *siblings* (all choices offered at one
  passage) must be mutually distinct (the apply already enforces distinct labels).
  So the natural independent unit is "at passage A, write its N choice labels
  together." Different source passages are independent of one another.

## Design

Make POLISH's pass list **computed from the project** (like FILL's per-passage
queue — `StageImpl.passes` already accepts a callable). Replace the single
`passages` pass with two families of **independent, minimal-context** passes — no
batch constant, the unit is the natural one:

1. **`summary:<group>`** — one pass per collapse group. Context: *only* that
   group's beats, its ending flag, and (for a heavy-residue frontier group) the
   world-states/flags its variants must cover. Schema: one `PassageSpec` (summary,
   ending_title, variants). Apply: build the `Passage` node(s) for this group via
   the mutation layer — and **persist each variant's gating flag on its passage**
   (see prerequisite below) so wiring can recover it later.
2. **`labels:<source>`** — one pass per passage that has outgoing choices. Context:
   the source passage + each destination's summary/beats + the engine-known
   gate/grant of each edge. Apply: wire that source's choice edges (label +
   requires + grants + holdability, I10/I13), reading the destination's persisted
   variant flag for a gated variant.

All `summary:<group>` passes run before any `labels:<source>` pass (labels
reference destinations that must exist). Order within each family follows the
deterministic `collapse_groups(...)` order, so the computed pass list is stable
across ledger replay/resume (A16).

### Prerequisite: persist the variant→flag mapping (review finding, PR #70)

Today `_passages_apply` builds `ids_of_group: {group -> [(passage_id, flag)]}`
**in the same call** that creates the variant passages (from `VariantSpec.flag`)
and consumes it immediately for edge gating; nothing survives on the graph
(`Passage` has no flag field; `add_variant` records a bare `VARIANT_OF` edge). Once
creation (`summary:<group>`) and wiring (`labels:<source>`) are separate passes,
that mapping must be **persisted**. Fix: add a `variant_flag: str | None` field to
`Passage` (set only on a variant), written by the create mutation in the
`summary:<group>` apply; the `labels:<source>` apply reads `dest.variant_flag` to
set `Choice.requires`. This is a small model + mutation change and is a **build
prerequisite**, done first. (Alternative considered: have the engine own the
pairing by presenting the group's flags in a fixed order and taking variant
summaries positionally — drops `VariantSpec.flag` entirely. Persisting the flag is
the smaller change and keeps the LLM's explicit flag↔summary pairing; chosen.)

**Coverage / gate:** each `summary:<group>` pass covers exactly its one group; the
stage gate G4 still enforces I11 (every beat in exactly one passage) across the
whole graph, so total coverage stays gate-guaranteed. A missing group is a missing
pass — the computed list is exhaustive over `collapse_groups(...)`.

## Decisions (resolved with the author, 2026-07-13)

1. **Decompose into independent per-item calls, not batches.** Call count is not
   a cost we optimize against; independent minimal-context calls are strictly
   better for weak tiers. → `summary:<group>` per group + `labels:<source>` per
   source passage. No `B` constant.
2. **Persist the variant→flag mapping** on `Passage` (`variant_flag`) as a build
   prerequisite (review finding above).

## Fixture / doc blast radius

- **Keeper e2e** (`tests/fixtures/keeper/…`, `test_pipeline_e2e.py`): the single
  recorded `passages` call is replaced by one `summary:<group>` call per group
  plus one `labels:<source>` call per source passage. The keeper is micro, so this
  is a bounded, mechanical re-record (same content, re-partitioned into the new
  per-item schemas; ~8–9 summary calls + a few label calls), plus refreshed POLISH
  snapshots (now carrying `variant_flag` on any variant passage). Golden story
  (`keepers-bargain`) is a *static* project (no pass execution) — **unaffected by
  the pass split**, but its variant passages gain the new `variant_flag` field, so
  the golden YAML + round-trip fixtures get that one field added.
- **Unit tests** (`tests/test_passages.py` — where `_passages_apply`/
  `PassagesProposal` are exercised, e.g. `test_heavy_residue_creates_gated_variants`
  at `test_passages.py:156`): re-point at the per-group summary apply + the
  per-source labels apply; add a test that `variant_flag` persists and that wiring
  reads it back to gate the variant's incoming choices; keep the
  distinct-sibling-labels and holdability assertions on the labels apply.
- **Docs:** 02 §POLISH — describe the *passages* pass as per-group summary calls +
  per-source label calls (minimal context each), with the greedy-context motivation.
  01 §6 / `models/presentation.py` — note `variant_flag` on `Passage`. 03 §9
  mini-ADR — record the decompose-for-weak-tiers decision (A2x). STATUS decision
  log + a "Next up" pointer to this plan.

## Build order

1. **Prerequisite:** add `Passage.variant_flag` + the create-mutation that sets it;
   have the current single-pass apply persist it (keeps everything green as a
   standalone step). + a persistence test.
2. `polish.py`: replace the single `passages` pass with the computed
   `summary:<group>` + `labels:<source>` pass families (per-item schema, minimal
   context, per-item apply). Wire POLISH's `passes` to the computed list. + unit tests.
3. Re-record the keeper e2e per-item calls; refresh snapshots;
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
