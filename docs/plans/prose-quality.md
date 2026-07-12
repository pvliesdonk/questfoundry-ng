# Prose quality at scale — implementation contract

> Effort plan for STATUS next-up #1 (author-directed, 2026-07-11). The
> design brief is the decision-log entry "live run 8 reading findings";
> this document turns it into buildable contracts. Like earlier plan
> docs (M6, M8) it retires into STATUS/design-doc records when the
> effort completes.

## The problem

Reading "Closed Circle" (live run 8, 49k words) surfaced the first
quality gap only a book-length read could: **verbatim recurring
descriptions**. One character takes "the wide lateral stance of a
classical fencer" in 25 of 148 passages, near word-for-word. The trace
(decision log): FILL discovers a vivid micro-detail once, every later
write context renders it verbatim whenever the entity is on stage, the
writer performs the phrase already sitting in its prompt, the window
doubles the exposure, and the per-passage review *rewards* the
repetition as consistency. Two aggravators: details are stored as
performed prose sentences (the pre-voiced-summary bias vector, now in
the entity layer), and the key-level single-assignment guard lets
near-duplicates accrue under different keys (`habit` vs `stance_width`,
both the fencer stance).

A second input arrived from the weak-tier DRESS chase (decision log,
2026-07-11): with the deterministic causes fixed, the residual
weak-tier blocker is **reviewer sub-clause literalism + one-sentence
quoting**, unfixable by rule tweaks on a map whose arbiter is the same
weak model.

## Direction (author's brief, recorded verbatim in the decision log)

1. The deterministic **echo check at FILL apply** is approved — modest
   expectations, cannot hurt.
2. Most of the fix is **prompt engineering: tell the writer how to
   interpret each context block and what to do with it** — facts are
   constraints, not choreography; the window is continuity, not a
   style template.
3. The generalized register rule: **everything that is not prose
   should not be prose** — micro-details and every other LLM-written
   non-prose field carry the brief register. Relatedly, a too-thin
   Voice may itself cause copying: a writer short on style guidance
   leans on whatever styled text is at hand.
4. A deeper prose look-back blows up tokens; build a **rolling
   story-so-far summary by a utility-tier summarizer** instead.
5. **Character-arc metadata** (the POLISH output deferred to be shaped
   by its consumer; 02 already contracts it) — its trigger condition
   has demonstrably fired. It paces *specific aspects* of a character
   per scene instead of pushing all details into all scenes.

## Workstreams

### W1 — Echo check at FILL apply (deterministic, repairable)

`pipeline/echo.py`: pure functions over punctuation-stripped,
lowercased token sequences. At `write` apply, after the word-budget
check:

- **Fact echo** — any rendered entity fact value (base + overlays) of
  ≥ 4 tokens appearing verbatim in the prose fails the apply, naming
  the entity, key, and phrase: the fact is established, restating it
  is the stamp; the repair asks for fresh wording or silence.
- **Window echo** — any ≥ 8-token verbatim run shared with a window or
  lookahead passage's prose fails the apply, quoting the run. Eight
  tokens is conservative: names and stock collocations don't reach it,
  a lifted sentence does.
- **Micro-detail register cap** — a proposed detail value over 12
  words is prose, not a fact: rejected with the register rule in the
  message.
- **Near-duplicate guard** — a proposed detail value sharing a
  ≥ 4-token run with an existing fact of the same entity is the same
  fact under a new key: rejected naming the existing key (closes the
  `habit`/`stance_width` accrual).

