# `narration_scope` — POV/Coda Feasibility — Build Contract

> Status: **BUILT** (2026-07-13) — checkpoints 1–6 landed (model, GROW annotate,
> FILL consumption, SEED context, golden/fixtures, docs). **Live validation on
> Ollama remains** (the noir re-run + a real medium — see Risks/follow-ups).
> Resolves the epilogue/POV collapse-feasibility bug surfaced by the `scene_type`
> live validation (STATUS "Next up" kickoff, 2026-07-13). Frontier-authored
> (POV / freeze / story-model semantics). Sibling of
> [`scene-type-modulation.md`](scene-type-modulation.md) — same annotation
> machinery, same GROW-pre-freeze placement.

## The bug (one paragraph)

A weak-tier noir micro run ("The Black Bird", `gpt-oss:120b`) failed FILL twice
on its finale passage. The Voice fixed a single **3rd-person limited** POV
(Mace); `p-finale` collapsed a bridge + the climax `scene` + two `sequel`
aftermath/epilogue beats whose summaries described **world-scope events the
viewpoint character cannot perceive** ("the Falcon is auctioned… fueling
Victor's armaments"; "Mace becomes a cautionary ghost in rainy alleys" — his own
*posthumous* reputation). The writer hit a catch-22: include them → POV break
(fails review rule 1), omit them → missing beats. Two independent runs failed on
two different legitimate defects. Per **iron rule 5**, this is a structural
feasibility problem, not a writing failure — the model correctly refused to fake
omniscience.

## The reframe (why it is two problems, not one)

The corpus's own POV note
(`corpus/interactive-fiction/prose-and-language/narrative_point_of_view.md`)
supplies the distinction: **psychic distance** (camera distance) is a spectrum
*independent* of POV person. A limited narrator can pull the camera back to
far/summary register ("the city prepared for another day") without ever entering
another mind. The two failing beats are different animals:

- **(A) World-scope fact, deliverable by widening distance.** "The Falcon is
  auctioned; Victor's armaments grow." No other character's interiority — this is
  far-distance narration/coda, legitimate under limited POV. **This half is a
  prompt over-constraint**: `fill_write.j2`'s POV block says *"Only that
  narrator's thoughts… may be stated directly… Every other character reaches the
  reader only through what the narrator can observe,"* conflating *no other
  minds* (the true limited rule) with *close distance always* (no world
  summary). The model refused a rule that was miswritten. AGENTS.md §"Prompt and
  error-message quality": the prompt is the first suspect.

- **(B) Fact beyond the viewpoint character's horizon.** "Mace becomes a
  cautionary ghost" — his posthumous reputation, after he exits. No
  distance-widening rescues this inside a Mace-tied limited POV; the viewpoint
  character is gone. This needs a sanctioned detached/coda register — a real,
  corpus-permitted POV shift *"with a clear structural marker."* **This half is
  structural.**

## Root cause

POV is chosen at **FILL** (the `Voice` singleton — one POV string for the whole
book, `models/concept.py:Voice.pov`), but the beats whose feasibility depends on
POV are written at **SEED**, four stages earlier, with zero POV awareness — the
scaffold prompt does not even render `vision.pov_hint`, which already exists. So
SEED mints omniscient world-fact aftermath beats. The acute failure is then a
**collapse** event: heterogeneous beats (live scene + world coda) crushed into
one passage, forcing one register across incompatible material.

## Decisions locked (author-confirmed 2026-07-13)

1. **Mechanism: a narrow per-beat annotation + the prompt fix** (decision 1.a).
   Add `narration_scope ∈ {limited, wide}` to `Beat`, folded into GROW's existing
   `annotate` pass (one LLM call already tags every beat; it now emits
   `scene_type` **and** `narration_scope`), settled at the freeze like
   `scene_type`. **Not** a full per-beat viewpoint-character/distance field — that
   invites the mid-story head-hopping the corpus warns against and vastly exceeds
   the problem. The **case-A prompt fix ships regardless of the annotation** (it
   is a correctness fix to a blunt rule).

