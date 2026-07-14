# 05 — Roadmap

Epic-scale plan, organized by horizon: **Shipped** (done), **Now** (in flight),
**Next** (picked up soon), **Later** (after that). Milestones are vertical slices
ordered so the riskiest design bets were tested earliest with the least code;
each has a demoable exit criterion and none depends on a later one.

Granularity here is the **epic**. Sub-epic loose ends live in
[`../BACKLOG.md`](../BACKLOG.md); a task owned by an epic below lives *under that
epic*, not in the backlog. Decisions live in the mini-ADR table (design doc 03
§9) and the dated [`decision-log.md`](../decision-log.md).

> Written and maintained by coding agents for hand-off (AGENTS.md
> §"Documentation contract"). Framing is an agent's unless it cites the author.

## Shipped

The built milestones. Their contracts are authoritative in the design docs
(01–04); the record of how each landed is in the decision log.

- **M0 — Skeleton & graph engine.** `models/`, `graph/` (store, mutations,
  queries, validators I1–I13), project-on-disk, `qf new/validate/graph`. The
  hand-authored golden story loads and passes all gates. → 01, 03.
- **M1 — Front of pipeline (DREAM → SEED).** Uniform stage runner (checkpoints,
  repair loop), LLM adapter (cache, ledger, mock), stages DREAM/BRAINSTORM/SEED,
  gates G0–G2. `qf run --to seed` from a premise, offline via fixtures. → 02.
- **M2 — GROW (the risk milestone).** Deterministic interleaving, divergence/
  convergence wiring, flag derivation, intersections, bridges, topology freeze,
  gate G3, `qf simulate --all-arcs`. Four complete arcs through the golden DAG. → 01 §5, 02.
- **M3 — POLISH & structural play.** Passage collapse, choice wiring, feasibility
  audit, variants, residue, false branches, gate G4; `qf play` on beat summaries. → 01 §6, 02.
- **M4 — FILL & first exports.** Voice, per-passage context, automated review,
  gate G5; runtime JSON + HTML player + Twee with round-trip validation. → 02, 04.
- **M5 — DRESS, print & scope hardening.** Art direction, briefs, codex, the
  gamebook PDF (codewords, Typst), `qf rerun --keep`, multi-hard weaving; first
  live `medium` run within budget. → 02, 04, 03 §9 (A12/A14).
- **M6 — Craft-corpus research.** A research pass at each stage head grounds
  generation in a project-configured markdown corpus (advisory, never binding),
  persisted as checkpointed digests; corpus-less projects run unchanged. A/B
  exit run showed visible craft grounding. → 02 §1, 03 §10 (A13).
- **M7 — Illustrations (`qf illustrate`).** DRESS briefs render to images via
  `image-generation-mcp` as a library (OpenAI/Gemini + hermetic placeholder);
  post-DRESS command, idempotent by file presence. Live on both cloud providers. → 03 §9 (A18).
- **M8 — Depth & scale.** Words-primary scale table (A19), per-scope scaffold
  depth, tensored residue arms, words-aware cadence, bands recalibrated by
  structural simulation. Live `medium` exit run "Closed Circle" at 20–60k words. → 01 §2/§5, 02, 03 §9 (A19).

Post-M8 structural/prose efforts (each a plan doc + decision-log entry): the
prose-quality-at-scale engine, `scene_type` and `narration_scope` beat
annotations + the B8 pacing report, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), and the POLISH passages-pass
decomposition (A21). See `docs/plans/` and the decision log.

## Now

- **Prose quality at scale — the remaining live validation.** The engine half is
  built (echo check, rolling story-so-far, input-role framing, richer Voice,
  character-arc metadata, `scene_type`/`narration_scope` modulation, the
  structured review contract) and offline-green. **Open:** no weak tier
  (`gpt-oss:120b`) has completed a full clean FILL/DRESS at scale — runs reach
  FILL and stochastically exhaust review on the hardest passages. The *Closed
  Circle* medium run (2026-07-14) advanced this: POLISH now clears clean at
  medium (the A21 passages decomposition validated), and FILL surfaced the
  rotating-POV gap (below) as its passage-1 blocker. **Exit:** a corpus-grounded
  weak-tier story completes FILL and DRESS gate-clean, exports round-trip, and
  reads without prose-quality rework.

