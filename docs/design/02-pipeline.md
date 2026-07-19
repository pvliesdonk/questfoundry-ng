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
if issues: proposal = llm.repair(proposal, issues)     # ≤2 repair rounds (a pass may widen its own budget)
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
  Every error the model repairs against must be **actionable**, not a raw
  diagnostic: reason + subject + a recovery_action (the specific corrective
  — *pick a fresh id*, *use one of these values*), phrased as an
  instruction (heritage `semantic-conventions.md` §Error Messages). A raw
  exception fed back (`duplicate node id 'X'`) is a bug in the feedback,
  which a weak tier cannot recover from — so store rejections raise
  `GraphError` (a duplicate/missing reference), the runner catches it as
  repairable alongside `ApplyError`/`MutationError`, and no model-reachable
  graph write can escape as an uncaught crash. See `AGENTS.md` §"Prompt and
  error-message quality". **Feedback is batched**: an apply reports every
  violation it can see in ONE error, never the first found — with ≤2
  repair rounds, one-at-a-time feedback is a budget the model spends
  fixing exactly what was quoted while the next violation waits (learned
  twice on the texture-trial live run: the audit's scaffold-precedent
  batching, then FILL's echo check exhausting repairs one lift per
  round).
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
| In | Premise (free text), scope preset, optional words target, author preferences |
| Out | **Vision** record |
| Gate G0 | Vision complete; scope budgets resolved; `words_target` (when set) inside the scope's words band; content boundaries explicit |

The LLM expands the premise into genre/subgenre, tone, themes, audience,
content boundaries, and a POV hint; the engine binds the scope preset's
budgets — coupled to the author's `words_target` when one is set (the soft
dilemma budget scales so the scope earns its length or shrinks; 01 §2,
structural-depth W1). Premise, scope, and words target are the author's;
DREAM never invents them. Cheapest stage to iterate on — the author should churn here, not
later. Everything downstream that contradicts the vision gets cut, so this
is where taste is captured.

### BRAINSTORM — cast and dilemmas

| | |
|---|---|
| In | Vision |
| Out | Entities (cast), Dilemmas with two Answers each, `anchored_to` edges |
| Gate G1 | Budgets met — per-role dilemma counts at least the branched budget (the words-target-coupled budget, 01 §2), surplus within the locked + reserve allowances (B1); I1, I2; every entity anchors ≥1 dilemma *or* is flagged for triage; ≥2 dilemmas share an entity |

The LLM generates generously — more dilemmas and cast than will survive
as player choices — because SEED triages down and it is far cheaper to
cut than to weave in a missing character later (the cast is effectively
locked here). The overgeneration is structural: the prompt asks for the
branched budget *plus* the scope's locked allowance *plus* its reserve
allowance, and triage locks part of the surplus into single-answer
storylines and reserves the rest as unwoven texture feedstock (01 §4,
structural-depth W2) rather than cutting it. The shared-entity check exists because dilemmas that share no
entities produce parallel novels, not a woven story.

Deterministic: ID assignment, namespace enforcement, anchoring-graph
analysis (which entities are load-bearing).

### SEED — commitments and scaffolds

| | |
|---|---|
| In | Vision + full BRAINSTORM output |
| Out | Triage dispositions (branched / locked / reserve, 01 §4); Paths (+ Consequences) per explored answer; per-path beat scaffolds with temporal hints and flexibility annotations; dilemma ordering (`wraps`/`serial`/`concurrent`, woven dilemmas only); convergence sketch |
| Gate G2 | I3 per explored path; branched role budget met exactly (e.g. `micro` = 1 hard + 1 soft; the words-target-coupled counts when `words_target` is set, 01 §2) with locked and reserved dispositions within their allowances (B1, a reserved dilemma carries no path); ordering relations acyclic and consistent; every surviving entity anchored (reserved dilemmas exempt, I2); every cut justified |

The heaviest creative stage, run as three LLM passes with engine checks
between:

