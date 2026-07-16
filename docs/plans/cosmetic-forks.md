# Cosmetic forks — one mechanism, renderings as peers, residue keywords (milestone plan)

> Status: **DESIGNED, not started** (2026-07-15). The unifying insight is the
> **author's, directed 2026-07-15**: "diamonds, sidetracks and texture worlds
> are all intrinsically the exact same mechanism"; "one arm should not have a
> different treatment than the other" (the texture trunk is currently
> privileged); and recursion "basically means running the same phase several
> times in a loop". It absorbs two earlier author-ratified threads from the
> same day: the keyword-per-fake-branch loop (residue as memory) and the
> "even fake branching needs residue" rule (already durable in 01 §6). The
> *mechanical designs* below — the segment/rendering model, the grant model,
> the iteration mechanics — are **this agent's**, derived from those
> directions against the shipped W3 code; the author ratified the whole shape
> ("I'm happy with this shape", 2026-07-15), explicitly including the three
> flagged leans recorded under "Ratified decisions". Frontier-authored
> (freeze/arc/I15 seams, grant semantics).

## Ratified decisions (author, 2026-07-15, via the shape ratification)

1. **Budget parity replaces structural parity.** Renderings no longer keep
   the same choice topology by twinning (mirrored cadence diamonds); each
   rendering grows its own forks until *its walks* hit the B6 band. Equality
   is guaranteed in the outcome measure, not by structural copying. This
   amends I15 and retires the mirrored-cadence machinery (A23's third
   column) once the loop exists.
2. **Rendering 0's premise may sharpen, not only describe.** The trunk
   segment's declared premise must be grounded in what its beats already
   carry, but where the weave left the backdrop vague the premise may
   honestly sharpen it (consequence-free, same contract as any arm).
3. **The empty rendering stays unmarked.** Walking past a sidetrack mints no
   keyword and needs no premise — nothing happened. This is the one
   asymmetry left standing, and it is a recorded choice, not an accident.

## The problem (one paragraph)

Three same-day findings converged. Reading letter-and-frontier: a sidetrack's
exit label re-offers the trunk label the reader just passed over — root-caused
to independent label calls converging on a shared destination summary, with
the durable rule ("even fake branching needs residue") landed in 01 §6. The
keyword escalation: every fake branch should leave a testable mark later
structures may consume. And the unification: the shipped shapes — diamond,
sidetrack, texture world — differ only in parameters, yet live as three
mechanisms with three splice functions, two content models, and a trunk that
is treated as "the original" while its parallel arm carries all the rendering
identity (`texture_premise` on arm beats only). The asymmetry is not
cosmetic: FILL grounds only the arm's prose in its premise (W4 works for half
the readers), the fork's entry label cannot name what the trunk-side choice
means, and any minting rule phrased as "on added arms" inherits the bias.

## 1. The unified model

**A cosmetic fork is k ≥ 2 renderings of one trunk segment.** Take a segment
of the trunk between `before` and `after` (length 0 to cap−1 beats within a
linear run, or cap-aligned stretches at run scale); offer k parallel
renderings; the reader chooses one; all rejoin at `after`. A **rendering** is
a beat chain that is *empty*, *the segment's own beats*, or *fresh*:

| Today's shape | Segment | Renderings |
|---|---|---|
| Sidetrack | empty (an edge) | {empty ("walk on"), fresh chain} |
| Diamond | empty (an edge) | {fresh, fresh} |
| Small two-worlds (new) | 1 to cap−1 beats | {the segment itself, fresh} |
| Texture world | ≥ cap beats (cap-aligned) | {the segment itself, fresh} |

The evidence this is one mechanism is already in the code:
`insert_texture_world` makes the trunk stretch "conditionally traversed like
a diamond arm" — a texture world *is* a diamond whose second arm happens to
be pre-existing beats. The small two-worlds row is not a new mechanism
either; it is admission of shorter segments into the same machinery.

**The content contract is a function of segment length, not shape.** A
non-empty segment means every rendering re-expresses the *same events*
(I15's mirror rule: one beat per segment beat, in order, effective
annotations copied); an empty segment has no events, so each rendering
invents a breath of texture (the current diamond/sidetrack arm register).

**Every rendering carries a premise** — its value on the declared
consequence-free axis — including rendering 0 (the segment itself) and
excluding only the empty rendering. The premise is what FILL grounds prose
in (W4, now for every reader), what entry labels name, and what the minted
keyword remembers.

