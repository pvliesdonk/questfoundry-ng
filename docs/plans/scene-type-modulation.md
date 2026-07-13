# `scene_type` Structural Modulation — Build Contract

> Status: **plan** (2026-07-13). The hand-off spec in
> [`reading-difficulty.md`](reading-difficulty.md) § "Hand-off spec — the
> `scene_type` modulation build" is the parent; this is the sharpened,
> decisions-resolved contract a build session follows. Frontier-authored;
> mid-tier implementable against this spec.

## Goal (one line)

Give FILL a **per-beat prose-intensity signal** (`scene_type`) so style
distributes across passages — a plain, load-bearing baseline with a few
heightened peaks — instead of every passage running hot. This is the
*structural* fix the reading-difficulty effort identified: the disease is
unmodulated over-stylization, and heritage's cure was a beat annotation NG
deferred (design doc 01 §10.3) whose trigger has now fired.

## Decisions locked (author-confirmed 2026-07-13)

1. **Placement: GROW, pre-freeze.** `scene_type` is an *intrinsic property of
   the beat* — **why the beat exists dramatically** (Swain: a *scene* is active
   goal→conflict→turn; a *sequel* is the reactive processing after) — fixed when
   the beat is born and never restated. GROW is the last stage that establishes a
   beat's "why"; **POLISH only ever *adds* beats** (residue, false-branch,
   variants) for pacing/presentation and must never touch why an existing beat
   exists. Pre-freeze means `scene_type` is *settled at the freeze* exactly like
   `summary` (`mutations.set_beat_summary` already enforces "beat content is
   settled at the freeze") — **no freeze-exemption, no new invariant.** This is
   also heritage's placement (GROW Phase 4b).

   *Corollary settled in the same discussion:* the POLISH `arcs` pass
   (character-arc metadata) correctly stays in POLISH — a character arc is **not**
   a per-beat property but a *synthesis read off the whole frozen DAG*, so the
   "intrinsic-to-the-beat → GROW" rule does not bind it. Split: **GROW builds and
   freezes the skeleton (each beat's intrinsic `scene_type` included); POLISH
   reads the frozen skeleton to prepare what FILL needs (feasibility audit,
   passage summaries, character arcs).**

2. **Method: LLM classification + deterministic structural defaults.** One LLM
   pass judges `scene_type` for every beat present at annotate-time (SEED scaffold
   beats + GROW's per-world clones = all narrative beats + `setup`/`epilogue`).
   Scene-vs-sequel is a genuine narrative judgment a heuristic cannot make.
   Structural transition beats that a *later* stage adds — GROW `bridge`, POLISH
   `residue`/`false_branch` — never call the LLM; they ride a deterministic
   fallback by `purpose` (below). Split rule: **beats present at annotate-time →
   LLM; beats added later → purpose fallback.**

3. **Scope: `scene_type` only.** `exit_mood` (the other annotation 01 §10.3 named)
   stays deferred — it is not the intensity lever. `narrative_function` stays
   trimmed (already NG's decision).

4. **Advisory, not gating.** No G3/G4 error invariant on `scene_type` in this
   slice; unannotated beats fall back deterministically. Coverage of the
   annotatable set *is* enforced at the **apply** layer (repairable `ApplyError`,
   same pattern as `contextualize`/`audit`), which is not the same as a gate —
   "complete at the apply, advisory at the gate." No iron-rule-6 invariant / no
   violating-construction *invariant* test (there are unit tests, below).

5. **Pacing report (G4) and the `overwriting` guardrail come after.** This slice
   is model → GROW pass → FILL consumption → golden/fixtures/docs. Steps 4–5 of
   the parent plan (advisory G4 pacing report; `overwriting` variance metric) are
   follow-up PRs once the signal exists and a live run calibrates them.

## The model (`models/structure.py`)

```python
class SceneType(StrEnum):
    SCENE = "scene"          # active conflict — goal, obstacle, turn; may rise
    SEQUEL = "sequel"        # reactive processing — plain, shorter
    MICRO_BEAT = "micro_beat"  # transition — brief, low-key
```

- Add `scene_type: SceneType | None = None` to `Beat`. Default `None` = "not
  annotated"; the effective value is derived, never assumed present.
- Add a module-level `effective_scene_type(beat: Beat) -> SceneType` (the single
  fallback authority):
  1. `beat.scene_type` if set (the LLM annotation);
  2. else by `purpose`: `BRIDGE`/`FALSE_BRANCH` → `MICRO_BEAT`, `RESIDUE` →
     `MICRO_BEAT` (preserves today's texture short band — see FILL);
  3. else (an unannotated narrative/`setup`/`epilogue` beat — only on partial
     coverage) → `SCENE` (heritage's "absent → scene" default; conservative, never
     starves prose).
- **`is_texture` stays as-is** (purpose-based, `models/structure.py:92`). Its
  structural fallback in `effective_scene_type` is intentionally consistent with
  it (texture purposes → `MICRO_BEAT` → short band), so the two agree by
  construction; `effective_scene_type` is the richer signal FILL consumes, and
  `is_texture` remains the convenience predicate. Document the layering in both
  docstrings.
- Intensity ordering for aggregation: `SCENE > SEQUEL > MICRO_BEAT`.

## The mutation (`graph/mutations.py`)

`set_beat_scene_type(g, beat_id, scene_type)` — mirror `set_beat_summary`
exactly: reject a non-beat; **reject a frozen beat** (`if g.frozen and beat_id in
g.frozen.beats: raise MutationError(... "scene_type is settled at the freeze")`).
Pre-freeze it is settable (repair may re-run the pass); post-freeze it is settled.
No I9 change; add `scene_type` to the "settled at the freeze" note in
`freeze_topology`'s neighborhood / `set_beat_summary`'s docstring.

## The GROW `annotate` pass (`pipeline/stages/grow.py`)

Position: **after `contextualize`, before `bridge`** — after contextualize so the
per-world clone summaries are final (better scene/sequel judgment); before bridge
because bridges are definitionally `MICRO_BEAT` and ride the fallback, so the LLM
pass need not see them. Pass order becomes: intersections → weave → contextualize →
**annotate** → bridge → gate(freeze). Never skips (there are always narrative
beats).

- **Role:** `writer` (a narrative reading, like `contextualize`/`arcs`; not a
  topology decision, so not `architect`). One call per run — cheap. Tunable.
- **Schema:**
  ```python
  class BeatScene(BaseModel):
      beat: str
      scene_type: SceneType     # enum → grammar-safe finite set (A11), no pin
  class AnnotateProposal(BaseModel):
      annotations: list[BeatScene]
  ```
  `annotate_proposal_schema(project)` refpin-pins `("BeatScene", "beat")` to the
  **annotatable beat ids** = every beat present now (`queries.topological_order`),
  which is exactly SEED scaffold + GROW clones (bridge/residue/false_branch do not
  exist yet). `scene_type` needs no pin (enum).
- **Context (`_annotate_context`):** the ordered beat list with `summary`,
  `beat_class`, `purpose`, `dilemma_impacts` (effect names), `entities`,
  `is_ending`; the dilemma questions; the vision. The prompt (`grow_annotate.j2`)
  states the Swain definitions crisply and — per AGENTS.md prompt quality —
  *quotes the rule and shows the signal*: a **scene** advances a dilemma through
  active conflict (a `commits`/`complicates` beat is almost always a scene); a
  **sequel** is the reactive/decompression beat between scenes (a quiet
  `advances`, an `epilogue`); a **micro_beat** is a pure transition. Give the
  intensity consequence explicitly ("a scene earns heightened prose and a longer
  word band; a sequel/micro stays plain and short") so the model understands what
  it is choosing, not just labelling.
- **Apply (`_annotate_apply`):** require the proposal to cover the annotatable set
  exactly once (repairable `ApplyError` naming missing/duplicate/stray beats —
  same shape as `_contextualize_apply`); set each via `set_beat_scene_type`. Report
  the scene/sequel/micro counts (a useful pacing signal in the run log). This
  **deviates from heritage's lenient partial-coverage-4b** deliberately: NG's
  populate passes require coverage (contextualize, audit, passages), and forcing
  the signal to actually be produced is the whole point; the purpose fallback
  covers only later-added structural beats, not LLM laziness.

## FILL consumption (`pipeline/stages/fill.py`, `models/concept.py`)

The payoff. Two changes:

1. **Word band keys off intensity** (`ScopePreset.words_for`). New signature:
   ```python
   def words_for(self, *, intensity: SceneType, ending: bool = False) -> tuple[int,int]:
       lo, hi = self.words_per_passage
       if ending:
           return (lo, hi + 100)               # unchanged: climax headroom, on top
       span = hi - lo
       if intensity == SceneType.SCENE:
           return (lo, hi)                      # full band, may rise
       if intensity == SceneType.SEQUEL:
           return (lo, lo + 2 * span // 3)      # reduced — reactive, plainer
       return (lo, lo + span // 3)              # micro_beat — shortest (== today's texture band)
   ```
   A passage collapses ≥1 beats; its intensity is the **max** over
   `effective_scene_type` of its beats (a scene beat justifies the words; a sequel
   riding along must not starve it). New helper `_passage_intensity(g, beats)`.
   Replace both current call sites — `_write_context_for` (`fill.py:436`) and
   `_word_budget_finding` (`fill.py:618`) — which pass
   `texture=all(b.is_texture...)`, with `intensity=_passage_intensity(...)`.

   **Behavior preservation:** an all-texture passage (residue/false-branch →
   `MICRO_BEAT`) gets `(lo, lo+span//3)` — byte-identical to today's texture band.
   An all-`scene` passage gets `(lo, hi)` — today's non-texture band. **New:** a
   `sequel`-dominant passage gets the middle band (the modulation), and a
   lone-bridge passage tightens from full→short (a bridge *should* be brief).

   This band feeds the **graded** `_word_budget_finding` (`fill.py:614`), which is
   the load-bearing mechanism for per-passage length: length today is *not* an LLM
   rule (`word_budget` is not in `FILL_REVIEW_RULES`; the reviewer never sees a
   count or band) — it is a mechanical finding merged into the same graded loop the
   LLM findings feed, blocking only on a large miss. Keying the band off
   `scene_type` is therefore what makes length **self-correct per beat type** (the
   author's point, 2026-07-13): a correctly-short sequel now sits inside its band or
   gets at most a low-confidence, non-blocking finding, while a thin *scene* or a
   runaway is still caught. The exact tier arithmetic is thus not load-bearing —
   the graded finding adapts — which is why the aggregate recalibration below is a
   safe measure-after.

2. **Per-beat intensity directive** (`fill_write.j2`). The write context already
   renders per-beat summaries; add each beat's `effective_scene_type`, plus one
   line stating the passage's dominant intensity and its band. Directive text:
   a **scene** beat is where the prose may rise (active conflict — render the turn
   fully); a **sequel**/**micro_beat** beat stays plain, brief, low-key (reactive
   processing / transition — do not perform it). This makes PR #64's "STYLE
   BELONGS TO THE STORY, NOT TO THIS PARAGRAPH" directive **concrete per beat**:
   the band uses the aggregate, the *directive* uses the per-beat signal, so style
   distributes *within* a passage as well as across the story.

3. **Render `scene_type` to the reviewer too** (`fill_review.j2`). The review runs
   on the same `_write_context_for` context, but the template shows only
   `b.summary`. Render each beat's `effective_scene_type` there as well and frame
   `beat_infidelity`/register expectations by it — a plain, brief *sequel* is
   *correct* (not a defect to warn against), a *scene* is where fuller rendering is
   expected. Without this the reviewer can fight appropriate plainness; with it the
   qualitative judgment aligns with the modulation intent. (Length stays the
   deterministic graded finding — this is about the LLM axes not penalizing a
   correctly plain sequel, per the author's "reviewer gets beat types" point.)

## Golden story + fixtures + docs

- **Annotate `examples/keepers-bargain` beats** (hand-authored `scene_type` in the
  per-beat YAML): active-conflict / commit beats → `scene`; reactions and the
  quiet lead-ins → `sequel`; pure transitions → `micro_beat`. Keep it gate-clean;
  confirm FILL's hand-authored prose still sits in (or acceptably near) the new
  per-passage bands (bands are advisory findings, but the golden should read
  clean).
- **Re-record e2e fixtures** for the keeper run: the `annotate` pass adds one GROW
  LLM call, and the shifted FILL bands may change word-budget findings — re-record
  GROW→FILL recorded calls and refresh snapshots. Verify the generated e2e story
  still reaches its stages with 0 gate errors.
- **Tests** (mirror the behavior, not an invariant): `effective_scene_type`
  fallback table; `set_beat_scene_type` write-once + frozen-reject; `words_for`
  three-tier bands + ending headroom + texture-preservation; `_passage_intensity`
  max-aggregation; `annotate` apply coverage (missing/dup/stray repairable);
  refpin pins `beat` to the annotatable set.
- **Docs:**
  - 01 §10.3: change "NG starts with two" present-tense wording — `scene_type` is
    **built** (not "will start with"); `exit_mood` remains deferred. Add a short
    "Beat annotations" subsection defining `SceneType` and the GROW-owned,
    settled-at-freeze rule.
  - 01 beat-purpose table / Beat section: note `scene_type` and the
    `effective_scene_type` fallback.
  - 02 GROW: add the `annotate` pass to GROW's phase list and the Out contract
    ("each beat's `scene_type`"); keep the G4 pacing report marked deferred.
  - 02 FILL: replace the texture-band note in G5 with the three-tier
    `scene_type`→band mapping.
  - STATUS.md: decision-log entry + flip the "Next up" kickoff / "Known deferrals"
    `scene_type` item to built.

## Risks / follow-ups (flag, do not preempt)

- **Scale recalibration is a *measure-after*, not a derive-now** — and only the
  *aggregate* half of it. Per-passage length **self-corrects** through the graded
  `_word_budget_finding` once the band is `scene_type`-keyed (FILL consumption
  §1), so the exact tier arithmetic need not be nailed. What does not self-correct
  is the *aggregate* advisory picture: modulation lowers effective mean
  words/passage, so a sequel-heavy story trends toward the low end of `words_total`
  (B7, advisory) and the `tests/scale.py` simulation (uniform-band, pre-`scene_type`)
  reads slightly high. **Do not touch the scale table in this PR** (no data yet);
  after the first modulated live run, re-check `words_total`/`passages` bands and
  teach the sim a scene:sequel mix. Recorded as the calibration follow-up.
- **G4 pacing report** (parent step 4): advisory "no > N consecutive
  same-intensity passages," now buildable because the signal exists.
- **`overwriting` guardrail** (parent step 5): the *modulation-variance* metric
  (plain baseline + a few peaks across passages) + compound-density > 15/1k as the
  one clean aggregate red flag. Calibrated by the exemplars in the parent plan.
- **The "arc" naming overload** (author-agreed 2026-07-13): "arc" means both
  *computed story arcs* (playthroughs, iron rule 2) and *character-arc metadata*
  (`Entity.arc`). Worth a rename for clarity — **separate cleanup**, not this
  slice.
- **Live validation** (unbilled, per budget discipline): after the offline build
  is green, a targeted `gpt-oss:120b` run read by a human for whether style now
  modulates (plain sequels, heightened scenes) — the acceptance test is a human
  read, not a metric.

## Build order (checkpoints)

1. Model: `SceneType`, `Beat.scene_type`, `effective_scene_type`, mutation. + tests.
2. GROW `annotate` pass (schema, refpin, context, prompt, apply). + tests.
3. FILL consumption: `words_for` v2, `_passage_intensity`, `fill_write.j2`
   directive. + tests.
4. Golden-story annotation; re-record e2e fixtures; full `pytest`/`ruff`/golden
   `validate` green.
5. Docs (01, 02, STATUS).
6. (Follow-up PRs) G4 pacing report; `overwriting` guardrail; live validation;
   arc rename.