2. **No forced passage split** (decision 2, resolved *no* per the author's
   narrative argument). A passage may carry a `limited` paragraph then a `wide`
   paragraph; there is no reason the presentation unit must be single-register,
   and forcing a collapse boundary would insert a spurious single-option
   page-turn between a climax and its coda. FILL modulates register **per beat
   within a passage**, exactly as it already modulates prose intensity per
   `scene_type`. **POLISH collapse is untouched** — the fix lives entirely in the
   model, GROW's annotate pass, FILL, and the prompts. (The "mechanically better
   for writing" instinct behind a split is satisfied by the per-beat tag: each
   beat has a coherent register even inside a mixed passage.)

3. **Scope: epilogue default, opt-in elsewhere** (decision 3.a). The structural
   prior is `epilogue`-purpose → `wide`, everything else → `limited`. The annotate
   pass may mark *any* beat `wide` when the drama genuinely demands a world-coda a
   single character cannot perceive, but the prompt defaults hard to `limited` so
   `wide` is the deliberate exception, never the norm.

4. **Advisory, not gating.** No new G3/G4 invariant. Coverage is enforced at the
   annotate **apply** (repairable `ApplyError`, same as `scene_type`); unannotated
   beats fall back deterministically by purpose. No iron-rule-6 invariant / no
   violating-construction *invariant* test (unit tests only, below).

## The model (`models/structure.py`)

```python
class NarrationScope(StrEnum):
    LIMITED = "limited"  # inside the Voice's POV — no mind but the narrator's,
                         # though psychic distance may still widen (world facts
                         # the narrator could plausibly report)
    WIDE = "wide"        # a coda/epilogue register licensed to narrate beyond the
                         # viewpoint character's horizon (world aftermath, a
                         # character's fate after they exit) — a marked shift
```

- Add `narration_scope: NarrationScope | None = None` to `Beat`. `None` = "not
  annotated"; the effective value is derived, never assumed present.
- Add `effective_narration_scope(beat: Beat) -> NarrationScope` (the single
  fallback authority, mirroring `effective_scene_type`):
  1. `beat.narration_scope` if set (the LLM annotation);
  2. else by `purpose`: `EPILOGUE` → `WIDE` (a wrap-up after all dilemmas
     resolve is the sanctioned coda site);
  3. else → `LIMITED` (setup, bridge, residue, false-branch, every narrative
     beat: inside the Voice's POV — the conservative default).
- No aggregation helper is needed (unlike `passage_intensity`): scope is consumed
  **per beat** in the write/review prompt, not aggregated to a passage-level band.
  A passage's word band still comes from `passage_intensity` (`scene_type`)
  alone — scope does not touch length.

## The mutation (`graph/mutations.py`)

`set_beat_narration_scope(g, beat_id, scope)` — mirror `set_beat_scene_type`
exactly: reject a non-beat; **reject a frozen beat** (settled at the freeze, same
"scene_type is settled at the freeze" clause). Add `narration_scope` to the
settled-at-freeze note alongside `summary`/`scene_type`.

## GROW `annotate` pass (`pipeline/stages/grow.py`, `grow_annotate.j2`)

Extend the existing pass — do **not** add a new pass. It already runs after
`contextualize`, before `bridge`, once per run.

- **Schema:** `BeatScene` gains `narration_scope: NarrationScope` (enum →
  grammar-safe finite set, no pin needed). `annotate_proposal_schema` is
  unchanged except the wider `BeatScene`.
- **Context (`_annotate_beats`):** already renders per-beat `purpose`; ensure
  `purpose` and `is_ending` are visible so the model can anchor the
  epilogue/coda judgment. Render `vision.pov_hint` (the intended POV) so the model
  knows what "beyond the viewpoint character" means.
- **Prompt (`grow_annotate.j2`):** add the `narration_scope` definition beside the
  `scene_type` one. Per AGENTS.md prompt quality — *quote the rule, show the
  signal, anchor every case*:
  - **Default is `limited`.** Almost every beat is `limited`: the story has one
    viewpoint (the POV hint), and a `limited` beat is narrated inside it. Psychic
    distance may still widen for a world fact the narrator could plausibly know —
    that is *not* `wide`; `wide` is only for narration the viewpoint character
    could not deliver at all.
  - **`wide` is the marked exception.** A beat is `wide` only when it narrates
    events **beyond any single character's perception** — a world coda after the
    story's dilemmas resolve (an auction elsewhere, a faction's rise), or a
    character's fate after they exit the story (their legend, their death's
    aftermath). An `epilogue`-purpose beat is `wide` by default; a mid-story beat
    is `wide` only when the drama genuinely requires the omniscient coda register.
  - State the FILL consequence: a `limited` beat stays in the narrator's frame; a
    `wide` beat licenses the detached coda register (and the reviewer will *not*
    treat its world-scope narration as a POV break).
