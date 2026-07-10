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
  snapshot. Between checkpoints, each accepted pass's proposal is
  journaled to an **in-flight ledger** (`inflight/<stage>/`, mini-ADR
  A16). The ledger is *not* a checkpoint — no gate has passed, no
  snapshot exists, and no stage artifacts (prose files, graph YAML)
  reach the working tree. It exists so an interrupted stage resumes
  without re-buying completed passes, and it is consumed and cleared
  at the stage's gate-passing checkpoint.

### Craft context (M6)

Stages can be grounded in a craft corpus (design doc [05 §M6](05-roadmap.md))
without changing the loop above: a **research pass** runs at the stage
head, in the uniform loop like any other pass (`skip_if` no corpus is
configured — corpus-less projects, CI, and the golden story run
unchanged, to the byte). It emits *queries* — a typed proposal, judged
like any other — and the engine retrieves inside the pass's apply, so
kept-pass replay and ledger resume re-run retrieval deterministically.
Two query kinds feed one search: **standing queries** the engine
builds deterministically (from the vision's open-vocabulary
genre/subgenre/tone/themes) and **librarian queries** the research
pass emits for this story's specific needs; the prompt shows the
standing half so the librarian asks only for what's missing. At
DREAM's head no vision exists yet, so DREAM's research runs on the
premise alone and standing queries start at BRAINSTORM. Both kinds go
through hybrid search over the configured corpus, and the top-k
digests are persisted as a checkpointed, author-editable artifact
(`research/<stage>.md`). The stage's later passes read the artifact,
never the search index — so reruns and resumes replay retrieval
byte-for-byte, and "review = edit + revalidate" extends to what the
pipeline read before writing.

Author edits keep their meaning across reruns (mini-ADR A17): the
research pass *skips itself* when the stage's digest is **fresh** —
its recorded corpus fingerprint and story inputs (the standing
queries, or a premise hash where none existed: DREAM's research is
premise-grounded) match current values — and `rerun` preserves the
target stage's own digest through the rewind (the predecessor
snapshot never contains it; editing it is a reason to rerun, like
vision.yaml). A corpus, vision, or premise edit makes the digest
stale and re-retrieves; deleting `research/<stage>.md` forces
re-retrieval by hand.

