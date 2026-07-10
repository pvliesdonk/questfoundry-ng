# Project Status

> **Living document — the session hand-off note.** Every PR updates this
> file: what changed, what's next, decisions made. If you are an agent
> starting a session, read this first; if you are ending one, leave it
> the way you'd want to find it.
>
> Last updated: 2026-07-10 · M6 engine landed (research pass, A17, PR #30) — the live A/B validation run completes the milestone

## Where we are

**The M6 engine is built** (PR #30; plan and design record in PR #29 /
`docs/plans/m6-craft-corpus.md`): configure a `craft:` block in
project.yaml and a **research pass** heads every stage — the librarian
proposes at most `max_queries` search strings (standing queries derived
from the vision are shown so it asks only for what's missing; DREAM
runs premise-only), the engine retrieves via `markdown-vault-mcp`'s
Python API (hybrid or keyword, per-folder, re-sorted deterministically)
and persists an author-editable `research/<stage>.md` whose body every
substantive pass reads as an advisory `_craft.j2` block. Review
prompts are structurally immune (they render themselves); the
feasibility audit and the mechanical picks are excluded deliberately.
The digest is checkpointed, fingerprinted (A16: corpus hash + craft
config join the knobs only when configured), and reused while fresh
(A17: `prepare_rerun` preserves the target's digest; a corpus or
vision edit re-retrieves; deleting the file forces it). Corpus-less
projects are untouched to the byte — the pass skips, positional
fixtures hold, and CI never installs the retrieval stack (tests drive
real hybrid search through a deterministic fake embedding provider).
Not yet done: the live A/B exit run (next up #1).

**Locked dilemmas + richer residue are built** (the structural
volume/depth effort, author-blessed 2026-07-09; decision log below has
the design record):

- **Locked dilemmas** end-to-end: BRAINSTORM overgenerates by the
  scope's new locked allowance (B1 checks a range pre-triage, branched
  equality after); SEED triage gives every dilemma a disposition —
  branched or locked-with-a-reason — and scaffolds locked storylines as
  lead-in / resolution / aftermath chains on the single explored path;
  the weave threads each chain through the story one movable unit per
  beat (wraps/serial anchor at first beat and resolution; locked beats
  may join intersection groups — they are on every arc); after a hard
  fork the chain clones per world like any unit and contextualize
  rewrites the clones. Invariants: I3 gained the locked-chain shape,
  I6 requires every arc to resolve every locked dilemma exactly once,
  and a locked outcome is a world fact — G3-FLAGS exempts its
  consequences and rejects flags granted from a locked path (mini-ADR
  A15: the disposition is derived from topology, no marker). A locked
  hard-role dilemma makes no worlds and cannot be the backbone.
- **Richer residue**: light residue now demands the full diamond — one
  flag-gated residue arm per path per world (G4 + finalize apply,
  repairable), and an arm may carry a `followup` beat; passage collapse
  merges identically gated adjacent beats, so a 2-beat arm reads as one
  gated passage, not click-through singletons.
- **The golden story exercises both**: `dilemma:second-keeper` (what
  ended the previous keeper's watch — locked, resolved on every arc,
  no flags, woven pre-fork), a hide-side residue arm (`beat:unspoken`,
  new passage, codeword UNSPOKEN now that the detour gate tests
  `flag:lie-between`), and a 2-beat tell arm (`counsel` +
  `honest-chart` collapsing into `p-counsel`). 8 passages, all exports
  round-trip clean, PDF compiles with zero numbering warnings (the old
  7-passage impossibility dissolved at 8). 256 tests.

Not yet exercised live: the next generated story should confirm a real
model locks sensible dilemmas at triage and writes residue followups
where they earn their room (the prompts ask for exactly this).

**M5 is complete.** Both halves of the exit criterion are met: the
golden story prints as a real gamebook (PR #20), and the pipeline
generated its first live `medium`-scope story end-to-end within budget
(PR #23) — "The Bubblegum Alibi", a closed-circle murder mystery in a
bubblegum high-school setting, on the default model map
(claude-opus-4-8 architect/writer + claude-haiku-4-5 utility):

- **The medium run** (preserved as `examples/bubblegum-alibi/`):
  4 dilemmas (2 hard nested by the live multi-hard weave, 2 soft — one
  rejoining at the other's fork), 10 entities, 46 frozen beats across
  two worlds, 20 passages (~10.4k words), 16 arcs all simulating
  complete, 4 titled endings, full DRESS enrichment (direction, 10
  profiles, 4 briefs, 7 codex entries, 4 on-diction codewords:
  CRACKED, SILENT, SNAPPED, MURKY), 0 gate errors, all four exports
  round-trip clean including the print PDF. Budget: **~$3.25** — 187
  calls (99 live: opus 259k in / 74k out; haiku 82k in / 3k out; 88
  free cache replays across crash-resumes), ~24 min wall-clock summed
  over eight attempts. The run surfaced **six engine/contract bugs**,
  each fixed in-flight with a violating-construction test (decision
  log); the crash-resume machinery (content-addressed cache + per-stage
  checkpoints) is what made eight attempts cost ~one clean run. 221
  tests. Stage output was committed per checkpoint on PR #23 — a useful
  pattern for future live runs.

- **Multi-hard weave expansion** (PR #22) (the tensor model, design doc 01 §5,
  mini-ADR A14): `weave.realize` walks the chosen order tracking
  *worlds* — the climax hard resolve is always the final unit; every
  unit placed after the first hard fork is instantiated once per world
  (world-suffixed ids, `belongs_to` copied, the template Y removed
  symmetrically so no world owns the "original"), each further hard
  resolve multiplies the worlds, and the earlier forks' tails stop
  being endings (2 hard → 4 endings). Candidates enumerate per viable
  nesting (an even share of the 64 cap each) so the weave LLM chooses
  the nesting like any interleaving; `wraps`/`serial` between hards
  constrain it — `serial(hard, soft)` now legitimately places a whole
  soft dilemma inside the worlds, cloned per world with per-world
  convergence. A new GROW pass *contextualize* (skip_if single-hard)
  rewrites each clone's summary for its world and each de-ended tail
  to leave the climax question open. Invariants refined: I3 is now
  "commit beats occupy pairwise distinct worlds" (worlds are made by
  *other* dilemmas' forks), I6 checks exactly one commit per path per
  arc, I7 checks hard non-reconvergence pairwise across commit sets
  and soft payoff per world; `queries.commit_beats`/`grant_beats` are
  list-valued with any-grant semantics; `FreezeRecord.convergences`
  records one beat per world (legacy single-beat files coerce on
  load). POLISH gained per-world variant support: a heavy-residue soft
  dilemma rejoining at a hard fork now requires variants at every
  frontier beat (the old G4 "unsupported" error is gone), and light
  residue coverage is checked per world. Intersections stay
  constrained to the truly shared region before every hard fork.
  215 tests; the 2-hard topologies are built through the real weave,
  never hand-wired.

- DRESS (`pipeline/stages/dress.py`), four passes sharing gate G6:
  *direction* (art direction + one visual profile per retained entity;
  `skip_if` keeps an author-approved direction on reruns), *briefs*
  (prioritized illustration briefs, `max(3, min(20, passages//5))`, the
  engine checks every cited entity is in the passage and profiled),
  *codex* (one diegetic entry per dilemma-anchoring entity, spoiler
  safety enforced by a paired utility review whose contract follows the
  review-legibility lessons: numbered FAIL rules, quote the offending
  text, hedged findings excluded), *codewords* (one memorable word per
  gate-tested flag — suggested at DRESS, not POLISH, because "drawn from
  the story's diction" needs voice and prose to exist; mini-ADR A12).
  Enrichment lives on the Project like the Voice (`art/direction.yaml`,
  `art/briefs/`, `codex/*.md`), never in the graph; gates see it via
  `run_checks(enrichment=…)` — one validation path. Codewords are graph
  data on flags via `mutations.set_flag_codeword` (stable once set).
- Print gamebook (`export/gamebook.py`, `qf export pdf`): consumes the
  canonical runtime JSON only; codeword projection (= gate-tested
  flags; slug-derived fallback + warning for pre-DRESS projects),
  grant lines hoisted to a section iff every arriving choice grants the
  flag, variant lowering ("if you have X, turn to N; otherwise …"),
  seeded numbering under anti-spoiler constraints (start=1, linked and
  variant and ending sections non-adjacent; best-effort + warnings when
  unsatisfiable — the 7-passage golden provably cannot satisfy all
  three families, verified by brute force), Typst layout (title,
  how-to-play, codeword log, sections, codex appendix, titles-only
  ending index) compiled to PDF in-process via typst-py (CI-hermetic),
  and a paper-specific lint (turn-to resolution, codeword granted
  before every test, no orphaned or dead section) that blocks export.
  `print_seed` persists in project.yaml on first export, like the IFID.
- `qf rerun <stage> [--keep <pass>]` (design doc 02 §3): checkpoints now
  persist each pass's accepted proposal; rerun rewinds stage artifacts
  (graph, prose, art, codex, voice) to the predecessor checkpoint while
  preserving the author's knobs (steering, vision edits — editing those
  is *why* you rerun), then re-runs the stage with kept passes
  re-applied without an LLM call; stale keeps fail loud. The runner's
  failed-apply restore now covers enrichment too (and the PR review
  caught that kept passes must restore on failure like live ones).
- HTML player gained the codex panel (design doc 04 §2); runtime JSON
  now ships codex + art (art entries only for briefs whose
  `art/images/<slug>.png` actually exists) and validates them in the
  round-trip check.
- The golden story is at stage `dress` with hand-authored enrichment
  (direction + 4 profiles, 3 briefs, 4 spoiler-safe codex entries,
  `CONFESSED` on the one gate-tested flag) and exports a complete
  14-page PDF; e2e now runs `--to dress` offline (36 ledger calls, one
  staged codex-review-fail/revise round). 203 tests total.

**M4 is complete.** FILL writes the prose and the story ships to its
first playable formats — `qf run --to fill` then `qf export html` puts
"The Keeper's Bargain" in a browser:

- FILL (`pipeline/stages/fill.py`) rides two small runner extensions:
  `StageImpl.passes` may be computed from the project (the work queue —
  one write pass per passage, reference-arc-first; the reference arc is
  seeded FILL-local scheduling state, `fill_seed` in project.yaml), and
  `PassSpec.review` runs a post-apply LLM judgment whose issues re-enter
  the ordinary repair loop — so "≤2 revision rounds, then halt: the
  structure is wrong, not the words" is `max_repairs`, not bespoke
  orchestration (mini-ADR A10)
- Per-passage write context: voice, beats, entities (base + overlays),
  flag statuses (certain / possible / foreclosed — gated residue
  passages count their gate as certain), shadows, window of
  already-written predecessor prose, convergence lookahead, choice
  labels, word budget (deterministically enforced at apply, repairable)
- Voice is a singleton `voice.yaml` (locked before any prose; skipped
  when author-provided); prose lives on the Passage node in memory and
  as sibling `prose/<slug>.md` files on disk; universal entity
  micro-details merge into base state through the mutation layer and
  never overwrite established facts
- Gate G5: prose presence (error), B5 word budget (advisory), voice
  presence (checked in the stage gate)
- First exports (`export/`): canonical runtime JSON with a
  self-contained round-trip validator (re-walks the exported document
  alone — I10/I13 at the export boundary), standalone HTML player
  (dependency-free, gated choices hidden, journey recap, one save
  slot), Twee 3 / SugarCube (entry `<<set>>` grants, `<<if>>`-guarded
  links, IFID persisted in project.yaml without rewriting the project);
  `qf export json|html|twee`, always round-trip-checked first
- The golden story now carries hand-authored prose (7 passages + voice,
  stage: fill) and was played **in an actual browser** (headless
  Chromium over the exported HTML) start to "The Long Watch" — the M4
  exit criterion
- e2e: `run --to fill` writes all 8 passages offline with one staged
  review-fail/revise round exercised (29 ledger calls), exports
  validate clean, and the runtime document alone replays all four
  journeys (132 tests total)

**M3 is complete** (PR #10). POLISH compiles the frozen beat DAG into the passage
graph, and the story is playable in the terminal with zero prose:

- Deterministic passage core (`pipeline/passages.py`): maximal-linear-run
  collapse (boundaries at forks/joins; flag-gated beats are singleton
  passages), choice topology with engine-computed endpoints, gates
  (target head's `requires_flags`) and grants (commit beats contained in
  the target), residue/false-branch splicing, convergence-need and
  long-run detection, I12-style active-flag computation. **The golden
  story is the oracle**: collapse and choice derivation reproduce its
  hand-authored passage layer exactly (tested).
- POLISH stage (`pipeline/stages/polish.py`), three passes: *finalize*
  (LLM writes flag-gated residue beats for every light-residue soft
  convergence — required, repair-checked — and may propose false-branch
  diamonds on long runs; skipped when nothing is needed), *passages*
  (engine fixes groups and choice wiring; LLM contributes only words:
  summaries, labels, ending titles, and variant summaries for
  heavy-residue convergences, which the engine wires behind disjoint
  gates, skipping variant choices whose gate is unholdable from a
  source — I10), *audit* (feasibility: LLM marks irrelevant flags;
  I12 enforces the cap on the rest)
- Gate G4 additions: `G4` label checks (non-empty; sibling duplicates
  only behind different gates, for variants) and residue coverage
  (light convergence → gated residue beat; heavy → variant passages)
- `qf play` (`play/engine.py` + `play/tui.py`): flag-tracking traversal
  with hidden-not-disabled gated choices (design doc 04 runtime
  semantics), rendering beat summaries pre-FILL; `--show-state` for
  structural debugging. The golden story plays end-to-end — four
  distinct journeys, gated counsel detour, both endings (tested
  headlessly and via the CLI)
- e2e: `run --to polish` on the Keeper's Bargain premise reaches POLISH
  with 0 gate errors — 8 passages (residue beats on both truth paths),
  two titled endings, four distinct playable journeys (109 tests total)

**M2 is complete** (PR #9). GROW weaves SEED's disconnected Y scaffolds into one
frozen beat DAG; `qf run --to grow` goes premise → four complete,
validated arcs, fully offline against recorded fixtures:

- Deterministic interleaving core (`pipeline/weave.py`): each dilemma
  becomes movable shared pre-commit units plus one atomic *resolve* unit
  (commits + post-commit chains — a reconverging diamond for soft, the
  terminal split for hard); constraints from `wraps`/`serial`, temporal
  hints (advisory: dropped with a report note if unsatisfiable), and
  intersection adjacency; bounded candidate enumeration; realization is
  a full PREDECESSOR edge-set recompute through the mutation layer
- GROW stage (`pipeline/stages/grow.py`), three passes: *intersections*
  (LLM proposes co-occurrence groups over shared pre-commit beats, which
  merge into one interleaving unit), *weave* (LLM only **chooses among**
  engine-valid interleavings; engine rewires the DAG and derives one
  flag per consequence, granted at the path's commit), *bridge* (engine
  finds entity-disjoint adjacencies; LLM writes structural bridge beats;
  pass skipped when there are no gaps — `PassSpec.skip_if`)
- Topology freezes on a clean gate G3 (`freeze.yaml` written); G3 gained
  `G3-FLAGS` (flag derivation total, error) and `B4` (beats per arc
  within scope, advisory like B3); presets carry `arc_beats_min/max`
- SEED now emits **temporal hints** and **flexibility annotations**
  (M1 deferral resolved): `Beat.temporal_hints` / `Beat.flexibility`,
  scaffold schema + prompt updated, hints validated against known
  dilemmas
- `qf simulate --all-arcs` (`play/simulate.py` + CLI): walks every
  computed arc with commit/flag/ending markers, exits non-zero on
  incomplete arcs; golden story and generated story both walk 4/4
  complete
- Golden story gained a natural intersection (`ledger-landing`), so I8
  disk I/O is exercised end-to-end
- e2e: `run --to grow` on the Keeper's Bargain premise reaches GROW with
  0 gate errors — 16 beats, single root, the soft dilemma converging on
  the shared `beat:the-offer` (90 tests total)
- Documentation hardening after the multi-hard episode: the original
  QuestFoundry source documents now live in `docs/heritage/` (reference-
  only, NG design docs remain the single authority) and design doc 01
  gained §9 "Where the mapping breaks" — the danger zones that stranded
  the original or nearly stranded NG

**M1 is complete** (PR #8). The front of the pipeline runs end-to-end,
fully offline against recorded fixtures:

- Uniform stage runner (`pipeline/runner.py`): context → render →
  complete → apply (repair ≤2, graph restored on failed applies) →
  gate → checkpoint (snapshot + report); `run_pipeline` chains stages
- LLM adapter (`llm/`): schema-validated structured output with retry-
  on-invalid, content-addressed cache, JSONL cost ledger; providers:
  Anthropic (thin SDK wrapper) and Mock (fixture replay/record)
- Stages DREAM, BRAINSTORM, SEED (`pipeline/stages/`) with Jinja2
  prompts; proposals carry content, the engine derives all structure
  (beat classes, impacts, `belongs_to`, intra-dilemma Y ordering)
- Gate G0 (vision completeness) added to the validator registry;
  `Stage.NEW` marks a scaffolded-but-unstarted project
- CLI: `qf run <stage>` / `qf run --to seed [--yes]`; project.yaml
  gained `llm:` (provider, role→model map) and `steering:` (per-stage
  author notes injected into prompts)
- e2e: `run --to seed` on the Keeper's Bargain premise via MockProvider
  reaches SEED with 0 gate errors (53 tests total)

**M0 is complete** (merged: PR #3). The foundation exists and is green:

- Typed models for all five layers with scope-preset budgets
  (`src/questfoundry/models/`)
- Story graph with a single validated write path
  (`graph/store.py` + `graph/mutations.py`)
- Invariants I1–I13 + budget checks wired to gates G1–G4, run
  cumulatively by project stage (`graph/validate.py`)
- Computed arcs, DAG walks, flag grant positions (`graph/queries.py`)
- YAML-per-node project format with lossless round-trip (`project/io.py`)
- CLI: `qf new / validate / status / graph` (`cli.py`)
- Golden story `examples/keepers-bargain/`: 2 dilemmas (1 hard, 1 soft),
  17 beats, 7 passages, 4 arcs; exercises freeze semantics, a post-freeze
  residue beat, and a flag-gated choice
- 32 tests + Hypothesis property test; CI runs ruff + pytest + golden gates

**Design docs** (`docs/design/00-05`) were merged in PR #1 and are
authoritative. Repo also carries `REVIEW.md` (automated-review norms,
PR #5) and this agent/doc infrastructure (PR #6).

## Milestones

- [x] **M0 — Skeleton & graph engine** (PR #3)
- [x] **M1 — Front of pipeline (DREAM → BRAINSTORM → SEED)** (PR #8)
- [x] **M2 — GROW** (the risk milestone: interleaving, intersections, freeze) (PR #9)
- [x] **M3 — POLISH & structural play** (`qf play` on beat summaries) (PR #10)
- [x] **M4 — FILL & first exports** (JSON, HTML player, Twee)
- [x] **M5 — DRESS, print gamebook, scope hardening** — DRESS/G6,
  `qf export pdf`, `qf rerun --keep` (PR #20); multi-hard weaving
  (PR #22); the live `medium`-scope run within budget (PR #23)
- [ ] **M6 — Craft-corpus research** (added 2026-07-09; roadmap §M6,
  design docs 02 §1 and 03 §10) — ground the pipeline's LLM calls in a
  markdown craft corpus via an engine-side research pass; **engine
  built** (PR #30, plan: PR #29 / `docs/plans/m6-craft-corpus.md`);
  exit = the live A/B run (same premise with and without a corpus)

## Next up

1. **M6 exit — the live A/B validation run** (procedure:
   `docs/plans/m6-craft-corpus.md` §PR-2): the author exports the
   IF-craft subtree of his vault as a local corpus directory, then the
   same premise generates with and without a `craft:` block — verify
   digests at every stage, fingerprints in every report, the
   byte-stability drills (crash-resume, `--keep research`, edited
   digest surviving a rerun), and judge the craft-grounding delta
   side by side.
2. **A live run exercising locked dilemmas + richer residue** — folds
   into the M6 validation premise; watch triage's lock choices, the
   residue followup judgment, and whether the new summary register
   holds (beat summaries as briefs, not prose).
3. **Scaffold deepening after M6** (corpus-medium word totals, 20–60k):
   deeper/tensored Ys once the research pass can feed them real
   material; scale table becomes words-primary at that point.
4. Optional polish: an image backend behind the briefs (design doc 02
   lists illustrations as optional; briefs + the PDF/HTML plumbing are
   in place — `art/images/<passage-slug>.png` is picked up when
   present).

## Known deferrals / open items

- ~~A Gemini provider is unbuilt~~ **Built and validated** (PR #18):
  `llm/providers/gemini.py` over the google-genai SDK, wired into the
  CLI (`llm.provider: gemini`; the SDK reads `GEMINI_API_KEY` itself).
  First Gemini-driven generation ran 2026-07-08 — results in the
  "live run 4" decision-log entry. All three provider families
  (Anthropic, OpenAI, Gemini) have now produced a complete story.

- ~~Crash-resume replay of FILL was leaky~~ **Both halves are now
  fixed.** The cache half (byte-stable prompts) was fixed 2026-07-08,
  and `save_project` pruning closed the stale-file leak (PR #23). The
  artifact half is resolved by the **in-flight proposal ledger**
  (2026-07-10, mini-ADR A16 — see the decision log): every accepted
  pass journals its proposal to `inflight/<stage>/` as it lands, and
  re-entering an interrupted stage replays those passes through the
  kept-pass machinery with zero LLM calls, independent of the cache.
  Prose files still reach the working tree only at the gate-passing
  checkpoint — the ledger is not a checkpoint, so 02's semantics hold.
  Residual (recorded, accepted): a crash *inside* `_checkpoint` itself
  can leave a partial snapshot — pre-existing, unrelated to the
  ledger, and recoverable by rerunning the stage.

- ~~Prompt framing: early stages claim certainty they don't have~~
  **Addressed** (calibration batch, see decision log): DREAM's prompt
  now states that a vision is texture and intent, never countable
  coverage; BRAINSTORM's states it supplies ingredients for triage and
  that every entity must anchor a dilemma. Validated on the next live
  run.

- ~~Established entity attributes don't reliably survive FILL~~
  **Addressed** (calibration batch): `Entity.pronouns` is an explicit
  field, BRAINSTORM fills it, FILL's write context renders it
  prominently ("PRONOUNS: they/them, exactly"), and the FILL review
  gained numbered rule 6 — pronoun contradiction, quote the offending
  text — the checkable, taste-free shape the review contract demands.
  Validated on the next live run.

- ~~Medium preset ranges don't match what the pipeline builds~~
  **Recalibrated** (calibration batch, author-confirmed: the original
  numbers were *beat* counts from the one-beat-one-passage era — see
  decision log). Passage bands now state structural yield (medium
  25–40; others extrapolated pending runs), medium's word cap is 650,
  and the *feel* of size has its own advisory: **B6, words traversed
  per genuine choice per arc** (target 250–800, from the craft
  corpus's 300–600 "balanced agency" band). The Bubblegum Alibi reads
  at ~1206 — the cadence gap is real and now measured. POLISH's
  false-branch pass is cadence-targeted to close it (diamond every
  3–5 beats of a choice-less run, arms of 1–2 beats). Deeper scaffolds
  are the structural fix — next item.

- ~~Multi-hard weaving is not implemented~~ **Built** (PR #22) **and
  exercised live** (PR #23, the Bubblegum Alibi): hard forks nest,
  every unit after the first fork is instantiated per world, endings
  multiply, and the tensor model (design doc 01 §5) is realized in
  `weave.realize` + GROW's contextualize pass — all of it ran against
  a real model with the contextualize prompt performing first-shot.
- **M2 intersections group shared pre-commit beats only.** Intersections
  involving exclusive (post-commit) beats are structurally meaningful
  but interact with arc membership in ways the spine model doesn't
  cover; revisit when a generated story demands one. Same for temporal
  hints: only hints on shared beats are consumed (a hint on a beat
  inside an atomic fork unit has nothing to move).
- **The weave enumerates at most 64 candidates** (deterministic DFS,
  up to 8 shown to the model, evenly spread; with several hard
  dilemmas the cap is split evenly across viable nestings so every
  nesting is represented). First `medium` data point (13 units, 2
  nestings): the model chose #3 of 8 shown, weave realized first-shot,
  and `world_of` cost nothing measurable on the 66-beat graph — but
  one story is not a profile; keep watching the spread heuristic as
  stories grow (the lexicographic DFS varies the tail of the order
  first, so early-position variety may still under-sample at larger
  unit counts).
- ~~Locked dilemmas (heritage's "unexplored dilemmas") are the designed
  next structural effort~~ **Built** (2026-07-10, this PR — see "Where
  we are" and the decision-log entry): overgeneration + locked
  dispositions + fork-less weave units + I3/I6/G3-FLAGS refinements,
  and richer residue (per-path arms, followup beats, same-gate
  collapse). Still deferred from that item: **tensoring a shape inside
  a diamond arm** (a residue arm containing its own diamond) — revisit
  when a generated story wants residue that big; and **cosmetic flags
  on locked storylines** are unbuilt like all cosmetic grants (below).
  Not yet exercised on a live model.
- **The G4 pacing report is deferred** (design doc 02 lists it: "no >N
  consecutive same-intensity passages"). It needs the `scene_type`
  annotation, which per design doc 01 §10 arrives only when a FILL
  quality gap demonstrably calls for it — implement both together in
  M4+ if the gap shows.
- **Character-arc metadata remains unbuilt** (a POLISH output in design
  doc 02, deferred to be shaped by its consumer). M4's FILL wrote a
  micro story well without it — entities+overlays+shadows+window proved
  sufficient context at this scale. Per the annotation discipline
  (design doc 01 §10), add it when a FILL quality gap at `short`+
  scope demonstrably calls for it, and update doc 02 if it never earns
  its keep.
- ~~The HTML player has no codex panel yet~~ **Built** with DRESS
  (PR #20): a `<details>` codex panel, server-rendered, omitted when no
  entries exist.
- **Image generation is unbuilt** (deliberately — design doc 02 lists
  illustrations as optional). Briefs, the runtime `art` entries, the
  HTML embedding path, and the PDF illustration slots all exist and key
  off `art/images/<passage-slug>.png`; a pluggable backend that renders
  briefs into those files is future work.
- **Derived fallback codewords may contain digits** (slugs allow them;
  `^[A-Z]{3,12}$` binds only DRESS-stored codewords). Cosmetic at
  worst — a print warning already tells authors to run DRESS.
- ~~M6's retrieval library is an external bet~~ **Largely retired at
  planning time** (2026-07-10 decision-log entry): as of 3.1.0 the
  library ships a documented Python API (`Vault` facade with
  reader/index facets, hybrid `search(query, mode, folder)`, a public
  `EmbeddingProvider` ABC with a local pinned `FastEmbedProvider`, an
  `[embeddings]` extra). The phase-0 spike then passed everything
  (PR #30 decision-log entry): hybrid ranking deterministic across
  repeats and rebuilds, warm-cache embeddings fully offline, custom
  provider accepted — the item is closed.
- **Twee prose mapping is bounded and unlinted** — the lint step that
  flags constructs that don't survive SugarCube conversion arrives with
  SHIP (design doc 04 §3).
- **False branches carry no cosmetic flags yet** (choice-feel diamonds
  only). The flag machinery exists (`FlagSource.COSMETIC`); wire grants
  when a residue beat or print codeword actually wants one.
- **`qf simulate --random N` (false-branch/detour coverage, design doc
  04 §5) is not implemented** — `--all-arcs` covers dilemma
  combinations; random walks become interesting once false branches
  actually occur in generated stories.
- Fixture passage count (7) is below the `micro` target (15–25); B3 is
  an advisory warning by design — as is B4 (arc beat count), whose
  preset ranges are uncalibrated until generated stories exist.
- `export/` package and the rest of `play/` (engine, TUI) arrive with
  M3–M4; `play/simulate.py` landed early because M2's exit criterion
  needs it.
- ~~Live-provider recording is wired but unexercised~~ **Exercised**:
  the first live generation ran on 2026-07-08 (OpenAI gpt-5 architect/
  writer + gpt-4.1-mini utility via the new `providers/openai.py`) and
  produced a complete, gate-clean, export-valid story — results, three
  hardening lessons, and budget data in the decision log. Anthropic
  live runs work via the `QF_ANTHROPIC_API_KEY` passthrough (hosted
  environments strip the reserved `ANTHROPIC_API_KEY` name); billing
  was resolved 2026-07-08 and the first Claude-driven generation ran
  the same day — results in the "live run 3" decision-log entry.
- **`qf run --yes` is a stub.** Interactive checkpoint pauses (design doc
  02 §3) are not implemented; batch is currently the only mode. The flag
  is accepted for forward compatibility. Wire real interactive review
  when the review UX milestone lands.

## Decision log

- **2026-07-10 (M6 engine: research pass, A17, spike findings —
  PR #30):** Built to the PR #29 plan; what the record needs beyond it:
  (1) **The library spike passed everything** — `markdown-vault-mcp`
  3.1 hybrid ranking was deterministic across repeats *and* fresh
  index rebuilds, warm restart is O(1), a custom `EmbeddingProvider`
  ABC implementation drives hybrid search (needs `numpy` even with a
  custom provider — dev group carries library core + numpy, never
  fastembed), and fastembed loads from a warm cache in ~0.5s fully
  offline (first use downloads the model once). No upstream issues
  filed; `>=3.1,<4` pinned. (2) **Retrieval runs inside apply**, so
  kept-pass replay and A16 resume re-retrieve identically; the vault's
  tracker state routes into `cache/research/` (its default would
  pollute a read-only corpus checkout). (3) **A17 shipped as designed**
  (03 §9): freshness = digest frontmatter's corpus fingerprint +
  standing queries match current values, checked in `skip_if`, which
  the runner dispatches before keep/resume — that ordering is what
  lets a fresh digest beat a stale ledger. (4) **Injection is one
  runner-level render variable** (always defined, StrictUndefined-safe)
  — review templates never receive it, making the no-taste-laundering
  rule structural; `polish_audit` joined the exclusion list as
  review-shaped. (5) The automated reviewer caught a dangling
  citation (planning-doc-internal hazard numbering leaking into code
  comments) — worth keeping in mind when code is built from a plan
  document: cite repo artifacts, not the plan's internal labels.

- **2026-07-10 (M6 planned — the craft-corpus implementation
  contract):** Full milestone plan written to
  `docs/plans/m6-craft-corpus.md` (frontier planning session; the
  plan is the hand-off contract, this entry is the record). Four
  decisions worth logging. (1) **The library bet is largely retired
  on paper**: `markdown-vault-mcp` 3.1.0 publishes a documented
  Python API — `Vault` facade, hybrid `search(query, mode, folder)`,
  a public `EmbeddingProvider` ABC with a pinned local
  `FastEmbedProvider`, an `[embeddings]` extra — so the feared
  upstream API work shrinks to a phase-0 spike on two questions:
  hybrid tie-break determinism (the plan re-sorts `(-score, path,
  heading)` itself either way) and offline behavior on a warm
  embedding cache. (2) **A17, the plan's one real design find — rerun
  semantics for author-edited digests**: as specced, "author-editable
  artifact" would be vacuous (a rerun rewinds to the *predecessor*
  snapshot, which never contains the target stage's digest, and
  re-retrieval would clobber the edit). Resolution: `prepare_rerun`
  preserves the working tree's `research/<target>.md`; the research
  pass skips when the digest is *fresh* (frontmatter-recorded corpus
  fingerprint + standing queries match current values — corpus or
  vision edits re-retrieve, unchanged worlds reuse for free); forcing
  re-retrieval = deleting the file. Mirrors the vision.yaml
  precedent; the mini-ADR row lands in 03 §9 with the engine PR.
  (3) **DREAM's research runs premise-only** — no vision exists at
  the stage head, so standing queries start at BRAINSTORM (02 §1
  amendment with the PR). (4) **Digest injection is one runner-level
  render variable**, so review templates are structurally immune
  (they render themselves) rather than immune by convention; the
  exclusion list gains `polish_audit` (review-shaped — the same
  taste-laundering channel 02 §1 already closes). Sequencing per the
  tiering policy: contracts and prompt framing at frontier tier,
  mechanical phases delegable; engine PR first, live A/B exit run as
  a second PR once the author exports the IF-craft corpus from his
  vault (the locked-dilemmas live validation rides that premise).

- **2026-07-10 (crash resume: the in-flight proposal ledger, mini-ADR
  A16):** The open artifact-half question is decided: **not** per-pass
  prose flushing but a per-pass **proposal ledger** — every accepted
  pass journals its proposal to `inflight/<stage>/proposals/` the
  moment apply + review succeed, and re-entering an interrupted stage
  replays those passes through the existing `rerun --keep` machinery
  (schema-validate → apply through the mutation layer, no LLM call).
  Prose flushing was rejected on three grounds: a write pass produces
  more than prose (entity micro-details; the voice pass produces the
  Voice — files alone lose graph state), partial prose in the working
  tree breaks 02 §1's checkpoint definition, and reloading flushed
  prose before re-running from pass 0 can leak later-written
  predecessor prose into earlier windows (writing order is
  reference-arc-first, not globally topological), silently breaking
  the byte-stability fixed on 2026-07-08. Two hardenings shipped with
  it, both found in design stress-testing: (1) a **stage-input
  fingerprint** (vision/voice/graph/prose/art/codex bytes + steering +
  fill_seed + llm config) voids the whole ledger on any author edit —
  without it the ledger would silently replay stale proposals where
  the cache would have regenerated, a regression against "review =
  edit + revalidate"; (2) ledger writes are atomic (`os.replace`) and
  reads tolerant — a torn entry is stale, never fatal. The staleness
  contract splits by intent: auto-resume degrades to a live run with a
  report note; explicit `--keep` stays fail-loud and takes precedence.
  The checkpoint consumes the ledger; `prepare_rerun` discards all of
  `inflight/` (a rewind ends every interrupted run); a gate failure
  retains it, so unchanged-input retries reproduce the failure free.
  Uniform across all stages (A4) — DRESS and GROW passes are now as
  crash-resumable as FILL's — and independent of the LLM cache, which
  remains the second net for a pass that died before its ledger write.
  Also fixed in passing: `.gitignore` now actually ignores `cache/`
  (design doc 03 §6 claimed it already; the drift would otherwise have
  extended to `inflight/`). 13 new tests including an e2e that kills
  FILL mid-stage at a pass boundary and proves the resumed story is
  byte-identical to an uninterrupted run with zero re-spent calls.

- **2026-07-10 (summary register: briefs, not prose):** The author
  flagged that generated beat summaries arrive as finished prose ("her
  heart the last casualty of the lock-in" — a GROW contextualize
  rewrite in the Bubblegum Alibi), though FILL owns the words. The
  diagnosis: every summary-writing prompt injects the vision's tone two
  lines above a "events, not prose" instruction, and a prohibition
  loses to that pull every time. The fix follows the author's insight —
  tell the model what its output is *for* instead of what it must not
  be: a shared prompt block (`_summary_brief.j2`, included by SEED
  scaffold, GROW contextualize/bridge, POLISH finalize/passages) frames
  every summary as a brief for the prose writer who comes later, with
  one stated-vs-performed contrast pair ("the mentor is dead and the
  group blames Rell" is a brief; "grief hangs over the camp like early
  winter" is prose) and the incentive spelled out (imagery spent in a
  summary is stolen from the page). FILL's write prompt gets the
  mirror-image line: summaries are the brief, not the style — the
  Voice owns how anything sounds. Design doc 01 §5 now names the
  register authoritatively and files pre-voiced summaries in the
  bias-vector family (a style anchor smuggled past the Voice — the
  canonical-answer trap again). Deliberately NOT a gate or review
  rule: "flowery" is taste, and the review-legibility lessons say a
  cheap reviewer given a taste rule will launder it. The golden story's
  own summaries were swept to model the register (three similes and a
  personification removed; prose untouched). Validation rides the next
  live run (next-up #2).

- **2026-07-10 (locked dilemmas + richer residue):** The structural
  volume/depth effort, built as designed with five decisions worth the
  record. (1) **The disposition is topology, not a marker** (mini-ADR
  A15): a locked dilemma is exactly "one explored path" — heritage's
  own definition (an answer with no `explores` edge is the permanent
  shadow) — so nothing can drift; `queries.locked_dilemmas` /
  `branched_dilemmas` partition by explored-path count, and arc math
  never sees locked dilemmas at all (no selection, no multiplication).
  (2) **Locked outcomes are world facts, never flags**: every reader
  holds them, so a flag could gate nothing and would only bloat I12's
  universe — G3-FLAGS now rejects in both directions (a locked
  consequence needs no flag; a flag on a locked path is an error), and
  FILL reads the outcome from the beats. (3) **A locked chain weaves
  one movable unit per beat** under chain constraints — the storyline
  threads through the story instead of lumping — with wraps/serial
  anchored at its first beat and its resolution; only *branched* hard
  dilemmas make worlds or qualify as the climax (a locked hard-role
  question is texture, not backbone). Locked beats are on every arc,
  so they became intersection-eligible alongside shared pre-commit
  beats. (4) **No dilemma cuts at triage**: BRAINSTORM's overgeneration
  (branched budget + locked allowance, B1 as a pre-triage range) is
  absorbed entirely by locking — every dilemma gets a disposition, all
  arithmetic enforced repairably at triage apply so a bad disposition
  costs a repair round, not a dead stage. (5) **Richer residue is the
  diamond**: one gated arm per path per world (G4 strengthened from
  "any arm" to per-path — the story must remember whichever side was
  chosen), arms of 1–2 beats via `followup`, and the collapse rule
  refined from "gated beats are singletons" to "identical gates merge",
  so a multi-beat arm is one gated passage (the gate boundary is where
  the passage breaks, not every gated beat). Deferred, recorded on the
  open item: tensoring a shape inside a diamond arm. The golden story
  grew to exercise everything (locked second-keeper subplot, both
  residue arms, the 2-beat arm) and, at 8 passages, the print
  numbering constraints became satisfiable — the documented 7-passage
  impossibility is gone, and the README transcript no longer shows a
  numbering warning. Not yet run against a live model; folded into the
  next-up list.

- **2026-07-09 (Sonnet 5 evaluation — closed, keep Opus):** Question under test:
  can `claude-sonnet-5` ($3/$15 per MTok, $2/$10 intro through
  2026-08-31) replace `claude-opus-4-8` ($5/$25) as architect/writer in
  the default model map? Method: the same Bubblegum Alibi premise +
  dream steering, fresh project (`medium`, recalibrated presets), full
  DREAM→DRESS run on an all-Sonnet map, judged against the preserved
  Opus run on cost, repair rounds, gate cleanliness, and prose. Two
  adapter findings before GROW even started, both fixed here: (1)
  Sonnet 5 runs *adaptive thinking by default* and thinking tokens
  bill/count against `max_tokens` — the 8192 default starved a writer
  call into an empty response after ~7.5k-token thinks on architect
  calls (Opus never exceeded ~3k output). Adapter default is now 32768;
  unused budget costs nothing. (2) The Anthropic SDK rejects
  non-streaming requests whose `max_tokens` implies a >10-minute worst
  case — the provider now streams and collects the final message, same
  contract otherwise. **Default-config verdict: not faster, not
  cheaper.** Aborted mid-run (author's call) at the GROW/POLISH
  boundary — at the abort decision, 11 Sonnet calls had emitted 88k
  output tokens (single GROW calls at 18–22k, ~90% billed thinking)
  versus 74k for the *entire* 63-call Opus run; one more in-flight
  call completed before the kill, putting the run's final ledger at
  12 calls / 107k output / $1.18 intro. Pace projected $5–8 intro
  for the full story versus Opus's $3.24,
  and slower wall-clock. Second experiment in flight: the provider now
  takes an optional `llm.thinking` config ("disabled" opts out of
  Sonnet 5's thinking-on default; unset sends nothing, so the Opus
  default map is untouched), and the same premise is rerunning
  thinking-off through FILL — enough to judge structure + prose
  quality at the config where Sonnet actually is cheap (~$1–1.5 per
  medium story at intro pricing). First thinking-off finding, and the
  first engine improvement a cheaper model has bought us: it violated
  the scaffold prompt's explicit ending contract (endings on one hard
  dilemma's tails but not the other's) and under-built one soft arm —
  neither caught until GROW's unrepairable gate, ~10 wasted calls
  later (I6 ×16, I7 ×1). `_scaffold_apply` now rejects both shapes as
  repairable `ApplyError`s at SEED (hard tails must be endings, ending
  nowhere else, soft arms carry the scope's `min_payoff_beats`), with
  violating-construction tests (`tests/test_seed.py`) and the SEED
  contract paragraph in design doc 02 extended. Opus never tripped
  this; a model that does now costs one repair round instead of a dead
  stage. The rerun then repaired SEED on the first live round, passed
  GROW's gate, and cleared POLISH — before FILL died on the next
  finding: thinking-off Sonnet writes *literal newlines* inside JSON
  strings (prose payloads), which strict JSON rejects as control
  characters, and it repeated the mistake on retry. The adapter now
  parses with `strict=False` — that relaxes only control-chars-in-
  strings (unambiguous intent in a prose payload); structural errors
  still raise and retry.

  **Final verdict (author's call, run aborted in FILL): keep
  `claude-opus-4-8` as the default architect/writer.** Thinking-on
  Sonnet is strictly worse here: 2–3× the cost (billed thinking
  dominates: 107k output tokens in 12 calls vs 74k for Opus's whole
  63-call run) and slower. Thinking-off Sonnet is genuinely cheap
  ($0.65 through POLISH; a full run would land ~$1–1.5 intro vs Opus
  $3.24) but needed three engine interventions in one partial run —
  a scaffold-contract violation Opus never made, repeated
  JSON-discipline failures, plus the shared adaptive-thinking/
  streaming adapter fixes — and still never produced a passage to
  judge. The failure profile fits the model-economics table's
  prediction for sub-frontier tiers on narrative/DAG semantics; the
  three hardening fixes (SEED apply-time scaffold rules, max_tokens
  headroom + streaming, lenient string parse) are the evaluation's
  lasting value and stay regardless of model choice. Total tuition:
  ~$1.83 intro ($1.18 thinking-on final ledger + $0.65 thinking-off
  through its FILL abort). Evaluation projects left at
  `/home/user/stories/bubblegum-sonnet{,-nothink}` (session-local,
  not committed).

- **2026-07-09 (live run 6, validation micro — "The Cartography of
  Small Kindnesses", PR #24):** Fresh micro premise (they/them
  protagonist by design) validating the calibration batch. Results:
  framing prompts held (4 entities, all anchored, zero G1 warnings —
  the medium run had three), pronouns held (Wren consistently
  they/them through every passage and micro-detail; the field renders
  as "PRONOUNS: they/them, exactly"), cadence diamonds engaged hard
  (22 passages at micro vs 7–17 in every earlier run), and B6 measured
  ~1072 words/choice even so — the diamonds each add prose along with
  their choice, so the marginal rate improves slowly; closing the feel
  gap needs the locked-dilemmas effort, exactly as planned. Five
  findings, all fixed in-flight: (1) *review rule 1 misread POV* — a
  scene opening on another character's actions was failed as "third
  person"; rule 1 now defines a departure (narrator in the wrong
  person, or narration beyond their perception) and names the
  non-cases. (2) *the amnesiac reviewer never converges* — after the
  writer fixed round 1's genuine defect, round 2 failed on brand-new
  taste; review rounds now carry prior rounds' issues into the prompt
  (persistence is signal, novelty is usually taste). (3) *the halt
  verdict needed an arbiter* — prompt fences hit the cheap reviewer's
  ceiling (somatic rendering flagged as "naming emotion"; a rule-4
  complaint about a state that is no listed flag), and every stage
  halt across every run has been reviewer noise: a second failure now
  escalates once to an architect-tier arbitration whose strict verdict
  is final (design doc 02 FILL; tiering policy: escalate rather than
  improvise). (4) *the id contract had a hole at beat applies* — a
  diamond arm carrying entity display names ('Wren') sailed through
  every gate until DRESS's brief check collided with it; a shared
  `resolve_entity_ref` (types.py) now guards every apply that stores
  entity refs on a beat (SEED scaffold, GROW bridge, POLISH residue
  and arms) — FILL's micro-detail resolver generalized, per mini-ADR
  A11. (5) *the codex review had the same disease as FILL's* — it
  double-failed spoiler-safe entries by quoting the conditional-
  material list from its own context as "the entry's assertion" (the
  entry explicitly left the question open, which is what spoiler-safe
  means); the anchored+arbitrated contract generalized to DRESS
  (passes become per-run computed so review state can't leak), and
  rule 1 now defines assertion. Final: **complete at ~$2.75** over all
  attempts (174 calls, 41 cached; opus 231k in / 58k out) — 22
  passages, 8,810 words, 4 arcs, 2 endings, full enrichment (codewords
  KNOTTED / UNFOLDS), all exports round-trip clean; preserved as
  `examples/small-kindnesses/`. Meta-lesson for the record: the
  reviewer-contract failure class (live runs 1, 3, and now 6) kept
  yielding to wording fixes one instance at a time; the arbitration
  mechanism ends the class by making the expensive judgment structural
  instead of textual.

- **2026-07-09 (scope recalibration: the passage numbers were beats):**
  The author identified why B3 missed by 3x: the original scale numbers
  (medium 60–90) were *beat* counts from the era when one beat was one
  passage; the passage collapse silently redefined the unit under them,
  and heritage's surplus passages came from window-dressing choices.
  The author's second insight: how big a story *feels* is how many
  choices you make and how many passages you traverse — not inventory.
  The craft corpus agrees and supplies the band (scope-and-length note:
  ~300–600 words per choice reads as balanced agency; 1000+ reads as
  a book). Decisions: (1) passage bands recalibrated to structural
  yield (medium 25–40, measured; others extrapolated), documented as
  such in design doc 01 §2; (2) **B6** added — average words traversed
  per *genuine* choice per arc, target 250–800; a choice is offered
  when its gate is satisfiable, not when its target is on the same arc
  (the first draft under-counted exactly the real forks); (3) POLISH's
  false-branch pass is cadence-targeted (a diamond per ~3–5 beats of
  choice-less run, arms of 1–2 beats via an optional followup beat) —
  safe as dressing precisely because the dilemma structure guarantees
  the real choices, which inverts the corpus's false-choice-tax
  warning; (4) medium word cap 650 (opus climax endings run ~600);
  (5) DREAM/BRAINSTORM prompts reframed to their epistemic position
  (vision = texture not inventory; brainstorm = ingredients, anchor
  what you invent); (6) `Entity.pronouns` explicit end-to-end with a
  numbered FILL-review rule. The structural volume fix — locked
  dilemmas (heritage lookup confirmed: a triaged dilemma may explore
  one answer as a woven linear storyline) plus richer residue diamonds
  — is the designed next effort (open items); corpus-medium word
  totals (20–60k) wait for scaffold deepening after M6.

- **2026-07-09 (M5 exit: live run 5, the first medium — "The Bubblegum
  Alibi", PR #23):** Closed-circle murder mystery in a bubblegum
  high-school setting; claude-opus-4-8 architect/writer +
  claude-haiku-4-5 utility; premise → complete DRESSed story with all
  exports (incl. print PDF) for **~$3.25 / ~24 min** across eight
  attempts — the first live exercise of multi-hard weaving, fork-rejoin
  under bridges, and crash-resume at scale. Six findings, all fixed
  in-flight with violating-construction tests, all in territory only a
  multi-hard live run could reach: (1) *bridge into a fork commit* —
  the bridge pass spliced a shared bridge into one commit of a fork,
  dead-ending sibling arcs (I6 ×4); a gap into a fork commit is a gap
  into the fork — the bridge now spans the whole frontier and `_gaps`
  verifies coverage against real arc views. (2) *POLISH couldn't see
  through bridges* — new `queries.frontier_feeds` makes bridges
  transparent for arrival questions; the residue splices on the tail's
  side. (3) *`save_project` never deleted files of removed nodes* —
  the weave's removed template beats resurrected on reload as orphan
  roots with commit impacts; every per-node directory now prunes to
  the live node set on save (the single-process e2e could never see
  this; only a real crash-resume could). (4) *I12 counted upstream
  grants, not ambiguity* — at a 2-hard climax ending every upstream
  flag is a world fact; I12 now caps only ambiguous flags (grant and
  opposing commit both upstream), one computation
  (`queries.ambiguous_flags`) shared by gate and audit; design doc 01
  §8 refined. (5) *micro-detail keys are single-assignment* — the
  writer kept proposing a second `tell` for the character the scene
  was about; the prompt now states the rule and the refusal names the
  corrective action (the review-contract lesson again: write for the
  cheapest reader — including repair errors). (6) *exact word windows
  are unhittable* — 553 then 613 words against a 200–550 cap exhausted
  repairs; apply now enforces with 20% slack (band catches runaway/
  skimpy, review owns quality; G5 row updated), and whether medium's
  cap should rise is preset calibration (open items). Calibration
  data recorded in open items: prompt framing (vision/BRAINSTORM
  overpromise — the author's sharper diagnosis: early stages speak
  with certainty their pipeline position doesn't grant), medium preset
  ranges (20 passages vs B3's 60–90 comes from SEED's scaffold depth,
  not a prompt miss), and the weave/`world_of` first data point.
  Tooling note: committing each stage checkpoint to the PR as it
  landed made the run reviewable in-flight — the automated reviewer
  independently confirmed finding 3 from the committed artifact.

- **2026-07-09 (M5: multi-hard weave):** The tensor model (design doc
  01 §5) is realized with four decisions confirmed with the author.
  (1) **The nesting order is an interleaving choice**: candidates are
  enumerated once per viable climax (each hard resolve as final unit,
  an even share of the cap), the weave LLM picks; `wraps`/`serial`
  between hards constrain the enumeration — no new SEED contract.
  (2) **Between-fork placement is in scope**, not just the climax
  resolve: any unit after the first hard fork (inner pre-commit
  development, whole soft dilemmas via `serial(hard, soft)`) is
  instantiated per world — this is the heritage-canonical reading
  ("an inner-dilemma beat materializes once per world"), and it made
  soft-convergence, residue coverage, payoff, and heavy variants
  per-world concepts throughout. (3) **Symmetric instantiation**: the
  template Y is removed and every world gets a fresh world-suffixed
  copy — keeping the SEED beats as "world one" would be a
  canonical-world bias vector, the same trap as the removed canonical
  answer (mini-ADR A14). (4) **GROW de-ends and rewrites**: SEED still
  authors every hard Y complete with endings (the mini-story
  property); realization clears `is_ending` on the earlier forks'
  tails and the new *contextualize* pass rewrites clone summaries per
  world and de-ended tails to leave the climax open — structure is
  copied by the engine, words never are. Two check subtleties worth
  remembering: worlds are made by *other* dilemmas' hard forks (a
  dilemma's own commits are its fork, never its coordinate — otherwise
  a duplicate commit downstream of the first looks like "another
  world" and I3 goes blind), and G4's light-residue coverage matches
  residue beats to worlds by hard-commit ancestry, not adjacency.
  Deferred: units after the *last* hard fork (nothing may follow the
  endings — the climax resolve is always final), and intersections
  inside worlds (groups stay in the truly shared region; a cloned
  "shared scene" isn't shared).

- **2026-07-09 (M6 added: craft-corpus research):** The author's IF
  craft corpus (once `if-craft-corpus`, now living and much extended in
  his Obsidian vault; its indexing engine evolved into
  `markdown-vault-mcp`) should ground the pipeline's LLM calls. The
  original QuestFoundry exposed the corpus as a *tool* the model called
  mid-generation, because what a stage needs is content-shaped and hard
  to predict programmatically. That mechanism is incompatible with NG's
  one-shot adapter, content-addressed cache, and fixture replay (A3) —
  so NG splits the judgment from the fetch: a **research pass** at each
  stage head emits queries (an ordinary typed proposal), the engine
  retrieves via hybrid search and **persists the digests as a
  checkpointed artifact** later passes read (mini-ADR A13). Two design
  corrections from the discussion, both author pushback: (1) no
  exact-key retrieval anywhere — vision genre/tone are open vocabulary
  ("maritime folk horror" keys to no note), so even the engine's
  standing queries are search-ranked over several related notes;
  (2) **corpus material may widen or ground, never bind** — style
  exemplars appear at the voice pass as a contrasting spread, never a
  nearest-match target (clone risk compounds through the prose window),
  fade from write contexts once neighboring prose exists, and never
  enter review prompts (a third taste-laundering channel, declined).
  Milestone M6 in the roadmap; M5 finishes first.

- **2026-07-09 (M5 slice: DRESS, print, rerun — PR #20):** Codeword
  *suggestion* moved from POLISH (design doc 04's original wording) to
  DRESS pass 4 — "drawn from the story's diction" needs the voice and
  prose to exist, and neither does until after FILL; *projection*
  (which flags become codewords) stays a SHIP-side deterministic rule:
  exactly the gate-tested flags (mini-ADR A12; docs 02/04 updated).
  Enrichment (direction, profiles, briefs, codex) lives on the Project
  like the Voice, not in the graph — DRESS describes the story rather
  than being story structure — and gates see it via an explicit
  `run_checks(enrichment=…)` parameter, keeping the one-validation-path
  property. The runner's failed-apply restore set widened to include
  enrichment (apply functions may now mutate it), and the automated PR
  review caught that kept-proposal replay (`rerun --keep`) needed the
  same restore — the fix carries a partial-mutation regression test.
  Rerun semantics: rewind restores what the stage and its successors
  *produced* (graph, prose, art, codex, voice) and preserves what the
  author *steers with* (steering, vision.yaml, seeds) — editing those
  is the reason to rerun. Print facts worth remembering: typst-py
  compiles fully offline with embedded fonts but refuses input files
  outside its project root (the temp `.typ` is created inside the
  project); the 7-passage golden story provably cannot satisfy all
  three numbering-constraint families at once (brute-forced — minimum
  one violation), so the best-effort-plus-warning path is its expected,
  tested behavior, and the README transcript shows the warning. Built
  per the tiering policy: two mid-tier subagents implemented DRESS and
  the gamebook against written contracts; this session owned the
  contracts, the spine (enrichment models/IO/gate plumbing,
  `projected_flags`, rerun machinery), integration, and review.

- **2026-07-08 (crash-resume replay made exact):** The leak recorded
  after live run 4 is fixed at its root: `fill.py::_neighbor_prose`
  now returns window/lookahead entries in canonical (passage id,
  label) order instead of raw edge-store order. Store order was the
  only context ingredient that differed between a live run and a
  reloaded project (choice edges reload grouped by source file; beats
  were already topo-sorted, flags already id-sorted, out-edge order is
  file-order-stable), so the write-context prompt is now byte-stable
  across save/load and cache replay of a crashed FILL is exact and
  free. Parallel predecessors are alternative branches with no
  narrative order to preserve, so id order is as principled as any.
  Two violating-construction tests: same window regardless of wiring
  order, and in-memory context == reloaded-project context with
  wiring deliberately reversed from filename order. One-time cost:
  cache entries recorded before this change key on the old prompt
  bytes, so replays of pre-fix runs (e.g. the Salt-Glass Choir cache)
  re-spend at multi-predecessor passages once. The per-pass prose
  flush question stays open (see open items).

- **2026-07-08 (live run 4 — the first Gemini-driven generation):**
  "The Salt-Glass Choir" (fresh premise, micro scope) on the new
  `providers/gemini.py` — gemini-3.1-pro-preview architect/writer +
  gemini-2.5-flash utility — completed **first attempt, end-to-end,
  with zero engine or prompt bugs surfaced**: 24 beats, 14 passages
  (two false-branch diamonds, residue beats on both soft-dilemma
  paths, two bridge beats, and a `wraps` relation exercised), 4 arcs,
  0 gate errors, 4/4 arcs simulate complete, all three exports
  round-trip clean; preserved as `examples/salt-glass-choir/`.
  Budget: 46 calls, pro 42k in / 80k out, flash 23k in / 35k out —
  roughly ~$1 at pro-tier list pricing; one adapter schema retry
  total, FILL repair rounds on two passages (2 and 3 attempts),
  everything else first-shot — the hardened review contract held on a
  third reviewer family with no new lessons. Provider notes: Gemini's
  thought tokens are billed as output, so the provider counts
  candidates + thoughts as `output_tokens`; the models API still
  *lists* `gemini-3-pro-preview` but calling it returns 404 "no longer
  available" — probe a model id before pinning it in a model map.

- **2026-07-08 (live run 3 — the first Claude-driven generation):**
  "The Orchard of Hours" (fresh premise, micro scope) on the default
  model map — claude-opus-4-8 architect/writer + claude-haiku-4-5
  utility — is **the first story the pipeline generated on Claude**:
  24 beats, 10 passages (incl. a false-branch diamond and two
  fork-frontier residue beats — this premise also produced the
  fork-rejoin topology, handled cleanly by the PR #15 fix), 4 arcs,
  0 gate errors, 4/4 arcs simulate complete, all three exports
  round-trip clean; preserved as `examples/orchard-of-hours/`.
  Budget: 43 calls, opus 76k in / 22k out, haiku pennies —
  **~$0.95**, with **one repair round total** (intersections), the
  cleanest live run yet; opus needed ~4x fewer output tokens than
  gpt-5 for the same shape of work (no reasoning-token inflation on
  chat completions). One attempt failed mid-FILL and yielded the
  taste-laundering review-contract lesson (entry below); under the
  hardened contract all ten writes converged with haiku reviewing.

- **2026-07-08 (live run 2 — id-contract validation):** Second live
  generation ("The Cartographer's Debt", fresh premise, micro scope,
  gpt-5 architect/writer + gpt-4.1-mini utility — chosen because the
  Anthropic account has no credits, see open items, and gpt-5 is the
  distribution that produced the original id failures). Outcome: **a
  complete story — 24 beats, 7 passages, 4 arcs, ~350-word passages —
  0 gate errors, 4/4 arcs simulate complete, all three exports
  round-trip clean.** The id contract **held**: zero id-shaped repairs
  anywhere — the POLISH audit cited every passage and flag by full id,
  and all 10 FILL micro-details arrived with exact entity ids, so the
  retired display-name matcher was never missed. The run took four
  attempts and each failure was a real engine/prompt bug now fixed
  with its own entry and test (fork-rejoin convergence; finalize
  repair errors that didn't name expected values; a review contract
  the utility model misread). Budget across all four attempts: 40
  calls, gpt-5 46k in / 83k out, utility pennies — **~$0.90 total**;
  repair rounds: finalize 3 attempts, everything else first-shot.
  The project is preserved as `examples/cartographers-debt/` (like
  the Winding House, PR #14): project/vision/voice, graph, prose —
  snapshots, ledger, cache, and exports excluded. Structurally it is
  the fork-rejoin story: both residue beats splice before both hard
  commits, the topology the fix exists for.

- **2026-07-08 (review contract legibility):** Fourth live-run lesson,
  extending the first run's reviewer-discipline fix: the utility
  reviewer failed a passage twice *for being written in the voice's own
  required POV* — it misread the review prompt's one-line rule ("a
  banned pattern appears (banned: ...), or the POV (...) or tense (...)
  is broken") and treated the required first person as banned, so the
  write pass could never converge. `fill_review.j2` now separates
  REQUIRED (pov, tense — prose in them is correct; fail only on
  departure) from BANNED (a bulleted list), and narrows leakage to
  naming the machinery itself (ids, or "flag"/"beat"/"path" used
  mechanically) — in-world objects that flags merely describe are
  story, not leakage. Prompt-only; positional fixture replay is
  unaffected. The pattern across both reviewer lessons: contract text
  that a frontier model reads correctly can still be ambiguous to the
  small model actually holding the pen — write review contracts for
  the cheapest reader. *Extended same day (first Claude run):* the
  haiku reviewer laundered taste through the objective categories —
  a cliché became "state dishonesty", the ordinary verb "beats"
  became "potential leakage". The contract now says taste must not be
  relabeled as a rule, requires each issue to cite its rule number
  and quote the text, and rules out hedged findings ("risks",
  "potential", "could be") outright.

- **2026-07-08 (fork-rejoin convergence):** The id-contract validation
  run surfaced a real structural bug: when the weave places a soft
  dilemma's resolve unit directly before the hard resolve (a legal,
  common interleaving), the soft diamond rejoins at the hard fork and
  there is no single convergence beat. `soft_convergence` ("first beat
  reachable from both commits, in topo order") returned one **hard
  commit** — a beat not on every arc — and the residue splice then
  dead-ended every arc on the other hard branch (two I6 errors at
  POLISH's gate). Fix, per the tensor model (design doc 01 §5): the
  rejoin is a *frontier* — the minimal shared descendants of the two
  commits — usually one beat, one per world at a hard fork. New query
  `soft_rejoin_frontier`; `soft_convergence` returns a beat only when
  the frontier is single; the residue splice inherits the tail's edge
  into every frontier beat, so the residue exists in every world; G4
  reports heavy residue at a fork-rejoin as explicitly unsupported (M5
  per-world variants) instead of wiring variants at a wrong beat. The
  freeze record still stores only single-beat convergences — a fork
  frontier is the hard dilemma's commits, already frozen under forks.
  Violating-construction tests build the fork-rejoin story through the
  real weave. Design doc 01's convergence definition updated.

- **2026-07-08 (id contract):** The PR #12 open item is resolved as
  agreed (mini-ADR A11, design doc 03 §5): the adapter's JSON
  instruction now states the id contract once, globally — every node
  reference is the full `kind:slug` id exactly as it appears in the
  prompt — and `_resolve_entity`'s display-name branch is retired;
  micro-detail apply accepts only exact ids and the unambiguous bare
  slug (prefix restoration is parsing, not prediction). Repair errors
  keep naming the expected ids — and the validation run exposed one
  straggler: POLISH's finalize residue errors named only the offending
  value, so the repair loop couldn't converge when the model echoed a
  prompt annotation ("(residue: light)") into the dilemma field; both
  errors now enumerate the expected set, with a test mirroring the
  live failure. The violating-construction test for `_resolve_entity`
  now asserts display names are *rejected*. Validation: the intended
  Anthropic live run is blocked on billing (see open items), so the
  prompt-side fix was validated with a second live gpt-5 run — the
  distribution that produced the original id failures — on a fresh
  premise ("The Cartographer's Debt", micro scope); results in the
  "live run 2" entry above.
  Positional fixture replay is unaffected by the instruction change
  (fixtures key on call order, not prompt bytes), and the recorded
  fixtures already cite entities by full id.

- **2026-07-08 (live run):** First live generation: fresh premise
  ("The Winding House"), micro scope, gpt-5 architect/writer +
  gpt-4.1-mini reviewer, record mode. Outcome: **a complete story — 30
  beats (22 frozen + 8 POLISH-added, incl. live false branches), 17
  passages, 4 arcs — with 0 gate errors and 0 runtime
  problems**, end-to-end in ~1h wall-clock and ~$2.50 (95 calls; gpt-5
  124k in / 219k out incl. reasoning; the utility reviewer cost
  pennies). The run surfaced and fixed three robustness gaps, each now
  a violating-construction test: (1) models drop id namespaces — the
  POLISH audit accepts slug-form ids and repair errors name the
  expected set; (2) **a taste-based reviewer under the two-round limit
  can never converge** — each round finds a fresh stylistic opinion, so
  the "structure is wrong" halt tripped on style nits; the review
  prompt now confines *failure* to objectively checkable defects, and
  post-fix the loop demonstrably converges (fail → fix → pass); (3)
  models cite entities by display name — micro-detail apply resolves
  any unambiguous id/slug/name reference. Repair-round rates for budget
  planning: DREAM/BRAINSTORM 1 attempt, SEED ~2, GROW intersections up
  to 3, FILL writes averaged ~1.7 attempts. The three failures cost
  ~$0.60 of the total — cheap tuition.

- **2026-07-08 (M4):** FILL's review is a post-apply hook on the
  uniform repair loop (mini-ADR A10) and its pass list is computed from
  the project — the runner stays the only orchestrator. The reference
  arc is `fill_seed`-selected, stage-local, and tested to be genuinely
  seed-sensitive. Prose is stored on Passage nodes in memory and as
  sibling `prose/*.md` on disk (the YAML never carries it). Micro-
  details go through `add_entity_detail`, which refuses to overwrite
  established facts. Exports: the runtime JSON validator re-walks the
  exported document with no graph access, so export-only bugs can't
  hide behind graph validators; `qf export` refuses to write anything
  that fails it; the Twee IFID is persisted by touching project.yaml
  only (an export must not rewrite the project). Golden prose and the
  e2e prose fixtures were drafted by mid-tier subagents against written
  contracts and reviewed here — the tiering policy's intended shape.
  Voice's design-doc field "register" is `diction` in code (pydantic
  shadow warning); recorded here so nobody "fixes" it back.

- **2026-07-08 (M3):** Passage collapse is fully deterministic and the
  golden story is its oracle — the engine reproduces the hand-authored
  grouping and choice topology (endpoints, gates, grants) exactly; the
  LLM writes only words (summaries, labels, ending titles, residue and
  variant content, feasibility judgments). Choice grants derive from
  commit beats contained in the target passage; gates from the target
  head's `requires_flags`. Variant passages for heavy-residue
  convergences are wired behind disjoint per-flag gates, and a variant
  choice is only offered from sources where its gate is holdable
  (otherwise I10 would rightly reject it). Gated (residue) beats are
  always singleton passages. Same-label sibling choices are legal only
  behind different gates (the runtime hides all but one). `qf play`
  implements design doc 04's runtime semantics directly on the graph;
  the runtime JSON arrives with SHIP in M4.

- **2026-07-08 (PR #1):** Design docs merged as authoritative; departures
  from the original QuestFoundry recorded per-doc.
- **2026-07-08 (PR #1, revision):** No canonical/default answer marker in
  the data model — known bias vector; FILL uses a stage-local seeded
  reference arc instead.
- **2026-07-08 (PR #3):** `requires-python >= 3.11` (design said 3.12;
  nothing needed it; CI runs 3.12). No `networkx` — toposort/reachability
  hand-rolled (~10 lines each at this scale).
- **2026-07-08 (PR #3 review):** Intersection groups got disk I/O
  (`graph/intersections/*.yaml`); embedded answers/consequences preserve
  non-default `created_by`.
- **2026-07-08 (PR #5):** Automated PR review is CI-gated and follows
  `REVIEW.md` (no CI reproduction, `file:line` citations, converge).
- **2026-07-08 (PR #6):** `AGENTS.md` is the single source of agent
  instructions (`CLAUDE.md` imports it); this file is the living
  hand-off; PR template enforces the documentation contract.
- **2026-07-08 (PR #8):** SEED wires *intra-dilemma* Y ordering edges
  itself (the Y's internal order is a scaffold fact); GROW owns only the
  cross-dilemma weave. Design doc 02 updated. Also: `Stage.NEW` for
  scaffolded projects; G0 joined the validator registry; proposals carry
  content while the engine derives structure. M1 built per the tiering
  policy: two Sonnet subagents implemented `llm/` and `runner.py`
  against written contracts; frontier session owned stage semantics,
  prompts, fixtures, and integration.
- **2026-07-08 (M2):** The weave treats each dilemma's fork as one
  atomic unit (diamond / terminal split) on a linear spine of shared
  units, and realization *recomputes the whole ordering edge set* rather
  than patching SEED's seams — idempotent, and the only way splices stay
  honest. Intersections are proposed *before* the interleaving choice so
  member adjacency is a constraint, not a hope. Temporal hints are
  advisory by design (dropped + reported when unsatisfiable) — SEED
  cannot see the whole weave, so its hints must not be able to wedge it.
  The LLM never emits an order, only an index into engine-enumerated
  candidates. Flag ids reuse their consequence's slug
  (`consequence:elias-knows` → `flag:elias-knows`). Freeze happens
  inside GROW's gate callable, after checks pass and before checkpoint
  save. Multi-hard weaving deferred to M5: per the original source
  documents and review discussion, the settled model is the weave as a
  **tensor of Y graphs**: soft dimensions collapse at convergence into
  flags/residue; hard dimensions stay expanded, so an inner beat's
  dilemma-relative meaning is copied per world while the realized
  beats stay distinct (content follows the full coordinate). M2's
  spine is the flattened one-hard special case; the weave rejects >1
  hard dilemma until M5 builds true expansion — see open items for the
  invariant refinements it needs. (This entry was revised three times
  — "impossible" → "duplication machinery" → tensor-of-graphs — a real
  misunderstanding corrected against the source documents; kept here
  as the record.) Hardening from the episode: heritage source docs
  imported reference-only under `docs/heritage/`, danger zones recorded
  as design doc 01 §9, and AGENTS.md now directs doc-silent questions to
  heritage before first-principles derivation — the stranding mode of
  the original was exactly this understanding decaying across sessions.
  M2 was frontier-authored
  end-to-end: the weave semantics *are* the narrative/DAG mapping, and
  every module touched them (per the tiering policy's escalation rule,
  not despite it).
- **2026-07-08 (PR #7):** Model-tiering policy in `AGENTS.md`: frontier
  models (Fable/Opus) own semantics/design/integration/final review;
  mid-tier (Sonnet) implements against written contracts; small tier
  (Haiku) does mechanical work. Expensive sessions delegate typing;
  cheap sessions escalate semantics instead of improvising. Mirrors the
  pipeline's own `architect`/`writer`/`utility` roles (design doc 03 §5).
