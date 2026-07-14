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

The working administration is split by lifecycle so no single file grows
unbounded — and all of it is written and maintained by coding agents for
hand-off (read the caveat under "Documentation contract"):

1. **[`docs/STATUS.md`](docs/STATUS.md)** — the hand-off note: the current epic
   and the immediate next steps. A page, not a scroll. Start here.
2. **[`docs/design/05-roadmap.md`](docs/design/05-roadmap.md)** — the epic-scale
   roadmap (Shipped / Now / Next / Later): where the current work sits in the arc.
3. **[`docs/BACKLOG.md`](docs/BACKLOG.md)** — the working backlog: sub-epic loose
   ends not owned by a roadmap epic.
4. **[`docs/decision-log.md`](docs/decision-log.md)** — the dated session
   decision log: a provenance archive, **search it** for *why* something changed;
   don't read it end-to-end. (Architecture decisions proper are the mini-ADR
   table in design doc 03 §9.)
5. The **design doc for the area you're touching** (table below) — the
   authoritative rules, including its Departures section and (for 03) the
   mini-ADR table. This, not the decision log, is where an agent reliably gets
   the history for its area into context.
6. Skim the code you'll change — the package map below tells you where.

| Design doc | Owns |
|---|---|
| `docs/design/00-vision.md` | Goals, non-goals, the six guiding principles |
| `docs/design/01-story-model.md` | Domain model, invariants **I1–I13**, terminology |
| `docs/design/02-pipeline.md` | Stage contracts, gates G0–G6, backtracking, review model |
| `docs/design/03-architecture.md` | Stack, package layout, LLM adapter, project format, mini-ADRs |
| `docs/design/04-export-and-play.md` | Runtime JSON semantics, export formats, play/QA tooling |
| `docs/design/05-roadmap.md` | Epic-scale roadmap (Shipped/Now/Next/Later), top risks |

**The design docs are authoritative.** Code follows docs. If an
implementation must deviate, change the doc *in the same PR* and record
the deviation (Departures section in 01/02, mini-ADR table in 03 §9).
Undocumented divergence is a bug even when the code is better.

When the design docs are **silent** on a story-model question, do not
derive from first principles: consult `docs/heritage/` (the original
QuestFoundry source documents, reference-only — see its README) and the
danger zones in design doc 01 §9 first, then bring the answer into the
NG docs. Free derivation in doc-silent territory produced a confidently
wrong invariant claim once already (decision log, 2026-07-08).

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
  illustrate.py  # qf illustrate: DRESS briefs -> art/images/ (A18; not a stage)
  cli.py      # qf new / run / validate / status / graph / simulate / play / export / illustrate
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

## Prompt and error-message quality (always diagnose this first)

The recurring bottleneck in this project is **blunt prompts and error
messages that happen to work because the model is smart enough to
reconstruct the intent** — until a weaker tier isn't, and the failure
looks like a model limit when it is a prompt defect. So:

- **You (the agent reading this) will feel the urge to blame a weak model
  for a failed pass — and you will almost always be wrong.** This is the
  single most reliable failure of judgment in this repo. Name the urge and
  distrust it: "known weak-tier difficulty", "the model isn't strong
  enough", "a bigger model would handle it" are red-flag phrases you may
  not write until you have *read the prompt and the error message and shown
  they are already correct and complete*. Absent that proof, the honest
  diagnosis is always *prompt defect, not yet fixed* — never *weak model*.
- **Model strength is not the axis at all** (author correction,
  2026-07-14). An under-determined prompt makes EVERY tier sample the gap:
  a strong model does not "reconstruct the intent", it fills the gap
  *plausibly and confidently*, which hides the defect instead of fixing
  it — the same variance, delivered more fluently. Two consequences:
  strong-tier success is never evidence a prompt is correct — it is
  evidence the model was smart enough to **paper over the defect**, which
  is still there, now invisible, waiting for a different sample, story,
  or tier (only constraint completeness validates a prompt — schemas,
  pinned sets, mechanical checks, explicit self-verification steps); and
  "stochastic weak-tier behavior" is as much a red-flag phrase as "weak
  model" — variance across samples is the *prompt's* under-determination
  showing, on any tier. The weak tier surfaces defects first only because
  it fails less persuasively.
- **When a pass fails (repair exhaustion, a bad proposal, a review that
  fabricates or misapplies a rule), the prompt or the message is the
  first suspect, not the model.** Assume the prompt is blunt until you
  have shown it is correct and complete; do not conclude "weak model"
  until the prompt provably forces the right behavior.
- **Every model-facing error must be actionable** (heritage
  `semantic-conventions.md` §Error Messages): state the *reason*, the
  *subject/location*, and the *recovery_action* — the specific corrective
  the model should take (pick a fresh id, use one of these values, move
  X to Y) — phrased as an instruction, not a diagnostic string. A raw
  exception fed back to the model (`duplicate node id 'X'`) is a bug in
  the feedback, not just a weak model that couldn't recover from it.