The rule that keeps this safe: **corpus material may widen or ground,
never bind.** Injected digests carry an explicit advisory framing
(the shared `_craft.j2` block) and cannot override invariants or
stage contracts. Style exemplars appear at the voice pass as a
*contrasting spread* (a map of the possibility space, never a
nearest-match target), fade from write contexts once neighboring
prose exists (the window is the true style anchor), and never enter
review prompts — review judges against the Voice record alone, or
exemplar-conformance becomes a new taste-laundering channel. The
feasibility audit (POLISH) is excluded for the same reason — it is
review-shaped — as are the mechanical picks (SEED's order choice,
DRESS's codewords), which have no judgment for craft notes to widen.

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
| Gate G1 | Budgets met — per-role dilemma counts at least the branched budget, surplus within the locked allowance (B1); I1, I2; every entity anchors ≥1 dilemma *or* is flagged for triage; ≥2 dilemmas share an entity |

The LLM generates generously — more dilemmas and cast than will survive
as player choices — because SEED triages down and it is far cheaper to
cut than to weave in a missing character later (the cast is effectively
locked here). The overgeneration is structural: the prompt asks for the
branched budget *plus* the scope's locked allowance, and triage locks
the surplus into single-answer storylines (01 §4) rather than cutting
it. The shared-entity check exists because dilemmas that share no
entities produce parallel novels, not a woven story.

Deterministic: ID assignment, namespace enforcement, anchoring-graph
analysis (which entities are load-bearing).

### SEED — commitments and scaffolds

| | |
|---|---|
| In | Vision + full BRAINSTORM output |
| Out | Triage dispositions (branched / locked, 01 §4); Paths (+ Consequences) per explored answer; per-path beat scaffolds with temporal hints and flexibility annotations; dilemma ordering (`wraps`/`serial`/`concurrent`); convergence sketch |
| Gate G2 | I3 per explored path; branched role budget met exactly (e.g. `micro` = 1 hard + 1 soft) with locked dispositions within the allowance (B1); ordering relations acyclic and consistent; every surviving entity anchored; every cut justified |

The heaviest creative stage, run as three LLM passes with engine checks
between:

1. **Triage** — select the cohesive ensemble; cut brilliant-but-
   disconnected material. Give every dilemma a disposition: exactly the
   scope's role budget is **branched** (both answers get paths); the
   rest are **locked** — one answer gets a path, declared with a
   reason, and the other stays a permanent shadow (01 §4). The apply
   step enforces the disposition arithmetic repairably: branched counts
   per role equal the budget, every dilemma gets 1 or 2 paths, a
   single-path dilemma must be declared locked, and locked stays within
   the allowance.
2. **Scaffold** — per branched dilemma, the Y-shape: pre-commit chain
   (shared, dual `belongs_to`), one commit beat per path, post-commit
   chains; per locked dilemma, the chain: lead-in beats, one resolution
   beat (the `commits` impact — the story settles the question), and
   aftermath beats, all on the single path. Each path's beats must read
   as a complete story alone — GROW interleaves, it must never have to
   invent missing spine. SEED wires the *intra-dilemma* ordering edges
   itself (chain order is a fact of the scaffold, not an interleaving
   decision); after SEED the beat graph is a set of disconnected Y
   components and locked chains (plus a setup chain), and GROW's job is
   exclusively the *cross-dilemma* weave. Beats also get **flexibility
   annotations** ("the docks could be the market"; "the spy could be
   the informant") — invitations GROW uses to create intersections —
   and **temporal hints** ("before D1's commit") guiding interleave
   order. The apply step rejects (repairably, inside the pass)
   scaffolds that would only detonate at GROW's unrepairable gate: a
   hard path's chain tail must be an ending (the weave keeps the climax
   fork's endings and demotes the rest — I6), an ending anywhere else —
   including anywhere in a locked chain — is a contradiction, and a
   soft path's post-commit chain must carry the scope's minimum payoff
   beats (I7).
3. **Order & sketch** — declare pairwise dilemma relations; sketch where
   soft paths reconverge and with what residue weight.

### GROW — weave the DAG

| | |
|---|---|
| In | All SEED output |
| Out | The **beat DAG** (ordering edges; per-world beat instances where hard forks nest); intersection groups (consumed here); bridge beats; state flags derived from branched paths' consequences; entity overlays activated; convergence points fixed |
| Gate G3 | I4–I9; every computed arc complete (I6); flag derivation total (every consequence → ≥1 flag); budgets (beat count per arc within scope) |

The hardest stage, split deliberately:

- **Deterministic core:** candidate interleaving from temporal hints +
  ordering relations (topological constraints) — branched dilemmas
  contribute movable shared units plus one atomic resolve unit; a
  locked dilemma contributes every beat of its chain as a movable unit
  under chain constraints, so the storyline threads through the story
  (wraps/serial anchor it at its first beat and its resolution) —
  divergence wiring at each commit, convergence-point computation for
  soft dilemmas (per world), multi-hard realization (below), flag
  derivation (branched paths only: a locked outcome is a world fact on
  every arc, never a gateable flag — G3 rejects flags on locked paths),
  arc enumeration and validation. This is graph algorithm territory; a
  model adds nothing but risk.
- **LLM judgment calls:** choosing among valid interleavings for dramatic
  pacing (commits distributed, not clustered — and, with several hard
  dilemmas, which fork is the climax: candidates cover every viable
  nesting, wraps/serial between hards constrain it); proposing
  intersections from shared entities + flexibility annotations over
  beats every player sees — shared pre-commit beats and locked-chain
  beats alike (each accepted intersection resolves the scene's
  location/entities); contextualizing per-world beat instances (below);
  writing bridge beats where adjacent scenes share no entities or place.

Sequencing matters: intersections are proposed *before* the interleaving
is chosen, so member adjacency enters the candidate enumeration as a
constraint rather than being retrofitted. The LLM never emits an
ordering — it returns an index into the engine's candidate list.
Temporal hints and intersection groups are advisory: a hint or group
that would make the constraints unsatisfiable is dropped and reported
(the report names the group and whether it is impossible on its own or
conflicts with an earlier accepted group), never allowed to wedge the
weave — SEED wrote the hints, and the intersections LLM proposed the
groups, without seeing the whole ordering web. Dense relation webs
(several wraps/serial dilemmas, locked chains) can make most
cross-dilemma pairings cyclic; a stage must not be lost to enrichment.

**Multi-hard realization** (design doc 01 §5, mini-ADR A14): with more
than one hard dilemma the chosen order is walked tracking worlds — the
climax hard resolve is always the final unit; every unit placed after
the first hard fork is instantiated once per world (world-suffixed beat
ids, `belongs_to` copied, the template Y removed symmetrically so no
world owns the "original"), each further hard resolve multiplies the
worlds, and the earlier forks' chain tails stop being endings. A
*contextualize* pass then has the LLM rewrite each per-world instance's
summary for what is true in its world, and each de-ended tail to leave
the climax question open — structure is copied by the engine, words
never are. Intersection groups stay in the truly shared region (before
every hard fork): their point is one scene every player shares.

After G3 passes, **the topology freezes** (I9). This is the pipeline's
central commitment point.

### POLISH — compile to passages

| | |
|---|---|
| In | Frozen beat DAG, flags, overlays, residue weights |
| Out | Passage graph: passages (collapse), choice edges (labels, requires, grants), variant passages, residue arms, false branches, pacing bridges; character-arc metadata per entity |
| Gate G4 | I10–I13; every choice label distinct and non-spoiling; pacing report (no >N consecutive same-intensity passages); per world, every heavy-residue convergence has variants at every frontier beat and every light one a residue arm per path |

Two phases:

1. **Finalize the DAG** (additions only): reorder within linear runs for
   flow; insert bridge beats for pacing; insert residue arms per the
   convergence sketch — one flag-gated arm per path per world (the
   residue diamond: the story visibly remembers whichever side was
   chosen), an arm being one beat or a 2-beat chain where the memory
   deserves a scene (an identically gated chain collapses into a single
   passage); add false branches at cadence — a cosmetic
   diamond (arms of 1–2 beats, different textures of the same forward
   motion) roughly every 3–5 beats of a choice-less run, so a
   playthrough keeps a genuine-feeling decision every ~250–800 words
   (B6). The real choices are the dilemmas; cadence diamonds are safe
   dressing precisely because the structure guarantees the real ones.
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
| Gate G5 | Every passage has prose within its word budget (enforced at apply with 20% slack — models cannot hit exact windows; the exact range stays B5's advisory line); automated review (voice drift, continuity, beat-summary fidelity) clean or explicitly waived; ≤2 revision rounds per passage |

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
structure (Principle 4). Because that halt is expensive and the utility
reviewer has repeatedly laundered taste through the objective rules
(review-legibility lessons), the verdict that triggers it is not the
utility reviewer's alone: review rounds are anchored on the previous
rounds' issues (persistence is signal; all-new complaints each round
are usually taste), and a second failure escalates once to an
architect-tier arbitration whose strict verdict — uphold only outright
rule violations — is final. One extra frontier call on the rare
contested passage buys the halt its meaning.

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
- **Crash resume** — re-running an interrupted stage replays its
  in-flight passes through the same kept-pass machinery, no LLM calls.
  Unlike `--keep` (fail-loud: the author demanded that proposal), a
  stale in-flight entry degrades to a live run with a report note; a
  change to any stage input (vision, steering, graph/prose edits,
  model map) voids the whole ledger — review = edit + revalidate wins
  over resume. `qf rerun` always discards it. A gate *failure* retains
  the ledger, so re-running reproduces the failure quickly and for
  free until an input changes.

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