- **Rotating limited POV.** A wanted, previously-mis-deferred feature: the
  viewpoint character changes across the book while each unit stays in one head.
  The author answered the design questions directly (2026-07-14: per-passage
  head, GROW-annotate assignment, no cadence engine constraint, first-person
  interludes in v1) and the engine half is **built offline-green** (per-beat
  `viewpoint`/`interlude`, the collapse cut, I14, per-passage FILL enforcement,
  `Voice.interlude`). **Open:** the live *Closed Circle* validation on a
  fresh medium project (the prior session's project died with its container;
  a surviving pre-viewpoint project would resume at `qf rerun grow`, since
  heads are minted at GROW's annotate pass and a POLISH checkpoint is
  headless by construction) — the acceptance test is FILL clearing the
  rotating-scheme passages, with the rotation reading deliberately.
  → [`../plans/rotating-pov-build.md`](../plans/rotating-pov-build.md).

## Next

- **M9 — Retrieval refinement (exemplars & standing queries).** The two
  retrieval findings from M6's exit run, made first-class. (1) **A reserved
  exemplar mechanism**: style exemplars belong at the voice pass as a contrasting
  spread and nowhere else — config names the exemplar folders, the voice pass
  retrieves a *diverse* spread, every other stage excludes them structurally
  (today the only guard is manual `craft.folders` scoping, and an unscoped corpus
  floods early digests with atmospheric prose). (2) **Standing-query shape**:
  verbatim vision fields make poor search strings (a 30-word tone sentence
  retrieves the same boilerplate at every stage) — condense to keyword form or
  rebalance toward the librarian, whose queries carried the value in the A/B run.
  **Exit:** on the same corpus *without* manual scoping, no exemplar material
  appears in any non-voice digest; the voice pass shows a spread of distinct
  exemplars; per-stage digest sources visibly differ.

## Later

- **Pipeline operator loop** (author-proposed, 2026-07-14). A frontier-tier AI
  operator supervising live runs as part of the pipeline itself, doing what
  this session's external loop did for the *Closed Circle* validation: watch
  pass telemetry, diagnose each halt (prompt defect vs structural vs
  non-convergence at the review cap), journal every stall verbatim, re-roll a
  failed pass's cached call chain with a per-passage retry cap, and stop for
  escalation when a stall repeats or a failure isn't review-shaped. The
  in-session prototype (a ~90-line driver + stall journal) cleared 7 stalls
  across a medium FILL unattended and its journal fed 5 prompt fixes back
  into the repo — the pipeline version would be a first-class runner mode
  (an `--operator` supervisor around `qf run`), with the frontier tier doing
  the diagnosis and the unbilled tier doing the writing.

- **Sampling & reasoning knobs per stage** (author-proposed, 2026-07-14).
  The Ollama provider already exposes `temperature` and `think` project-wide;
  make them per-role/per-stage and measure whether they matter where it
  counts: does low temperature help the mechanical passes (annotate, labels,
  codewords) converge; does higher temperature help the writer's variety
  without hurting review convergence; does reasoning effort/thinking help the
  reviewer and arbiter apply rules as written (the fabricated-rule class) —
  the A16 ledger and the stall journal give the measurement instruments.
  Fold in the model-tier question the same experiments raise: the cloud
  catalog now carries stronger tiers (GLM-5.x, Kimi K2.5+, DeepSeek-V4-Pro)
  worth benchmarking against the `gpt-oss:120b` baseline — remembering the
  2026-07-14 doctrine note: a stronger model *hiding* more defects is not
  the same as fewer defects; judge by gates and the stall journal, not by
  fluency.