All four are `ApplyError`s — the ordinary repair loop, ≤ 2 rounds.
Thresholds are constants in `echo.py` with the rationale beside them;
they are expectations-modest by design (the author's framing) and the
prompt work below is the real fix.

### W2 — Input-role framing in the write prompt

`fill_write.j2` is restructured so every context block states what it
is *for* and what the writer may *do* with it:

- **Cast facts are constraints, not choreography**: they are already
  true and mostly already known to the reader; write the scene so they
  hold; spend words on one only when the scene turns on it, in fresh
  wording (the echo check enforces the floor of this).
- **The window is continuity, not a style template**: continue from
  it; never reuse its imagery or phrasing — the reader just read those
  words.
- Beats keep their existing brief-not-style framing; WORLD STATE and
  shadows keep their audited framing.

### W3 — Non-prose register + a richer Voice

- Micro-details are reported in **note form** ("stance: wide,
  fencer-like"), never as a sentence of the passage's prose — stated
  in the prompt (W1's cap enforces the floor). This generalizes the
  01 §5 summary register to every LLM-written non-prose field; 01 §5
  gains the generalization.
- **Voice grows two fields**: `imagery` (where the voice's images come
  from — sensory domains and their limits) and `dialogue` (how speech
  behaves on the page). Rationale: a writer short on style guidance
  copies whatever styled text is at hand; a palette gives it somewhere
  else to reach. Fields default empty so author-provided `voice.yaml`
  files load unchanged; the voice pass must propose them; the write
  prompt renders them. 01 §2's Voice field list is updated in the same
  PR.

### W4 — Rolling story-so-far

- `Passage.prose_summary` (presentation layer; on-node YAML like
  `summary`) written through a new mutation.
- A `summarize:<slug>` **utility-role** pass follows each
  `write:<slug>` pass: given the accepted prose, produce a ≤ 60-word
  brief-register summary (events, reveals, state changes — a note for
  a later writer, never quoting the prose). No review; word cap at
  apply. One utility call per passage; journaled in the in-flight
  ledger like any pass, so crash resume replays it free.
- The write context gains `story_so_far`: per-passage summaries along
  **one deterministic route** from the story's root to this passage —
  prefer reference-arc predecessors, else lowest passage id; the
  route's last hop (the window passage, whose full prose is already
  shown) is excluded; capped at the most recent 40 summaries with an
  elision note. The prompt frames it honestly: one route among
  several; branch-specific events on it may not have happened for
  every reader — WORLD STATE governs what may be asserted.
- Writing order guarantees every route predecessor is already written
  (reference arc first, then the rest in story order), so the block is
  never partial.

### W5 — Character-arc metadata

Realizes the existing 02 contract (POLISH out: "character-arc metadata
per entity — begins X, pivots at beat Y, ends Z per path"; FILL
context: "character-arc position"). Design:

- `EntityArc` on the world layer: `begins` (state in brief register),
  `pivots` (list of `{beat, becomes}` anchored to real beat ids),
  `ends` (list of `{path, state}`). Stored on `Entity.arc` via a new
  mutation; set-once (POLISH-owned; `qf rerun` rewinds it with the
  graph).
- A fourth POLISH pass **arcs** (writer role, after audit, per 02's
  phase-2 order): proposes arcs for the entities worth arcing —
  every retained entity (author doctrine 2026-07-12: unarced means
  scenery — an extra, a backdrop, a mcguffin, a link; originally
  built characters+objects only, widened same day); `entity`,
  `pivots[].beat`, and
  `ends[].path` are refpin-pinned enums; apply checks pivots are in
  topological order and requires at least one arc.
- FILL's write context renders **ARC POSITION** per on-stage arced
  entity: the latest pivot at or upstream of the passage's beats (else
  `begins`), the next pivot ahead (where the character is heading),
  and a path `ends` entry only when that path's commit is upstream of
  the passage. Framing: this scene foregrounds the named aspect;
  other established facts stay background.

### Follow-up (contracted here, not built in the first PR)

- **Review-contract redesign** for weak tiers — **promoted to its own
  spec, [`docs/plans/review-contract.md`](review-contract.md)** (2026-07-12),
  because the failure is a *class* over every review pass, not prose-only.
  The gpt-oss run drove it concrete: the binary `pass/fail` + free-text
  `issues` verdict false-positive-halts the producer, in three successive
  shapes (rule fabrication → voice-ban footgun → Rule-2 over-literalism).
  The spec replaces it with a structured multi-axis finding schema (rule /
  assessment / confidence / quote / reason / recovery_action) shared by all
  reviews; the engine gates only proceed-vs-rework; the producer gets the
  full-fidelity findings and decides. **BUILT 2026-07-12** (`pipeline/review.py`,
  adopted by fill_review + dress_codex_review); weak-tier live validation
  is the one open item.
- **Live validation**: a fresh `medium` run on a strong map, read for
  recurrence (grep the top n-grams of run 8's stamps), plus a
  weak-tier (`gpt-oss:120b`) FILL attempt to measure the register +
  framing changes against yesterday's failure signature.

## Acceptance

- Violating-construction tests for every W1 check; unit tests for
  route determinism (W4) and arc-position selection (W5); prompt-source
  tests where templates make checkable promises.
- The golden story carries an `arc` on one character (round-trip +
  FILL context exercised); e2e keeper fixtures gain the new passes'
  calls (positional splice, the keeper-craft pattern).
- `uv run pytest -q`, `ruff check`, golden `qf validate` all green;
  fixtures' existing prose clears the echo check (a false positive on
  recorded prose means the threshold is wrong — fix the threshold,
  not the fixture).
- STATUS + design docs updated per the documentation contract: 01 §2
  (Voice fields), 01 §5 (register generalization), 02 FILL (story-so-
  far block, echo check, summarize pass), 02 POLISH (arcs pass now
  built — the contract text already exists).
