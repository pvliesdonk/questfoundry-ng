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
    enrichment.py    #   ArtDirection, VisualProfile, IllustrationBrief, CodexEntry
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
                     # constraints, candidate orders, spine realization)
    passages.py      # POLISH's deterministic core (collapse, choice
                     # topology, residue/false-branch splicing)
    research.py      # craft-corpus retrieval: standing + librarian queries
                     # -> persisted digests (M6, see §10)
    stages/          # dream.py .. ship.py — schemas, prompts, gates only
    prompts/         # Jinja2 prompt templates, versioned
  llm/
    adapter.py       # complete(prompt, schema) -> validated model
    providers/       # anthropic.py, openai.py, gemini.py, mock.py
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
  illustrate.py      # `qf illustrate`: DRESS briefs -> art/images/ (A18)
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

Mid-stage crash resume is likewise the runner's, not any stage's: every
accepted pass journals its proposal to the in-flight ledger
(`inflight/<stage>/`, A16) and re-entering the stage replays those
passes without LLM calls. The content-addressed cache (§5) remains an
independent second net — a pass that succeeded but never reached the
ledger re-runs live and hits the cache for free.

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
- **The id contract is stated once, adapter-side.** The JSON instruction
  accompanying every schema requires node references to be the full
  `kind:slug` id exactly as rendered in the prompt. Engine-side
  canonicalization is limited to provably unambiguous forms (restoring a
  dropped kind prefix is parsing); fuzzy matching such as display-name
  resolution is out — it converts loud repair failures into quiet wrong
  answers. Repair errors always name the expected ids.
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
  project.yaml           # name, scope, model-role mapping, images provider, stage configs & steering notes
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
  research/<stage>.md    # persisted craft-corpus digests per stage (M6)
  reports/<run>/<stage>.md   # stage reports (human-readable audit trail)
  snapshots/<run>/<stage>/   # full-graph checkpoint per gate
  inflight/<stage>/          # in-flight pass ledger (transient, gitignored; consumed at checkpoint)
  cache/llm/                 # call cache (gitignored); cache/images/ is the image service's scratch
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
qf illustrate --budget 8 --priority 2         # render DRESS briefs to art/images/ (04 §6)
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
| A10 | FILL's automated review is a post-apply hook on the uniform repair loop | Bespoke write-review-revise orchestration inside FILL | One loop owns retries, restore, and the halt ('structure is wrong, not the words'); review issues re-enter the prompt exactly like validation errors, so ≤2 revision rounds is `max_repairs`, not new machinery |
| A11 | Id contract stated once in the adapter's JSON instruction; engine canonicalizes only provably unambiguous forms | Per-pass engine tolerances; fuzzy name matching | Fuzzy acceptance is a treadmill against a model distribution and can turn loud repair failures into quiet wrong answers; slug-prefix restoration is parsing, not prediction |
| A12 | Codewords are suggested at DRESS, not POLISH; enrichment lives on the Project (like Voice), not in the graph | Codeword pass inside POLISH (04's original wording); codex/briefs as graph nodes | "Drawn from the story's diction" needs the diction to exist — there is no voice or prose until after FILL; DRESS reads the finished story. Enrichment describes the story rather than being story structure, so gates see it via an explicit `run_checks(enrichment=…)` parameter — one validation path, no graph pollution |
| A13 | Craft-corpus retrieval is engine-side (a research pass emitting queries), and retrieved digests persist as checkpointed artifacts that later passes read | Mid-call tool use (the original QuestFoundry's approach); live MCP access from the adapter; re-searching on every rerun/resume | Preserves A3's one-shot adapter, the content-addressed cache, positional fixture replay, and crash-resume byte-stability; the persisted artifact is author-reviewable ("review = edit + revalidate" covers what the pipeline read); the model still decides *what it needs* — it just cannot fetch mid-thought (§10) |
| A14 | Multi-hard realization is part of the weave: every unit after the first hard fork is instantiated once per world with the template Y removed symmetrically; the nesting order is an ordinary interleaving choice (wraps/serial-constrained), and a contextualize pass rewrites per-world content | A duplication layer bolted onto POLISH; SEED declaring the nesting; keeping the SEED-authored beats as the first world's instance | Structure is copied, content follows the full coordinate (01 §5): the copy is mechanical and belongs to the weave, the words belong to an LLM pass; a template kept as "world one" would be a canonical-world bias vector — the same trap as the removed canonical answer |
| A15 | A locked dilemma is derived from topology — exactly one explored path (heritage: an answer no `explores` edge points at is the shadow) — and its outcome derives no state flag | A stored disposition marker on the dilemma; deriving flags from locked consequences like any other | The graph already says it, so a marker could only drift out of sync; a flag every reader holds can gate nothing and would only bloat the flag universe — a locked outcome is a world fact FILL reads from the beats themselves (G3 rejects flags granted from locked paths, both directions) |
| A16 | Crash resume is a per-pass in-flight proposal ledger replayed through the kept-pass machinery, voided by a stage-input fingerprint | Flushing prose files per write pass; relying on the LLM cache alone | A pass's effects exceed prose (micro-details, voice) and must reproduce through the mutation layer; the working tree never carries ungated partial state (02 §1's checkpoint definition holds); uniform across stages (A4) and independent of cache eviction or prompt-code changes. Auto-resume degrades to live on staleness while `--keep` stays fail-loud, and any input edit voids the ledger — "review = edit + revalidate" is never bypassed. Replay assumes apply functions are deterministic, the same assumption `rerun --keep` and cache replay already make |
| A17 | A research digest is reused while *fresh* (its recorded corpus fingerprint + story inputs match current values — the standing queries, or a premise hash where none existed, since DREAM's research is premise-grounded); `prepare_rerun` preserves the target stage's own digest through the rewind; forcing re-retrieval = deleting the file | Always re-retrieving on rerun; `--keep research` replaying the digest file itself | Always-re-retrieve makes "author-editable artifact" vacuous — the digest is consumed by the *same* stage's later passes, so an edit only matters on rerun, and re-retrieval would clobber it (the predecessor snapshot never contains the target's digest). Replaying the file would break "ordinary `--keep`-able pass" — keeps replay *proposals* through apply. Freshness is checked in `skip_if`, which the runner dispatches before keep/resume replay; a corpus or vision edit re-retrieves, an unchanged world reuses for free — the vision.yaml never-restored precedent, extended |
| A18 | `qf illustrate` is a post-DRESS *command*, idempotent by file presence (`art/images/<slug>.png` exists → skip; `--force` re-renders), with `image-generation-mcp` consumed as a library (`ImageService` + `register_provider`, no fastmcp code) and all orchestration engine-side: prompt assembly from art direction + entity visual fragments, sample-first gate, `--budget`/`--priority` filtering, ledger entries, one LLM reformulation on a typed content-policy refusal, and PNG normalization at the single write site (providers return what they like — Gemini hands back JPEG) | A DRESS pipeline pass; wrapping the library's MCP server; a content-addressed image store | Cloud providers expose no seeds, so rendered bytes can never join checkpoint byte-stability or A16 fingerprint replay — generation must sit beside `qf export`, outside stage semantics. The library deliberately owns no cache/budget/ledger, so the heritage lessons (consistency fragments, sample-first cost gate, the refusal the original swallowed) live in the engine. Slug-named files keep the presence-keyed skip and the export plumbing that has keyed on slugs since M5; content addressing's free dedup wasn't worth breaking that |

## 10. Craft-corpus research (M6)

The runtime counterpart of `docs/heritage/` (which grounds *development*
sessions): a markdown craft corpus grounds the *pipeline's* LLM calls.
Roadmap milestone M6 owns it; contract details in
[02 §1 Craft context](02-pipeline.md). Architecture specifics:

- **Retrieval library.** Hybrid (FTS + local embeddings) search over a
  directory of frontmattered markdown, via
  [`pvliesdonk/markdown-vault-mcp`](https://github.com/pvliesdonk/markdown-vault-mcp)
  used *as a Python library* (`Vault` facade, `reader.search(query,
  mode, folder)`), not as an MCP server — validated ≥3.1, pinned `<4`,
  installed by the `craft` packaging extra. The embedding model is
  local and version-pinned (`FastEmbedProvider`, default
  `BAAI/bge-small-en-v1.5`); after a one-time model download, warm-cache
  retrieval runs fully offline, and `search_mode: keyword` is the
  embeddings-free degradation. The vault index, embeddings, and tracker
  state live under `<project>/cache/research/` (gitignored, like the
  LLM cache). The engine never trusts library tie-breaking: results
  re-sort under `(-score, path, heading)` before truncation.
- **Corpus as configuration.** `project.yaml`'s `craft:` block
  (`models/craft.py`) — corpus root (absolute or project-relative),
  eligible `folders` (a gamebook project scopes to the IF corpus and
  ignores tabletop/workshop material), retrieval budget (`top_k`,
  `words_per_query`, `max_queries`). The engine is corpus-agnostic; the
  corpus fingerprint (content hash over the eligible files) is recorded
  in the digest's frontmatter and each stage report, so a run names
  exactly what it read. **Scope `folders` away from style-exemplar
  clusters**: atmospheric queries nearest-match atmospheric prose, so
  an unscoped corpus fills early-stage digests with exemplars — the
  02 §1 bias vector (exemplars belong at the voice pass as a
  contrasting spread; live run 7 hit this). A first-class reserved
  exemplar mechanism is future work (STATUS next-up).
- **Determinism rules.** Search results feed prompt bytes, so retrieval
  runs once per stage (inside the research pass's apply — replay
  re-retrieves identically), and the persisted `research/<stage>.md` is
  the only thing later passes read, injected as an always-defined
  render variable so review prompts are structurally immune. Digests
  carry no timestamps: their bytes join the next stage's A16
  fingerprint, and the craft config + corpus hash join the fingerprint
  knobs only when configured (corpus-less fingerprints are byte-stable
  across the M6 upgrade). Fixture replay is positional and unaffected;
  the content-addressed cache sees stable bytes; a rerun that should
  re-retrieve does so by re-running the research pass, an ordinary
  `--keep`-able pass (freshness/edit semantics: mini-ADR A17).
- **No corpus, no change.** The research pass `skip_if`s when no corpus
  is configured; CI and the golden story never require one, and the
  retrieval library is imported only past that guard (missing install
  fails loud naming the `craft` extra before any LLM spend).
