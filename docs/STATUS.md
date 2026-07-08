# Project Status

> **Living document — the session hand-off note.** Every PR updates this
> file: what changed, what's next, decisions made. If you are an agent
> starting a session, read this first; if you are ending one, leave it
> the way you'd want to find it.
>
> Last updated: 2026-07-08 · M4 (FILL & first exports)

## Where we are

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
- [ ] **M5 — DRESS, print gamebook, scope hardening**

## Next up — M5 scope (from `docs/design/05-roadmap.md`)

DRESS (art direction, briefs, optional images, codex; gate G6), the
print gamebook PDF pipeline (codeword projection, residue-variant
lowering, seeded numbering/shuffling, Typst layout, lint), `qf rerun
--keep` partial regeneration, and `short`/`medium` scope hardening —
which needs the multi-hard weave expansion (tensor model, see open
items) and a live-provider recording session for real fixtures.

**Exit criterion:** a printable PDF gamebook with working codeword
play, plus a `medium`-scope story generated end-to-end within budget.

## Known deferrals / open items

- **Multi-hard weaving is not implemented** (the weave rejects >1 hard
  dilemma with a clear error). The intended topology is settled by the
  original source documents ("How Branching Stories Work" §The Cost of
  Branching; ontology §The 2^N Law): hard forks **nest** — after the
  first hard commit, the remaining hard dilemma forks again on *each*
  branch, with its own independently authored per-branch beats, and
  endings multiply (2 hard → 4 endings). No beat is shared across a
  hard fork, so nothing reconverges; the per-combination beats are the
  accepted, deliberately minimized cost of late-committing backbones.
  The working mental model (decision log): the weave is a **tensor of
  Y graphs** — each dilemma one dimension, a story position a
  coordinate in every dilemma's Y. Soft dimensions *collapse* at
  convergence (the coordinate leaves the DAG and lives on as flags /
  overlays / residue — why "beats are not cloned per reachable
  state"). Hard dimensions *never collapse* (the coordinate stays in
  the DAG as position). Where two hard dimensions are expanded at
  once, an inner-dilemma beat materializes once per world: both
  instances project to the same node of the inner Y (same
  dilemma-relative meaning) and to different nodes of the outer Y
  (different context) — structure copied, content contextual, distinct
  beats. M2's spine weave is the flattened special case (at most one
  dimension expanded at a time). M5 adds true expansion: GROW
  instantiates the inner Y's skeleton per world (mechanical) and
  contextualizes its beat content per world (LLM). Structural
  consequence: an inner path carries one commit beat *per world*,
  refining I3's count and the single-grant-point assumptions in
  `queries.commit_beat` / `queries.grant_beat` / `FreezeRecord.forks`.
  Frontier-tier work, needed for M5's `medium` scope.
- **M2 intersections group shared pre-commit beats only.** Intersections
  involving exclusive (post-commit) beats are structurally meaningful
  but interact with arc membership in ways the spine model doesn't
  cover; revisit when a generated story demands one. Same for temporal
  hints: only hints on shared beats are consumed (a hint on a beat
  inside an atomic fork unit has nothing to move).
- **The weave enumerates at most 64 candidates** (deterministic DFS,
  up to 8 shown to the model, evenly spread). Fine at micro/short unit
  counts; check the spread heuristic when `medium` stories arrive.
- **Every retained dilemma explores both answers in M1.** Locked-dilemma
  shadows (exploring one side only) need an I3 refinement — the current
  check demands dual-membership pre-commit beats, which single-explored
  dilemmas can't have. Frontier-tier work.
- **Triage cannot cut dilemmas** (only entities). Tied to the above and
  to the generous-brainstorm question: B1 checks *equality* with the
  scope preset, so BRAINSTORM is prompted to produce exact counts rather
  than overgenerating for triage. Revisit both together in M3+.
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
- **The HTML player has no codex panel yet** (design doc 04 §2 lists
  one) — there is no codex before DRESS (M5). Add the panel when codex
  entries exist.
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
- Live-provider recording (`MockProvider(record_with=...)`) is wired but
  unexercised — needs an API key session to record real fixtures.
- **`qf run --yes` is a stub.** Interactive checkpoint pauses (design doc
  02 §3) are not implemented; batch is currently the only mode. The flag
  is accepted for forward compatibility. Wire real interactive review
  when the review UX milestone lands.

## Decision log

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