- **Prompts encode intent explicitly; they do not rely on inference.**
  A rule the reviewer must apply should be structurally enforced (quote
  the rule, quote the offending text, show the match), not merely stated
  and trusted. If a smart model is silently correcting for a loose
  prompt, the prompt is still wrong — a cheaper tier will expose it.
- Distinguish **model-facing/repairable** errors (need a recovery_action)
  from **engine-internal invariant failures** (signal a code bug, not a
  model action) — only the former are prompt-quality surface.

## Documentation contract

**This administration is written and maintained entirely by coding agents**, for
hand-off to the next session — every roadmap line, backlog item, and decision
record. Read it as such: a recorded decision is *an agent's* write-up, not
author-ratified ground truth, unless it cites an explicit author instruction. An
agent recording its own scope-cut as the author's call has burned a whole session
before ([`docs/plans/rotating-pov.md`](docs/plans/rotating-pov.md)). So attribute
decisions to the agent that made them; call a choice author-directed only with a
direct reference to the author saying so. (Real provenance arrives when the
backlog moves to GitHub issues; until then this caveat is the guard.)

A PR that changes behavior must leave the documentation true. Update whichever of
these it touches — each is deliberately small, so none becomes a single growing
file:

- **[`docs/STATUS.md`](docs/STATUS.md)** — the hand-off note: current epic +
  next steps. Keep it a page; history does not accrete here.
- **[`docs/design/05-roadmap.md`](docs/design/05-roadmap.md)** — move an epic
  between Shipped / Now / Next / Later when it starts or finishes.
- **[`docs/BACKLOG.md`](docs/BACKLOG.md)** — add a loose end you open; delete one
  you close (git history keeps it).
- **A decision worth keeping** — an *architecture* decision gets a new row in the
  mini-ADR table (design doc 03 §9) and the durable rule lands in the relevant
  design-doc section (so a by-area reader gets it in context); a notable session
  decision/effort gets a dated entry in [`docs/decision-log.md`](docs/decision-log.md)
  (the searchable provenance archive — never the primary source of a rule).
- **Affected `docs/design/*` sections** — or state in the PR body why none apply.
- **The README status section** stays true (milestone claims, sample transcripts).
- **The golden story stays green** — extend the fixture when you add something it
  could represent (a new node kind, a new gate).

The PR template (`.github/pull_request_template.md`) carries this as a checklist.
Check items honestly; "N/A because …" is acceptable, silence is not.

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

- Renames, formatting, doc-link fixes, YAML fixture typing, BACKLOG.md and
  STATUS.md upkeep, decision-log entries, changelog-style edits.

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
rules, stop and flag it for a frontier session (add it to
`docs/BACKLOG.md`, or the roadmap if it's epic-scale) instead of improvising.

## Live-run budget discipline (billed API calls are scarce)

The pipeline's own LLM calls run against **pay-per-credit API keys**
(Anthropic, Gemini, OpenAI) with hard project spend caps — the Claude
Max / OpenAI *subscriptions* are not available to the pipeline. Treat
those keys as a scarce, exhaustible resource. **Ollama (local models and
the cloud tier via `OLLAMA_API_KEY`) is not billed per credit — it is the
default for any exploratory or iterative run.**

- **Never run a whole pipeline "just to see if it finishes."** That is no
  longer acceptable behaviour. A full `--to fill`/`--to dress` on a billed
  provider is the most expensive thing in the repo and produces almost no
  targeted signal per dollar.
- **Every billed (Anthropic/Gemini/OpenAI) call must serve a stated need.**
  Before spending, write down: the *question* the run answers, the
  *smallest* run that answers it, the *signal* you expect, and *why the
  weak tier can't answer it*. If you can't fill those in, don't spend.
- **Reach for the cheapest path that answers the question:** a single
  stage (`qf run <stage>`), a `qf rerun <stage>` of just the failing pass,
  a `micro`/`short` scope, or a replay from a checkpoint — not a fresh
  end-to-end run. The A16 ledger and per-stage checkpoints exist so you
  never re-buy completed work.
- **Do exploration and reproduction on Ollama** (`gpt-oss:120b` cloud, or
  a local model). Reserve a billed strong model for the *one* step that
  genuinely needs strong-tier quality and has been shown to fail on the
  weak tier — and run only that step.
- **A capped/failed billed run is a stop, not a retry.** If a provider
  returns `RESOURCE_EXHAUSTED` / a spend-cap error, record it and stop;
  do not thrash re-invoking it.

(These are two different knobs, as in the section above: this governs the
*pipeline's runtime* spend during development; the model-economics tiers
govern which model does the *development work*.)

## Scope discipline

Milestones are vertical slices (`docs/design/05-roadmap.md`). Build the
current milestone; resist pulling later-milestone machinery forward
"while you're here" — the roadmap ordering is deliberate (risk-first).
If you discover the design is wrong, change the design doc and say so,
don't silently build something else.
