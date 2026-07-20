# 01 — Story Model

This document defines the domain model: the concepts a story is made of,
how they relate, and the invariants that keep a branching story sound.
It is written story-first; the serialization and engine mechanics live in
[03 — Architecture](03-architecture.md).

A running example is used throughout:

> **"The Keeper's Bargain"** (scope: micro). A lighthouse keeper discovers
> that the light is the only thing keeping something in the sea asleep.
> - **D1 (hard, backbone):** *Does the keeper keep the bargain or break
>   it?* Keeping it means tending the light forever and losing her chance
>   to leave with the visiting cartographer; breaking it frees her but
>   wakes what sleeps.
> - **D2 (soft, subplot):** *Does she tell the cartographer the truth?*
>   Telling makes him an ally but puts him in danger; hiding it keeps him
>   safe but builds the lie between them.

## 1. The layered model

A story exists at five layers of abstraction. Each pipeline stage works
mostly at one layer and compiles it down to the next.

| Layer | Concepts | Who sees it |
|---|---|---|
| **Concept** | Vision (genre, tone, themes, scope), Voice | Pipeline only |
| **World** | Entities: characters, locations, objects, factions | Author + (exported) player runtime |
| **Drama** | Dilemmas, Answers, Paths, Consequences | Author + pipeline |
| **Structure** | Beats, the beat DAG, state flags | Author + pipeline |
| **Presentation** | Passages, choices, variants, prose, art, codex | The player |

The load-bearing distinction is **beats vs. passages**: the author (and
pipeline) think in *beats* — atomic story moments — while the player reads
*passages* — prose units with choices between them. Structure is decided
entirely at the beat layer and frozen before prose exists.

## 2. Concept layer

**Vision** — a singleton record capturing the creative contract from
DREAM: genre/subgenre, tone, themes, audience, content boundaries
(include/avoid), a POV hint, and **scope**. Scope is a named preset
(`micro` / `short` / `medium` / `long`) that fixes concrete budgets: number
of dilemmas (and how many hard), cast size, beats per path, passage count
range, words per passage. Budgets make cost predictable (Goal G3) and give
every LLM stage concrete targets.

**The scale table is words-primary** (mini-ADR A19, M8): each scope's
primary anchor is the total prose words it targets — the thing the
author holds, prints, and pays for. Every other band is *derived* from
it and recalibrated by structural simulation (`tests/scale.py`:
synthetic scaffolds at the shape bands, compiled through the real weave,
collapse, and cadence machinery — never against stories generated under
the old bands), then padded for live-run inflation (bridges; models
exceeding minimums).

| Preset | Words (total) | Dilemmas (hard+soft, branched) | Locked (max) | Reserve (max) | Cast | Passages (derived) |
|---|---|---|---|---|---|---|
| `micro` | 2.4–9k | 1 + 1 | 1 | 1 | 3–5 | 8–24 |
| `short` | 9–22k | 1 + 2 | 2 | 2 | 5–8 | 24–64 |
| `medium` | 20–55k | 2 + 3 | 3 | 3 | 8–12 | 90–160 |
| `long` | 45–95k | 2 + 4 | 4 | 4 | 10–16 | 140–280 |

Scaffold depth is scope data too (`ScaffoldShape` — before M8 the
depths were universal prompt literals, so `micro` and `long` got the
same skeleton; micro still pins those literals so the golden story and
recorded fixtures hold):

| Preset | setup | pre-commit | post-commit/path | locked lead-in | locked aftermath |
|---|---|---|---|---|---|
| `micro` | 1–2 | 2–3 | 1–3 | 1–3 | 1–2 |
| `short` | 1–2 | 3–4 | 2–4 | 2–4 | 1–3 |
| `medium` | 2–3 | 4–6 | 3–5 | 3–5 | 2–3 |
| `long` | 2–3 | 5–8 | 4–7 | 4–6 | 2–4 |

The derivation, recorded so recalibration stays arithmetic: models
write a passage at ~0.9× its word band's cap (measured across every
live run), so words ≈ passages × 0.9·cap; passages come from beats via
the collapse cap (§6) plus the cadence diamonds; beats come from the
shape bands through the weave (units after a hard fork instantiate per
world). The *feel* of size — how often the reader genuinely chooses —
is checked separately — primarily as the **choice-stretch cap** (B10;
author metric 2026-07-16): per arc view at most `choice_stretch_max`
consecutive passages may offer no choice, because a no-choice passage is
inherently a cost and the stretch length is what reads as a book instead
of a game; and advisorily as B6 (words per choice along a *playthrough
walk*, target ≈250–800; a walk traverses one diamond arm, not both,
which is what an arc-view sum over-counted). Total words are checked as
B7; mandatory stretch-break sites are exempt from the words ceiling
until the density calibration lands.
Scale by adding structure (locked dilemmas §4, deeper Ys), never by
padding prose — and the word budgets enforce the converse: texture
passages (residue and false-branch arms) write toward a short band,
about a third of the scene band above the floor, because an arm written
at scene weight is the false-choice tax in word form. Ending passages
get headroom above the scene band (climax resolutions run long). The
locked and reserve columns are allowances, not floors: BRAINSTORM
overgenerates by up to their sum and triage locks or reserves the surplus
(B1) — locked becomes fork-less woven storylines, reserve becomes unwoven
texture feedstock (§4, structural-depth W2).

**A scope earns its length — the words-target coupling** (structural-depth
milestone W1, [`docs/plans/structural-depth.md`](../plans/structural-depth.md)):
the vision may carry an author-chosen `words_target` inside the scope's
words band (an economic input like scope itself, never invented by DREAM's
LLM; G0 checks the band). When set, the **soft** dilemma budget scales with
it: `table_soft + round((words_target − anchor) / words_per_soft)`, clamped
to `[1, table_soft + 2]`, where each scope's `anchor_words` is the
simulation-projected story words at the table budget and `words_per_soft`
the measured marginal story words of one soft dilemma through the real
weave/collapse/cadence machinery (2026-07-14 measurement, `tests/scale.py`:
short ≈ 3.2k over a 13.6k anchor, medium ≈ 9k over 49.3k, long ≈ 11k over
72.5k). Hard counts never move (hard forks multiply worlds; ending count is
story shape, not a length knob), the locked allowance stays the table's,
and micro is exempt (its shape pins pre-M8 literals). Unset means the table
counts exactly — the pre-coupling behavior. The rationale is the flat-book
post-mortem (decision log, 2026-07-14): the projected structure at the
table budget only reaches the *top* of each words band, so the lower band
was reachable only by stretching — bridge-fed length with no dramatic
material behind it. B9 (bridge share over all beats, warn above 25%) is
the advisory tripwire for exactly that signal.

