# Agent Guide — QuestFoundry NG

Instructions for AI coding agents (Claude Code, Codex, …) and humans.
This file is the **single source of truth** for working instructions:
`CLAUDE.md` imports it, so edit here, never there.

## What this project is

QuestFoundry NG is a **story compiler**: a one-paragraph premise goes in;
a complete, playable branching gamebook (Twee, HTML, JSON, print PDF)
comes out. An eight-stage pipeline (DREAM → BRAINSTORM → SEED → GROW →
POLISH → FILL → DRESS → SHIP) does the creative work with LLMs inside
structural rails enforced by a deterministic engine.

## Orientation order (do this at session start)

1. **[`docs/STATUS.md`](docs/STATUS.md)** — where the project stands,
   what is in flight, what's next. Start here, always.
2. **[`docs/design/05-roadmap.md`](docs/design/05-roadmap.md)** — the
   milestone plan and exit criteria.
3. The **design doc for the area you're touching** (table below).
4. Skim the code you'll change — the package map below tells you where.

| Design doc | Owns |
|---|---|
| `docs/design/00-vision.md` | Goals, non-goals, the six guiding principles |
| `docs/design/01-story-model.md` | Domain model, invariants **I1–I13**, terminology |
| `docs/design/02-pipeline.md` | Stage contracts, gates G0–G6, backtracking, review model |
| `docs/design/03-architecture.md` | Stack, package layout, LLM adapter, project format, mini-ADRs |
| `docs/design/04-export-and-play.md` | Runtime JSON semantics, export formats, play/QA tooling |
| `docs/design/05-roadmap.md` | Milestones M0–M5, risks |

**The design docs are authoritative.** Code follows docs. If an
implementation must deviate, change the doc *in the same PR* and record
the deviation (Departures section in 01/02, mini-ADR table in 03 §9).
Undocumented divergence is a bug even when the code is better.

When the design docs are **silent** on a story-model question, do not
derive from first principles: consult `docs/heritage/` (the original
QuestFoundry source documents, reference-only — see its README) and the
danger zones in design doc 01 §9 first, then bring the answer into the
NG docs. Free derivation in doc-silent territory produced a confidently
wrong invariant claim once already (STATUS decision log, 2026-07-08).

## Commands

```bash
uv sync --group dev                            # install (Python >= 3.11)
uv run pytest -q                               # test suite
uv run ruff check src tests                    # lint
uv run qf validate examples/keepers-bargain    # golden story gates
```

All of these must be green before pushing — CI runs exactly these plus
the golden validate. Useful extras: `uv run qf status <project>`,
`uv run qf graph <project> --layer beats|passages` (Mermaid to stdout).

## Package map

```
src/questfoundry/
  models/     # Pydantic node/edge types per layer (concept, world, drama,
              # structure, presentation) + scope presets with budgets
  graph/      # store.py (typed graph), mutations.py (THE write path),
              # queries.py (computed arcs, DAG walks), validate.py (I1-I13 -> gates)
  pipeline/   # runner.py (uniform stage loop), weave.py (GROW's core),
              # passages.py (POLISH's core), research.py (craft-corpus
              # retrieval + the research head pass), stages/ (schemas +
              # apply), prompts/
  llm/        # adapter.py (schema-validated structured output), providers/
              # (anthropic, openai, mock replay/record), cache.py, ledger.py
  play/       # engine.py + tui.py (qf play), simulate.py (arc walker for QA)
  export/     # runtime_json.py (canonical, self-validating round-trip),
              # html.py (standalone player), twee.py (SugarCube)
  project/    # io.py: YAML-per-node project directory, load/save
  cli.py      # qf new / run / validate / status / graph / simulate / play / export
tests/        # invariant negative cases, mutation guards, golden, round-trip
examples/keepers-bargain/   # hand-authored golden story (must always pass)
```

## Iron rules (violating these is always a bug)

1. **All graph writes go through `graph/mutations.py`.** The store's
   underscore methods are its private surface — never call them from
   stages, loaders, tools, or tests of other modules. LLM proposals and
   hand-edited files face the same mutation layer; there is no
   privileged writer.
2. **Arcs are computed, never stored.** Anything cached must carry a
   `materialized_` prefix and must never be read by pipeline stages.
3. **Answers are strictly equal.** Never add a default / primary /
   canonical marker to answers or paths — this was removed deliberately
   (bias vector). FILL's writing order is FILL-local scheduling state.