1. **Triage** — select the cohesive ensemble; cut brilliant-but-
   disconnected material. Give every dilemma a disposition: exactly the
   budget's role counts are **branched** (both answers get paths); the
   rest are **locked** — one answer gets a path, declared with a
   reason, the other a permanent shadow — or **reserved**: no path,
   kept as unwoven texture feedstock POLISH finalize grafts from
   (01 §4, structural-depth W2). The apply step enforces the
   disposition arithmetic repairably: branched counts per role equal
   the budget, every non-reserved dilemma gets 1 or 2 paths, a
   single-path dilemma must be declared locked, a reserved dilemma may
   carry no path, and locked/reserved each stay within their allowance.
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
   including anywhere in a locked chain — is a contradiction, a
   soft path's post-commit chain must carry the scope's minimum payoff
   beats (I7), and every chain's depth must sit inside the scope's
   `ScaffoldShape` bands (01 §2 — depth is scope data since M8, not a
   universal prompt literal), with all violations batched into one
   repairable error.
3. **Order & sketch** — declare pairwise dilemma relations; sketch where
   soft paths reconverge and with what residue weight.

### GROW — weave the DAG

| | |
|---|---|
| In | All SEED output |
| Out | The **beat DAG** (ordering edges; per-world beat instances where hard forks nest); intersection groups (consumed here); bridge beats; state flags derived from branched paths' consequences; entity overlays activated; convergence points fixed; each beat's `scene_type` (prose-intensity), `narration_scope` (POV/coda register), and `viewpoint`/`interlude` (whose head narrates it; headless for `wide` codas) — the annotations FILL reads, set pre-freeze (01 §Beat annotations) |
| Gate G3 | I4–I9; every computed arc complete (I6); flag derivation total (every consequence → ≥1 flag); every set beat `viewpoint` resolves to a retained character entity; budgets (beat count per arc within scope); **B9** (advisory) bridge share ≤ 25% — the stretching tripwire (01 §2): engine-computed but not in-pass repairable (bridges must cover every gap, I6), so the fix is upstream material, never a count a pass can hit; re-checked at G4 after POLISH's pacing bridges |

The hardest stage, split deliberately:

- **Deterministic core:** candidate interleaving from temporal hints +
  ordering relations (topological constraints) — enumeration switches to
  fair-split (prefix-diverse) when plain lexicographic order exhausts the
  candidate cap inside one subtree, so deep stories never choose among
  near-identical orders (M8) — branched dilemmas
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
  resolving the prose POV scheme into ids (the *scheme* pass, utility
  role, after contextualize: `vision.pov_hint` → `pov_head` marks on the
  followed characters and at most one `interlude_carrier` — the declared
  register's voice, roster membership not required; marks are reset per
  run, `docs/plans/pov-sequences.md`); annotating every beat with its
  `scene_type` and `narration_scope` **and assigning each *sequence* one
  viewpoint head** (the *annotate* pass, after scheme and before the
  freeze: the engine computes the sequences — maximal choice-free linear
  runs, `grow_sequences` — and renders them with their roster-candidate
  presence; the model returns per-beat scene/scope/interlude plus one
  head per sequence, splitting a sequence only with a stated
  dramatic-center justification and marking a `""`-headed segment as a
  wide cutaway whose beats must be wide; the engine expands sequence
  heads to the per-beat `viewpoint`, interlude beats taking the declared
  carrier — 01 §Beat annotations; scene/scope advisory with a purpose
  fallback, every head enum-pinned to the roster (pre-roster graphs: the
  retained character ids), checked referentially at G3, against the
  scheme at I17, and for sequence health at B11, with unannotated
  later-added beats as wildcards); writing bridge beats where adjacent
  scenes share no entities or place.

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
| Out | Passage graph: passages (collapse), choice edges (labels, requires, grants), variant passages, residue arms, cosmetic forks (sidetracks, diamonds, small two-worlds, texture worlds — one mechanism, I15) with one minted cosmetic keyword per non-empty rendering; character-arc metadata per entity |
| Gate G4 | I10–I16 (I15: non-empty-segment renderings mirror their segment — content and boundary parity, composition-closed under nesting and decoration, structural choice-topology parity deliberately retired for per-walk budget parity; I16: a cosmetic keyword gates only cosmetic-fork renderings; 01 §6, §8); every choice label distinct and non-spoiling; the **B10 choice-stretch report** (advisory; the author metric, 2026-07-16): per arc view, no more than `choice_stretch_max` consecutive passages may offer no choice — DAG-wide, so the desert inside an unwalked rendering counts, and conservatively, so a keyword-gated choice does not break a stretch for readers without the key; the **B8 pacing report** (advisory): along each playthrough, a run of more than N same-`scene_type` **beats** warns — beat-level, not passage-level, because `passage_intensity` is a max and passages read scene-heavy (01 §Beat annotations); per world, every heavy-residue convergence has variants at every frontier beat and every light one a residue arm per path; character-arc references resolve (a dangling pivot beat or path fails loud at the gate, not inside FILL) |

