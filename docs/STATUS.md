# Project Status

> **Living document — the session hand-off note.** Every PR updates this
> file: what changed, what's next, decisions made. If you are an agent
> starting a session, read this first; if you are ending one, leave it
> the way you'd want to find it.
>
> Last updated: 2026-07-08 · PR #6 (agent/doc infrastructure)

## Where we are

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
- [ ] **M1 — Front of pipeline (DREAM → BRAINSTORM → SEED)**
- [ ] **M2 — GROW** (the risk milestone: interleaving, intersections, freeze)
- [ ] **M3 — POLISH & structural play** (`qf play` on beat summaries)
- [ ] **M4 — FILL & first exports** (JSON, HTML player, Twee)
- [ ] **M5 — DRESS, print gamebook, scope hardening**

## Next up — M1 scope (from `docs/design/05-roadmap.md`)

1. Uniform stage runner: context → propose → validate → repair (≤2) →
   apply → gate; checkpoints/snapshots; resume (`pipeline/runner.py`)
2. LLM adapter: `complete(prompt, schema, model_role)`; Anthropic +
   deterministic mock provider; content-addressed cache; cost ledger
   (`llm/`)
3. Stages DREAM, BRAINSTORM, SEED with gates G0–G2 (`pipeline/stages/`)
4. CLI: `qf run <stage>`, `qf run --to seed [--yes]`
5. Recorded fixtures so CI replays the pipeline offline

**Exit criterion:** `qf run --to seed` produces a valid triaged,
scaffolded story from a one-paragraph premise; CI runs it offline
against recorded fixtures.

## Known deferrals / open items

- Golden fixture has no `graph/intersections/` entry — I8 disk I/O is
  round-trip-tested but not exercised by the golden story. Add a natural
  intersection when M2 (GROW) makes them real.
- Fixture passage count (7) is below the `micro` target (15–25); B3 is
  an advisory warning by design. Revisit when a generated story exists.
- `pipeline/`, `llm/`, `export/`, `play/` packages from the architecture
  doc don't exist yet — they arrive with M1–M4.

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