- **M10 — SHIP & the author loop.** The last pipeline stage and the review
  experience around it.
  - **SHIP**: final assembly + the Twee lint that flags constructs which don't
    survive SugarCube conversion (04 §3).
  - **Interactive checkpoint review**: `qf run --yes` stops being a stub — batch
    stays, but without `--yes` the run pauses at each checkpoint for
    review/edit/continue (02 §3).
  - **`qf simulate --random N`** (04 §5): its trigger is met — false-branch
    diamonds now occur in every generated story and `--all-arcs` never walks them.
  - **Run resilience**: a transient transport failure (provider disconnect, 5xx —
    live run 8 died four times on drops) should auto-resume the interrupted stage
    with bounded backoff instead of exiting. The Gemini provider already streams
    and retries per call; stage-level auto-resume (free via the A16 ledger) is
    the remaining piece — today a human re-invokes `qf run`.
  - *(Progress reporting was pulled forward and shipped: per-pass stderr
    heartbeat, `qf status` live run state.)*
  - **Exit:** `qf run` pauses at a checkpoint, the author edits an artifact, the
    run resumes and revalidates; `qf export twee` lints; a random-walk simulation
    covers detours the arc walk misses; a killed connection costs a log line, not
    a dead run.

- **Explicitly deferred (revisit on demand):**
  - Local review web UI (graph explorer + prose reader with approve/edit) —
    builds on M10's CLI review semantics.
  - LLM playtester with subjective reports.
  - Distributed commits ("Witcher principle") — needs a threshold-flag
    primitive; revisit after real stories expose the demand.
  - Cosmetic codeword curation, translation/localization, EPUB export.
  - **Provenance for this administration** — the real fix for "agents author the
    record" is moving the backlog to **GitHub issues** (and milestones for this
    roadmap); deferred while development velocity makes issue ceremony cost more
    than it returns. The AGENTS.md caveat is the interim guard.

## Top risks

| Risk | Mitigation |
|---|---|
| Weak-tier prose quality at scale — a cheap model reaches FILL but exhausts review on the hardest passages | The prose-quality engine (echo check, story-so-far, modulation, review contract) is built; the remaining work is live validation, not new machinery — the "Now" epic |
| Illustration cost/quality on non-reproducible providers (no seeds, content-policy refusals, character drift) | M7's sample-first gate + budget/priority caps; skip-if-exists makes reruns free; typed refusals get one reformulation; entity visual fragments in every prompt, reference-image conditioning as the escalation |
| Preset calibration circularity — bands tuned on stories generated under the old bands | Words-primary scale table anchors on the corpus's external 300–600 words/choice band; recalibrate against modulated live runs (BACKLOG: scale recalibration) |
| Feasibility audit mis-calls (hedged prose) | I12 hard cap at 3 states; heavy residue *must* produce variants. Still open: no live run has stress-tested the audit against genuinely hedged prose |
| Exemplar leakage / style anchoring ahead of the Voice | M9 makes the reserved-folder exclusion structural; until then `craft.folders` scoping is documented as required (03 §10) |
| Token cost blowups at `long` scope | Budgets gate-checked from DREAM; ledger + cache; `utility` model role for cheap calls |
| Author edits breaking invariants silently | Single validation path: `qf validate` runs the same gates on files as the pipeline runs on proposals |

Retired risks, for the record: GROW interleaving quality and prose coherence
across convergences (seven+ live runs across four provider families produced
gate-clean, seam-free stories); the weave's 64-candidate spread at scale
(measured and fixed in M8 PR-1, exercised live at 40+ units in run 8); deep
scaffolds stretching choice-less runs faster than false branches close them
(addressed in M8 PR-1 — the collapse cap cuts deep runs into pages and POLISH's
diamond budget is sized by iterated playthrough projection against the B6 band;
the live exit run confirmed).