**Every non-empty rendering mints a cosmetic keyword** (§4). The choice
leaves a mark; the empty rendering leaves none (ratified decision 3).

**What does NOT unify** (state the fence or the concept over-extends):

- **Residue arms** are the same *shape* (parallel chains rejoining) but the
  reader does not choose them — the flag routes them. They are obligation
  machinery (a promise the story must keep: I12, arc completion, GROW-frozen
  gates), one per path, gated. Chosen-and-consequence-free unifies; routed
  or obligated does not.
- **Dilemma forks** carry consequence. Obviously outside; said once.

The obligation boundary from the keyword analysis is the general rule: a
dilemma's flag is a *promise* (downstream must honor); a keyword is
*permission* (downstream may use; prose that ignores it is correct). Anything
downstream *depends* on is a dilemma in costume and belongs in GROW.

## 2. Renderings are peers (the symmetry rework)

The current differential treatment of trunk vs arm, triaged:

- **Harmful, fixed here:** `texture_premise` on arm beats only. Fix: the
  fork proposal declares one premise per rendering, **including rendering
  0**, constrained to extract-or-sharpen what the segment's beats already
  carry (ratified decision 2). FILL grounds both worlds; the fork's entry
  labels can name both axis values; minting is symmetric. The asymmetry is
  enforced in the model today: `Beat._class_consistency` rejects a
  `texture_premise` on any beat whose `purpose != TEXTURE_WORLD`
  (`models/structure.py`), and rendering 0's beats are GROW beats — PR-2
  relaxes that guard (premise legal on any beat, still engine-set only)
  along with the splice change (flagged by PR #84's automated review).
- **Harmful, fixed here:** minting on "added arms" only (never shipped —
  caught at design time). Fix: mint per non-empty rendering.
- **Harmless, kept:** `mirrors` pointing rendering→segment is provenance
  (like A14's world suffixes), not privilege; `created_by` likewise;
  `entities` differing per rendering is the point (different backdrop);
  segment summaries stay freeze-settled — **premise annotation is an
  addition, not a summary rewrite**, so A23's rejection of "re-texturing the
  trunk" stands in its narrow sense while its framing (trunk as original)
  is superseded.

**Freeze clarification (doc change, rides PR-2 — the PR that first
annotates a frozen beat):** the freeze (I9, iron rule 4) is
*topological* — no beat deleted, no dilemma fork or convergence moved.
Presentation-layer annotations added to frozen beats by POLISH through the
mutation layer (`texture_premise` on rendering 0, `grants_flags` on a
rendering head) are legal additions. Without this sentence in 01, the first
future session to see POLISH writing a field onto a GROW beat will read it
as a freeze violation.

## 3. The loop (iterative finalize)

Finalize stops being one giant proposal and becomes a **fixed-point
iteration of the one splice primitive**. Each round, on the *current* graph:

1. The engine computes qualifying segments and the remaining budget —
   words headroom (`words_target` or band top) and the B6 projection —
   and **assigns shape and arm count per site** (sidetrack / diamond-2 /
   diamond-3 / two-worlds over segment S), mandatory at apply. Shape is a
   pacing knob and passes the three-part mandatory test (engine-computed,
   exact, in-pass repairable); model discretion over shape produced the
   all-sidetracks trial exactly as discretion over counts produced the flat
   book. The mix ratio lives in the scope preset (open question 1).
2. One small proposal per site (or per run) words the renderings: premises
   (one per non-empty rendering, including rendering 0 where the segment is
   non-empty) and fresh-rendering beats. Small calls, pinned choices — the
   A21 decomposition, and the fix STATUS already predicts for finalize
   exhaustion at ~60 sites.
3. The engine splices, mints keywords (§4), and re-projects. Loop while
   budget remains; terminate on B6-target-reached, words exhausted, or the
   per-round admission cap.

**Consequences, each a simplification:**

- **Recursion falls out.** A segment inside a rendering is just a segment
  the next round may fork (drop the `purpose == TEXTURE_WORLD` exclusion in
  `qualifies()`). `mirrors` chains arise naturally; I15 relaxes "twin is not
  itself an arm beat" to "mirror chains are acyclic and ground out in trunk
  beats", and the edge-projection rule composes transitively. Worlds within
  worlds, diamonds inside arms — no mirror-of-mirror machinery is ever
  written. FILL's premise lever becomes a premise *stack* (outer + inner),
  rendered the way world truths already stack after hard forks.
- **The mirrored-cadence machinery retires** (ratified decision 1). Twinned
  diamonds (`insert_cadence_diamond`'s mirror-into-arms) and the
  probe-arm scratch sizing (`_texture_and_cadence`) exist only because the
  one-shot pass decides everything on the pre-fork graph. Under iteration, a
  run inside a rendering is just a run the next round budgets normally —
  different roads honestly grow different detours, and every walk still
  lands in the B6 band. I15 shrinks to content + shape rules; per-walk B6
  owns choice fairness.
- **Keyword consumption slots into the round structure**: round N's sites
  may consume keywords minted in rounds < N whose grant sits strictly
  upstream (§4) — the ledger ordering is iteration order, no topological
  sort inside a mega-proposal.

**Runner mechanics:** each round is a pass (`finalize:<n>`); the post-apply
expansion (`PassSpec.expand`, the A21 mechanism) schedules `finalize:<n+1>`
while budget remains. Determinism on ledger resume must be verified against
`runner.py` when built (same graph → same next-pass decision); the loop
decision is a pure function of the checkpointed graph, so this should hold
by construction. LLM cost is bounded by the shrinking budget; each round is
weak-tier-sized by design.

## 4. Residue keywords

### Grant model (the engine gap)

There is no cosmetic grant model today: `grant_beats()` returns `[]` for
`path=None` flags, so the first keyword-gated consumer fails I10 as "no arc
can satisfy". Choice edges cannot carry the primary grant — they do not
exist until the passages pass, and all flag reasoning is beat-layer. Fix,
parallel to how dilemma flags already work (commit beat grants; choice
wiring projects onto edges):

- `Beat.grants_flags: list[str]` (symmetric with `requires_flags`), set by
  the splice on each non-empty rendering's head beat — rendering 0's head
  included (a legal frozen-beat annotation, §2).
- `grant_beats()` returns granting heads for cosmetic flags; I10's ancestor
  walk is then already correct (rendering beats are DAG ancestors of
  everything past the rejoin, and "some history holds it" is exactly the
  optional-arm semantics). `choice_grants` projects onto the rendering's
  entry edges for the runtime; play engine and exports already honor edge
  grants.
- Reuse `FlagSource.COSMETIC` (its docstring is this feature); no new enum,
  no back-pointer. The flag's `description` is derived from the rendering's
  premise/head-beat summary at splice time — it is what later consumption
  prompts read.
- Known wrinkle to note in the PR: B6's walker derives `held` from
  grant-beats-in-view; structural beats sit in every view, so the walker
  over-holds keywords from detours the walk didn't take. Affects only which
  gated entries count as live decisions; fix or document when B6 is touched.

### Minting

Engine-deterministic at splice time: one keyword per non-empty rendering
(`flag:cw-<rendering-slug>`), never model-proposed. The empty rendering
mints nothing (ratified decision 3). Grants are free — storage is trivial,
`projected_flags` surfaces only *tested* flags to print, and I12 skips
cosmetic flags by construction. A medium run minting ~60–100 keywords is
expected and fine; consumption, not granting, is budgeted.

### The obligation boundary, made structural (invariant I16)

A rule a model must apply gets enforced, not trusted:

> **I16 (cosmetic-gate locality):** a cosmetic flag may be required only
> inside constructs that converge by construction — a beat gated on a
> cosmetic flag is itself a cosmetic-fork rendering beat (later: a cosmetic
> variant's gate, a DRESS print acknowledgment). Never a GROW beat, never a
> passage outside a cosmetic construct.

With I16, "downstream depends on a keyword" is impossible to *express* in
the graph. Prose-side: cosmetic flags never enter FILL's write context
except at a gated consumer, where the gate makes them certain-held — the
mechanical form of "may color, never must" (a shared "the whisper returns"
would assert state some readers lack). Check in `graph/validate.py` citing
01 §8, violating-construction test, per iron rule 6.

### Consumption

Ranked by machinery cost; v1 is form (1) only:

1. **Keyword-gated rendering** (an extra arm only holders see — the natural
   shape is a diamond's third arm, hence 3+ arms lands first): zero new
   runtime semantics. Gated choice menus already work in play engine, HTML,
   and print; I13 holds via the ungated siblings; I10 works once the grant
   model lands.
2. **Gated variant of a page** — deferred: current variant gates are
   mutually exclusive (path flags partition arrivals); holders/non-holders
   partitioning needs gate-precedence semantics ("most specific wins") in
   every runtime. Real machinery, no driver yet.
3. **Print codeword acknowledgment** ("If you noted PINE: …" as an inline
   conditional paragraph) — a DRESS/export device; the plumbing is eager
   (`projected_flags` already picks up tested cosmetic flags,
   `StateFlag.codeword` + DRESS naming exist) but the export form is new.
   Own PR, after a live run mints keywords.

**Consumption discipline — acknowledges, never rewards.** If keyword-gated
content is systematically richer, the detour stops being declinable without
loss and consequence sneaks back through the cosmetic door as *value*.
Concretely: a gated rendering gets the same size budget as any rendering;
**one consumer per keyword** in v1; **a keyword never gates a scene-scale
world**. Consumption sites pass the same words-budget admission as any
rendering (their words are printed for holders only, walked by holders
only).

## 5. Exit-label residue (ships first, standalone)

The live defect from letter-and-frontier, unchanged by the rework above and
worth shipping immediately. Two layers, plus a generalization the backlog
item missed:

1. **Root (finalize prompt):** a fresh rendering's beat summaries must state
   the mark the choice leaves — what taking this rendering changes in how
   the reader walks on — because the labels pass words labels from beats,
   and today's arm summaries describe the detour's content while the only
   other anchor (the destination summary) is identical across parallel
   calls; independent samples converge (the confirmed mechanism).
2. **Context (labels pass):** the engine knows which edges are cosmetic
   rejoins (source group contains fork-rendering beats). Order those label
   passes after their parallel trunk/sibling groups (a deterministic
   ordering tweak in `_polish_expand`), include the parallel label(s)
   already worded onto the same destination, and instruct: carry this
   rendering's residue; never re-offer that action.
3. **Generalize:** the bug is not sidetrack-specific — a diamond's sibling
   arms converge on each other the same way (same destination summary, two
   independent calls), and a texture arm's tail exit parallels the trunk
   tail's exit at world scale (`mirrors` pairs them exactly). The fix covers
   every set of parallel edges into a shared rejoin from one construct.

No validator: a label-similarity check is the pedantic reviewer that
manufactures non-convergence (AGENTS.md); the fix is context, not a fence.

## 6. The loop, specified (PR-5's build spec)

§3 gives the shape; this section pins the decisions a fresh session would
otherwise have to derive (doc-silent derivation is the failure mode
AGENTS.md warns about). Each ⭐ is a frontier seam.

- **Round 0 is residue, unchanged.** Residue arms are obligation machinery
  (§1's fence), not a budget round: `finalize:0` keeps today's semantics —
  one flag-gated arm per path per light convergence, the existing
  `ResidueSpec`/apply machinery, skipped when needs are empty. Obligations
  land before decoration, which also dissolves today's splice-order
  subtlety (texture → false branches → residue existed only because the
  one-shot cadence table was sized on a probe scratch): residue's rerouted
  frontier edges are already in place before any cosmetic round computes
  segments, and gated residue chains never qualify as segments
  (`qualifies()` rejects `requires_flags`).
- **Budget rounds** `finalize:<n>` (n ≥ 1): the engine recomputes
  qualifying segments and both budgets on the *current* graph — the same
  graph-pure functions as today (`texture_sites` generalized to the
  segment-length tiers of §1's table, `projected_walks` for the B6
  projection, the words-admission rule of `texture_plan`) — assigns shape
  and arm count per admitted site, and expands (A21 `PassSpec.expand`) into
  one pass per site with deterministic names (`fork:<n>:<k>`, sites ordered
  by segment-head beat id). ⭐ Admission per site: marginal projected story
  words must fit the headroom (`words_target` or band top), scene-scale
  segments (≥ cap beats) stay under the story-total `TEXTURE_WORLDS_MAX`;
  smaller shapes are uncapped by count — words-bounded only.
- **Termination**: a round admits no sites, the projected B6 mean reaches
  the target, or the words headroom is smaller than the smallest site's
  marginal cost. Each is checked before expansion, so the last round is an
  empty expansion, not a wasted proposal.
- **Per-site call contract**: the site (segment beats or the empty-segment
  edge), its assigned shape/arm count, the reserve feedstock, and up to
  **8** holdable, unconsumed keywords (grant strictly upstream of the
  site's `before`; engine-computed; 8 is a context-bloat guard, revisit on
  live evidence). The model words the premises (one per non-empty
  rendering, rendering 0's extract-or-sharpen) and fresh-rendering beats,
  and MAY attach one keyword-gated extra rendering consuming one offered
  keyword — consumption is always optional, never assigned.
- **Splice + mint at apply**: the engine splices, writes `grants_flags` on
  each non-empty rendering's head (rendering 0's head included — the
  frozen-beat annotation of §2), derives the flag description from the
  premise, marks a consumed keyword consumed (one consumer per keyword,
  ratified discipline §4), and the I16 check covers the gated rendering.
- **Gates and resume**: rounds are ordinary POLISH passes — G4 runs at
  stage end as today, the A16 ledger covers each pass, and resume
  determinism holds iff the next-round expansion is a pure function of the
  checkpointed graph (open question 4 — verify against `runner.py`).
- **What retires**: the probe-scratch sizing in `_texture_and_cadence`,
  the mirroring splice variants (`insert_cadence_diamond`/
  `insert_cadence_sidetrack`), and the one-shot `FinalizeProposal`'s
  false-branch/texture halves. **What stays**: `convergence_needs` and the
  residue apply path (round 0), `insert_texture_world`'s mirror-content
  splice for non-empty segments, I15's field and shape halves
  (restated composition-closed in PR-5, alongside the code that makes the
  restatement true).

## PR slicing

**Doc-truth rule for every slice** (settled 2026-07-15 after the PR-1 build
session flagged the collision; agent ruling applying iron rule 6 and the
AGENTS.md doc-truth contract, forwarded via the author): **01/02 carry
current-state truth only — a restatement of the model rides the PR whose
code makes it true, and an invariant's statement, check, and
violating-construction test always land together.** The forward-looking
record is this plan plus the A24 mini-ADR row (decisions are facts once
made; system descriptions are not).

| PR | Contents | Tier |
|---|---|---|
| PR-0 | Exit-label residue (§5): finalize-prompt sharpening, labels ordering + parallel-label context. Ships before everything; improves the pending medium validation run | frontier prompt design, small diff |
| PR-1 | Docs, **current-state truth only**: 01 §6 presents false branch + texture world as one mechanism *as parameterized today* — §1's table, the content regimes, the two non-unifying boundaries, the rendering/segment vocabulary later PRs' code will use — with today's asymmetries (premise on fresh arms only, mirrored-cadence parity) described as current behavior carrying A24/plan pointers for what changes. NO I15 restatement, NO I16, no freeze clarification (each rides the PR that makes it true; the A24 row landed with this plan) | frontier (doc-only) |
| PR-2 | Symmetry engine: one splice primitive behind the three current entry points, premise per rendering incl. rendering 0 (relaxing `Beat._class_consistency`'s premise-only-on-`TEXTURE_WORLD` guard, §2), FILL/entry-labels reading it. Doc half in the same PR: the freeze clarification and the premise-per-rendering rule land in 01 §6 | frontier design, mid-tier typing |
| PR-3 | 3+ arms + engine shape/count assignment (mandatory mix) — small, and the consumer shape for PR-5. Lands in the *one-shot* finalize (before the loop exists): `cadence_plan` gains the per-site shape, the prompt's CADENCE table states it, `_finalize_apply` enforces it like it enforces counts | mid-tier against this contract |
| PR-4 | Grant model: `Beat.grants_flags`, `grant_beats`/`choice_grants`/I10/round-trip + violating-construction tests; B6 held-note | mid-tier against this contract |
| PR-5 | The loop, **sub-sliced (agent decision + author, 2026-07-16)** because it bundled ~6 major changes across the freeze/arc/I15 seams — the epic's riskiest area — into one diff. The loop enables the rest, so the sub-slices stage on it. A coupling
surfaced while reading the code against the plan (2026-07-16): **retiring
mirrored cadence is inseparable from recursion + budget parity** — dropping
the trunk↔arm cadence mirroring leaves a texture arm cadence-less and
choice-asymmetric unless recursion budgets the arm's own run (the budget-
parity amendment to I15). So they land together, not in 5a. Refined slices:
**PR-5a** the finalize loop mechanism (`finalize:<n>` expansion decomposing
the one giant proposal into per-round wording passes — the A21 fix STATUS
predicts for ~60-site exhaustion), engine assignment + mirrored cadence
unchanged, 02's POLISH contract names the loop; **PR-5b** minting +
gated-rendering consumption + I16 (stated in 01 §8 with its
`graph/validate.py` check + violating test); **PR-5c** recursion (drop the
`qualifies()` texture exclusion) + small-segment admission + **retire
mirrored cadence + budget parity**, with I15 restated segment-relative and
composition-closed and its check updated. Each rides its own PR; all frontier (freeze/arc/I15 seams) | frontier (freeze/arc/I15 seams) |
| PR-6 | DRESS print acknowledgment paragraphs | deferred until a live run mints keywords |

**Acceptance criteria per PR** (what "done" means, checkable without this
plan's authoring session):

- **PR-0**: on a regenerated letter-and-frontier label layer, every cosmetic
  rejoin exit label differs from — and does not re-offer — the parallel
  label(s) onto the same destination; the labels-pass ordering is
  deterministic (a test pins it); no schema or graph-model change.
- **PR-1**: docs only, and every sentence added to 01 is true of the code
  on that PR's merge day. 01 §6 presents the one-mechanism framing and the
  rendering/segment vocabulary; today's asymmetries read as current
  behavior with A24/plan pointers; no invariant text changes, no forward
  claims.
- **PR-2**: the golden story and all checked-in exemplars validate
  unchanged (rendering-0 premises appear only on newly spliced forks); the
  `Beat._class_consistency` premise guard is relaxed (premise legal on any
  beat, engine-set only); a recorded-fixture test shows the trunk premise
  reaching FILL's write context and the fork's entry-label context; 01 §6
  gains the premise-per-rendering rule and the freeze clarification in the
  same PR.
- **PR-3**: the proposal schema accepts 3 arms; apply enforces the
  engine-assigned shape and arm count with actionable repair messages
  (reason, location, corrective); a violating construction per rule.
- **PR-4**: violating-construction tests both ways — a keyword-gated beat
  passes I10 when its grant is upstream and fails when it is not; runtime
  JSON round-trips `grants_flags`; B6's over-holding caveat is documented
  or fixed at the touch point.
- **PR-5**: an offline (mock/replay) fixture runs the loop to a terminal
  round; every walk's words-per-choice lands in the B6 band; every
  non-empty rendering minted a keyword; at least one fixture round consumes
  one (gated rendering, I16-checked, I13 intact); the retired machinery is
  deleted, not stranded; the I15 restatement and the I16 statement land in
  01 §8 in this PR, each with its check and violating-construction test
  (iron rule 6 — statement, check, and test travel together).

**Sequencing against the in-flight milestone:** the structural-depth medium
validation run (band-top `words_target`, DRESS at scale) should run **before
PR-2+** — it validates the machinery as shipped, and its author read informs
the mix ratio and the small-segment appetite. PR-0 ships first regardless
(the run then also validates the label fix). PR-1 (docs) can land any time.

**Handoff note:** each PR is buildable from this plan plus the repo's own
orientation order (AGENTS.md) — read 01 §5–6 and A23/A24 first, then the
functions this plan names in `pipeline/passages.py`,
`pipeline/stages/polish.py`, `graph/queries.py`, and `graph/validate.py`.
Nothing needed to
build lives only in the 2026-07-15 design session; if a seam turns out
underspecified anyway, that is a plan bug — sharpen this doc in the same PR
rather than deriving silently (AGENTS.md, doc-silent territory).

## Open questions (for the author or a later frontier session)

1. **The mix ratio** (diamond : sidetrack : two-worlds per scope) is author
   taste; placeholder ~1 diamond per 2–3 sidetracks, revisit on the medium
   read.
2. **Consumer count per keyword** — v1 pins 1; raise only if a live read
   wants recurring callbacks (and then watch the reward discipline).
3. **Nesting depth in practice** — the loop admits recursion structurally,
   but words-budget admission may never buy depth ≥ 2 below long scope;
   confirm the budgets are the only limiter rather than adding a depth cap.
4. **Runner resume determinism for the `finalize:<n>` chain** — verify
   against `runner.py` when PR-5 is built (expected to hold: the next-round
   decision is a pure function of the checkpointed graph).
5. **B6 walker over-holding** cosmetic keywords (grant-beats-in-view vs
   actually-walked) — fix or explicitly document when B6 is next touched.
