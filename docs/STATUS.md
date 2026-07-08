# Project Status

> **Living document — the session hand-off note.** Every PR updates this
> file: what changed, what's next, decisions made. If you are an agent
> starting a session, read this first; if you are ending one, leave it
> the way you'd want to find it.
>
> Last updated: 2026-07-08 · PR #8 (M1)

## Where we are

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
- [ ] **M2 — GROW** (the risk milestone: interleaving, intersections, freeze)
- [ ] **M3 — POLISH & structural play** (`qf play` on beat summaries)
- [ ] **M4 — FILL & first exports** (JSON, HTML player, Twee)
- [ ] **M5 — DRESS, print gamebook, scope hardening**

## Next up — M2 scope (from `docs/design/05-roadmap.md`)

The risk milestone. Deterministic interleaving core (temporal hints +
ordering relations → candidate orders), divergence/convergence wiring,
flag derivation from consequences, intersection proposals, bridge
beats, topology freeze, gate G3, `qf simulate --all-arcs`.

**Exit criterion:** four complete, validated arcs through the golden
story's beat DAG.

## Known deferrals / open items

- **SEED emits no temporal hints or flexibility edges yet** (design doc
  02 says it should). Deferred to M2, where GROW consumes them — the
  field/edge plumbing should be shaped by its consumer. Frontier-tier
  work (touches beat semantics).
- **Every retained dilemma explores both answers in M1.** Locked-dilemma
  shadows (exploring one side only) need an I3 refinement — the current
  check demands dual-membership pre-commit beats, which single-explored
  dilemmas can't have. Frontier-tier work.
- **Triage cannot cut dilemmas** (only entities). Tied to the above and
  to the generous-brainstorm question: B1 checks *equality* with the
  scope preset, so BRAINSTORM is prompted to produce exact counts rather
  than overgenerating for triage. Revisit both together in M2+.
- Golden fixture has no `graph/intersections/` entry — I8 disk I/O is
  round-trip-tested but not exercised by the golden story. Add a natural
  intersection when M2 (GROW) makes them real.
- Fixture passage count (7) is below the `micro` target (15–25); B3 is
  an advisory warning by design. Revisit when a generated story exists.
- `export/`, `play/` packages arrive with M3–M4.
- Live-provider recording (`MockProvider(record_with=...)`) is wired but
  unexercised — needs an API key session to record real fixtures.

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
- **2026-07-08 (PR #7):** Model-tiering policy in `AGENTS.md`: frontier
  models (Fable/Opus) own semantics/design/integration/final review;
  mid-tier (Sonnet) implements against written contracts; small tier
  (Haiku) does mechanical work. Expensive sessions delegate typing;
  cheap sessions escalate semantics instead of improvising. Mirrors the
  pipeline's own `architect`/`writer`/`utility` roles (design doc 03 §5).
