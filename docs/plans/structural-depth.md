# Structural depth — material density & texture worlds (milestone plan)

> Status: **DESIGNED, PR-1 building** (2026-07-14). The milestone itself and
> its four ingredients are **author-directed 2026-07-14** (roadmap "Next",
> now "Now"; the stretching diagnosis, the brainstorm-surplus lever, the
> texture-worlds idea, and the different-context lever are the author's,
> quoted in the roadmap entry). The *mechanical designs* below — the
> words-target coupling arithmetic, the reserve disposition, the
> texture-fork contract — are **this agent's**, derived from those
> directions plus the structural simulation; each open judgment is flagged.
> Frontier-authored (budget semantics, freeze/arc/collapse interaction).

## The problem (one paragraph)

The first weak-tier medium to finish FILL gate-clean read as "essentially a
flat story" (author, 2026-07-14): 10 branch points over 112 passages,
words-per-choice ~4× over the B6 band, 89 of 239 beats bridges (the healthy
runs: 27, 33). The immediate fix — the cadence budget mandatory at
`_finalize_apply` — is the floor, not the fix. The author's diagnosis is
**stretching**: "if we do not have enough branching material we may not be
able to sustain such a long story and need more dilemmas", and false
branching "may help, but cannot compensate something as bare as the
finished run". The structural A/B agrees: even kimi's budget-saturated
structure projects 1020 words/choice — beat-scale texture saturates on a
bare trunk. The simulation sharpens it: at the table budgets the projected
B6 sits at the band's very top (780 at medium) with ~80% of decisions
cosmetic; and the projected story words at the table budget span only
~46–52k of medium's 20–55k band, so most of every scope's words band is
reachable only by stretching.

## Why beat-scale texture saturates (the arithmetic)

A cadence diamond's arm is a texture passage projected at the micro band
(~285 words at medium). Marginally each diamond adds one decision *and* one
arm's traversed words, so words-per-choice converges toward ~285 — inside
band — but only at cap-aligned seams, and capacity runs out before the mean
reaches mid-band on a long trunk. Two consequences drive this milestone:

1. **Density**: real forks (dilemmas) must scale with the words budget —
   each soft dilemma adds walk words *and* a real decision plus residue
   texture, improving both the ratio and the diet.
2. **Texture worlds**: a diamond laid over a whole *run* adds a decision at
   **near-zero marginal traversed words** — the reader walks one parallel
   world of roughly the trunk's length. Scene-scale texture is the only
   cosmetic form whose reader-cost does not grow with its substance. (Its
   cost is FILL tokens: the paralleled stretch is written twice.)

## W1 — Material density (PR-1, building)

**Contract: a scope earns its length.** The words budget and the dilemma
budget stop being independent knobs.

- `Vision.words_target: int | None` — an author-chosen point inside the
  scope's `words_total` band (`qf new --words-target`, default `None`).
  G0 validates it against the band. It is an *economic* input like scope,
  never invented by DREAM's LLM.
- `ScopePreset.budget_for(words_target)` derives the dilemma budget:
  - **hard count never moves** (hard forks multiply worlds — cost is
    exponential, and ending count is a story-shape decision, not a length
    knob);
  - **soft count scales**: `table_soft + round((words_target − anchor) /
    words_per_soft)`, clamped to `[1, table_soft + 2]`, where `anchor` is
    the simulation-projected story words at the table budget (midpoint of
    the shape corners) and `words_per_soft` the simulation-measured
    marginal story words of one soft dilemma (2026-07-14 measurement,
    `tests/scale.py` machinery: medium ≈ 9.0k, short ≈ 3.2k, long ≈ 10.8k
    — worlds multiplication included, since `words_total` is story-total);
  - the locked *allowance* stays the table's (it is a maximum, not a
    demand; W2 owns retention).
  - `words_target=None` → exactly the table counts (every existing
    project, fixture, and exemplar validates unchanged).