**Voice** — a singleton record created by FILL before any prose: POV,
tense, register, rhythm rules, an imagery palette (where the voice's
images come from and their limits), dialogue rules, banned patterns. The
operational descendant of the vision ("gritty noir" becomes "second
person, present tense, short declaratives, no semicolons"). The palette
fields exist because a thin voice makes the writer lean on whatever
styled text sits in its prompt — rendered facts, adjacent prose — and
book-scale repetition follows (live run 8; the prose-quality effort).
The voice characterizes the **whole story, not every paragraph**: within
any passage most prose is plain and load-bearing, and the voice's
distinctive qualities surface only at the moments that earn them
(reading-difficulty effort, 2026-07-13). The failure it guards against
is *over-stylization* — the writer applying the full voice to every
sentence until the prose reads airless — which an author read of the
generated stories found is what "too complex for a gamebook" actually
means (grade-level metrics are anti-correlated: the most readable sample
scored the *highest* Flesch–Kincaid, the least readable the lowest; see
`docs/plans/reading-difficulty.md`). Both the voice pass and the FILL
write prompt frame the voice as a story-level property applied with
restraint, never a per-paragraph quota. As with register generally,
style intensity is taste — no gate grades it, the fence is the framing.

## 3. World layer

**Entity** — a character, location, object, or faction. The category is a
namespace (`character:keeper`, `location:lighthouse`). Each entity has:

- **Base state** — facts true on every playthrough: name, concept,
  appearance, personality. FILL may append a universal micro-detail
  discovered while writing (the keeper hums when nervous), or update a
  listed fact with a sharper version (re-using its key) — once written,
  true everywhere. Adding is the *exception*, at most one per passage: the
  writer is told most passages add none, so it does not manufacture a
  re-observation of a recurring entity every scene. Whether a detail
  genuinely adds and does not contradict an established fact is the FILL
  reviewer's `micro_detail` rule — not a blunt apply guard (author-directed
  redesign, 2026-07-12; the old single-assignment hard guard turned a
  capable writer's natural re-observation into a prose-blocking failure).
- **Overlays** — conditional state activated by state flags: `when:
  [bargain_broken] → demeanor: haunted, speech: clipped`. Overlays are
  embedded on the entity (an entity is one node, always); multiple active
  overlays compose. Overlays are how a single entity honestly differs
  across playthroughs.

The cast is effectively **locked after BRAINSTORM**. A character invented
later has no dilemma anchoring, no beats, no chance to intersect other
storylines — a walk-on at best. The pipeline enforces this socially, not
mechanically (late entities are allowed but flagged in review).

## 4. Drama layer

**Dilemma** — a binary dramatic question where *both* answers are
compelling and choosing costs something ("Keep the bargain or break it?").
Carries the question, a *why-it-matters* statement (the seed of residue),
`anchored_to` edges to its central entities, and three orthogonal
properties:

- **Role** — `hard` (backbone: introduces early, commits at/near the
  climax, paths never structurally reconverge) or `soft` (subplot:
  introduces later, commits earlier, paths reconverge after payoff).
  Role is the primary concept; convergence behavior is *derived* from it.
  If two paths could never honestly rejoin, the dilemma is hard by
  definition.
- **Residue weight** — `heavy` / `light` / `cosmetic`: how much prose must
  differ where arcs share structure (after soft convergence, or at
  hard-dilemma intersections). Independent of role: a soft dilemma can
  have heavy residue at particular moments.
- **Ending salience** — `high` / `low` / `none`: how much endings must
  differ by this dilemma's resolution.

**Answer** — one of exactly two responses per dilemma. Answers are
**strictly equal**: no answer is default, primary, or canonical, and the
data model carries no marker that could suggest otherwise. (FILL must
write *some* arc first so that shared-passage prose exists at convergence
points, but that is a scheduling choice made inside FILL — see
[02 § FILL](02-pipeline.md) — never a property of an answer. A previous
QuestFoundry marked one answer `canonical` and every downstream LLM stage
quietly invested more in that side; the marker is gone so the bias has
nothing to attach to.)

**Path** — one answer explored as a storyline: an ordered scaffold of
beats proving that answer, plus `has_consequence` links. An answer with no
path is a **shadow** — the road not taken. Shadows are not dead data: FILL
is given them as context so the prose can make the reader feel what the
chosen path cost.

**Disposition** — decided at SEED triage. Two dispositions are derived
from topology, never stored: a dilemma with two explored paths is
**branched** (the fork the player chooses); a dilemma with exactly one is
**locked** — the story canonizes one answer as a fork-less storyline woven
through every playthrough, and the unexplored answer is a permanent
*locked-dilemma shadow* (the heritage term; identifiable as an answer no
path explores). The third disposition, **reserve** (structural-depth W2),
is the one that *needs* a stored marker (`Dilemma.reserved`), because its
topology — zero explored paths — is also the pre-triage state: a reserved
dilemma is kept in the graph as **unwoven texture feedstock**. No path, no
beats, never woven; it is invisible to the weave, ordering, arcs, budgets
(beyond its own allowance), anchoring (I2 — its anchors may legitimately
be cut), shadows, and the codex, and surfaces in exactly one place: POLISH
finalize sees reserved material as advisory graft stock for texture (and,
from W3, texture-world) arms — real brainstormed material instead of
invented flavor. A reserved dilemma with an explored path is a gate error.
It is also the author's shelf: a rerun that raises `words_target` can
promote a reserve at triage instead of re-brainstorming. Branched counts
match the budget's role counts exactly; at most the scope's allowance may
lock, at most its reserve allowance may be reserved (B1). A locked path
still carries consequences, but they are facts of the world on every arc —
never gateable flags — and its `commits` beat is the **resolution**: the
moment the story, not the player, settles the question. Locked storylines
buy plot volume and world texture with no fork, no arc multiplication, and
no prose-feasibility pressure; in a mystery they are the red herrings, and
extra cast earns its place by anchoring them.

**Consequence** — a narrative outcome of a path, phrased as world state
("the cartographer knows the truth"), not player action. Each consequence
becomes one or more state flags in GROW.

**Dilemma ordering** — SEED declares pairwise temporal relationships that
guide interleaving: `wraps` (A opens before B, B resolves before A —
backbone wraps subplots), `serial` (A fully resolves before B introduces —
serial subplots never multiply each other), `concurrent` (interleaved, no
nesting). In the example, D1 `wraps` D2.

## 5. Structure layer

### Beats

A **beat** is a concrete story moment — the atomic unit from SEED onward.
Every beat has a summary (what happens), entity references, and one of two
classes:

**Narrative beats** serve a dilemma. Each carries `dilemma_impacts`
(which dilemma, and one of four effects: *advances*, *reveals*,
*complicates*, *commits*) and `belongs_to` edges to path(s). Position in
the Y-shape determines the edge count:

- **Pre-commit** — before the fork; experienced by every player;
  `belongs_to` **both** paths of its dilemma (and only ever paths of the
  *same* dilemma).
- **Commit** — the point of no return; the first beat exclusive to one
  path; exactly one `belongs_to`.
- **Post-commit** — plays out one answer's consequences; exactly one
  `belongs_to`.

For a **locked** dilemma (§4) the Y degenerates to a chain: every beat
belongs to the single explored path, and the one `commits` beat is the
resolution, flanked by lead-in and aftermath. Like any beats, a locked
chain's beats materialize once per world when they land after a hard
fork.

**Structural beats** serve the story's shape, not any dilemma: zero
`dilemma_impacts`, zero `belongs_to`. One type with a `purpose` field
rather than a zoo of subtypes:

| `purpose` | Added by | Job |
|---|---|---|
| `setup` | SEED | World-building before any dilemma opens |
| `epilogue` | SEED | Wrap-up after all dilemmas resolve |
| `bridge` | GROW, POLISH | Transition/pacing/gap-smoothing between scenes |
| `residue` | POLISH | Flag-gated mood-setter before a shared beat |
| `false_branch` | POLISH | Arm of a cosmetic fork-rejoin (choice-feel without consequence) |

Residue and false-branch beats are *conditionally traversed* (by flag or
by cosmetic choice); the rest are traversed by every arc that reaches
them.

**Beat annotations** carry per-beat craft signals that are *properties of
the beat*, not topology (§10.3 governs which the model keeps):

- **`scene_type` ∈ {scene, sequel, micro_beat}** (Swain's beat rhythm) —
  the intrinsic prose-intensity signal. A *scene* is active conflict (goal,
  obstacle, turn) and earns heightened prose and a fuller word band; a
  *sequel* is the reactive processing between scenes, plain and shorter; a
  *micro_beat* is a transition, the briefest. GROW's *annotate* pass (02
  §GROW) writes it per beat **before the freeze** — it names *why the beat
  exists* dramatically, settled at the freeze like the summary; POLISH only
  *adds* beats and never restates an existing beat's `scene_type`. Beats a
  later stage adds (a GROW bridge, a POLISH residue/false-branch arm) carry
  no annotation and take a deterministic fallback by `purpose`
  (transition/texture → `micro_beat`; else → `scene`). FILL sets each
  passage's word band from its highest-intensity beat (a scene beat
  justifies the words) and modulates prose per beat — style belongs to the
  story, not to every paragraph. Advisory, not gated: an unannotated beat
  falls back, never fails. (`exit_mood` remains deferred — §10.3.)
