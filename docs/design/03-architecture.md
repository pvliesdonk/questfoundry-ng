# 03 — Architecture

Technical design: stack, module layout, the graph engine, the LLM
adapter, the project-on-disk format, the CLI, and testing strategy.

## 1. Stack

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Ecosystem for LLM tooling; matches team familiarity; the pipeline is I/O-bound, not compute-bound |
| Packaging | `uv` + `pyproject.toml` | Fast, lockfile-first, single tool |
| Schemas | Pydantic v2 | Typed models double as LLM JSON-schema contracts and file formats |
| CLI | Typer + Rich | Subcommand ergonomics; rich stage reports and progress in-terminal |
| Graph | Hand-rolled typed store (see §3) | Our invariants are domain-specific; `networkx` is used *internally* for algorithms (toposort, reachability), not as the store |
| LLM access | Thin in-house adapter (§5) | One interface, provider-agnostic; avoids framework lock-in for what is ~200 lines |
| Templates | Jinja2 | Prompts and export formats are both templating problems |
| PDF | Typst | Programmable page layout for the gamebook; far saner than LaTeX for generated input |
| Tests | pytest + Hypothesis | Property-based tests are the natural fit for graph invariants |

## 2. Package layout

```
src/questfoundry/
  models/            # Pydantic: nodes, edges, proposals, reports
    concept.py       #   Vision, Voice, ScopePreset
    world.py         #   Entity, Overlay
    drama.py         #   Dilemma, Answer, Path, Consequence
    structure.py     #   Beat, StateFlag, IntersectionGroup
    presentation.py  #   Passage, Choice, Variant
    proposals/       #   per-stage LLM output schemas
  graph/
    store.py         # StoryGraph: typed node/edge store, load/save
    mutations.py     # the ONLY write API; every op re-checks invariants
    queries.py       # arcs, reachability, flag histories, Y-shape checks
    validate.py      # invariant registry (I1..I13) + gate definitions
  pipeline/
    runner.py        # the uniform stage loop; checkpoints; resume
    context.py       # per-stage context builders (incl. sliding prose window)
    weave.py         # GROW's deterministic interleaving core (units,
                     #   constraints, candidate orders, spine realization)
    stages/          # dream.py .. ship.py — schemas, prompts, gates only
    prompts/         # Jinja2 prompt templates, versioned
  llm/
    adapter.py       # complete(prompt, schema) -> validated model
    providers/       # anthropic.py, openai.py, mock.py
    cache.py         # content-addressed call cache
    ledger.py        # token/cost accounting per stage/run
  export/
    runtime_json.py  # canonical format (source of truth for players)
    twee.py          # Twee 3 / SugarCube
    html.py          # standalone player (embeds JSON + JS runtime)
    gamebook.py      # numbering, shuffling, codewords -> Typst -> PDF
  play/
    engine.py        # flag-tracking traversal of the passage graph
    tui.py           # `qf play` terminal player
    simulate.py      # exhaustive/random arc walker for QA
  cli.py             # Typer app: qf ...
```

Rule of dependency direction: `models` ← `graph` ← `pipeline`/`export`/
`play`; `llm` is used only by `pipeline`. Stages contain **no graph
mutation code** — they emit proposals; `graph/mutations.py` applies them.

## 3. The graph engine

`StoryGraph` is a typed, in-memory store persisted to plain files (§6).
Design points:

- **Typed nodes and edges.** Every node is a Pydantic model with an
  `id` (`kind:slug`, e.g. `beat:keeper-lights-lamp`), a `kind`, and
  `created_by` provenance (stage + run id). Edges are typed triples
  (`belongs_to`, `predecessor`, `anchored_to`, `grouped_in`, `choice`,
  `variant_of`, …) with optional payloads (choice label/requires/grants).
- **One write path.** All mutation goes through `mutations.py` operations
  (`add_beat`, `set_ordering`, `freeze_topology`, `group_passage`, …).
  Each operation validates its local invariants; gates validate global
  ones. Direct store writes are private.
