# 02 — Pipeline

The pipeline compiles a premise into a playable gamebook in eight stages.
This document defines each stage's contract — inputs, outputs, what the
LLM does vs. what the engine does — the validation gates between stages,
and the human-review model.

```
DREAM → BRAINSTORM → SEED → GROW → POLISH → FILL → DRESS → SHIP
  │G0       │G1        │G2     │G3      │G4      │G5     │G6     └─ exports
```

## 1. The stage execution model

Every stage runs the same loop, which is what makes the pipeline testable
and the stages interchangeable to the engine:

```
context = build_context(graph, vision, stage_config)   # deterministic
proposal = llm.generate(prompt(context), schema)       # typed, validated JSON
issues   = validate(proposal, graph)                   # invariant checks
if issues: proposal = llm.repair(proposal, issues)     # ≤2 repair rounds
apply(proposal, graph)                                 # mutation layer only
gate(graph)                                            # stage exit gate
checkpoint(stage)                                      # snapshot + review
```

Key properties:

- **LLMs propose, the engine disposes** (Principle 2). Model output is a
  Pydantic-typed proposal. Only the mutation layer touches the graph, and
  it re-checks every invariant — a model cannot corrupt structure.
- **Repair, then escalate.** Invalid proposals go back to the model with
  the concrete validation errors, at most twice. Still invalid → the stage
  halts with a human-readable report. Never silently drop or auto-mangle.
- **Deterministic where possible.** Anything computable — DAG assembly
  bookkeeping, flag derivation, passage collapse boundaries, arc
  enumeration, all validation — is code, not model. The LLM is reserved
  for genuinely creative judgment.
- **Checkpoint every stage.** A snapshot of the whole project is written
  after each gate. Any stage can be re-run from its predecessor's
  snapshot.

### Craft context (planned — M6)

