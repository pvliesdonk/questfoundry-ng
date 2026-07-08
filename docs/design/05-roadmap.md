# 05 — Roadmap

Milestones are vertical slices ordered so that the riskiest design bets
are tested earliest with the least code. Each has a demoable exit
criterion; none depends on a later one.

## M0 — Skeleton & graph engine

Repo scaffolding (`uv`, pytest, CI), `models/`, `graph/` (store,
mutations, queries, validators I1–I13), project-on-disk load/save,
`qf new` / `qf validate` / `qf graph`.

**Exit:** a hand-written "Keeper's Bargain" project (YAML files, no LLM)
loads, passes all gates, and `qf graph` renders its beat DAG. The golden
story is born as a hand-authored fixture *before* any generation exists.

## M1 — Front of pipeline (DREAM → SEED)

Uniform stage runner (checkpoints, repair loop, snapshots), LLM adapter
(Anthropic + mock, cache, ledger), stages DREAM, BRAINSTORM, SEED with
gates G0–G2.

**Exit:** `qf run --to seed` produces a valid triaged, scaffolded story
from a one-paragraph premise; recorded fixtures let CI run it offline.

## M2 — GROW (the risk milestone)

Deterministic interleaving core (hints + ordering → candidate orders),
divergence/convergence wiring, flag derivation, intersection proposals,
bridge beats, topology freeze, gate G3, `qf simulate --all-arcs`.

**Exit:** four complete, validated arcs through the golden story's beat
DAG. *This milestone is deliberately early: if dilemma weaving doesn't
work, the product doesn't work, and we want to know before investing in
prose.*

## M3 — POLISH & structural play

Passage collapse, choice wiring, feasibility audit, variants, residue
beats, false branches, gate G4; `qf play` on beat summaries.

**Exit:** the golden story is *playable in the terminal* end-to-end —
choices, gates, four distinct journeys — with zero prose written.

## M4 — FILL & first exports

Voice, reference-arc-first work queue, per-passage context building,
automated review (≤2 rounds), gate G5; exports: runtime JSON + HTML
player + Twee; round-trip validation.

**Exit:** a stranger plays "The Keeper's Bargain" in a browser, start to
one of its endings, and can't tell where the seams are.

## M5 — DRESS, print, and finish

Art direction, briefs, optional image generation, codex; the gamebook
PDF pipeline (codewords, shuffling, Typst); `qf rerun --keep` partial
regeneration; `short`/`medium` scope hardening.

**Exit:** a printable PDF gamebook with working codeword play, plus a
`medium`-scope story generated end-to-end within its budget estimate.

## Later / explicitly deferred

- Local review web UI (graph explorer + prose reader with approve/edit).
- LLM playtester with subjective reports.
- Distributed commits ("Witcher principle") — needs a threshold-flag
  primitive; revisit after real stories expose the demand.
- Cosmetic codeword curation, translation/localization support,
  EPUB export.

## Top risks

| Risk | Mitigation |
|---|---|
| GROW interleaving quality — valid but dramatically flat orderings | M2 first; LLM chooses among engine-valid orders (never invents them); pacing checks in G3 |
| Prose coherence across convergences | Canonical-arc-first order + lookahead context; residue beats absorb tone shifts; ≤2-revision rule pushes failures back to structure |
| Token cost blowups at `long` scope | Budgets are gate-checked from DREAM; ledger + cache; `utility` model role for cheap calls |
| Feasibility audit mis-calls (hedged prose) | I12 hard cap at 3 states; heavy residue *must* produce variants — the gate rejects "poly-state" claims over incompatible flags |
| Author edits breaking invariants silently | Single validation path: `qf validate` runs the same gates on files as the pipeline runs on proposals |