- **The freeze is mechanical.** `freeze_topology()` (end of GROW) records
  the fork/join fingerprint; every later mutation is checked against it —
  deletion of beats or movement of dilemma forks raises, unconditionally
  (I9).
- **Arcs are a query, not a table.** `queries.arcs()` yields traversals
  by walking `predecessor` edges from the root, choosing the successor
  matching the arc's path selection at each fork. Anything cached is
  prefixed `materialized_` and is never read by stages.
- **Scale honesty.** A `long` story is ~10³ nodes and ~10⁴ edges.
  Everything fits in memory; every algorithm may be O(V+E) or worse
  without consequence. No database, no indices, no cleverness.

## 4. The uniform stage loop

`pipeline/runner.py` owns the loop from [02 §1](02-pipeline.md). A stage
is a declarative bundle:

```python
class Stage(Protocol):
    name: str
    proposal_schema: type[BaseModel]        # what the LLM must emit
    def build_context(self, g: StoryGraph, cfg: StageConfig) -> Context: ...
    def prompt(self, ctx: Context) -> RenderedPrompt: ...
    def apply(self, proposal: BaseModel, g: StoryGraph) -> ApplyReport: ...
    gate: list[Check]                       # invariant refs + stage checks
```

The runner supplies, uniformly: proposal validation, the ≤2-round repair
loop (validation errors serialized back into the prompt), checkpoint
snapshots, stage reports, resume-from-snapshot, the spend ledger, and
`--interactive` pauses. Multi-pass stages (SEED, FILL) are expressed as
sub-stages sharing one gate.

FILL additionally gets a **work queue**: passages ordered reference-arc-
first (the reference arc is FILL-local scheduling state — seeded,
author-overridable, invisible to other stages), then per-arc toward
convergence points; each item carries its sliding-window context. The queue is resumable mid-stage — prose is the
expensive stage, and a crash at passage 61/90 must not cost 60 passages.

## 5. The LLM adapter

One interface: `adapter.complete(prompt, schema, *, model_role) ->
BaseModel`.

- **Structured output always.** Every call carries a JSON schema derived
  from the proposal model; responses are parsed and validated before the
  pipeline sees them. Free-text generation exists only *inside* schema
  fields (prose is a `str` field of a `PassageProse` proposal).
- **Model roles, not model names.** Stages request a role — `architect`
  (SEED/GROW judgment), `writer` (FILL prose), `utility` (labels,
  summaries) — mapped to concrete provider/model in project config.
  Default mapping uses a frontier model for `architect`/`writer` and a
  small model for `utility`.
- **Cache.** Content-addressed on (prompt hash, schema version, model,
  temperature). Re-running a stage with unchanged inputs is free; this is
  what makes iterate-on-DREAM-then-rerun cheap and tests fast.
- **Ledger.** Every call logs tokens/cost/latency per stage per run;
  `qf status` shows spend against the scope preset's budget estimate.
- **Mock provider.** Deterministic fixture-backed provider for tests and
  offline development; records/replays live calls to build fixtures.

## 6. Project on disk

A story is a directory (Principle 5: everything is a file, git-friendly,
no opaque state):

```
keepers-bargain/
  project.yaml           # name, scope, model-role mapping, stage configs & steering notes
  vision.yaml            # DREAM output (author-editable)
  voice.yaml             # FILL's voice contract
  graph/
    entities/keeper.yaml           # one file per entity (base + overlays)
    dilemmas/bargain.yaml          # dilemma + answers + anchoring
    paths/bargain-kept.yaml        # path + consequences + scaffold refs
    beats/keeper-lights-lamp.yaml  # beats: summary, class, impacts, belongs_to
    edges.yaml                     # ordering/choice/variant edges (grouped by type)
    flags.yaml
    passages/p-017.yaml            # structure + feasibility notes (no prose)
  prose/p-017.md         # one markdown file per passage/variant — diff-, edit-, review-able
  art/direction.yaml, briefs/, images/
  codex/*.md
  reports/<run>/<stage>.md   # stage reports (human-readable audit trail)
  snapshots/<run>/<stage>/   # full-graph checkpoint per gate
  cache/llm/                 # call cache (gitignored)
  exports/                   # twee/html/json/pdf (gitignored)
```

