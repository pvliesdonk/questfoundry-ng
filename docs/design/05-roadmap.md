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

## M6 — Craft-corpus research

Ground every stage in real craft knowledge without breaking the
one-shot adapter (mini-ADR A3): a **research pass** at each stage
head emits *queries* as a typed proposal; the engine runs them —
together with deterministic standing queries built from the vision
(genre, subgenre, tone, themes are open vocabulary, so retrieval is
always search-ranked over several related notes, never an exact-key
lookup) — through hybrid search over a project-configured markdown
corpus, and persists the top-k digests as a checkpointed,
author-editable artifact (`research/<stage>.md`) that the stage's
later passes read. The retrieval library is
[`pvliesdonk/markdown-vault-mcp`](https://github.com/pvliesdonk/markdown-vault-mcp)
used *as a Python library*, not as an MCP server — its documented
`Vault` API passed the seam validation (hybrid determinism, offline
warm-cache embeddings, custom provider; ≥3.1, pinned <4). No corpus
configured → the pass skips and the pipeline runs unchanged (the
golden story never depends on a corpus).

Governing principle: **corpus material may widen or ground, never
bind.** The Voice record and the invariants bind; retrieved notes are
advisory reference, style exemplars calibrate the voice pass as a
contrasting spread (never a nearest-match target) and fade from write
contexts once neighboring prose exists, and corpus text never enters
review prompts (a third taste-laundering channel we decline to open).
Details: design docs [02 §1](02-pipeline.md) and [03 §10](03-architecture.md).

**Exit:** the same premise generated with and without a configured
corpus produces two gate-clean stories with visibly different craft
grounding; research artifacts exist at every stage, are checkpointed,
and reruns/resumes replay them byte-stable; corpus-less projects (and
CI) run exactly as before.

## M7 — Illustrations (`qf illustrate`)

Render the DRESS-produced illustration briefs into real images — pulled
up front at the author's call: the consuming plumbing has existed since
M5 (briefs, art direction, per-entity visual profiles, the runtime
`art` entries, HTML embedding, PDF slots, all keyed off
`art/images/<passage-slug>.png`), and both cloud image APIs are a
config block away.

**Not a pipeline stage.** Cloud image generation is non-deterministic —
OpenAI's gpt-image and Gemini expose no seed — so rendered bytes can
never join checkpoint byte-stability or A16 fingerprint replay. `qf
illustrate` is a post-DRESS command beside `qf export`: idempotent by
file presence (skip when `art/images/<slug>.png` exists; `--force`
re-renders), never entering stage semantics. Mini-ADR on arrival.

**Provider seam:** [`pvliesdonk/image-generation-mcp`](https://github.com/pvliesdonk/image-generation-mcp)
*as a Python library* (the markdown-vault-mcp precedent — and this
library is itself the hardened fork of the original QuestFoundry's
image providers, so it is a re-adoption, not a new bet). `ImageService`
+ `register_provider` import cleanly without fastmcp code; providers:
OpenAI (`gpt-image-2` lineup), Gemini (`gemini-3.1-flash-image`,
SynthID-watermarked), and the deterministic zero-network **placeholder
that is CI's hermetic path**. Optional extra
`images = ["image-generation-mcp[openai,google-genai]"]`; typed
`ImageContentPolicyError` on safety refusals.

**Engine-side orchestration** (absent from the library by design, and
where the heritage lessons apply): prompt assembly from art direction +
per-entity `visual` fragments (the heritage consistency device — every
prompt naming an entity carries its profile fragment); sample-first
gate (render one, confirm, then batch); `--budget N` and priority
filtering; ledger entries for cost accounting; no automatic retry on
generation (expensive) but one reformulation attempt on a typed
content-policy refusal — the failure mode the original swallowed.
Style-reference conditioning (feeding a first rendered image back as a
reference for the rest) is the coherence upgrade text fragments can't
give; the library's edit path supports it on both providers — in scope
if the sample images show drift.

**Exit:** a generated story illustrates end-to-end on a real provider
within a stated budget — every brief above the priority floor renders
to `art/images/`, the HTML player embeds them, the PDF fills its
illustration slots; re-running `qf illustrate` costs zero API calls;
CI exercises the full command hermetically via the placeholder
provider.

## M8 — Depth & scale (scaffold deepening)

The structural effort that makes stories *book-sized*. Every live run
to date (5–7) lands at 8–22k words with B6 (words per genuine choice)
reading ~1.1–1.25k against the 250–800 feel target — the stories are
good but small, and the gap is scaffold depth, not prose. Deeper and
tensored Ys (SEED scaffolds with more pre-commit development and
longer payoff chains; a residue arm may carry its own diamond — the
shape deferred from the locked-dilemmas effort), fed real material by
the M6 research pass. The scale table becomes **words-primary**
(passage/beat bands derive from it), and the presets recalibrate
against measured live-run yield — `short` currently overshoots its
own B3/B4 bands (35–48 passages, 48–55-beat arcs vs 14–40; two locked
chains add real volume), so bands and scaffold depth move together.
Watch the weave's 64-candidate spread heuristic as unit counts grow
(the lexicographic DFS varies the tail first; early-position variety
may under-sample — STATUS open item, first measured data at 13 units).

**Exit:** a corpus-grounded `medium` story generates end-to-end at
20–60k words within budget, B3/B4 land inside the recalibrated bands,
B6 reads ≤ ~800, and all arcs simulate complete with exports clean.

## M9 — Retrieval refinement (exemplars & standing queries)

The two retrieval-quality findings from M6's exit run, made
first-class. (1) **A reserved exemplar mechanism**: style exemplars
belong at the voice pass as a contrasting spread (02 §1) and nowhere
else — today the only guard is manually scoping `craft.folders` away
from the exemplar cluster, and an unscoped corpus floods early-stage
digests with atmospheric prose (the 02 §1 bias vector, live run 7).
Config names the exemplar folders; the voice pass retrieves a
*diverse* spread from them (a map of the possibility space, never
nearest-match); every other stage's retrieval excludes them
structurally. (2) **Standing-query shape**: verbatim vision fields
make poor search strings — a 30-word tone sentence retrieves the same
audience-targeting boilerplate at every stage (live run 7's digests).
Condense standing queries to keyword form, or rebalance toward the
librarian, whose queries carried the value in the A/B run.

**Exit:** on the same corpus *without* manual folder scoping, no
exemplar material appears in any non-voice digest; the voice pass
shows a spread of stylistically distinct exemplars; per-stage digest
sources visibly differ (the standing half stops repeating).

## M10 — SHIP & the author loop

The last pipeline stage and the review experience around it. SHIP:
final assembly plus the Twee lint that flags constructs which don't
survive SugarCube conversion (design doc 04 §3). Interactive
checkpoint review: `qf run --yes` stops being a stub — batch mode
stays, but without `--yes` the run pauses at each checkpoint for
review/edit/continue (design doc 02 §3). `qf simulate --random N`
(design doc 04 §5) lands here too: its trigger condition is met —
false-branch diamonds now occur in every generated story, and
`--all-arcs` never walks them.

Run resilience lands here too: a transient transport failure
(provider disconnect, 5xx — live run 8 died four times on transport
drops and a 503) should auto-resume the interrupted stage with bounded
backoff instead of exiting. The Gemini provider now streams and
retries transport drops and 5xx server errors per call, which absorbs
most transience; a sustained failure still exits, and the A16
in-flight ledger already makes the stage-level retry free — today a
human re-invokes `qf run`.

Progress reporting is **built, pulled forward** (author call,
2026-07-12 — the pain was live, not hypothetical: a deep-scope FILL is
~300 calls over an hour+, and the only in-stage signals were buffered
console lines and counting cache files by hand, live run 8). `qf run`
emits a flushed one-line heartbeat per pass on stderr (pass m/n,
attempts, running spend from the ledger — token counts, the ledger
records no prices), and `qf status` reads live run state — spend
totals and any interrupted stage's journaled passes — from the cost
ledger and A16 in-flight ledger it already has.

**Exit:** `qf run` pauses at a checkpoint, the author edits an
artifact, the run resumes and revalidates; `qf export twee` lints; a
random-walk simulation covers detours the arc walk misses; a killed
provider connection costs a log line, not a dead run — and a long
stage shows its pulse: per-pass heartbeats in the run log, live
stage/pass/spend in `qf status`.

## Later / explicitly deferred

- Local review web UI (graph explorer + prose reader with approve/edit)
  — M10's CLI review loop first; the web UI builds on its semantics.
- LLM playtester with subjective reports.
- Distributed commits ("Witcher principle") — needs a threshold-flag
  primitive; revisit after real stories expose the demand.
- Cosmetic codeword curation, translation/localization support,
  EPUB export.

Demand-triggered (tracked as STATUS open items, built when a real
story or a demonstrated quality gap calls for them, per the annotation
discipline in 01 §10): the G4 pacing report,
intersections over exclusive beats, temporal
hints inside fork units, cosmetic flags on false branches and locked
storylines, and non-digit codeword fallbacks. (Tensored residue arms
were pulled in by M8, as this list anticipated; `scene_type` and
character-arc metadata were built when the over-stylization gap and the
prose-quality effort called for them — PR #65 and the prose-quality
effort respectively. The G4 pacing report now has its `scene_type`
signal and is the next demand-triggered item.)

## Top risks

| Risk | Mitigation |
|---|---|
| Illustration cost/quality on non-reproducible providers — paid APIs, no seeds, content-policy refusals, character drift across images | M7's sample-first gate + budget/priority caps spend; skip-if-exists makes reruns free; typed refusals get one reformulation; entity visual fragments in every prompt, reference-image conditioning as the escalation |
| Deep scaffolds break the cadence math — more beats per Y may stretch choice-less runs faster than false branches can close them | Addressed in M8 PR-1: the collapse cap cuts deep runs into pages without choices, and POLISH's diamond budget is sized by iterated playthrough projection against the B6 band (cap-aligned seams only); the live exit run confirms |
| Preset calibration circularity — bands tuned on stories generated under the old bands | Words-primary scale table anchors on the corpus's external 300–600 words/choice band, not on our own output |
| Weave candidate spread thins at scale — 64-candidate cap with tail-first DFS variety may under-sample early positions on 20+ unit stories | Measured watch item (first data at 13 units); widen the cap or diversify enumeration when a run shows clustering |
| Exemplar leakage / style anchoring ahead of the Voice | M9 makes the reserved-folder exclusion structural; until then `craft.folders` scoping is documented as required (03 §10) |
| Feasibility audit mis-calls (hedged prose) | I12 hard cap at 3 states; heavy residue *must* produce variants — the gate rejects "poly-state" claims over incompatible flags. Still open: no live run has stress-tested the audit against genuinely hedged prose |
| Token cost blowups at `long` scope | Budgets are gate-checked from DREAM; ledger + cache; `utility` model role for cheap calls |
| Author edits breaking invariants silently | Single validation path: `qf validate` runs the same gates on files as the pipeline runs on proposals |

Retired risks, for the record: GROW interleaving quality and prose
coherence across convergences — seven live runs across three provider
families produced gate-clean, seam-free stories; the mitigations
(engine-enumerated orders, canonical-arc-first windows, residue beats)
are now standing architecture rather than open bets.