Stages can be grounded in a craft corpus (design doc [05 §M6](05-roadmap.md))
without changing the loop above: a **research pass** runs at the stage
head, in the uniform loop like any other pass (`skip_if` no corpus is
configured). It emits *queries* — a typed proposal, judged like any
other — and the engine retrieves: deterministic standing queries (built
from the vision's open-vocabulary genre/tone/themes) plus the pass's
story-specific ones go through hybrid search over the configured
corpus, and the top-k digests are persisted as a checkpointed,
author-editable artifact (`research/<stage>.md`). The stage's later
passes read the artifact, never the search index — so reruns and
resumes replay retrieval byte-for-byte, and "review = edit +
revalidate" extends to what the pipeline read before writing.

The rule that keeps this safe: **corpus material may widen or ground,
never bind.** Injected digests carry an explicit advisory framing and
cannot override invariants or stage contracts. Style exemplars appear
at the voice pass as a *contrasting spread* (a map of the possibility
space, never a nearest-match target), fade from write contexts once
neighboring prose exists (the window is the true style anchor), and
never enter review prompts — review judges against the Voice record
alone, or exemplar-conformance becomes a new taste-laundering channel.

### Backtracking

Gates fail *backwards*: a problem is fixed at the stage that owns it,
never patched downstream (Principle 4).

| Symptom | Owner |
|---|---|
| Dilemma has no viable second answer; cast member connects to nothing | BRAINSTORM |
| Path scaffold incomplete; dilemma ordering contradictory | SEED |
| Arc incomplete / unreachable beat / convergence violates role | GROW |
| Passage infeasible (too many states); gate unsatisfiable | POLISH |
| Prose fails review twice | **Structure is wrong** → POLISH or GROW, not more prose |

## 2. The stages

### DREAM — the creative contract

| | |
|---|---|
| In | Premise (free text), scope preset, author preferences |
| Out | **Vision** record |
| Gate G0 | Vision complete; scope budgets resolved; content boundaries explicit |

The LLM expands the premise into genre/subgenre, tone, themes, audience,
content boundaries, and a POV hint; the engine binds the scope preset's
budgets. Cheapest stage to iterate on — the author should churn here, not
later. Everything downstream that contradicts the vision gets cut, so this
is where taste is captured.

### BRAINSTORM — cast and dilemmas

| | |
|---|---|
| In | Vision |
| Out | Entities (cast), Dilemmas with two Answers each, `anchored_to` edges |
| Gate G1 | Budgets met; I1, I2; every entity anchors ≥1 dilemma *or* is flagged for triage; ≥2 dilemmas share an entity |

The LLM generates generously — more dilemmas and cast than will survive —
because SEED triages down and it is far cheaper to cut than to weave in a
missing character later (the cast is effectively locked here). The
shared-entity check exists because dilemmas that share no entities produce
parallel novels, not a woven story.

Deterministic: ID assignment, namespace enforcement, anchoring-graph
analysis (which entities are load-bearing).

### SEED — commitments and scaffolds

| | |
|---|---|
| In | Vision + full BRAINSTORM output |
| Out | Triage dispositions; Paths (+ Consequences) per explored answer; per-path beat scaffolds with temporal hints and flexibility annotations; dilemma ordering (`wraps`/`serial`/`concurrent`); convergence sketch |
| Gate G2 | I3 per explored path; role budget met (e.g. `micro` = 1 hard + 1 soft); ordering relations acyclic and consistent; every surviving entity anchored; every cut justified |

The heaviest creative stage, run as three LLM passes with engine checks
between:

1. **Triage** — select the cohesive ensemble; cut brilliant-but-
   disconnected material. Decide which answers get explored paths and
   which stay locked shadows.
2. **Scaffold** — per explored path, the Y-shape: pre-commit chain
   (shared, dual `belongs_to`), one commit beat, post-commit chain. Each
   path's beats must read as a complete story alone — GROW interleaves,
   it must never have to invent missing spine. SEED wires the
   *intra-dilemma* ordering edges itself (pre-commit chain → per-path
   commit → post-commit chain), since the Y's internal order is a fact
   of the scaffold, not an interleaving decision; after SEED the beat
   graph is a set of disconnected Y components (plus a setup chain), and
   GROW's job is exclusively the *cross-dilemma* weave. Beats also get
   **flexibility annotations** ("the docks could be the market"; "the
   spy could be the informant") — invitations GROW uses to create
   intersections — and **temporal hints** ("before D1's commit") guiding
   interleave order.
3. **Order & sketch** — declare pairwise dilemma relations; sketch where
   soft paths reconverge and with what residue weight.

### GROW — weave the DAG

| | |
|---|---|
| In | All SEED output |
| Out | The **beat DAG** (ordering edges); intersection groups (consumed here); bridge beats; state flags derived from consequences; entity overlays activated; convergence points fixed |
| Gate G3 | I4–I9; every computed arc complete (I6); flag derivation total (every consequence → ≥1 flag); budgets (beat count per arc within scope) |

The hardest stage, split deliberately:

- **Deterministic core:** candidate interleaving from temporal hints +
  ordering relations (topological constraints), divergence wiring at each
  commit, convergence-point computation for soft dilemmas, flag
  derivation, arc enumeration and validation. This is graph algorithm
  territory; a model adds nothing but risk.
- **LLM judgment calls:** choosing among valid interleavings for dramatic
  pacing (commits distributed, not clustered); proposing intersections
  from shared entities + flexibility annotations (each accepted
  intersection resolves the scene's location/entities); writing bridge
  beats where adjacent scenes share no entities or place.

Sequencing matters: intersections are proposed *before* the interleaving
is chosen, so member adjacency enters the candidate enumeration as a
constraint rather than being retrofitted. The LLM never emits an
ordering — it returns an index into the engine's candidate list.
Temporal hints are advisory: a hint that would make the constraints
unsatisfiable is dropped and reported, never allowed to wedge the weave
(SEED wrote it without seeing the whole).

After G3 passes, **the topology freezes** (I9). This is the pipeline's
central commitment point.

### POLISH — compile to passages

| | |
|---|---|
| In | Frozen beat DAG, flags, overlays, residue weights |
| Out | Passage graph: passages (collapse), choice edges (labels, requires, grants), variant passages, residue beats, false branches, pacing bridges; character-arc metadata per entity |
| Gate G4 | I10–I13; every choice label distinct and non-spoiling; pacing report (no >N consecutive same-intensity passages); every heavy-residue convergence has variants, every light one a residue beat |

Two phases:

1. **Finalize the DAG** (additions only): reorder within linear runs for
   flow; insert bridge beats for pacing; insert residue beats per the
   convergence sketch; add false branches where long linear stretches
   need choice-feel.
2. **Build the passage layer:** collapse maximal linear runs into
   passages (boundaries at forks/joins); merge intersection-adjacent
   beats into single scenes where narratable; run the **prose-feasibility
   audit** on every passage — for each possibly-active flag decide
   *irrelevant here* (annotate "don't address"), *compatible* (poly-state
   prose, ≤3 states), *light* (residue beat covers it), or *heavy*
   (variant passages); wire choices with labels/gates/grants; synthesize
   character-arc metadata ("begins X, pivots at beat Y, ends Z per
   path") for FILL's benefit.

The engine computes collapse boundaries and gate satisfiability; the LLM
writes labels, decides feasibility judgments, and drafts arc metadata.

### FILL — prose

| | |
|---|---|
| In | Passage graph + everything (entities w/ overlays, flags, arc metadata, shadows, vision) |
| Out | **Voice** record; prose per passage (and per variant); universal entity micro-details |
| Gate G5 | Every passage has prose within its word budget; automated review (voice drift, continuity, beat-summary fidelity) clean or explicitly waived; ≤2 revision rounds per passage |

Order matters: FILL locks the Voice first, then picks a **reference
arc** — one arbitrary complete playthrough, chosen by seeded selection
(author-overridable) — and writes it end-to-end, establishing
shared-passage prose. Each remaining arc is then written *toward* the
already-written convergence points, with the awaiting prose in context so
branches land smoothly. The reference arc is FILL-internal scheduling
state, not a story property: it exists only so convergence-point prose
has a first author, it is invisible to every other stage, and nothing
about it may influence depth, length, or quality budgets — G5 applies the
same word budgets and review bar to every arc.

Per-passage context is rich by design: voice, beat summaries, full entity
state (base + active overlays), a sliding window of preceding prose,
character-arc position, active flags, the *shadows* (what didn't happen —
so prose can carry the weight of it), and convergence lookahead.

A passage failing review twice is a structural bug: it goes back to
POLISH (or GROW), never to a third rewrite. Prose cannot rescue a broken
structure (Principle 4).

### DRESS — art and codex

| | |
|---|---|
| In | Finished prose, entities, vision, voice |
| Out | Art direction; entity visual profiles; illustration briefs (prioritized) per key passage; illustrations (via pluggable image backend, optional); codex entries; print codewords on projected flags |
| Gate G6 | Every brief references only established visual facts; codex is spoiler-safe (entries reveal nothing the earliest-reaching arc hasn't); every gate-tested flag carries a well-formed, unique codeword |

DRESS reads the story; it never changes it — its outputs live beside the
graph (the enrichment bundle, like the Voice), except codewords, which
are presentation metadata stored on their flags. Four passes: *direction*
(art direction + a visual profile per retained entity), *briefs*
(prioritized illustration briefs; the engine checks every referenced
entity is in the passage and has a profile — the mechanical half of G6's
"established facts"; the judgment half is prompt contract), *codex* (one
diegetic entry per dilemma-anchoring entity, spoiler-safety enforced by a
paired review pass whose contract separates REQUIRED register from BANNED
reveals, per the review-legibility lessons), and *codewords* (memorable
single words for every flag some choice gate tests — suggested here, not
at POLISH, because "drawn from the story's diction" needs the diction to
exist: there is no voice and no prose until after FILL; see mini-ADR A12).

### SHIP — export

| | |
|---|---|
| In | Passage graph + prose + flags + art + codex |
| Out | Twee 3, standalone HTML, canonical JSON, print PDF |
| Gate | Round-trip check: exported JSON re-imported and re-validated; per-format lint (see [04](04-export-and-play.md)) |

Purely deterministic — no LLM. SHIP owns the **codeword projection**:
selecting which flags become player-facing codewords in print (soft
routing flags yes; hard flags no — page structure already separates those
readers) and generating the "write down / if you have" text.

## 3. Human-in-the-loop

Review is a stage-boundary concept, uniform everywhere:

- **Checkpoint** — after each gate, the pipeline halts (interactive mode)
  or auto-approves (batch mode `--yes`), writing the same artifacts
  either way: the snapshot, a **stage report** (what was created/cut and
  why, gate results, spend), and any warnings.
- **Review = edit + revalidate.** Author edits are ordinary file edits to
  the project directory ([03](03-architecture.md)); `qf validate` re-runs
  the same gates against them. The engine treats author edits and LLM
  proposals identically — one validation path, no privileged writer.
- **Steering** — each stage accepts author guidance notes (free text
  attached to the stage config) that are injected into its prompts:
  "keep the cartographer morally gray", "no more than one death".
- **Targeted re-runs** — `qf rerun seed --keep triage` style partial
  re-execution: keep accepted sub-artifacts, regenerate the rest.

The intended rhythm: churn cheaply in DREAM/BRAINSTORM, review SEED's
triage carefully (it decides the whole story), skim GROW's report (it is
mostly structural), spot-check POLISH's choice labels and feasibility
calls, and read prose per taste in FILL.

## 4. Departures from the original pipeline

- **Stage names and order are kept** — the DREAM→SHIP metaphor is good
  and battle-tested.
- **Sharper GROW/POLISH boundary**: GROW ends at the frozen beat DAG (+
  flags/overlays); *all* passage-layer work lives in POLISH. (The
  original drifted: its GROW created passages, routing, and several
  annotation phases that its own ontology doc later reassigned. NG adopts
  the ontology doc's boundary from day one.)
- **A uniform stage loop** (context → propose → validate → repair → apply
  → gate) replaces per-stage bespoke orchestration; stages differ only in
  schemas, prompts, and gates.
- **Numbered invariants wired to named gates** — every gate check cites
  the invariant it enforces, so failures are self-explaining and the test
  suite mirrors the gate list.
- **Author steering notes and partial re-runs are first-class**, not
  ad-hoc.