4. **The topology freeze is absolute.** After GROW, beats are never
   deleted and dilemma forks/convergences never move. POLISH adds only.
5. **Fix structure upstream, never patch with prose.** A passage that
   can't be written well is a POLISH/GROW bug, not a writing problem.
6. **Invariants are numbered and cited.** New structural rules get an
   invariant number in `docs/design/01-story-model.md` §8, a check in
   `graph/validate.py` citing it, and a violating-construction test.
7. **LLM output is typed proposals only** (M1+). The engine validates
   and applies; models never mutate the graph directly.

## Documentation contract

A PR that changes behavior must leave the documentation true. Concretely,
every PR:

- **Updates [`docs/STATUS.md`](docs/STATUS.md)** — current state, next
  steps, the decision log if a decision was made. This is the file that
  lets the next session (possibly a different agent) pick up where you
  left off; treat it as your hand-off note.
- **Updates affected `docs/design/*` sections** — or explicitly states
  in the PR body why none apply.
- **Keeps the README status section true** (milestone claims, sample
  transcripts must match actual output).
- **Keeps the golden story green** — and when you implement something
  the golden story could represent (a new node kind, a new gate), extend
  the fixture to exercise it.

The PR template (`.github/pull_request_template.md`) carries this as a
checklist. Check items honestly; "N/A because …" is an acceptable answer,
silence is not.

## Workflow conventions

- Branch from `main`; open PRs as **drafts**; CI (ruff + pytest + golden
  validate) must pass before review.
- Automated PR review follows [`REVIEW.md`](REVIEW.md) — don't reproduce
  CI in reviews, cite `file:line` for behavior claims, converge instead
  of re-litigating nits.
- Commit messages: imperative summary line, body explains *why*.
- Style: Python ≥ 3.11, ruff (line length 100), Pydantic v2 everywhere,
  match the existing code's comment density (sparse — comments state
  constraints, not narration).
- Tests mirror invariants: a fix to a validator without a violating
  construction test is incomplete.
- Never commit scratch files, generated exports, or `cache/` contents.

## Model economics — who thinks, who types

Development runs across many sessions on models with wildly different
prices. Match the model tier to the work — the same principle the
pipeline itself applies with its `architect`/`writer`/`utility` roles
(design doc 03 §5). Note these are two different knobs: 03 §5 configures
the *story pipeline's runtime* LLM calls; this section governs
*development sessions* working on this repo. When you are an expensive
model, delegate; when you are a cheap one, stay inside your tier's lane
and escalate rather than guess.

**Frontier tier (Fable/Opus-class) — decide what the words should be:**

- Story-model semantics: anything touching invariants, `belongs_to`,
  the freeze, convergence, arc computation. The narrative-vs-DAG mapping
  is *the* hard part of this codebase and where subtle wrongness hides.
- GROW algorithm design (M2), changes to gate/invariant semantics,
  prose-feasibility rules.
- Design-doc changes, milestone planning, cross-module integration,
  and final review of work produced by cheaper tiers.

**Mid tier (Sonnet-class) — make the code match the words:**

- Implementing a module whose design-doc section already specifies its
  contract (LLM adapter, stage runner plumbing, export writers, CLI
  commands, play engine).
- Writing tests for specified behavior; recording fixtures; addressing
  concrete review findings.

**Small tier (Haiku-class) — mechanical work:**

- Renames, formatting, doc-link fixes, YAML fixture typing, STATUS.md
  checkbox upkeep, changelog-style edits.

**Session pattern for expensive models:** act as architect + integrator.
Sharpen the contract first (design-doc section, module interface,
acceptance checks), hand implementation to cheaper subagents or
follow-up sessions, then verify their output against the gates and
review the diff yourself. Don't spend frontier tokens typing code a
mid-tier model can produce from a good spec — and never hand
narrative/DAG semantics to a cheap model to save money; that trade
always loses.

**Escalation rule for cheaper models:** if a task turns out to require
changing an invariant, a gate, a design doc, or anything in the iron
rules, stop and flag it for a frontier session (note it in
`docs/STATUS.md` under open items) instead of improvising.

## Scope discipline

Milestones are vertical slices (`docs/design/05-roadmap.md`). Build the
current milestone; resist pulling later-milestone machinery forward
"while you're here" — the roadmap ordering is deliberate (risk-first).
If you discover the design is wrong, change the design doc and say so,
don't silently build something else.
