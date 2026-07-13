# POLISH `passages` pass chunking — Plan

> Status: **BUILT** (2026-07-13). Fixes the medium-scale `AdapterError` the
> narration_scope live runs surfaced (STATUS decision log): the POLISH *passages*
> pass emitted the whole passage layer in one LLM call and overran the context
> window at medium scope. The pass is now decomposed — `finalize` expands into a
> `summary:<group>` per collapse group + a `labels:<group>` per source group
> (mini-ADR A21, 03 §9; 02 §POLISH). Offline-green (559 tests, ruff, golden 0/0);
> a live medium `--to polish` on `gpt-oss:120b-cloud` remains the one open
> acceptance check (build order §6, unbilled).

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
- **Labels are independent per *source group*, not per edge or per physical
  passage.** A single label needs its source + destination, but the *siblings*
  (all choices leaving one source group) must be mutually distinct (the apply
  enforces distinct labels), and a group-edge carries **one** label that the
  engine fans across the destination's variant passages ("Label granularity"
  below) — so a heavy-residue source group's several physical passages must not
  each write their own. The natural independent unit is therefore one source
  group's out-edge labels, written together. Different source groups are
  independent of one another.

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
2. **`labels:<group>`** — one pass per source group that has outgoing choices.
   Context: the source group + each destination's summary/beats + the engine-known
   gate/grant of each edge. Apply: wire that group's choice edges — one label per
   group-edge, engine-fanned across the destination's variant passages (label +
   requires + grants + holdability, I10/I13), reading each destination's persisted
   variant flag for a gated variant.

All `summary:<group>` passes run before any `labels:<group>` pass (labels
reference destinations that must exist). Order within each family follows the
deterministic `collapse_groups(...)` order, so the computed pass list is stable
across ledger replay/resume (A16).

### Prerequisite: persist the variant→flag mapping (review finding, PR #70)

Today `_passages_apply` builds `ids_of_group: {group -> [(passage_id, flag)]}`
**in the same call** that creates the variant passages (from `VariantSpec.flag`)
and consumes it immediately for edge gating; nothing survives on the graph
(`Passage` has no flag field; `add_variant` records a bare `VARIANT_OF` edge). Once
creation (`summary:<group>`) and wiring (`labels:<group>`) are separate passes,
that mapping must be **persisted**. Fix: add a `variant_flag: str | None` field to
`Passage` (set only on a variant), written by the create mutation in the
`summary:<group>` apply; the `labels:<group>` apply reads `dest.variant_flag` to
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
   better for weak tiers. → `summary:<group>` per group + `labels:<group>` per
   source group. No `B` constant.
2. **Persist the variant→flag mapping** on `Passage` (`variant_flag`) as a build
   prerequisite (review finding above).

## Fixture / doc blast radius

- **Keeper e2e** (`tests/fixtures/keeper/…`, `test_pipeline_e2e.py`): the single
  recorded `passages` call is replaced by one `summary:<group>` call per group
  plus one `labels:<group>` call per source group. The keeper is micro, so this
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

## Enumeration: the finalize dependency (runner pass-expansion)

POLISH's collapse groups depend on **finalize** (pass 1 — it adds
residue/false-branch/bridge beats → new groups), but the runner materializes a
stage's pass list **once at stage start** (`runner.py:349`), before finalize runs.
So the per-group `summary:<group>` passes cannot be enumerated up front (unlike
FILL's, whose passages already exist when FILL starts).

**Resolved (author decision #1, 2026-07-13): runner dynamic pass-expansion.** A
`PassSpec` gains an optional `expand(project) -> list[PassSpec]`; after a pass
completes (run **or** skipped — finalize may `skip_if` there is nothing to add),
the runner splices its expansion into the pass list right after it. Finalize
carries the expansion that, reading the *post-finalize* graph, returns the
`summary:<group>` + `labels:<group>` passes; `audit` stays last. Determinism/resume
hold: on resume finalize replays (kept/resumed) and re-expands deterministically
from the reproduced graph, so the expanded pass names match the ledger. The
progress `total` grows after finalize (a cosmetic heartbeat change).

## Label granularity (resolved)

Labels stay **one per group-edge**, engine-fanned across the destination's variant
passages (today's behavior — `labeled[(a,b)]` reused for every `dst_id` in
`ids_of_group[b]`). The `labels:<group>` unit is therefore **per source group**:
one call writes the labels for all of that group's out-edges (siblings must be
distinct). Distinct-per-variant-destination labels are a feature-add this fix does
not make.

## Build order

1. **Prerequisite (done):** `Passage.variant_flag`, set when POLISH creates a
   variant, persisted for the later wiring pass. + a persistence test.
2. **Runner (done):** `PassSpec.expand` + splice-after-complete (incl. skipped) in
   `run_stage`; determinism-preserving. + runner expansion tests
   (`test_expand_splices_successor_passes`, `…_even_when_the_expanding_pass_is_skipped`).
   No stage changed behavior (no stage used `expand` yet).
3. **POLISH (done):** the single `passages` pass is replaced with finalize-expanded
   `summary:<group>` (per group) + `labels:<group>` (per source group) passes —
   per-item schema (`SummaryProposal`/`LabelsProposal`), minimal context, per-item
   apply; the wiring apply reads `dest.variant_flag` via `_group_passages`.
   `polish_summary.j2` + `polish_labels.j2` replace `polish_passages.j2`. Unit
   tests re-pointed at the per-group summary + per-source labels applies
   (`tests/test_passages.py::_build_passages`, `test_multihard`,
   `test_proposal_schemas`).
4. **Keeper e2e (done):** the single recorded `passages` call is re-recorded as 8
   `summary:<group>` + 6 `labels:<group>` calls (59 fixtures total, +13); ledger
   counts bumped (POLISH 12→25, FILL 39→52, DRESS 46→59). Golden unaffected (no
   pass execution; its variant passages already carry `variant_flag` from the
   prerequisite). `pytest`/`ruff`/golden green.
5. **Docs (done):** 01 §6 (prerequisite), 02 §POLISH (the decomposition), 03 §9
   mini-ADR A21, STATUS + this plan.
6. (Follow-up, unbilled) a live medium `--to polish` on `gpt-oss:120b-cloud` to
   confirm the pass completes where it truncated before — the acceptance test.

## Risks / follow-ups

- **Per-group summary coherence:** passage summaries are brief and beat-derived, so
  a group's own beats are enough context; if a live run shows tonal drift, a small
  "premise + voice-of-the-whole" header per call is the fix (cheap, no restructure).
- **Runner blast radius:** `expand` is additive (opt-in per PassSpec), so no existing
  stage changes behavior; the risk is the resume/ledger path, covered by the runner
  test (expand reproduces the same pass names on replay).
- **Not a `num_ctx` change:** this fix leaves `num_ctx` alone; a separate, optional
  config bump for long scope remains available but is out of scope here.
