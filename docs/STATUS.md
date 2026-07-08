# Project Status

> **Living document — the session hand-off note.** Every PR updates this
> file: what changed, what's next, decisions made. If you are an agent
> starting a session, read this first; if you are ending one, leave it
> the way you'd want to find it.
>
> Last updated: 2026-07-08 · M2 (GROW)

## Where we are

**M2 is complete.** GROW weaves SEED's disconnected Y scaffolds into one
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
- [x] **M2 — GROW** (the risk milestone: interleaving, intersections, freeze)
- [ ] **M3 — POLISH & structural play** (`qf play` on beat summaries)
- [ ] **M4 — FILL & first exports** (JSON, HTML player, Twee)
- [ ] **M5 — DRESS, print gamebook, scope hardening**

## Next up — M3 scope (from `docs/design/05-roadmap.md`)

Passage collapse, choice wiring, feasibility audit, variants, residue
beats, false branches, gate G4 (I10–I13 checks already exist);
`qf play` on beat summaries.

**Exit criterion:** the golden story is playable in the terminal
end-to-end — choices, gates, four distinct journeys — with zero prose.

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
  Nothing is ever *duplicated*: "hard" means the commit makes the
  worlds too different to share, so the inner dilemma resolving in
  different worlds is different scenes — an authoring cost, never a
  copy operation (a beat that could be identical across the outer
  branches would mean the outer dilemma wasn't hard). What NG lacks is
  that per-world authorship — an LLM pass (SEED or GROW, open) writing
  the inner dilemma's resolution inside each outer world. Structural
  consequence: an inner path carries one commit beat *per world*
  (different scenes locking in the same answer), which refines I3's
  "exactly one commit beat per path" and the single-grant-point
  assumptions in `queries.commit_beat` / `queries.grant_beat` /
  `FreezeRecord.forks`. Frontier-tier work, needed for M5's `medium`
  scope.
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
  documents, hard forks nest (per-world authored beats, multiplied
  endings) — M2's weave rejects >1 hard dilemma; see open items for
  the invariant refinements per-world authorship needs. (Two earlier
  revisions of this entry were wrong: multi-hard topology is not
  "impossible" — the original docs settle it via nested forks — and
  nothing is "duplicated": post-fork content is original per world by
  the definition of hard; only NG's single-commit-beat plumbing
  assumes one hard dilemma.) M2 was frontier-authored
  end-to-end: the weave semantics *are* the narrative/DAG mapping, and
  every module touched them (per the tiering policy's escalation rule,
  not despite it).
- **2026-07-08 (PR #7):** Model-tiering policy in `AGENTS.md`: frontier
  models (Fable/Opus) own semantics/design/integration/final review;
  mid-tier (Sonnet) implements against written contracts; small tier
  (Haiku) does mechanical work. Expensive sessions delegate typing;
  cheap sessions escalate semantics instead of improvising. Mirrors the
  pipeline's own `architect`/`writer`/`utility` roles (design doc 03 §5).