- **`narration_scope` ∈ {limited, wide}** — the per-beat POV/coda signal. The
  Voice fixes the book's POV *scheme* (§2); *scope* is where a beat may step
  outside its viewpoint. A *limited* beat is narrated inside the beat's
  viewpoint — no mind but the narrator's, though psychic distance may still
  widen to report a world fact the narrator could plausibly know (reporting the
  world is not a POV break; entering another mind is). A *wide* beat is a
  sanctioned **coda**, licensed to narrate beyond the viewpoint character's
  horizon — world aftermath once the dilemmas resolve, or a character's fate
  after they exit (their legend, the wake of their death). Like `scene_type`,
  GROW's *annotate* pass writes it per beat **before the freeze**, settled at
  the freeze; the fallback is `epilogue` → `wide`, every other beat → `limited`
  (`wide` is always the marked exception, never the default). FILL renders each
  beat's scope and modulates register *within* a passage — a limited scene may
  close into a wide coda paragraph — so a passage is never split for register
  alone (a split would insert a spurious single-option page-turn); the reviewer
  keys its POV rule to scope, so a wide coda is not flagged as a departure.
  Advisory, not gated. Resolves the epilogue/POV collapse-feasibility gap the
  `scene_type` live validation surfaced (`docs/plans/pov-narration-scope.md`).
- **`viewpoint` (a character entity id) + `interlude` (bool)** — the per-beat
  viewpoint head, the mechanism behind **rotating limited POV**
  (author-confirmed 2026-07-14; `docs/plans/rotating-pov-build.md`). The Voice's
  `pov` describes the *scheme* ("third limited, rotating among the suspects");
  `viewpoint` names the one character whose head narrates *this* beat. GROW's
  *annotate* pass writes it per beat **before the freeze** (settled like the
  other annotations); a `wide` beat carries **no viewpoint** by construction
  (a coda has no head), and beats a later stage adds (bridge, residue,
  false-branch) stay unannotated — **wildcards** everywhere the head is
  consumed. The head is fixed **per passage** and never switches inside one
  (invariant I14): POLISH collapse cuts a passage boundary at every head
  switch, so a rotation is always a page-turn — the corpus's "clear structural
  marker" — while wildcard and `wide` beats ride along in any passage. FILL
  derives each passage's head from its beats (computed, never stored) and
  enforces *no other minds* against that head; a passage with no annotated
  head degrades to the book-wide `Voice.pov` rule. `interlude` marks a beat of
  the scheme's *marked deviant register* (the Voice's `interlude`: occasional
  first-person journal entries, letters); an interlude beat needs a viewpoint,
  is never `wide`, never shares a passage with base-register beats, and FILL
  writes/reviews its passage against the interlude register instead of the
  book-default pov/tense. **The unit of viewpoint assignment is the
  *sequence*** — the maximal choice-free linear run of beats (computed,
  never stored, like arcs; `grow_sequences`). v1 assigned heads per beat
  with cadence as trusted prose guidance; the live medium showed the
  predicted whiplash (58% of linear annotated pairs hopped heads and I14
  shattered the passage layer — 76 of 172 passages were pure POV splits),
  so the reserved escalation fired (author-directed 2026-07-17,
  `docs/plans/pov-sequences.md`): annotate assigns ONE head per sequence,
  may split a sequence only with a stated dramatic-center justification,
  and may mark a segment `""` as a justified **wide cutaway** (its beats
  must be wide); the engine expands sequence heads to the per-beat
  `viewpoint` field, which remains the stored form everything downstream
  reads. Interlude beats take the declared carrier as head, engine-side.
  B11 (advisory) keeps sequence health visible: mid-sequence switches
  (justified or not — each is a no-choice page-turn), non-coda wides, a
  declared register with zero interludes, and per-head share.