- B1 checks the derived budget; DREAM/BRAINSTORM/SEED prompts render the
  derived counts (they already render the table's).
- **B9 (advisory): bridge share.** `bridge beats / all beats` above
  threshold warns at G3/G4. Data: flat run 37%, M8 ~13%, kimi ~8%;
  threshold 0.25. Advisory *by design*: the count is engine-computed but
  not in-pass repairable — GROW's bridge pass must cover every gap
  (I6), so the actionable fix is upstream material (SEED scaffolds that
  share entities; the density coupling), not a count a pass can hit. This
  answers the BACKLOG tier-confound question for this knob: **the
  mandatory-at-apply treatment (cadence precedent) applies only where the
  target is engine-computed, exact, *and* repairable inside the proposing
  pass**; bridge share fails the third test, so it becomes a tripwire, and
  the enforcement lands in B1's coupled budget instead. The remaining
  floor-phrased knobs (scaffold shape bands, intersection group counts,
  residue fork uptake) each get judged against the same three-part test
  when they next bite.

Known non-goals in PR-1: `passages`/`arc_beats` bands do not yet scale with
the derived budget (advisory; the scale-recalibration BACKLOG item owns
them); micro is exempt from coupling (its shape pins pre-M8 literals for
the golden story; a micro that wants coupling is a design smell anyway).

## W2 — Brainstorm surplus as feedstock (PR-2, built)

**Author direction (2026-07-14):** overgenerate further and/or retain more
at triage as the source of *additional branching* when the words budget
demands it — surplus dilemmas, subplots, and settings kept available
(tagged, not woven) instead of discarded.

What shipped (as designed, plus the seams the build surfaced):

- `ScopePreset.reserve_dilemmas` (1/2/3/4 by scope) grows BRAINSTORM's
  requested total; G1's B1 range check admits locked + reserve surplus.
- Triage's third disposition **`reserve`**: `Dilemma.reserved` (the one
  disposition that *needs* a stored marker — zero paths is also the
  pre-triage state; branched/locked stay topology-derived), written only
  via `mutations.set_dilemma_disposition`. The triage proposal gains a
  schema-pinned `reserve` list; apply rejects reserve∩locked, a reserve
  with paths, and over-allowance, all repairably.
- Invisibility, enforced at each seam the sweep found: `weave.shapes`
  skips reserved (else a zero-path dilemma is a WeaveError); SEED's
  scaffold and order contexts and the order schema's dilemma enum exclude
  them; FILL's voice context and shadows exclude them; **I2 exempts
  them** (their anchors may legitimately be cut — feedstock, not story);
  DRESS codex eligibility and G6's check ignore their anchoring edges.
  I3/I6/I7/flag derivation/arcs ignore them by construction (no paths).
- B1 post-triage counts reserved against the allowance and errors on a
  reserved dilemma with an explored path.
- POLISH finalize's context carries the reserved dilemmas (question,
  stakes, anchor names) and the prompt frames them as advisory graft
  stock for false-branch arms: echo as texture, never advance or decide.
- The author's shelf: a rerun that raises `words_target` can promote a
  reserve at triage instead of re-brainstorming (promotion is a normal
  triage disposition on the rerun; no extra machinery).

## W3 — Tensored texture worlds (PR-3 engine + PR-4 pipeline BUILT)

**Author direction (2026-07-14):** generalize the false branch from a 1–2
beat graft between adjacent beats to a diamond laid over a whole *run* of
the DAG (many beats, even containing branches), temporarily creating
parallel texture-worlds — "one where the next events happen in the forest,
another where they happen in the mountains" — converging where the run
ends. Same contract as false branches (different textures, never different
consequences) but scene-scale.

**As built (PR-3), where it departs from the contract below** — three
build discoveries, each probed on the structural simulation:

1. **Sites are cap-aligned sub-stretches, not whole runs.** A real
   weave's long shared run always carries locked-chain resolutions
   (medium sim: the 60-beat trunk run), so whole runs never qualify; the
   site excises qualifying windows around commits/gates/endings and
   snaps boundaries to collapse chunks so the trunk's chunking survives
   the fork edges (`texture_sites`).
2. **"Even containing branches" arrived early, in cosmetic form.**
   Reserving textured stretches from the cadence budget starved a
   capacity-limited system (medium-max probe: B6 780 → 1129 — the forks
   displaced ~14 diamonds while adding 3 decisions). The fix is the
   author's own direction brought forward: a cadence diamond planted on
   a trunk edge inside a mirrored stretch is **mirrored into every arm**
   (`insert_cadence_diamond`: engine-suffixed texture twins of the fresh
   false-branch beats, wired identically), so both worlds keep the same
   choice topology and the I15 projection stays edge-exact. Result:
   B6 785 with 3 scene-scale worlds planted (21/15/6-beat stretches)
   vs 780 without — density preserved, substance added.