YAML for structure (comments matter for author editing), Markdown for
prose. `qf validate` re-loads the directory from scratch and runs all
gates, so hand edits are exactly as trustworthy as pipeline output.

## 7. CLI surface

```
qf new keepers-bargain --scope micro          # scaffold project, interview for premise
qf run dream                                  # run one stage (interactive checkpoint)
qf run --to polish --yes                      # run pipeline through POLISH, auto-approve
qf rerun seed --keep triage                   # partial regeneration
qf validate                                   # all gates against current files
qf status                                     # stage progress, gate results, spend
qf graph --format mermaid                     # beat DAG / passage graph visualization
qf play                                       # terminal playthrough (flag-tracking)
qf simulate --all-arcs                        # walk every arc; report completeness
qf export twee|html|json|pdf
```

A local review web UI (read-only graph explorer + prose reader) is a
later milestone ([05](05-roadmap.md)); the CLI + files are the complete
interface before that.

## 8. Testing strategy

- **Invariant unit tests** — each I1–I13 has direct tests in
  `graph/validate` with hand-built minimal graphs (violating and
  conforming).
- **Property tests** — Hypothesis generators build random
  dilemma/path/beat configurations; properties assert e.g. "every graph
  accepted by G3 yields only complete arcs", "freeze always rejects
  deletion".
- **Golden story** — "The Keeper's Bargain" (`micro`) is checked in as a
  fixture with recorded LLM responses; the full pipeline runs offline in
  CI against the mock provider, and exports are snapshot-tested
  (round-trip JSON, Twee lint, gamebook numbering).
- **Simulation QA** — `qf simulate --all-arcs` runs in CI on the golden
  story: every arc completes, every flag test is satisfiable, no passage
  unreached.
- **Prose evaluation is advisory** — automated FILL review (voice drift,
  continuity) gates the pipeline, but its thresholds are tuned via the
  golden story, and CI treats prose-quality regressions as warnings, not
  failures (LLM nondeterminism must not flake the build; live-model tests
  are a manual/nightly lane).

## 9. Key decisions (mini-ADRs)

| # | Decision | Alternatives rejected | Why |
|---|---|---|---|
| A1 | Files + in-memory graph, no DB | SQLite, Kùzu/graph DB | ~10³ nodes; diffability and author editing outweigh query power (Principle 5) |
| A2 | Hand-rolled typed store; networkx only for algorithms | networkx as store; graph DB | Invariant enforcement needs a domain API; generic stores make illegal states representable |
| A3 | Thin LLM adapter, no agent framework | LangChain/pydantic-ai/DSPy | One structured-output call pattern used everywhere; frameworks add churn where we need audit-grade control |
| A4 | Uniform stage loop, stages as data | Bespoke orchestration per stage | Testability; repair/resume/ledger written once |
| A5 | YAML structure + Markdown prose | Single JSON blob | Authors edit files; prose diffs must be readable in review |
| A6 | Typst for PDF | LaTeX, HTML→print CSS | Generated-input ergonomics; deterministic layout for page-number references |
| A7 | Python | TypeScript | LLM/data tooling maturity; repo convention (`.gitignore`) |
| A8 | Arcs computed on demand | Stored arc nodes | Stored arcs go stale and invite arc-level authoring, a known design trap |
| A9 | GROW weaves atomic fork units on a linear spine; realization recomputes the whole ordering edge set | Per-seam edge patching; LLM emits an ordering | Full recompute is idempotent and cannot leave stale SEED seams; the LLM picking an index among engine-enumerated orders keeps invalid topologies unrepresentable (Principle 2) |