- **`pov_head` + `interlude_carrier` (entity marks, characters only)** — the
  **declared POV scheme**, resolved from the prose `Vision.pov_hint` by
  GROW's *scheme* pass before annotate (`docs/plans/pov-sequences.md`).
  `pov_head` marks each followed head (the roster); at most one
  `interlude_carrier` marks the deviant register's voice, roster membership
  **not required** (an investigator's journal amid rotating suspects). The
  annotate schema pins `viewpoint` to roster ∪ carrier, so an off-scheme
  head is unrepresentable in the pipeline; invariant **I17** (§8) holds
  every other writer to the same rule, and FILL's voice pass *describes*
  the declared roster instead of re-deciding it. No marks = a pre-scheme
  project — the legal degenerate case (I17 skips, the pins fall back to the
  retained cast).

Whatever its class, a beat's summary is a **brief for the prose writer,
never the prose**: plain declarative present tense stating who does what,
what changes, and what it now costs — mood *named*, never performed. FILL
writes the page from the brief in a Voice that does not exist until after
POLISH; imagery spent in a summary is a style anchor smuggled past the
Voice (the same bias-vector family as the removed canonical answer) and
competes with the prose it is supposed to specify. The rule generalizes
past summaries: **everything that is not prose should not be prose**
(prose-quality effort, 2026-07-11) — micro-details, character-arc
metadata, and story-so-far notes are notes for later writers, and a
styled value stored in one is a phrase every later prompt will render
and every later passage will be tempted to perform (live run 8 read the
result at book scale: one detail restated verbatim in 25 of 148
passages). Every stage that writes summaries or notes (SEED, GROW's
contextualize and bridge passes, POLISH's residue, passage, and arcs
passes, FILL's micro-details and story-so-far summaries) carries this
register as a prompt contract. Register itself is taste, so no gate
grades it — the fence is the framing — but FILL enforces the deterministic
floor at apply: note-length caps on micro-details and story-so-far
entries, and an echo check that rejects prose restating a rendered fact
or a run lifted from adjacent prose verbatim.

### The beat DAG

GROW weaves all paths' beats into one directed acyclic graph. An edge
means "comes before." The DAG *is* the story's structure:

- A **divergence** is the last shared pre-commit beat having one successor
  per explored path (each successor a commit beat).
- A **convergence** is where a soft dilemma's post-commit chains rejoin.
  Precisely: the *rejoin frontier* — the minimal beats reachable from
  both commits. Usually that is a single shared beat; when the diamond
  feeds a hard fork directly (a legal and common weave), no single beat
  is on every arc and the frontier is one beat **per world** — each of
  the hard dilemma's commits. Residue beats splice between a path's
  exclusive tail and the whole frontier, so they exist in every world.
  Hard dilemmas never converge; their branches run to separate endings.
  With more than one hard dilemma, hard forks **nest**, and the right
  mental model is the weave as a **tensor of Y graphs**: each dilemma
  contributes its Y as one dimension, and a story position is a
  coordinate in every dilemma's Y at once. Soft dimensions *collapse*
  at convergence — the coordinate leaves the DAG and lives on as
  flags, overlays, residue. Hard dimensions *never collapse* — the
  coordinate stays in the DAG as position, so endings multiply (two
  hard dilemmas → four endings).
  Where two hard dimensions are expanded at once, an inner-dilemma
  beat materializes once per world: the instances project to the same
  node of the inner Y (same dilemma-relative meaning) and to different
  nodes of the outer Y (a genuinely different context — that
  difference is what "hard" means). Structure is copied per world;
  content follows the full coordinate, so the realized beats are
  distinct, few by design under late-committing backbones. GROW
  realizes the expansion (M5): every unit placed after the first hard
  fork is instantiated once per world — world-suffixed beat ids, the
  template replaced symmetrically so no world owns the "original"
  (mini-ADR A14) — the earlier fork's chain tails stop being endings,
  and a contextualize pass rewrites each instance's summary for its
  world. This refines I3: a path's commit beats occupy pairwise
  distinct worlds — exactly one commit absent expansion, one per world
  once its dilemma resolves inside a hard fork.
- An **intersection** is a co-occurrence declaration: beats from
  *different* dilemmas grouped into one scene (the keeper studies the
  charts — D2 — while deciding about the light — D1). The beats stay
  separate, keep their own `belongs_to`, and advance their own dilemmas;
  the group tells GROW to place them adjacently so POLISH *may* merge them
  into one passage. Beats from two paths of the *same* dilemma can never
  intersect — the player is only ever on one.

**After GROW, the dilemma topology is frozen.** Beats are never deleted;
forks and convergences never move. POLISH may only add structural beats
and reorder within linear runs. This freeze is what makes prose writing
safe.

**Arcs are computed, never stored.** An arc — one complete playthrough,
one path choice per dilemma — is a walk of the DAG from root to a
terminal, taking the matching successor at each fork. With D1 and D2 both
explored, "The Keeper's Bargain" has four arcs. Reasoning "this arc needs
a scene" is a design smell: nobody authors arcs; they author paths and
beats, and arcs emerge.

### State flags and residue

A **state flag** is a boolean world-state marker, always phrased as state
("the cartographer knows"), never as player action ("player chose to
tell"). Sources: derived from consequences at commit beats (dilemma
flags), or granted at a cosmetic-fork rendering's head beat
(`grants_flags`, symmetric with `requires_flags`) and projected onto its
entry choice (cosmetic flags — the beat-layer grant mirrors how a dilemma
flag is granted at its commit, so `grant_beats`/I10 reason about both
uniformly; cosmetic-forks PR-4). Flags do three jobs:

1. **Routing** — gating choices/variants after a soft dilemma converges
   (hard dilemmas need no routing flags; their graphs never rejoin).
2. **Overlay activation** — selecting which version of an entity is true.
3. **Prose context** — telling FILL what is true in the world at a passage.

**Residue** is the umbrella narrative concept: the lasting mark a choice
leaves. Mechanically it is delivered by weight:

| Weight | Mechanism | Example (D2, after convergence) |
|---|---|---|
| heavy | **Variant passages** — same moment, genuinely different prose, flag-gated | — (D2 is light) |
| light | **Residue arms** — one flag-gated arm *per path* before the shared scene (the residue diamond: the story remembers whichever side was chosen); an arm is one beat, a 2-beat chain where the memory deserves a scene, or a **tensored arm** (M8): two same-gate branches forking at the tail and rejoining at the frontier — the reader who made the matching upstream choice gets a choice in how to carry it, texture only | "He meets your eyes; he knows" vs. "He chatters, oblivious" → shared storm scene |
| cosmetic | Handled in prose wording alone | — |

**Codewords** are the *player-facing projection* of flags for print: a
curated subset the reader writes down ("Write CONFESSED in your log") and
checks at gates ("If you have CONFESSED, turn to 83"). Digital runtimes
track flags silently; SHIP decides which flags need codewords (soft
dilemma routing flags do; hard dilemma flags usually don't — the page
structure already separates those readers). Flags ≠ codewords, always.

## 6. Presentation layer

**Passage** — the unit the player reads: one or more beats compiled into a
prose container. POLISH creates passages by **collapsing** maximal linear
runs of beats (boundaries fall at divergences, convergences, and gate
changes — an identically gated linear chain, like a multi-beat residue
arm, is one gated passage) and by merging intersection-adjacent beats
into single scenes where narratable. Collapse is **capped** (M8,
`passage_beats_max`): a run longer than the scope's cap splits
front-to-back into cap-sized passages. Every beat is a story moment
with a prose claim, but a passage's word budget is fixed — unbounded
collapse would crush a deep run into one passage and the story would
mint no pages from its added structure. The cap is the choice-free
cutter; cadence diamonds meter *choices* (B6), never words.
Each passage carries its beats, a derived summary, entity refs, and —
after FILL — prose.

**Choice** — a directed, labeled edge between passages: label text,
`requires` (flags that must be active — the gate), `grants` (flags
activated by taking it). Most choices have empty `requires`; gates appear
after soft convergence.

**Variant passage** — a flag-gated sibling serving the same structural
moment when residue is heavy (`variant_of` edge to its base). A variant is
a full passage — different prose, not conditional text spliced into one. A
variant persists the flag it is gated on (the world-state it presents) on the
`Passage` node itself (`variant_flag`), not only via the `variant_of` edge, so
choice-wiring can recover which variant carries which gate when POLISH creates
passages and wires choices in separate passes
(`docs/plans/passages-chunking.md`).

**Cosmetic forks — one mechanism, four shapes.** A false branch and
a texture world are the same construct at different scales: **k ≥ 2
*renderings* of a trunk *segment*.** A segment is a stretch of the frozen
trunk between a `before` beat and an `after` beat — length zero (a single
edge) up to a whole cap-aligned run; a rendering is a parallel beat chain
the reader may choose, and every rendering rejoins at `after`. The shapes
differ only in parameters — the segment's length, how many renderings, and
whether a rendering is *empty* (walk the trunk straight through), *the
segment's own beats*, or a *fresh* invented chain:

| Shape | Segment | Renderings |
|---|---|---|
| Sidetrack | empty (an edge) | empty ("walk on") + one fresh chain |
| Diamond | empty (an edge) | two or three fresh chains |
| Small two-worlds | 1..cap−1 beats (a run tail) | the segment's own beats + one fresh chain |
| Texture world | a cap-aligned run | the segment's own beats + one fresh chain |

All four splice through one primitive (`insert_cosmetic_fork`; the named
splices are adapters), and POLISH plants them through one machinery — the
**finalize loop** (cosmetic-forks A24 in [03 — Architecture](03-architecture.md)
§9, contract `docs/plans/cosmetic-forks.md`): engine-only rounds
(`finalize:<n>`) recompute the qualifying sites and both budgets — the B6
projection per walk and the story-words headroom (`words_target` or the
band top) — on the current graph, assign shape and arm count per admitted
site, and expand into one small wording pass per site; the loop terminates
when every projected walk is at the B6 target or no site fits the remaining
words. Admission order follows marginal story-words per decision: scene
segments (capped story-total), seam edges, small two-worlds last. Because a
segment inside a rendering is just a segment a later round may fork,
**recursion falls out**: worlds nest, diamonds land inside arms, and mirror
chains ground out in trunk beats transitively (I15).

**The content regime follows segment length, not shape.** An empty segment
has no events, so each fresh rendering invents a breath of texture — a
diamond's two or three flavors of the same forward motion, a sidetrack's
optional detour. A non-empty segment carries real events, so every rendering
re-expresses *the same events* against another backdrop, beat for beat and
in order (the texture-world mirror rule, invariant I15 in §8).

**Empty-segment renderings (false branches)** are POLISH-added cosmetic
forks for the feel of agency: a *diamond* (two — or three — fresh arms, one
destination) or a *sidetrack* (a short detour that rejoins, which the reader
may also decline). **The shape and count are engine-assigned, not
model-chosen** (cosmetic-forks PR-3): the cadence budget cycles a mix (the
scope preset's `cadence_arm_cycle`) across its sites and the finalize apply
enforces it like it enforces counts — given the choice, a weak tier placed
44/44 sidetracks (the prompt undersold the diamond; medium validation
2026-07-15), exactly as discretion over counts once produced the flat book.
**Every non-empty rendering mints a cosmetic keyword** at splice
time (`flag:cw-<head-slug>`, `FlagSource.COSMETIC`, granted on the
rendering's head beat — rendering 0's frozen head included; the empty
rendering mints nothing: walking past a sidetrack leaves no mark, a
recorded choice, not an accident). A later round's edge-scale site may
offer up to 8 holdable, unconsumed keywords, and the wording pass MAY
attach one **keyword-gated extra rendering** consuming one — visible only
to holders, same size budget as any rendering (*acknowledges, never
rewards*: one consumer per keyword, never a scene-scale world), the v1
consumption form. A keyword is *permission*, never a promise: I16 (§8)
makes downstream dependence inexpressible. **Even fake
branching needs residue** (author-directed, 2026-07-15, reading
letter-and-frontier — the author's words: "even fake branching needs
consequence", meant in the reader-felt sense; the Drama-layer Consequence
stays off false branches by the contract above): a cosmetic arm is still
*chosen* — the reader picks the pine path, they don't decline the hall —
and the choice must leave a mark, at minimum in the arm's own beat and in
how the rejoin is worded (the exit label carries the arm's residue:
"reassured by the pine's whisper, step into the hall", never a re-offer of
the trunk's label — an identical rejoin label exposes the passage as a
mechanical sidestep). Cosmetic flags are the stronger form of the same rule.

**Non-empty-segment renderings (texture worlds)** are the false branch at
scene scale (structural-depth W3, author-directed 2026-07-14): a rendering
laid over a whole choice-free *stretch* of the DAG — **the same events
against another backdrop** — converging exactly where the stretch does.
"Backdrop" is deliberately wide (author clarification, 2026-07-14): any
consequence-free axis — the place ("the next events happen in the forest /
in the mountains"), the means ("go by bus or train"), the company, or the
small facts of things and people ("the car is blue / yellow", "the
innkeeper has a son / a daughter") — not location only. Same contract as an
empty-segment fork (different textures, never different consequences),
different economics: a beat-scale diamond buys one choice for one arm's
traversed words, while a texture fork buys one at near-zero traversed words
— the reader walks one world of roughly the trunk's length — paid for in
FILL tokens and print pages (the stretch is written twice). The fresh
rendering **mirrors the trunk beat-for-beat**: structural beats
(`purpose: texture_world`, zero `belongs_to`, zero impacts, ungated) each
carrying their trunk twin in `mirrors` and the twin's *effective*
`scene_type`/`narration_scope`/`viewpoint`/`interlude`, engine-copied at the
splice — both worlds read at the same band and head (the strictly-equal
doctrine's mechanical form; the false-branch micro_beat fallback would
starve the parallel world). `mirrors` is stored because it cannot be
recomputed once forks share endpoints — insertion provenance like A14's
world suffixes, consumed only by the engine and gate I15, never rendered to
a prompt. Renderings keep **budget parity, not structural parity** (ratified
cosmetic-forks decision 1): a detour a later round plants inside one
rendering is NOT mirrored into the others — each rendering grows its own
forks until its walks hit the B6 band, and per-walk B6 owns choice
fairness. Sites are seam-aligned sub-stretches containing no commit,
gate, or ending, and avoid rejoin frontiers (a residue splice would
otherwise be bypassed); an existing rendering's interior qualifies
(recursion). Arcs, flags, and the freeze are untouched by construction — the
arm is conditionally traversed structure, like any diamond arm. Feedstock
for the arm's material is the triage reserve (§4). Invariant I15 (§8) holds
the whole contract. The arm's material is model-worded in the finalize
proposal (one beat per trunk beat, in order, behind a declared one-line
**premise** — "the crossing goes over the mountain pass"), persisted on the
arm beats (`texture_premise`, the `Passage.variant_flag`
persist-for-a-later-pass precedent) so FILL's write prompt names the world
the passage grounds — the different-context lever (W4) that makes parallel
beats read as genuinely different scenes. **The premise is a per-rendering
value** (renderings are peers, cosmetic-forks §2): rendering 0 — the trunk
segment's own beats — carries its own `trunk_premise` too, so FILL grounds
*both* worlds' prose and the fork's entry label can name *both* backdrops.
Rendering 0's premise is grounded in what the trunk beats already carry,
sharpening only where the weave left the backdrop vague (never contradicting a
beat). **Freeze clarification:** the freeze (I9, iron rule 4) is *topological*
— no beat deleted, no dilemma fork or convergence moved — so a presentation
annotation POLISH adds to a frozen beat (a `texture_premise` on rendering 0's
trunk beats, set only through the mutation layer) is a legal addition, not a
content rewrite (`set_beat_texture_premise`, deliberately unlike the
freeze-rejecting `set_beat_summary`/`set_beat_scene_type`). The legacy
mirrored-cadence structures earlier runs produced (engine-suffixed twins of
false-branch beats inside arms) remain valid under I15; the machinery that
made them is retired.

**Two shapes that look like renderings but are not** (the fence). A
**residue arm** (§5) is the same *shape* — a parallel chain rejoining the
trunk — but the reader does not *choose* it: a flag *routes* it, and it is
an obligation the story owes (the world remembering a soft choice; I12, arc
completion), never a consequence-free option. A **dilemma fork** carries
real consequence and is a Drama-layer branch. The cosmetic construct is
*chosen and consequence-free*; routed-or-obligated and consequential both
stay outside it.

The **passage graph** — passages + choices — is what SHIP exports and the
player traverses. The beat DAG never ships; it is the authoring truth from
which the passage graph is compiled.

## 7. Enrichment layer

DRESS adds, without changing the story: an **art direction** record
(style, palette), per-entity **visual profiles**, per-passage
**illustration briefs** (caption + image prompt, prioritized), a **cover
brief** (the atmospheric, spoiler-safe front-page image), generated
or commissioned **illustrations**, and a diegetic **codex** (in-world
encyclopedia entries for major entities).

## 8. Invariants

The engine enforces these mechanically (see gates in
[02 — Pipeline](02-pipeline.md)). Numbered for reference throughout the
design.

**Drama**
- **I1** Every dilemma has exactly two answers, strictly equal — no
  default/primary/canonical marker exists in the model.
- **I2** Every dilemma is anchored to ≥1 surviving entity.
- **I3** Every explored path has a complete scaffold, with commit beats
  occupying pairwise distinct worlds — exactly one commit absent
  multi-hard expansion, one per world once the dilemma resolves inside
  a hard fork. Branched: ≥1 shared pre-commit beat and ≥1 exclusive
  post-commit beat around each commit's fork. Locked: ≥1 lead-in beat
  before, and ≥1 aftermath beat after, each resolution. Worlds are made
  by *other* dilemmas' hard forks; a dilemma's own commits are its
  fork, never its coordinate (§5) — and a locked dilemma, never
  forking, makes no worlds whatever its role.

**Beat DAG**
- **I4** The beat graph is acyclic, single-rooted, and every beat is
  reachable from the root.
- **I5** `belongs_to` discipline: shared pre-commit ⇒ exactly the two
  paths of one dilemma; commit/post-commit, and every beat of a locked
  chain ⇒ exactly one path; structural ⇒ zero. Cross-dilemma dual
  membership is always an error.
- **I6** Every arc (computed) is complete: root → terminal, contains
  exactly one commit per explored dilemma — the selected path's for a
  branched dilemma, the resolution for a locked one (every arc walks
  every locked storyline) — and no beat whose flag requirements are
  unsatisfiable on that arc.
- **I7** Hard dilemma paths never reconverge (no cross-path commit pair
  shares a descendant, in any world); soft dilemma paths always do, in
  every world they are expanded into, after a minimum payoff (≥ N
  exclusive post-commit beats per path per world, N from scope preset).
- **I8** Intersection groups never contain two beats of the same dilemma.
- **I9** Post-freeze (after GROW), no beat is deleted and no
  dilemma-driven fork or convergence moves.

**Flags & passages**
- **I10** Every flag is granted somewhere before it is required somewhere
  (per arc: no gate can test a flag no arc-consistent history could hold).
- **I11** Every beat is grouped into exactly one passage (variants may
  re-present the same beat behind disjoint gates).
- **I12** Prose feasibility: no passage requires FILL to honor more than
  3 *ambiguous dilemma states* simultaneously; incompatible heavy states
  force variants, not hedged prose. **The unit is the dilemma, not the
  flag** (corrected 2026-07-14, texture-trial live run: a path derives
  one flag per consequence and any of them identifies the path, so seven
  flags at one passage were two binary uncertainties): a dilemma's
  ambiguous flags count together as one state. A flag is ambiguous at a
  passage when readers arrive holding either value — its grant is
  upstream on some route and the opposing path's commit is upstream on
  another (a reconverged soft dilemma). A flag granted on every route
  there (only its own side upstream — e.g. this world's hard commits at
  an ending) is a fact the prose may simply assume: one state, not two,
  no load. Flags of a dilemma the passage is gated on — beat-level gates
  (residue) and passage-level gates alike (a variant's gate rides every
  in-choice; `passage_gate_flags`) — are likewise determined for
  everyone who arrives. When more states genuinely matter at a passage
  than the cap allows (the expected regime at medium/long, where several
  soft dilemmas overlap), the honest resolution is **splitting**: the
  audit keys the passage on a dilemma (`split_on`) and the engine
  re-presents the moment as flag-gated variants — each variant's
  arrivals hold a known side, removing that state — never marking a
  load-bearing state irrelevant to satisfy a budget (author-directed
  2026-07-14). **Exception: endings never split** — variants would
  multiply the story's ending set, fixed at the freeze. An ending's hard
  flags are facts (only its own side is upstream), but reconverged soft
  states stay ambiguous there, so an ending that genuinely turns on more
  than the cap has no in-audit escape: that is an upstream structure
  defect (too many soft threads collecting unresolved at one final
  scene — route their payoffs into gated residue before the finale), and
  the audit fails loudly rather than absorbing it with dishonest
  irrelevance.
- **I13** The passage graph has no dead ends: every non-ending passage
  has ≥1 always-satisfiable choice; every ending is reachable.
- **I14** One head per passage: among a passage's member beats that carry
  a `viewpoint`, all agree on `(viewpoint, interlude)`. The viewpoint
  never switches inside a passage — a rotation is always a page-turn
  (author-confirmed 2026-07-14, `docs/plans/rotating-pov-build.md`);
  unannotated beats and `wide` codas are wildcards.
- **I15** Non-empty-segment renderings mirror their segment (§6;
  restated segment-relative and composition-closed for the finalize loop,
  cosmetic-forks A24 — the original statement was structural-depth W3's).
  Field half: every `texture_world` beat names an existing twin in
  `mirrors`; the twin may itself be a mirror beat (worlds nest), so
  mirror chains must be acyclic and **ground out** in a non-mirror beat;
  the direct twin is not gated, commits nothing, and ends nothing (nested
  twins are mirror beats, so the rule composes link-by-link); the
  rendering beat is ungated and carries the twin's *effective*
  annotations. Shape half (the projection rule): on the beat graph with
  every *un-mirrored* `false_branch` beat contracted away (edge-scale
  decoration a later round spliced inside either world; a mirrored
  `false_branch` beat is a legacy cadence twin's counterpart and stays),
  every edge incident to a mirror beat projects — one `mirrors` step at
  either or both endpoints — onto an edge of that same contracted graph.
  This pins rendering contiguity and fork/convergence parity (the
  rendering rejoins exactly where its segment does) as local edge checks,
  and nested constructs project level-by-level. Structural choice-topology
  parity between renderings is deliberately **not** required (budget
  parity, ratified cosmetic-forks decision 1): each rendering grows its
  own forks under the loop's budgets, and per-walk B6 owns choice
  fairness.
- **I16** Cosmetic-gate locality (cosmetic-forks §4, the obligation
  boundary made structural): a cosmetic flag may be required only inside
  constructs that converge by construction — a beat gated on a cosmetic
  flag is itself a cosmetic-fork rendering beat, and a choice requiring
  one enters a rendering's passage; never a GROW beat, never a passage
  outside a cosmetic construct. With I16, "downstream depends on a
  keyword" is impossible to *express* in the graph: a keyword is
  permission (prose may color, a gated rendering may acknowledge), never
  a promise — anything downstream must honor is a dilemma in costume and
  belongs in GROW.
- **I17** Declared-scheme conformance (`docs/plans/pov-sequences.md`;
  author-ratified 2026-07-17): when a head roster exists (any character
  marked `pov_head`), every base-register beat's `viewpoint` is a roster
  member and every `interlude` beat's `viewpoint` is the declared
  `interlude_carrier` (who may be off-roster); at most one carrier per
  story. No roster → the check skips (pre-scheme projects are the legal
  degenerate case). The scheme/annotate schemas make pipeline violations
  unrepresentable; the gate holds hand edits to the same rule.

## 9. Where the mapping breaks (danger zones)

Places where the intuitive graph reading diverges from the narrative
meaning. Each stranded the original QuestFoundry, or nearly stranded
NG, by producing changes that were architecturally reasonable and
narratively wrong. When work touches one of these seams, re-read the
entry first; when the NG docs are silent, consult `docs/heritage/`
before deriving from first principles.

1. **Graph convergence ≠ narrative convergence.** When soft paths
   rejoin a shared beat, only the DAG has converged: flags, overlays,
   and residue beats keep differentiating arcs. Treating convergence as
   equivalence makes the story forget the choice exactly where it
   should be felt.
2. **Path membership ≠ scene participation.** `belongs_to` says which
   dilemma's storyline a beat *serves*, never which arcs reach it.
   Co-occurrence is an intersection group; cross-dilemma `belongs_to`
   is always wrong (I5). The original modeled intersections as
   cross-assigned `belongs_to` and got structurally impossible scenes.
3. **Arcs are computed, never authored.** "This arc needs a scene" is a
   phantom requirement — nobody authored an arc; they authored paths
   and beats (iron rule 2, invariant-adjacent to I6).
4. **Copied structure ≠ duplicated content (the tensor).** The weave is
   a tensor of Y graphs (§5): soft dimensions collapse into state; hard
   dimensions stay expanded, so with several hard dilemmas an inner
   beat materializes once per world — same inner-Y node (meaning),
   different outer-Y node (context), distinct realized beats. Two
   symmetric misreadings, both made and corrected on 2026-07-08
   (decision log): "beats are never cloned, therefore multi-hard
   is impossible," and "multi-hard needs duplication machinery."
5. **State multiplication ≠ world expansion.** Soft dilemmas multiply
   *states* on shared nodes (flags/overlays — no new beats); hard
   dilemmas multiply *worlds* (the DAG splits — new beats). Budgets,
   feasibility audits, and cost reasoning must not swap the two.

## 10. Departures from the original QuestFoundry model

Kept because it earns its keep: the five-layer model, binary dilemmas,
hard/soft roles with derived convergence, the Y-scaffold and `belongs_to`
discipline, frozen topology, computed arcs, flag/codeword split,
intersection-as-co-occurrence, overlays embedded on entities.

Changed:

0. **No canonical answer.** The original marked one answer per dilemma
   `is_canonical` (née `is_default_path`) to fix FILL's writing order —
   a residue of spine-first writing, and a known bias vector: any stage
   that sees the marker treats that side as the "real" story. NG removes
   the concept from the data model. FILL's need for a first-written arc
   is met by a **reference arc** chosen inside FILL (seeded, stage-local
   working data) that no other stage can see.

1. **One structural beat type, five purposes** — the original's seven
   subtypes (setup, epilogue, transition, micro-beat, gap, residue,
   false-branch) collapse to a single class with a `purpose` enum;
   transition/micro/gap were three names for "bridge" distinguished only
   by which phase inserted them, which belongs in provenance metadata
   (`created_by`), not the type system.
2. **No path-specific structural beats.** The original's gap beat carried
   a lone `belongs_to` as a special case. NG bridges that must stick to
   one path's exclusive segment get that property from DAG position (they
   sit on the exclusive branch), not from membership edges — removing the
   only exception to I5.
3. **Annotation trimming.** The original accreted per-beat craft
   annotations (scene_type, narrative_function, exit_mood,
   atmospheric_detail, path_theme, path_mood...). NG deferred all of them
   under YAGNI — annotations are cheap to add and expensive to maintain
   coherently — and adds one only when a FILL quality gap demonstrably
   calls for it. Three are now built, each on a demonstrated gap.
   **`scene_type` (scene/sequel/micro_beat)** answered the reading-difficulty /
   over-stylization gap (`docs/plans/scene-type-modulation.md`): the intrinsic
   prose-intensity signal GROW's *annotate* pass writes per beat (see "Beat
   annotations" above) and FILL reads to modulate prose across the story.
   **`narration_scope` (limited/wide)** answered the epilogue/POV
   collapse-feasibility gap that same live validation surfaced
   (`docs/plans/pov-narration-scope.md`): the per-beat POV/coda signal the same
   *annotate* pass writes alongside `scene_type`.
   **`viewpoint` + `interlude`** answered the rotating-limited-POV gap (the
   *Closed Circle* FILL blocker, `docs/plans/rotating-pov.md`) — note the
   earlier blanket deferral of "a full per-beat viewpoint-character/distance
   field" was an **agent scope-cut recorded under the author's name, not an
   author decision**; the author confirmed the feature was wanted and answered
   the design questions directly (2026-07-14,
   `docs/plans/rotating-pov-build.md`). What shipped is narrower than the
   original's field family: the head only (no per-beat distance — distance
   stays `narration_scope`'s job), one head per passage (I14), rotation only
   at passage boundaries — which does not conflict with the corpus's
   *mid-scene* head-hopping warning the earlier rejection conflated it with.
   `exit_mood` remains deferred; the rest stay trimmed.
4. **Budgets are first-class.** Scope presets bind hard numbers (dilemma
   counts, beats per path, passage ranges) that gates check, making cost a
   contract instead of an emergent property.
5. **Character-arc metadata is spine-indexed, not path-indexed.** The
   original (`docs/heritage/story-graph-ontology.md`, "Character Arc
   Metadata") stores one pivot **per path** plus per-path `arc_line` and
   `arc_type` records, dual-indexed with a must-agree constraint. NG's
   `EntityArc` is `begins` + an **ordered list of pivots anchored to
   beats** + `ends` per path: a turn every reader experiences (a shared
   spine beat) is stated once instead of repeated per path, multiple
   turns along one route are expressible, and a per-path turn is still
   expressible by anchoring a pivot to a path-exclusive beat — FILL
   activates a pivot only when its beat is upstream of the passage, so a
   reader's route turns on exactly the pivots it passed. The redundant
   dual index (and its consistency rule) is dropped for the same reason
   arcs are computed rather than stored. `arc_line` is derived
   (begins → pivots → ends), never stored; `arc_type` is implicit in the
   entity's category. Arc-worthiness matches the original: **every
   retained entity is arc-eligible** (author doctrine, 2026-07-12: a
   character without an arc is an extra, a location a backdrop, an
   object a mcguffin, a faction a link — any of them can be given
   choices). The arcs pass decides which entities to arc; leaving one
   unarced deliberately declares it scenery. The category flavors
   (character transforms, a location's atmosphere shifts, an object's
   significance moves, a faction's relationship moves) are prompt
   guidance, not schema.