3. **Parallel worlds consume words budget without walk words** (medium
   sim: story words 52.5k → 62.8k, walk words flat) — the FILL/print
   price of writing a stretch twice. PR-4 folded this into the plan:
   `texture_plan` admits a fork only while the projected story total
   stays inside the words budget (`words_target` when set, the scope
   band's top otherwise) — a scope earns its parallel worlds too. The W1
   calibration constants were measured texture-off, and `tests/scale.py`
   keeps `texture_worlds=False` as the default until recalibration.

The mirror evidence is stored: `Beat.mirrors` names the trunk twin —
insertion provenance that cannot be recomputed once forks share
endpoints (cf. A14's world suffixes), consumed only by the engine and
gate I15, never rendered to a prompt. I15's shape half is a local
**edge-projection rule** (every edge incident to a texture beat projects
via `mirrors` onto an existing trunk edge), which pins contiguity,
convergence parity, injectivity, and residue-bypass without chain
reconstruction. PR-4 wired the pipeline: `_texture_and_cadence` computes
both fork budgets together (cadence sized on a scratch graph carrying
probe arms, so the numbers the model sees are the numbers apply
enforces); the finalize proposal gains `texture_worlds` (site index +
one-line premise + one model-worded beat per trunk beat, mandatory
coverage checked before any splice, empty-list schema discipline when no
sites); apply splices texture → false branches → residue, with the
cadence splices dispatching through the mirroring variants; the premise
persists on arm beats (`Beat.texture_premise`, the `variant_flag`
precedent) and FILL's write prompt names it (W4). Mirrored diamond twins
keep engine-copied summaries (A14's "structure is copied" — their
one-line flavor is world-neutral by instruction; revisit if a live read
catches a twin clashing with its world). Still open: the milestone's
**live validation run**.

Contract (agent design; the starred items are the frontier seams):

- **A texture fork parallels a stretch of a maximal linear run** in the
  uncapped collapse (the same site model as cadence planning). v1 sites
  contain **no commit, divergence, convergence, or flag-gated beat** —
  "even containing branches" is deferred to a later slice, where the
  contained branches are themselves cosmetic (a cadence diamond inside the
  paralleled stretch); real forks inside a texture world stay out of scope
  until a story demands them.
- **The parallel arm mirrors the trunk beat-for-beat**: new structural
  beats, `purpose: texture_world` (a sixth `StructuralPurpose`), zero
  `belongs_to`, zero `dilemma_impacts` (I5 already enforces this for
  structural beats) — the *same events* re-textured, not new events. The
  choice may grant a cosmetic flag, exactly like a false branch.
- ⭐ **Annotation mirroring, not the micro_beat fallback.** Each arm beat
  copies its trunk twin's `scene_type`, `narration_scope`, and
  `viewpoint`/`interlude` at insertion (engine-copied, never model-set).
  This is the load-bearing asymmetry fix: with the false-branch fallback,
  the mountains arm would be written at texture weight while the forest
  trunk got scene weight — a reader-visible bias the strictly-equal
  doctrine exists to prevent. With mirrored annotations both arms carry
  the same intensity profile, word bands, and head; the trunk's only
  remaining privilege is provenance (`created_by`), which no prompt
  renders. (Full symmetry — re-texturing the trunk too — was considered
  and rejected: summaries are settled at the freeze and POLISH adds only;
  rewriting frozen summaries needs a freeze exception nothing else
  justifies.)
- ⭐ **Arc invisibility.** Arcs are computed from path selections
  (`arc_selections` × `arc_view`); structural beats are admitted to every
  view they are reachable in, exactly as false-branch arms are today, so
  arc enumeration, I6, convergence frontiers, and flag derivation are
  untouched by construction. The walk-based measures (B6, projected
  walks, `qf simulate`) traverse one arm — also existing diamond
  semantics. What changes is only *scale*: `--all-arcs` now misses whole
  scenes, which finally triggers the deferred `qf simulate --random N`
  (M10 already notes this).
- ⭐ **Freeze compliance.** Grafts are POLISH-finalize additions: trunk
  beats keep their edges into the run; the fork adds `before → arm[0]`,
  `arm[-1] → after` around the paralleled stretch… precisely: the trunk
  edge *into* the stretch is duplicated onto the arm head and the arm tail
  edges into the stretch's successor — no beat deleted, no dilemma fork or
  convergence moved (I9). The paralleled trunk beats become conditionally
  traversed, like residue arms — a property change the model already has a
  word for (conditionally traversed ≠ deleted).
- **Sites and counts are engine-computed and mandatory at apply** (the
  cadence precedent, and it passes all three tests: engine-computed,
  exact, in-pass repairable). The engine offers sites (long runs with
  enough substance — a minimum stretch length, e.g. one full collapse
  chunk) and sizes the count against the B6 projection *before* cadence
  diamonds fill the remainder: texture forks are the cheapest choices in
  reader-words, so they are budgeted first, then `cadence_plan` tops up.
  Expected counts are small (1–3 per story) — scene-scale substance, not
  cadence filler.
- **Feedstock**: the finalize prompt grafts from W2's reserved material
  ("the mountain crossing the triage shelved") and the site's own
  entities; the model writes each arm beat's summary in note register,
  mirroring the trunk twin's events in the declared alternate texture.
- **Collapse and FILL fall out**: the arm is a linear identically-gated
  chain → its own capped passages (I11, I13, I14 hold by construction);
  FILL windows work per route as they do through any diamond; the
  story-so-far route passes through one arm.
- **Gate additions**: arm/trunk mirror-parity (beat count and copied
  annotations agree) checked at G4; a `texture_world` beat outside a
  texture fork is an error. New checks cite this plan and design doc 01
  §6; if review finds an invariant-shaped rule here (e.g. mirror parity),
  it gets an I-number in 01 §8 per iron rule 6.

## W4 — The context lever (BUILT, rides PR-4)

**Author direction (2026-07-14):** similar beats in different worlds can
yield *completely different passages*, because FILL writes prose from
completely different context (world truths, window, head, story-so-far).
The multi-hard machinery already demonstrates this. Engine work is nearly
nil by design: the texture arm's beats carry their own summaries (the
alternate texture *is* the brief), the window along the arm is arm-prose,
and the head mirrors the trunk. The one addition: the write prompt names
the passage's texture-world premise (from the fork site) the way it names
world truths after hard forks, so the writer grounds the alternate setting
instead of inferring it from summaries alone.

## PR slicing

| PR | Contents | Tier |
|---|---|---|
| PR-1 (this branch) | `words_target` coupling, `budget_for`, B1 wiring, prompt plumbing, B9 bridge share, sim calibration, docs | frontier design, mid-tier typing |
| PR-2 (built) | reserve disposition end-to-end (BRAINSTORM → triage → gates), feedstock context plumbing | mid-tier against this contract |
| PR-3 (built) | texture-fork engine: model, splice, mirroring, site computation, gate checks (I15), sim extension | frontier (freeze/arc seams) |
| PR-4 (built) | finalize integration + prompts, FILL context lever; live validation remains the milestone's exit | frontier review, mid-tier typing |

Live validation for the milestone: a fresh weak-tier medium with
`words_target` near the band top — the budget derives more softs, POLISH
plants texture forks, B6 lands mid-band, B9 stays quiet, and the author
read finds actual interactivity. (The DRESS-at-scale run from the previous
epic remains a separate obligation and can run on any of these projects.)

## Open questions (for the author or a later frontier session)

1. **Soft-count clamp** `[1, table_soft + 2]` is an agent guess: the upper
   clamp guards cast pressure (`cast_max` fixed while dilemmas grow — each
   needs anchoring), the lower keeps one reconverging storyline. Right
   bounds may differ per scope.
2. **Should `words_target` gain a default** (band midpoint) once validated
   live, making the coupling opt-out instead of opt-in? Leaning yes; not
   in PR-1 (exemplars and recorded fixtures stay bit-stable meanwhile).
3. **Texture forks containing real branches** (the author's "even
   containing branches") — deferred from v1; needs the mirroring story for
   a paralleled divergence (both arms fork? one?), which interacts with I7
   per-world convergence.
4. **May a texture arm relocate an intersection scene?** v1 says sites
   avoid nothing about intersections (they are pre-freeze adjacency, not
   gates), but a paralleled intersection scene re-textures a *shared*
   moment — fine by the contract (texture, not consequence), worth an
   author read on the first live story that does it.
