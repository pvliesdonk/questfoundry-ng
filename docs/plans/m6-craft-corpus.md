# M6 implementation plan — craft-corpus research

> **Working plan, not a design doc.** The authoritative contract lives in
> design docs [02 §1 "Craft context"](../design/02-pipeline.md),
> [03 §10](../design/03-architecture.md) + mini-ADR A13, and
> [05 §M6](../design/05-roadmap.md). This file sequences the build,
> records the planning-time decisions that the design docs are silent
> on (each marked with where it must land in the docs during PR-1),
> and is the hand-off contract for the implementing session. Delete or
> archive once M6 ships and STATUS records the outcome.
> Code references (`file.py:NNN`) are as of the commit that adds this
> file; anchor on the named function if lines have drifted.

## Shape of the milestone

- **PR-1 — engine work** (phases 0–6 below): the research pass,
  retrieval core, config, prompts, tests, and the design-doc updates,
  all offline. One PR.
- **PR-2 — exit-criterion validation**: the live A/B run (same premise
  with and without a corpus) once the author exports the IF-craft
  subtree of his vault as a local markdown directory. Folds in the
  pending live validation of locked dilemmas + richer residue
  (STATUS next-up #2).

Session pattern per AGENTS model economics: contracts, integration,
and review at frontier tier; mechanical implementation against the
contracts below can go to mid-tier subagents. The prompt-framing work
in phase 4 is bias-vector-sensitive — frontier writes or reviews it.

## Library-seam findings (planning-time, 2026-07-10)

STATUS lists validating the `markdown-vault-mcp` seam as the first M6
step, and 03 §10 budgeted for upstream API work ("first non-dogfood
library consumer"). Checked against the published docs and PyPI: the
risk is largely retired. As of **3.1.0** the library ships a
documented Python API:

- `Vault(source_dir=Path, index_path=..., embeddings_path=...,
  embedding_provider=..., read_only=True)` — facade with `reader` /
  `writer` / `graph` / `index` facets; thread-safe; SQLite index at a
  caller-chosen path.
- `vault.index.build_index()` (warm restart is an O(1) no-op) and
  `vault.index.build_embeddings()`.
- `vault.reader.search(query, limit=k, mode="keyword"|"semantic"|"hybrid",
  filters={frontmatter}, folder=subtree)` → `list[GroupedResult]`
  (per-file grouped sections with scores and snippets);
  `vault.reader.read(path, section=heading)` recovers full sections.
- A public `EmbeddingProvider` ABC with a local
  `FastEmbedProvider(model_name="BAAI/bge-small-en-v1.5", cache_dir=...)`;
  packaging extra `markdown-vault-mcp[embeddings]` pulls fastembed.
  Hybrid mode raises `ValueError` without a provider.

Remaining questions for the phase-0 spike: hybrid tie-break
determinism, and offline behavior with a warm fastembed model cache
(03 §10 forbids network at generation time).

## Design decisions (the contract)

Numbered so PR-1 review can check each landed. D5 is a new mini-ADR.

1. **Retrieval runs inside the research pass's `apply`** — a
   deterministic function of (query proposal, corpus) that sets
   `project.research[stage]` in memory; the digest reaches disk only
   at save/checkpoint, preserving 02 §1's checkpoint semantics.
   Kept-pass replay and A16 ledger resume re-run retrieval through the
   same apply and must reproduce identical bytes. Query-shape
   violations (over the cap, empty) are repairable `ApplyError`s;
   infrastructure failures (missing corpus dir, index build error)
   raise plain exceptions — a repair round cannot fix a missing
   directory and would burn an architect call.
2. **Central injection, no stage-module edits**: a
   `with_research(impl)` wrapper applied where `IMPLS` is assembled
   (`stages/__init__.py:11-19`) prepends the research `PassSpec` to
   every stage. It must wrap callable `passes` lazily — DRESS builds
   per-run review closures and FILL builds its per-project work queue
   inside their `_passes(project)` callables; resolving them eagerly
   would leak review state across runs.
3. **DREAM special case** (doc-silent; lands in 02 §1): no vision
   exists at DREAM's head, so DREAM's research context is the premise
   + scope preset and `standing_queries()` is empty there. Standing
   queries (from the vision's open-vocabulary genre/subgenre/tone/
   themes, always search-ranked, never exact-key) start at BRAINSTORM.
4. **Digest format**: `research/<stage>.md` = YAML frontmatter (stage,
   corpus fingerprint, standing + librarian queries, top_k, source
   note paths) + one markdown section per query with the retrieved
   snippets. **No timestamps anywhere** — digest bytes enter the next
   stage's A16 fingerprint, so they must be replay-stable (unlike
   `reports/*.md`, which carry a datetime but are never fingerprinted).
5. **A17 — author-edit / rerun semantics** (new mini-ADR; the hazard
   this plan exists to record). Naively, "author-editable artifact" is
   vacuous: digests are consumed by the *same stage's* later passes,
   so an edit only matters on rerun — but `prepare_rerun` rewinds to
   the predecessor snapshot, which never contains the target stage's
   digest, and re-running research clobbers whatever the author wrote.
   Resolution, mirroring the vision.yaml precedent ("editing it is a
   main reason to rerun", `runner.py:341`):
   - `prepare_rerun` restores `research/` from the snapshot like the
     other artifact dirs **but preserves the working tree's
     `research/<target>.md`** if present.
   - The research pass's `skip_if` (checked after the no-corpus skip):
     skip when this stage's digest exists **and is fresh** — freshness
     means the frontmatter-recorded corpus fingerprint and standing-query
     list both match currently computed values. A corpus or vision edit
     re-retrieves; an unchanged world reuses the digest with no LLM call.
   - Forcing re-retrieval = delete `research/<stage>.md` before the
     rerun (document in `qf rerun` help and 02 §1). `--keep research`
     then means: recorded queries, fresh deterministic retrieval, no
     LLM call — 03 §10's "ordinary `--keep`-able pass".
   - Load-bearing ordering: `skip_if` runs before keep/resume dispatch
     (`runner.py:298-303`); research.py must note this.
   - Rejected alternatives (record in the A17 row): always-re-retrieve
     (makes author edits vacuous); `--keep` replaying the digest file
     itself (breaks "ordinary keep-able pass" — keeps must replay
     *proposals* through apply).
6. **Standing queries stay engine-side** (02 §1 already says so) but
   are *shown* in the research prompt ("already searched — ask for
   what's missing") so the librarian doesn't duplicate them. The
   ownership split is deliberate: `--keep research` freezes only the
   model's judgment; a vision edit still updates the engine's half.
7. **Digest injection is a runner-level render variable**: the render
   call (`runner.py:120`) gains `research=<digest body>` read from
   `project.research` at render time. Templates opt in via a shared
   `_craft.j2` advisory partial. Review prompts are structurally
   immune — FILL/DRESS review functions render their own templates and
   never receive the variable.
8. **Dependencies**: new packaging extra
   `craft = ["markdown-vault-mcp[embeddings]>=3.1,<4"]` with the
   embedding model pinned (`BAAI/bge-small-en-v1.5`); the library's
   *core* joins the dev dependency group so CI tests true hybrid
   search hermetically via a deterministic fake `EmbeddingProvider`
   (hashed bag-of-words), no model download. The import is lazy and
   sits behind the `skip_if`, so corpus-less installs never touch it;
   a configured-but-missing library fails loud naming the extra.

## New module contracts

`src/questfoundry/models/craft.py` (new module keeps the
io ↔ pipeline import graph acyclic):

```python
class CraftConfig(BaseModel):            # project.yaml `craft:` block; extra="forbid"
    corpus: str                          # root, absolute or project-relative
    folders: list[str] = []              # eligible subtrees; [] = whole corpus
    top_k: int = 4
    max_queries: int = 5                 # librarian cap; exceeding -> ApplyError
    words_per_query: int = 200
    search_mode: Literal["hybrid", "keyword"] = "hybrid"  # keyword = offline degradation
    embedding_model: str = "BAAI/bge-small-en-v1.5"       # pinned, local
```

`src/questfoundry/pipeline/research.py` public surface:

```python
STAGE_FOCUS: dict[Stage, str]                    # one-line stage purpose for the prompt
class ResearchQuery(BaseModel): query: str; reason: str = ""    # extra="forbid"
class ResearchProposal(BaseModel): queries: list[ResearchQuery]

def standing_queries(vision, stage) -> list[str] # deterministic; [] at DREAM
def corpus_fingerprint(cfg, root) -> str         # sha256 over sorted (relpath, bytes) of eligible *.md
def retrieve(cfg, root, queries) -> str          # (kind, query) list -> digest markdown
def digest_body(text) -> str                     # strip frontmatter for injection
def digest_meta(text) -> dict                    # frontmatter for the freshness check
def research_pass(stage) -> PassSpec             # name="research", role="architect",
                                                 # template="research.j2"
def with_research(impl: StageImpl) -> StageImpl  # prepend; lazy-wrap callable passes
def _embedding_provider(cfg)                     # module-level test seam (monkeypatch)
```

Multi-folder handling: the library's `search(folder=...)` filters one
subtree, so N eligible folders → N searches per query, merged, then
stable-sorted `(-score, path, heading)` and truncated in research.py —
never trust library tie-breaking. The vault index and embeddings live
under `<project>/cache/research/` (already gitignored).

`Project` gains `craft: CraftConfig | None = None` and
`research: dict[str, str] = {}` (stage value → digest markdown).

## Ordered work items (PR-1)

**Phase 0 — library-seam spike** (scratchpad, not committed; findings
→ STATUS decision log). Against `markdown-vault-mcp>=3.1`: hybrid
tie-break determinism (two runs → identical ranked lists; if not,
confirm scores are stable so our re-sort suffices), warm-restart
no-op, custom ABC provider accepted, offline behavior with a warm
fastembed cache. File upstream issues for any gap; pin version bounds
from what the spike validates.

**Phase 1 — config + IO** (`models/craft.py`, `project/io.py`):
CraftConfig; `meta["craft"]` load/save (`io.py:218-231`, `:300-311`,
guarded like the other optional keys); `research/*.md` load into
`project.research`, save + `_prune` (prose pattern, `io.py:378-397`).
Malformed frontmatter or a filename that isn't `<stage>.md` →
`ProjectError` (codex precedent, `io.py:257-268`) — a silently ignored
digest is a debugging trap.

**Phase 2 — retrieval core** (`pipeline/research.py`):
`standing_queries`, `corpus_fingerprint`, the vault wrapper + provider
seam, `retrieve` (per-folder search, merge, stable sort, word budget),
digest render/parse. Pure functions where possible; byte-deterministic
output is the acceptance bar.

**Phase 3 — pass + runner integration**:

- `research_pass`: `skip_if` per D5/D8 ordering (no corpus → skip;
  fresh digest → skip; missing lib → loud error from `build_context`
  before any LLM spend); `build_context` = stage focus,
  vision-or-premise, standing queries, corpus overview; `apply` = cap
  check → retrieve → `project.research[stage]` → applied lines
  including `corpus <fp[:12]> (<n> notes); <k> standing + <m>
  librarian; sources: …` — which is how the fingerprint reaches
  `reports/<stage>.md` (assembled at `runner.py:260-269`).
- `with_research` + `IMPLS` rewiring (`stages/__init__.py:11-19`).
- Runner edits: `project.research` joins the `_backup`/`_restore`
  tuple (`runner.py:96-107`) and the `PassSpec.apply` contract
  docstring; render variable (`runner.py:120`; thread the stage into
  `_run_pass`); A16 fingerprint — `"research"` joins the dir tuple
  (`runner.py:195`) and `knobs["craft"] = {config dump, corpus hash}`
  is added **only when configured** (`runner.py:203`), keeping
  corpus-less fingerprints byte-identical across the upgrade;
  checkpoint dir list (`runner.py:247`); `prepare_rerun` dir list +
  target-digest preservation (`runner.py:354-361`).
- `cli.py`: rerun help note (delete the digest to force re-retrieval).
- `pyproject.toml`: dev group + `craft` extra per D8.

**Phase 4 — prompts** (bias-vector-sensitive; frontier writes or
reviews):

- `research.j2`: emit search strings, not questions; at most
  `max_queries`; don't repeat the standing queries shown; includes
  `_shared.j2` last like every prompt.
- `_craft.j2`: `{% if research %}`-guarded advisory block — advisory
  reference that may widen or ground, never bind; the vision, voice,
  invariants, and the instructions above always win; never quote or
  imitate a source.
- Included in: `dream`, `brainstorm`, `seed_triage`, `seed_scaffold`,
  `grow_weave`, `grow_intersections`, `grow_bridge`,
  `grow_contextualize`, `polish_passages`, `polish_finalize`,
  `dress_direction`, `dress_briefs`, `dress_codex`.
- `fill_voice.j2`: bespoke contrasting-spread framing (a map of the
  possibility space; choose a voice none of these uses) per 02 §1.
- `fill_write.j2`: fade guard —
  `{% if research and not window and not lookahead %}` (the prose
  window is the true style anchor once it exists).
- **Never included**: `fill_review`, the DRESS codex review (02 §1
  iron rule), `polish_audit` (review-shaped — the same
  taste-laundering channel; record the exclusion in 02 §1),
  `seed_order` and `dress_codewords` (mechanical picks).

**Phase 5 — tests** (each behavior gets one; violating constructions
where a rule can be violated):

- Fixtures: `tests/fixtures/corpus/` (~8 frontmattered notes across
  two eligible folders plus one out-of-scope folder) and the fake
  `EmbeddingProvider`.
- `test_research.py`: standing-query determinism / stage variation /
  empty at DREAM; retrieve honors top_k, folder scoping, word budget;
  two runs → byte-identical digest; multi-folder merge stability;
  fingerprint sensitivity to content change; query cap → `ApplyError`;
  `skip_if` matrix (no corpus / fresh digest skips / stale fingerprint
  re-runs); missing-library loud error naming the extra;
  `with_research` prepends + all IMPLS wrapped + DRESS closure
  freshness across two `run_stage` calls.
- io: craft block + `research/` round-trip, prune, bad
  filename/frontmatter → `ProjectError`, pre-seeded future-stage
  digest survives save.
- runner: snapshot contains `research/`; `--keep research` replays
  with attempts=0 and identical bytes; `prepare_rerun` preserves the
  target digest and restores the rest; a corpus edit voids the
  in-flight ledger; corpus-less knobs carry no craft key
  (fingerprint byte-parity across the upgrade); crash-after-research
  resume replays identical bytes.
- prompts: `_craft.j2` renders the advisory frame; `fill_write` omits
  it when the window is non-empty; review templates rendered with a
  digest present never contain a digest sentinel.
- e2e: `tests/fixtures/keeper-craft/` — keeper fixtures copied with
  hand-written research-proposal fixtures spliced at the stage heads
  (positional replay ignores prompt bytes, so this is assemblable
  offline); `run --to seed` with a corpus → gates clean, three
  digests, reports carry fingerprints. The existing corpus-less e2e
  and golden story stay byte-untouched — that parity *is* the proof
  that fixture indices don't shift (a skipped pass makes no LLM call).
- Golden story: add one hand-authored `research/<stage>.md` to
  `examples/keepers-bargain` so `qf validate` exercises the loader
  path (AGENTS: extend the golden when it can represent a new
  artifact).
- Green gate before push: `uv run pytest -q`,
  `uv run ruff check src tests`,
  `uv run qf validate examples/keepers-bargain`.

**Phase 6 — docs (same PR)**: 02 §1 (DREAM amendment, A17 flow,
excluded templates); 03 §9 mini-ADR A17 row + §10 (index cache
location, extra, config fields, digest format); AGENTS package map
(`pipeline/research.py`); STATUS (state + decision log: spike
results, A17, pins); README status section if its claims move.

## PR-2 — exit-criterion validation procedure

1. **Regression**: full test/lint/golden gate green with zero fixture
   changes.
2. **Corpus prep**: `craft:` block pointed at the author's exported IF
   corpus; warm the embedding cache once; verify a second index run is
   offline-clean; record the fingerprint.
3. **Run A (baseline)**: fixed premise, `short` scope, no craft block —
   `qf run --to dress`, `qf validate`, `qf simulate --all-arcs`,
   `qf export html` + `pdf`. Watch the locked-dilemma triage and
   residue followups (STATUS next-up #2 rides along).
4. **Run B (grounded)**: identical premise/scope/seeds plus the craft
   block; same commands.
5. **Artifacts (B)**: `research/<stage>.md` for all seven stages; each
   snapshot carries the digests for stages ≤ it; every report names
   the corpus fingerprint; A's reports show
   `skipped: no craft corpus configured`.
6. **Byte-stability**: (a) interrupt FILL mid-stage and re-run — no
   re-spend, `research/fill.md` sha256 unchanged; (b) delete
   `research/dress.md` and rerun DRESS with `--keep research --keep
   direction --keep briefs --keep codex --keep codewords` — digest
   sha256 equals the recorded one; (c) hand-edit `research/dress.md`,
   rerun with keeps — the skip fires and the edit survives.
7. **Exit judgment** in the STATUS decision log: side-by-side A/B
   (voice.yaml diff, three sampled passages, dilemma questions) with
   cited examples and the ledger cost delta; tick M6 in STATUS and the
   roadmap; README updated.