- **Apply (`_annotate_apply`):** already requires full coverage of `scene_type`;
  set `narration_scope` in the same loop via the new mutation. Report the
  `limited`/`wide` split in the run log beside the scene/sequel/micro counts. Same
  repairable `ApplyError` shape on missing/dup/stray.

## FILL consumption (`pipeline/stages/fill.py`, prompts)

Three prompt-level changes; **no word-band change** (scope is register, not
length — `scene_type`/`passage_intensity` still own the band).

1. **Case-A POV rewrite in `fill_write.j2` (ships regardless).** Split the current
   "POINT OF VIEW IS LIMITED" block into two rules:
   - **No other minds.** Only the narrator's thoughts/intentions/feelings are
     stated directly; every other character reaches the reader through observable
     behavior. (This is the real limited rule and stays enforced.)
   - **Distance may widen.** Being limited does *not* forbid world-scope summary
     the narrator could plausibly report from within the story's frame — far
     narration of setting, rumor, or aftermath is allowed as long as it enters no
     other mind. (This unblocks case A.)

2. **Per-beat `narration_scope` directive in `fill_write.j2`.** The write context
   already tags each beat with `[scene_type]`; add its `narration_scope`. Render
   each beat as `[scene_type · scope]` and add one directive: a `limited` beat is
   narrated inside the Voice's POV; a **`wide`** beat is a **coda** — the narration
   may step back to a detached register and state what the viewpoint character
   could not know (world aftermath, a character's fate beyond their exit). Write
   the shift as a clean register change at the paragraph, not a head-hop
   mid-sentence. This makes register modulation concrete **within** a passage: the
   climax paragraph stays `limited`, the coda paragraph goes `wide` — the author's
   "one paragraph wide, the next limited."

3. **Render `narration_scope` to the reviewer (`fill_review.j2`).** The review runs
   on the same `_write_context_for` context. Render each beat's scope and **key the
   POV rule (review rule 1) to it**: a `limited` beat must stay in the narrator's
   frame (a stated non-narrator interiority is a defect, as today); a **`wide`**
   beat may narrate world-scope facts and a character's fate beyond their horizon —
   that is licensed coda, **not** a POV break. Without this the reviewer fights the
   very coda the annotation authorized (the second noir failure was a
   reviewer-legitimate defect on exactly this axis).

## SEED context gap (`seed_scaffold.j2`, `_summary_brief.j2`)

Reduce overspecified omniscient beats at the source — advisory, not a gate:

- Render `vision.pov_hint` into the scaffold context/prompt so SEED writes
  aftermath/post-commit beats with the intended frame in view.
- Add one line to the aftermath/post-commit guidance: consequences should read as
  something a character in the scene experiences; a world-scope wrap-up that no
  single character can perceive (an event elsewhere, a reputation after death) is
  a **brief coda**, not a full scene — keep it short and name it as aftermath, so
  GROW's annotate pass will mark it `wide` and FILL will write it as a coda. (This
  does not require SEED to know the final POV; it biases toward
  perceivable-consequence beats and flags true codas as brief.)

## Golden story + fixtures + docs

- **Annotate `examples/keepers-bargain` beats** with `narration_scope` in the
  per-beat YAML. The keeper is an intimate limited story — almost every beat is
  `limited`. If it has an epilogue/wrap beat, mark it `wide`; otherwise the golden
  may be all-`limited` and still exercises the default fallback + the write/review
  rendering. Keep it gate-clean; confirm the hand-authored prose still reads clean
  under the rewritten POV block (the case-A rewrite must not newly flag intimate
  prose).
