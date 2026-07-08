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

| Preset | Dilemmas (hard+soft) | Cast | Passages (approx.) |
|---|---|---|---|
| `micro` | 1 + 1 | 3–5 | 15–25 |
| `short` | 1 + 2 | 5–8 | 30–50 |
| `medium` | 2 + 2 | 7–10 | 60–90 |
| `long` | 2 + 3 | 9–14 | 100–150 |

**Voice** — a singleton record created by FILL before any prose: POV,
tense, register, rhythm rules, banned patterns. The operational descendant
of the vision ("gritty noir" becomes "second person, present tense, short
declaratives, no semicolons").

## 3. World layer

**Entity** — a character, location, object, or faction. The category is a
namespace (`character:keeper`, `location:lighthouse`). Each entity has:

- **Base state** — facts true on every playthrough: name, concept,
  appearance, personality. FILL may append universal micro-details
  discovered while writing (the keeper hums when nervous) — once
  discovered, true everywhere.
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
  Hard dilemmas never converge; their branches run to separate endings. With more than one
  hard dilemma, hard forks **nest**, and the right mental model is the
  weave as a **tensor of Y graphs**: each dilemma contributes its Y as
  one dimension, and a story position is a coordinate in every
  dilemma's Y at once. Soft dimensions *collapse* at convergence — the
  coordinate leaves the DAG and lives on as flags, overlays, residue.
  Hard dimensions *never collapse* — the coordinate stays in the DAG
  as position, so endings multiply (two hard dilemmas → four endings).
  Where two hard dimensions are expanded at once, an inner-dilemma
  beat materializes once per world: the instances project to the same
  node of the inner Y (same dilemma-relative meaning) and to different
  nodes of the outer Y (a genuinely different context — that
  difference is what "hard" means). Structure is copied per world;
  content follows the full coordinate, so the realized beats are
  distinct, few by design under late-committing backbones. Realizing
  the expanded case is M5 work; it refines I3's "exactly one commit
  beat per path" to one per world (tracked in `docs/STATUS.md`).
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
flags), or granted by false-branch choices (cosmetic flags). Flags do
three jobs:

1. **Routing** — gating choices/variants after a soft dilemma converges
   (hard dilemmas need no routing flags; their graphs never rejoin).
2. **Overlay activation** — selecting which version of an entity is true.
3. **Prose context** — telling FILL what is true in the world at a passage.

**Residue** is the umbrella narrative concept: the lasting mark a choice
leaves. Mechanically it is delivered by weight:

| Weight | Mechanism | Example (D2, after convergence) |
|---|---|---|
| heavy | **Variant passages** — same moment, genuinely different prose, flag-gated | — (D2 is light) |
| light | **Residue beat** — short flag-gated mood-setter before the shared scene | "He meets your eyes; he knows" vs. "He chatters, oblivious" → shared storm scene |
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
runs of beats (boundaries fall at divergences and convergences) and by
merging intersection-adjacent beats into single scenes where narratable.
Each passage carries its beats, a derived summary, entity refs, and —
after FILL — prose.

**Choice** — a directed, labeled edge between passages: label text,
`requires` (flags that must be active — the gate), `grants` (flags
activated by taking it). Most choices have empty `requires`; gates appear
after soft convergence.

**Variant passage** — a flag-gated sibling serving the same structural
moment when residue is heavy (`variant_of` edge to its base). A variant is
a full passage — different prose, not conditional text spliced into one.

**False branch** — POLISH-added cosmetic forks for the feel of agency:
*diamond* (two choices, same destination) or *sidetrack* (a short detour
that rejoins). May grant cosmetic flags for later flavor callbacks.

The **passage graph** — passages + choices — is what SHIP exports and the
player traverses. The beat DAG never ships; it is the authoring truth from
which the passage graph is compiled.

## 7. Enrichment layer

DRESS adds, without changing the story: an **art direction** record
(style, palette), per-entity **visual profiles**, per-passage
**illustration briefs** (caption + image prompt, prioritized), generated
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
- **I3** Every explored path has a complete Y-scaffold: ≥1 pre-commit
  beat, exactly one commit beat, ≥1 post-commit beat.

**Beat DAG**
- **I4** The beat graph is acyclic, single-rooted, and every beat is
  reachable from the root.
- **I5** `belongs_to` discipline: pre-commit ⇒ exactly the two paths of
  one dilemma; commit/post-commit ⇒ exactly one path; structural ⇒ zero.
  Cross-dilemma dual membership is always an error.
- **I6** Every arc (computed) is complete: root → terminal, contains
  exactly one commit per explored dilemma, and no beat whose flag
  requirements are unsatisfiable on that arc.
- **I7** Hard dilemma paths never reconverge; soft dilemma paths always
  do, after a minimum payoff (≥ N exclusive post-commit beats per path,
  N from scope preset).
- **I8** Intersection groups never contain two beats of the same dilemma.
- **I9** Post-freeze (after GROW), no beat is deleted and no
  dilemma-driven fork or convergence moves.

**Flags & passages**
- **I10** Every flag is granted somewhere before it is required somewhere
  (per arc: no gate can test a flag no arc-consistent history could hold).
- **I11** Every beat is grouped into exactly one passage (variants may
  re-present the same beat behind disjoint gates).
- **I12** Prose feasibility: no passage requires FILL to honor more than
  3 active states simultaneously; incompatible heavy states force
  variants, not hedged prose.
- **I13** The passage graph has no dead ends: every non-ending passage
  has ≥1 always-satisfiable choice; every ending is reachable.

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
   (STATUS decision log): "beats are never cloned, therefore multi-hard
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
   atmospheric_detail, path_theme, path_mood...). NG starts with two —
   `scene_type` (scene/sequel) and `exit_mood` — and adds more only when a
   FILL quality gap demonstrably calls for one. Annotations are cheap to
   add and expensive to maintain coherently.
4. **Budgets are first-class.** Scope presets bind hard numbers (dilemma
   counts, beats per path, passage ranges) that gates check, making cost a
   contract instead of an emergent property.