Two phases:

1. **Finalize the DAG** (additions only) — **the loop**
   (cosmetic-forks A24, `docs/plans/cosmetic-forks.md` §3/§6). **Round 0
   (`finalize:0`) is residue**: insert residue arms per the convergence
   sketch — one flag-gated arm per path per world (the residue diamond:
   the story visibly remembers whichever side was chosen), an arm being
   one beat, a 2-beat chain where the memory deserves a scene (an
   identically gated chain collapses into a single passage), or a
   tensored arm — two same-gate branches, each its own gated passage
   (M8; either branch satisfies G4's coverage). Obligations land before
   decoration, so the fork rounds always plan on the rerouted graph.
   **Budget rounds (`finalize:<n>`, n ≥ 1) are engine-only planners**:
   each recomputes the qualifying sites (segment tiers and seam edges,
   `fork_segments`) and both budgets — the per-walk B6 projection and the
   story-words headroom (`words_target` when set, the band top otherwise;
   every site's marginal story words must fit) — on the *current* graph,
   assigns shape and arm count per admitted site (sidetrack / diamond-2 /
   diamond-3 / two-worlds; the scope's `cadence_arm_cycle`, offset by the
   keywords already minted so resume reproduces the assignment; a shape
   that no longer fits the headroom degrades to a sidetrack), and expands
   into one small `fork:<n>:<k>` wording pass per site. The model words
   only the renderings — one premise per non-empty rendering, rendering
   0's trunk premise included (renderings are peers), fresh beats grafted
   from the triage reserve where it fits — while every count and shape is
   engine-mandated at the schema. **At apply the engine splices** through
   the one cosmetic-fork primitive, persists the premises (rendering 0's
   onto the frozen trunk beats — a legal presentation addition, the
   freeze is topological), and **mints one cosmetic keyword per
   non-empty rendering** (`flag:cw-*`, granted on the rendering's head
   beat, description = the premise). A round's edge-scale sites are
   offered up to 8 holdable, unconsumed keywords minted in earlier
   rounds (grants strictly upstream), and a pass MAY attach one
   keyword-gated extra rendering consuming one — acknowledges, never
   rewards; one consumer per keyword; I16 holds the locality. Admission
   runs in three phases (author direction, 2026-07-16): **depth first**
   (scene then small segments, words-gated with probe-measured exact
   pricing), then **mandatory stretch breaks** — along every arc view at
   most `choice_stretch_max` consecutive passages may offer no choice,
   and the break sites that enforce it are choice machinery, EXEMPT from
   the words ceiling (interruption outranks length until the density
   calibration lands; a stretch with no free seam is left to B10) — then
   **B6 fine-tuning** on the remaining seams, words-gated. The loop
   terminates when a round admits nothing.
   Because a segment inside a rendering is just a segment a later round
   may fork, recursion falls out — worlds nest, diamonds land inside
   arms — and renderings keep budget parity, not structural parity:
   per-walk B6 owns choice fairness (ratified decision 1). The real
   choices are the dilemmas; cosmetic sites are safe dressing precisely
   because the structure guarantees the real ones.
2. **Build the passage layer:** collapse maximal linear runs into
   passages (boundaries at forks/joins; runs split at the scope's
   `passage_beats_max` — the choice-free cutter, 01 §6 — **and at every
   viewpoint switch**: one head per passage, I14, with unannotated and
   `wide` beats riding as wildcards; the raw choice-topology runs the fork
   planner reads stay uncut — a head-switch chunks prose, not choices);
   merge intersection-adjacent
   beats into single scenes where narratable; run the **prose-feasibility
   audit** on every passage — ambiguity is presented and capped in
   *dilemma states* (a dilemma's per-path flags are one binary
   uncertainty, I12), and for each state the model decides *irrelevant
   here* (annotate "don't address" — all of the state's flags), keeps it
   for poly-state prose (≤3 states), or **splits** the passage on the
   dilemma (`split_on`, at most 2): the engine re-presents the moment as
   flag-gated variants whose arrivals hold a known side — the honest
   resolution when a state matters, enforced repairably at the apply
   with every violation batched into one error; wire choices with
   labels/gates/grants; synthesize
   character-arc metadata ("begins X, pivots at beat Y, ends Z per
   path") for FILL's benefit.

The engine computes collapse boundaries and gate satisfiability; the LLM
writes labels, decides feasibility judgments, and drafts arc metadata.

The passage layer is **not** emitted in one call. The finalize loop's
*terminal round* expands (runner `PassSpec.expand`) into independent,
minimal-context passes — the collapse groups are known only after every
residue arm and cosmetic fork has landed — one **`summary:<group>`** per
collapse group (context: that group's own beats, its ending flag, and
for a heavy-residue frontier group the world-states its variants must
cover) and one **`labels:<group>`** per source group with outgoing
choices (context: the source group plus each destination's summary and
the engine-known gate/grant of each edge). A single greedy call over the
whole passage layer + every edge overran the model's context window at
medium scope (the `AdapterError` a medium-scale run hit) while giving no
per-item benefit — a passage summary is derived from that group's own
beats alone. Call count is not a cost the pipeline optimizes against
(FILL already runs ~150 write calls per medium story); right-sized
independent calls are strictly better for weak tiers (mini-ADR A21).
Because passage creation (`summary:<group>`) and choice wiring
(`labels:<group>`) are now separate passes, each variant's gate is
persisted on `Passage.variant_flag` at creation and read back at wiring
(01 §6). Coverage stays gate-guaranteed: I11 (every beat in exactly one
passage) holds across the whole graph at G4, and the computed pass list
is exhaustive over the collapse groups.

### FILL — prose

| | |
|---|---|
| In | Passage graph + everything (entities w/ overlays, flags, arc metadata, shadows, vision) |
| Out | **Voice** record; prose per passage (and per variant); universal entity micro-details (note register, length-capped); a rolling story-so-far note per passage (utility-summarized) |
| Gate G5 | Every passage has prose within its word budget — per-passage since M8, keyed off the passage's aggregate `scene_type` (01 §Beat annotations): a `scene` passage takes the full band, a `sequel` the middle band, a `micro_beat` the short band (residue/false-branch arms fall back to `micro_beat`, so texture passages keep exactly their prior short band), and an ending gets headroom above all of them — enforced as a **graded review finding** (`word_budget`), not a hard apply gate: confidence scales with distance outside the band, so a near-miss with good prose and a real reason is a low-confidence finding the engine weighs rather than a forced rework, while a large miss blocks (author-directed 2026-07-12; models cannot hit exact windows and the review owns quality); a second mechanical finding, **`overwriting`** (coined hyphen-compound density — warn ~8/1k, fail ~15/1k, graded by distance), rides beside it, the one modulation red flag that survived a genre-diverse study with zero false positives (fragmentation is deliberately not gated — it false-positives on good noir — the modulation-variance half being the B8 pacing report); B6 (advisory) measures words per choice along a deterministic playthrough walk, not an arc view (a walk traverses one diamond arm — the arc-view sum counted words no single reader sees); B7 (advisory) checks total prose words against the scope's `words_total`; automated review (voice drift, continuity, beat-summary fidelity) clean or explicitly waived; write passes carry a repair budget of 4 rounds (a write faces several independent checks — echoes, review findings, grounding — that surface serially; the pipeline-default 2 halted a live run whose loop was converging, every shown finding fixed, texture-trial 2026-07-15) |

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

Per-passage context is rich by design: voice, **this passage's viewpoint
head** (derived from its beats, never stored — the write and review prompts
enforce *no other minds* against that head while `Voice.pov` stays the book's
scheme; a headless passage degrades to the book-wide rule, and an `interlude`
passage is written and reviewed against the Voice's interlude register
instead of the book-default pov/tense — 01 §Beat annotations,
`docs/plans/rotating-pov-build.md`), beat summaries each tagged
with their `scene_type` and `narration_scope` (the passage's aggregate
intensity sets its word band; the per-beat `scene_type` tells the writer where
the prose may rise and where it stays plain — style belongs to the story, not
the paragraph — and the per-beat `narration_scope` tells it which beats stay
inside the POV and which are a `wide` coda it may narrate beyond the viewpoint
character's horizon, so register modulates within a passage without a split;
the POV rule separates *no other minds* from psychic-distance widening, and the
reviewer keys that rule to scope so a wide coda is not a departure), the
passage's **texture-world premise** when its beats carry one
(structural-depth W4, the context lever: the writer grounds the parallel
world it is in, named the way world truths are named, instead of
inferring it from summaries alone), full
entity state (base + active overlays), a sliding window of preceding prose,
character-arc position (from POLISH's arc metadata: the aspect in play
now, the turn this scene carries, where the entity is heading),
the story so far (each already-written passage along one deterministic
route contributes a utility-summarized note — deep continuity at note
prices, where a full prose look-back would blow up tokens), active
flags, the *shadows* (what didn't happen — so prose can carry the weight
of it), and convergence lookahead. Every block states its role in the
prompt: facts are constraints, not choreography; the window is
continuity, not a style template (prose-quality effort — live run 8's
verbatim-recurrence findings). The apply enforces the deterministic
floor: an **echo check** rejects prose that restates a rendered entity
fact or lifts a long verbatim run from adjacent prose. The **word budget**
is no longer an apply gate — it is a graded `word_budget` review finding
(above): a near-miss is a low-confidence finding the engine weighs, a large
miss blocks, so good-but-terse prose is not force-reworked into padding. A
**micro-detail**
is optional enrichment — at most one per passage, framed as the exception
so the writer never invents a re-observation to fill the slot. It may add
a new universal fact or *update* a listed one (re-using its key); the only
apply check is the note-form length cap, and an over-long value is dropped,
never a repair that blocks the required prose. Whether a detail genuinely
adds and does not contradict an established fact is the reviewer's
`micro_detail` rule (below), not a blunt guard. The passage's outgoing
**choice labels are a planting contract, and the writer may re-ground
them** (author finding, 2026-07-14 — labels minted at POLISH from beat
summaries read as connective tissue to the *next* passage, "open the
door" with no door on the page — and author request, in-session same
day: "can we have the writer *also* rewrite the choice labels?"): the
write prompt lists the choices as a numbered menu (label + a
destination-summary hint) and requires every concrete referent a label
names to exist in this passage's prose — and the writer may **rewrite any
label inline** (`label_rewrites`, numbered so a rework round addresses the
same choice after a rename; destination, gate, and grants stay fixed;
distinctness across the page's labels is enforced at apply, the rewrite
lands through `relabel_choice` before the review runs). The reviewer's
`choice_grounding` rule then judges the labels the player will actually
read: quote the prose that plants each referent, or fail with the absent
referent named — the corrective is to the prose or, now, a rewrite that
names what the prose shows.

A passage failing review twice is a structural bug: it goes back to
POLISH (or GROW), never to a third rewrite. Prose cannot rescue a broken
structure (Principle 4). Because that halt is expensive and the utility
reviewer has repeatedly laundered taste through the objective rules
(review-legibility lessons), the review runs a **structured finding
contract** shared by every review pass (`pipeline/review.py`): the
reviewer states a top-level `verdict` (`approved` / `needs_work`) plus
findings, each carrying a `rule` (an enum of that review's clause set), an
`assessment` (`fail` = objective defect, `warn` = concern/taste), a
`confidence`, the offending `quote`, a `reason`, and a `recovery_action`.
An `approved` verdict auto-accepts; a `needs_work` verdict hands the
decision to the **engine**, which makes one mechanical call — rework iff
some finding is a `fail` the reviewer is at least moderately sure of, else
accept anyway. The reviewer can thus affirm a clean read but cannot *halt*
the stage on taste or a low-confidence guess: a block needs `needs_work`
and a confident `fail`. (The asymmetry is deliberate — a wrong `approved`
only passes marginal prose, which the deterministic echo/word-budget
checks still guard; a wrong halt was the failure this contract removed.)
The **producer** receives every finding on a rework (full fidelity,
labeled) and decides how to act: a `fail` is blocking, a `warn` or
low-confidence finding is weighed, not mandated. Review rounds are still
anchored on the previous rounds' findings (persistence is signal; all-new
complaints each round are usually taste), and a second rework escalates
once to an architect-tier arbitration emitting the same schema — a
genuinely stronger judge on a mixed model map. One extra frontier call on
the rare contested passage buys the halt its meaning.

Two writer-side levers make the rework *converge* rather than re-roll (the
LLM adapter is stateless — each attempt is a fresh call with no memory of
its prior draft, so a naive rework re-derives a losing draft under
multi-finding load). On a rework the write prompt (1) shows the writer its
**rejected prior draft** ("revise it, don't repeat it" — stashed at apply
time, so it covers a mechanical apply rejection like a word-budget miss as
well as a review rejection), and (2) requires a per-finding **`revision_notes`**
entry — the writer must state, for each
finding, the exact change it made; the reviewer then verifies each claim
against the prose (a claimed fix the prose doesn't deliver is itself a
defect). `revision_notes` are reviewer-facing only — never applied, so
replay stays deterministic. (Validated on `gpt-oss:120b`: the per-finding
account lifts a stuck beat-fidelity fix from 2/4 to 4/4 under the load that
halted a live run.)

**When the rework loop still fails, do not add more rules**
(author-directed, 2026-07-15): first check the existing *write* prompt
for clarity, then the existing *review* prompt for over-strictness — the
urge to fix a failing loop by adding a fence, a self-check step, or an
engine mechanism is micromanagement, and both were built and reverted on
a texture-trial halt before the author named the real defect. There, the
reviewer was too strict: it re-rejected hedged inference as interiority
and demanded an explicit possessive for a referent the context had already
attributed (one masked character on stage; "the mask" is theirs). Each
pedantic rejection forces another rewrite, and rewrites churn new nits —
the loop's non-convergence was manufactured by the review. The review
rules therefore lean permissive at the margins: context-supplied
attribution grounds a label's referent, and an explicit observed
inference ("as if weighing") is the narrator's own mind.

### DRESS — art and codex

| | |
|---|---|
| In | Finished prose, entities, vision, voice |
| Out | Art direction; entity visual profiles; illustration briefs (prioritized) per key passage; a cover brief (the front-page image); illustrations (via pluggable image backend, optional); codex entries; print codewords on projected flags |
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
A fifth pass, *cover*, writes the prompt for the book's front-page
illustration — atmospheric and spoiler-safe (setting, mood, genre
iconography, an emblematic object; no plot or ending reveals, since the
cover is seen before reading), built from the established art direction so
it matches the interior. It runs last (it depends only on *direction*) and
is optional to render; `qf illustrate` draws it first to
`art/images/cover.png`, and the exports lay the title over it (04 §2, §4).

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