- **Fixtures — narrower than it looks.** MockProvider replays in *call order*,
  not by prompt hash, so the FILL write/review prompt wording changes need **no**
  re-record (per the 2026-07-13 reading-difficulty decision-log note). What does
  change: the GROW `annotate` recorded call must emit `narration_scope` per beat
  (the widened schema — apply rejects a missing field), and any snapshot that
  serializes beat YAML now carries `narration_scope`. So: update the recorded
  `annotate` proposal + refresh the GROW/FILL snapshots; the FILL prose fixtures
  themselves hold. Verify the generated e2e story reaches its stages with 0 gate
  errors.
- **Tests** (behavior, not an invariant): `effective_narration_scope` fallback
  table (annotation wins → epilogue→wide → else limited); `set_beat_narration_scope`
  write-then-frozen-reject; `annotate` apply now covers both fields
  (missing/dup/stray still repairable); the annotate schema carries the enum.
- **Docs:**
  - 01 §5 "Beat annotations": add `narration_scope` beside `scene_type` — the
    per-beat POV/coda signal, GROW-annotated pre-freeze, settled at freeze, with
    the epilogue→wide / else→limited fallback; note FILL modulates register per
    beat within a passage and the reviewer keys the POV rule to it.
  - 01 §10.3 (annotation trimming): `scene_type` **and** `narration_scope` are now
    built; `exit_mood` remains deferred; the rest stay trimmed.
  - 02 GROW Out contract: the annotate pass now writes each beat's `scene_type`
    **and** `narration_scope`.
  - 02 FILL: the write/review context tags each beat with scope; the POV rule
    distinguishes no-other-minds (always) from distance-widening (allowed) and
    coda register (wide beats).
  - STATUS.md: decision-log entry + resolve the epilogue/POV kickoff at the top of
    "Next up".

## Risks / follow-ups (flag, do not preempt)

- **Over-use of `wide`.** A model handed a per-beat `wide` toggle could over-mark
  and drift toward omniscient narration everywhere — the head-hopping the corpus
  warns against. Mitigation is entirely in the prompt (hard `limited` default,
  `wide` as the named exception) and the reviewer (a `limited` beat's POV break
  still fails). If a live run shows over-marking, tighten the annotate prompt
  before adding any gate.
- **Interaction with the freeze.** `narration_scope` is settled-at-freeze like
  `scene_type`; a POLISH-added beat (residue/false-branch/bridge) rides the
  `limited` fallback. That is correct: those are never codas.
- **No band interaction.** Scope must not leak into `words_for`/`passage_intensity`
  — length stays `scene_type`-owned. Keep the two signals orthogonal.
- **Live validation** (unbilled, per budget discipline): re-run the noir micro
  ("The Black Bird") and a real *medium* noir on `gpt-oss:120b`; the acceptance
  test is a human read — the finale writes clean, the coda reads as a deliberate
  detached wrap, and no mid-story beat drifts omniscient. The operator slip that
  made the original "medium" actually micro (a `cat >` overwrite dropping the
  `scope:` line) must not recur — confirm `scope: medium` in `vision.yaml`.

## Build order (checkpoints)

1. Model: `NarrationScope`, `Beat.narration_scope`, `effective_narration_scope`,
   `set_beat_narration_scope` mutation. + tests.
2. GROW `annotate`: widen `BeatScene`, extend `_annotate_apply`, render
   `pov_hint`/`purpose` in context, add the `narration_scope` block to
   `grow_annotate.j2`. + tests.
3. FILL: the case-A POV rewrite (ships regardless), the per-beat scope directive in
   `fill_write.j2`, the scope-keyed POV rule in `fill_review.j2`. + tests.
4. SEED: render `pov_hint`; add the perceivable-consequence / brief-coda line.
5. Golden-story annotation; re-record e2e fixtures; full `pytest`/`ruff`/golden
   `validate` green.
6. Docs (01, 02, STATUS).
7. (Follow-up) Live validation on `gpt-oss:120b` — the noir re-run + a real medium.
