# POV sequences — run-unit viewpoint annotation (Build Contract)

> Status: **DESIGNED, ratified** (2026-07-17). The decisions below are
> **author-confirmed 2026-07-17**, in-session, from the author's own read of
> the run-6 passage graph (the sketches "keep the PoV unless impossible" /
> "cover this stretch with minimal PoV change" are the author's; the
> sequence-unit shape is the session's sharpening of the second, ratified).
> Frontier-authored (POV / collapse semantics). Successor to
> [`rotating-pov-build.md`](rotating-pov-build.md): this is the escalation
> that contract explicitly reserved — its decision 3 said *"no engine
> constraint in v1 … tighten only if live runs show whiplash"* and its Risks
> section named **over-rotation** verbatim. The live run has now shown the
> whiplash with the prompt guidance already in place, so the structural step
> is the recorded follow-up, not a reversal.

## The problem (evidence, run-6 medium graph, 2026-07-17)

GROW's annotate assigns each beat's viewpoint independently; the model picks
each beat's "perceiving center" myopically. On the run-6 graph, **58% of
consecutive annotated linear beat pairs switch heads** (`call-out-farmers`
runs gord, gord, **harper**, gord across four consecutive beats of one
thread). I14's one-head-per-passage split — correct, doing its job — then
mints a no-choice page-turn at every hop:

| passage boundary cause (172 passages) | count |
|---|---|
| passage ends in a real choice | 37 |
| fork rejoin (convergence) | 36 |
| **pure POV split (no choice, no gate)** | **76** |
| `passage_beats_max` cap | ~17 |
| gate (residue) | 6 |

Counterfactual with the repo's own `collapse_groups`: heads held per run →
**159 → 114 passages (−28%)**, singletons 59 → 18, avg beats/passage
1.79 → 2.49. Knock-ons: texture arms inherit trunk heads via `mirrors`
(`passages.py`, the splice's annotation copy), so the fragmentation
duplicates into every arm; the choice-stretch metric counts *passages*, so
the fork loop spends words interrupting deserts that are partly this
artifact; B3's 172>160 overflow is largely the same artifact.

The prompt already says "PREFER RUNS … rotate at a real shift of dramatic
center, never beat-by-beat" — stated and trusted, which by this repo's own
doctrine is the defect. Per the author's standing correction (2026-07-15):
do not add more rules — restructure the task so the failure is
unrepresentable.

## Decisions locked (author-confirmed 2026-07-17)

1. **The unit of viewpoint assignment is the *sequence*** — the maximal
   choice-free linear run of beats (what `collapse_groups(g, max_beats=None,
   split_viewpoints=False)` computes; 78 on the run-6 graph). One head per
   sequence. Ratified name: **sequence** ("scene" was considered and
   rejected — Swain's `scene_type` already owns that word in every
   writer-facing prompt; and both terms admit units spanning a choice, but
   sequence misleads less). Sequences are **computed, never stored** (iron
   rule 2's spirit, same as arcs): per-beat `Beat.viewpoint` remains the
   stored form and the single source downstream reads — nothing in POLISH
   collapse, I14, FILL enforcement, or export changes.
2. **A sequence may be split only with a stated justification** — the
   escape valve for a genuine mid-sequence shift of dramatic center (the
   audit `split_on` precedent). No hard cap on splits; visibility instead
   (B11, below).
3. **A head roster, resolved before annotate, pins the viewpoint enum.**
   The scheme stops being prose-only (`Vision.pov_hint` at DREAM,
   `Voice.pov` at FILL — the latter declared *after* annotate has already
   assigned every head, which is backwards). A small scheme pass translates
   `pov_hint` into explicit character ids; annotate's schema pins `head` to
   that roster, so an off-scheme head is unrepresentable — this closes the
   formerly-BACKLOG "head-scheme conformance is ungated" item (the kimi
   victim-head class) structurally. FILL's voice pass *reads* the roster
   (single source of truth) instead of independently re-declaring.
4. **A sequence no roster head can witness resolves by justified split or
   justified wide-cutaway — never an automatic wide fallback.** Wide stays
   doctrinally a coda register; a mid-story wide is a real device
   (cutaway) but must be chosen and justified, and it stays counted (B11).
   If the valve fires often, that is a weave/roster defect to fix upstream
   (iron rule 5), not an annotate problem.
5. **Head presence is advisory, not required.** A head can narrate a beat
   they can plausibly witness; entity lists don't capture witnessing. The
   engine *shows* each sequence's candidate heads (characters present
   across its beats) and *says so* when the intersection with the roster is
   empty — the model then splits or goes wide, justified. No hard presence
   gate.
6. **Reordering beats for head contiguity is out of scope here.** It is
   mechanically feasible (stable cross-thread interleavings; within-thread
   order, intersection adjacencies, and temporal hints stay pinned) and
   belongs **weave-side, pre-contextualize** — after contextualize the
   summaries chain narratively and reordering would force
   re-contextualization; before it, reorder is a pure engine step. On
   today's capsule-shaped weave output there is little to reorder (the
   measured hops are within-thread annotate noise). Recorded as a design
   constraint on the roadmap "Next" epic (weave linearization — drama-layer
   braiding), which builds the primitive when it has material.

## Design

### The scheme pass (`stages/grow.py`, new pass before `annotate`)

- **Model:** the character entity gains `pov_head: bool = False` — the
  roster is per-entity, graph-native, round-trips through the project
  format, and hand-edited files face the same mutation layer (iron rule 1).
  Roster = the retained characters with the mark. Default `False` means
  pre-roster projects load unchanged and degrade gracefully (empty roster =
  no pinning, no I17 — exactly today's behavior).
- **Mutation:** `set_pov_head(g, entity_id, flag)` — reject non-character
  entities; no freeze interaction (entity annotation, not beat).
- **Pass:** `scheme`, utility role, runs after `contextualize`, before
  `annotate` (it needs the retained cast, nothing else). Context:
  `vision.pov_hint` verbatim + the retained characters (`name (id):
  concept`). Proposal: `{heads: [character ids], min 1}`, enum-pinned to
  retained character ids. A single-viewpoint scheme is a roster of one —
  correct, not degenerate. Apply sets the marks and logs the roster.
- **Skip:** none — every story has a scheme, even the default "one limited
  viewpoint" (the pass resolves *who* that one head is).

### The annotate pass restructured (`stages/grow.py`, `grow_annotate.j2`)

Still **one call** (rotation is a global property — the model must see the
whole sequence list to distribute heads per the scheme; per-sequence calls
would lose exactly that). The A21 giant-call precedent stands as the
watch-item: if a live run degenerates, decompose by act, never per beat.

- **Context:** the engine computes the sequences
  (`collapse_groups(g, max_beats=None, split_viewpoints=False)`, topological
  order) and renders them as numbered blocks — each with its beats (id,
  class/purpose, entities, summary) and its **candidate heads** (roster ∩
  characters present across the sequence's beats; rendered as "any of: …"
  or "NO roster head spans this sequence — split it where the center
  shifts, or justify a wide cutaway"). The roster (with names/concepts) and
  `pov_hint` render once. The scene-type/narration-scope doctrine is
  unchanged.
- **Schema (two sections, one proposal):**
  - `beat_annotations`: exactly today's per-beat `scene_type` +
    `narration_scope` + `interlude` (per-beat concerns stay per-beat).
  - `heads`: one entry per sequence — `{sequence: <the sequence's first
    beat id, enum-pinned to the engine's sequence heads>, head: <roster id
    or "">, splits: [{after: <beat id>, head: <roster id or "">, why:
    <non-empty>}]}`. A split names the beat after which the head changes
    and carries its justification; `""` as a head = the segment is a
    justified wide cutaway (its beats must be marked `wide` in
    `beat_annotations` — cross-checked at apply).
- **Apply (all repairable, with recovery actions):** every sequence covered
  exactly once (missing/duplicate → the offending ids and the instruction);
  `splits[].after` must lie inside the sequence, not last, strictly
  ordered, no duplicates; the engine then **expands** sequence heads to
  per-beat `set_beat_viewpoint` — `limited` beats get the segment's head,
  `wide` beats normalize to `None` exactly as today. The run log records
  the head distribution, every split with its justification, and every
  wide cutaway (the justifications live in the log and the proposal
  snapshot, not on the graph — the gate reports counts, the log holds the
  why).
- **Unchanged:** per-beat storage (`Beat.viewpoint`/`interlude`), the
  freeze semantics, POLISH `split_viewpoints` collapse, I14, the mirror
  annotation copy into texture arms, FILL's per-passage head enforcement,
  bridge beats as unannotated wildcards (bridge runs after annotate). The
  blast radius is the annotate pass and its prompt, plus the scheme pass.

### Gates: I17 (error) and B11 (advisory), per iron rule 6

- **I17 — declared-scheme conformance** (01 §8 entry, `validate.py` check,
  violating-construction test): when the roster is non-empty, every beat
  `viewpoint` is a roster member. Errors; skipped entirely when no roster
  exists (pre-roster projects, the current golden). The annotate schema
  makes violations unrepresentable at proposal time; I17 is the guard for
  every other writer (hand edits, future passes) per iron rule 1.
- **B11 — sequence health** (advisory, B8/B9/B10 family):
  - mid-sequence head switches, with the beat pair cited (measured against
    the planner's own sequence computation, so gate and annotate cannot
    disagree — the B10 precedent);
  - non-coda `wide` beats (wide with a successor, outside the
    epilogue/ending region);
  - the per-head share of headed beats (report-only — a one-passage head is
    visible taste, not a violation).

### FILL: Voice reads the roster

`fill_voice.j2`'s context gains the roster (names + ids); the `pov` bullet
instructs the scheme description to name exactly those heads. No model
change to `Voice` (its `pov` stays the prose scheme; the roster is the
structured truth beside it). FILL's write/review machinery is untouched.

## Failure modes (the TDD contract — each gets a test before code)

| # | Mode | Guard |
|---|---|---|
| 1 | proposal omits a sequence / covers one twice | repairable `ApplyError` naming the missing/duplicated sequence ids |
| 2 | `sequence` key is not a sequence head-beat id | unrepresentable (enum pin) |
| 3 | `head` outside the roster | unrepresentable (enum pin) |
| 4 | split `after` outside the sequence / last beat / unordered / duplicated | repairable `ApplyError` with the valid split points |
| 5 | split or wide-cutaway without justification | schema (`why` min_length) |
| 6 | wide-cutaway segment whose beats aren't marked `wide` | repairable `ApplyError` (cross-check at apply) |
| 7 | scheme pass returns an empty roster | schema (min 1) |
| 8 | roster id not a retained character | unrepresentable (enum pin) |
| 9 | `wide` beat inside a headed segment | normalized to `None` (today's rule, kept) |
| 10 | hand-edit writes an off-roster head | I17 (error) |
| 11 | single-beat sequences (63 on run-6) | trivially one head — covered by the coverage test |
| 12 | pre-roster project loads | empty roster → no pinning, I17 skips, prompts degrade to today's — regression test |
| 13 | bridge/arm beats after annotate | wildcards / mirror copy — unchanged-behavior tests |
| 14 | mid-sequence switch sneaks through (justified split) | B11 reports it; test the count |

## PR slicing (sequential, each offline-green)

- **PR-A — the roster:** `pov_head` field + mutation, the scheme pass,
  I17 + violating construction, `fill_voice` context, golden untouched
  (no roster = degenerate case), e2e fixture gains a scheme proposal.
  Docs: 01 §5/§8, 02 GROW contract (the scheme pass), this plan's status.
- **PR-B — sequence-unit annotate:** context (sequences + candidate
  heads), schema (two sections; enum pins), apply (coverage, splits,
  expansion), `grow_annotate.j2` rewrite, B11, fixtures re-recorded.
  Docs: 01 terminology (*sequence*) + §10.3 pointer, 02 annotate contract,
  mini-ADR row (03 §9): sequence-unit assignment; alternatives rejected —
  stateful "keep unless impossible" (sticky bias, order-dependent,
  judgment fence), per-beat with more rules (prompt accretion), post-hoc
  smoothing (papers over the defect, overrides judgment mechanically).

## Live validation (unbilled, after PR-B)

On a **copy** of the cc-struct-medium project (never the FILL-in-progress
original): `qf rerun grow --keep intersections --keep weave --keep
contextualize --keep bridge` — the kept passes replay from the A16 cache
(free), `scheme` + `annotate` run fresh on the *same weave*; then rerun
POLISH. Direct A/B against run-6 on identical structure. Acceptance:
mid-sequence switches ≈ 0 (B11 quiet or every switch justified), passage
count on the same graph falls toward the ~114 counterfactual (+ audit
variants), B3 in band, stretch metric honest, head shares matching the
scheme. Then read one head-switch boundary for craft (does the rotation
land at a real shift?).

## Open questions (flagged, not preempted)

1. **Fold the interludes gap in?** (BACKLOG: "interludes never fire at
   annotate", both tiers.) The scheme pass is the natural home — it could
   also resolve the deviant register's carrier head and expected use from
   the `pov_hint`, giving annotate an explicit expectation instead of an
   unused option. Recommended: fold into PR-A (one small field, one prompt
   sentence). Author sign-off wanted because it touches the register
   semantics.
2. **Roster changes on rerun.** `qf rerun grow` re-runs the scheme pass; a
   different roster invalidates downstream heads by construction (annotate
   re-runs with it — consistent). No action; noted for operators.
