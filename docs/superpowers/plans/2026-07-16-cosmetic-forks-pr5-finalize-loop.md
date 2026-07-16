# Cosmetic Forks PR-5 — the iterative finalize loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace POLISH's one-shot finalize budgets with a fixed-point
iteration of the one cosmetic-fork splice — engine-planned rounds, one small
LLM call per site, keywords minted per rendering and consumable by later
rounds — retiring the probe-scratch sizing and the mirrored-cadence machinery,
and landing the restated I15 and the new I16 with their checks and
violating-construction tests (docs/plans/cosmetic-forks.md §6).

**Architecture:** `finalize:0` stays today's residue pass (obligations before
decoration). Engine-only planner passes `finalize:<n>` (n ≥ 1, always skipped,
`expand` only) compute a `fork_plan` on the current graph and splice in one
`fork:<n>:<k>` LLM pass per admitted site plus the next planner; a terminal
round (no admissions) expands into the existing passage passes instead. Each
site pass words premises + fresh beats; the apply splices via
`insert_cosmetic_fork`, mints one cosmetic `StateFlag` per non-empty
rendering, and may wire one keyword-gated extra rendering.

**Tech stack:** Python ≥ 3.11, Pydantic v2, existing engine modules
(`pipeline/passages.py`, `pipeline/stages/polish.py`, `graph/*`), pytest.

## Global constraints

- All graph writes through `graph/mutations.py` (iron rule 1).
- Topology freeze is absolute; splices are additions only save the diamond's
  spine removal (I9).
- Invariant statement, check, and violating-construction test land together
  (iron rule 6): I15 restatement and I16 both in this PR.
- Retired machinery is **deleted**, not stranded; grep-verify.
- The golden story (`examples/keepers-bargain`) and every checked-in exemplar
  must validate unchanged — the restated I15 must accept the legacy
  mirrored-cadence structures in `examples/letter-and-frontier`.
- Every model-facing `ApplyError` carries reason + location + recovery action.
- `uv run pytest -q`, `uv run ruff check src tests`,
  `uv run qf validate examples/keepers-bargain` all green before pushing.

## Frontier decisions frozen here (sharpen `docs/plans/cosmetic-forks.md` in Task 11)

1. **Gated (keyword-consuming) extra renderings are edge-scale only in v1**
   (a diamond/sidetrack's extra arm, purpose `FALSE_BRANCH`). Grounds: plan §4
   v1 is consumption form (1), "the natural shape is a diamond's third arm";
   the discipline "a keyword never gates a scene-scale world"; and I15's
   field half keeps "texture beats are ungated" intact.
2. **Restated I15 shape half:** on the PREDECESSOR graph with every
   *un-mirrored* `FALSE_BRANCH` beat contracted away (bypassed), every edge
   incident to a `TEXTURE_WORLD` beat projects — one `mirrors` step per
   endpoint — onto an edge of that same contracted graph; and mirror chains
   are acyclic, grounding out in beats with `mirrors=None`. Un-mirrored means
   "no beat mirrors it": legacy mirrored-cadence twins point `mirrors` at
   `FALSE_BRANCH` beats, which therefore stay in the contracted graph and
   keep validating; new-loop decoration (never a twin — `qualifies()`
   excludes `FALSE_BRANCH` from segments) contracts away, so a diamond
   spliced inside either side of a two-worlds fork no longer breaks parity.
3. **Shape-cycle offset across rounds** = count of existing cosmetic
   `StateFlag`s (a pure function of the checkpointed graph, so ledger resume
   reproduces the same assignment).
4. **Keyword offers pinned at round-plan time** (rounds < n only, per §6's
   ledger ordering), stored in the site closure.
5. **Flag minting:** id `flag:cw-<head-beat-slug>` (strip `beat:`; `-2`,
   `-3`… suffix on collision), `description` = the rendering's premise
   (rendering 0: the trunk premise), `source=COSMETIC`, `path=None`.
6. **Edge-scale marginal words** for admission: one micro-band chunk per
   fresh rendering — `round(preset.words_for(intensity=MICRO_BEAT)[1] * 0.9)`
   each; segment-scale: `_stretch_words(g, segment, preset)` per fresh
   rendering. The optional gated rendering is not charged at admission
   (bounded: ≤1 per site, one consumer per keyword).
7. **FILL premise *stack*** (plan §3 consequence) is deferred to BACKLOG:
   words-budget rarely buys depth ≥ 2 (open question 3), and the fork prompt
   shows the host context so summaries stay world-consistent. Not in §6's
   build spec or acceptance.
8. **Small-segment tier** = the cap-aligned remainder windows (start % cap
   == 0, 1 ≤ length < cap) `texture_sites` currently discards; scene tier =
   today's ≥ cap windows; edge tier = today's aligned seam edges. `qualifies`
   drops the `TEXTURE_WORLD` exclusion (recursion) and adds a `FALSE_BRANCH`
   exclusion (decoration is never re-rendered — keeps decision 2 sound).
9. **B6/`projected_walks` over-holding** (open question 5): fixed, not
   documented — cosmetic flags become walk-accumulated (held when the walk
   traverses the granting group / takes the granting choice edge); dilemma
   flags stay view-derived.

---

### Task 1: `add_beat_flag_grant` mutation

**Files:** Modify `src/questfoundry/graph/mutations.py`; test
`tests/test_mutations.py`.

**Produces:** `add_beat_flag_grant(g, beat_id, flag_id)` — appends `flag_id`
to `Beat.grants_flags` (kept sorted, idempotent). Rejects: non-beat,
non-flag, non-cosmetic flag (`source != COSMETIC`). Legal on frozen beats
(the freeze is topological; this is the rendering-0 head annotation,
01 §6).

- [ ] Failing tests: grant lands sorted+deduped on a frozen beat; non-beat /
      non-flag / dilemma-flag each raise `MutationError` naming the corrective
      ("only cosmetic flags are granted via grants_flags; a dilemma flag is
      granted at its path's commit").
- [ ] Implement; run; commit.

### Task 2: walk-accumulated cosmetic holds (B6 + projection)

**Files:** Modify `src/questfoundry/pipeline/passages.py`
(`projected_walks`), `src/questfoundry/graph/validate.py`
(`check_b6_choice_cadence`); tests `tests/test_passages.py`,
`tests/test_invariants.py`.

In both walkers: `held` starts as the view-derived **dilemma** flags only
(`f.path is not None`); cosmetic flags accrue as the walk goes —
`projected_walks` adds a cosmetic flag when the current group contains one of
its grant beats; the B6 walker adds `e.payload.get("grants", [])` of each
choice edge it takes. Update the stale comment block in `projected_walks`
(the open-question-5 note) to state the resolved semantics.

- [ ] Failing test: a graph with a sidetrack granting `flag:cw-x` and a later
      gated choice — a projected walk that declines the sidetrack must not
      count the gated entry as live; one that takes it must.
- [ ] Implement both walkers; run `uv run pytest tests/test_passages.py
      tests/test_invariants.py -q`; commit.

### Task 3: segment tiers + recursion enablement

**Files:** Modify `src/questfoundry/pipeline/passages.py`; test
`tests/test_passages.py` (move/extend the `texture_sites` tests).

**Produces:**
- `fork_segments(g, preset) -> tuple[list[list[str]], list[tuple[str, str]]]`
  — `(segments, seam_edges)`. Generalizes `texture_sites`: same window walk
  per uncapped run, but windows of length ≥ 1 qualify (scene tier ≥ cap,
  small tier 1..cap−1 — the remainder windows currently dropped by the
  `end - start + 1 >= cap` test); seam edges = the cap-aligned interior
  edges (`(e + 1) % cap == 0`) of `long_linear_runs`, excluding edges whose
  endpoints lie inside any qualifying segment window is NOT required (the
  planner handles overlap at admission). `qualifies()`: not gated / no
  commits / not ending / `purpose != FALSE_BRANCH`; the `TEXTURE_WORLD`
  exclusion is dropped (recursion). Frontier-boundary exclusion kept for
  segments.
- `scene_fork_count(g, cap) -> int` — existing scene-scale fresh renderings:
  maximal chains of mirror beats (`mirrors` set, linked by PREDECESSOR,
  twins consecutive) of length ≥ cap.
- `_mirror_onto_segment`: delete the "worlds do not nest" rejection (twin
  may be `TEXTURE_WORLD`); everything else stays.

- [ ] Failing tests: a 7-beat run at cap 3 yields one scene window and the
      1-beat remainder as a small segment; a texture arm's interior seam edge
      appears in `seam_edges` (recursion); a `FALSE_BRANCH` chain yields no
      segment; `scene_fork_count` counts a spliced 3-beat world once and a
      1-beat small fork zero times; nesting splice (`insert_texture_world`
      over a stretch inside an existing arm) succeeds.
- [ ] Implement; run; commit.

### Task 4: the round planner (`fork_plan`) + keyword offers

**Files:** Modify `src/questfoundry/pipeline/passages.py`; test
`tests/test_passages.py`.

**Produces:**

```python
@dataclass(frozen=True)
class ForkSite:
    before: str            # edge-scale: the seam edge; segment-scale: entry anchor (segment head's id)
    after: str             # edge-scale: seam successor; segment-scale: ""
    segment: tuple[str, ...]  # () for edge-scale
    arms: int              # fresh renderings: 1 = sidetrack/two-worlds, 2-3 = diamond
    keywords: tuple[str, ...]  # offered consumable keywords (≤ 8), pinned at plan time
```

`fork_plan(g, preset, words_target=None) -> list[ForkSite]` — one round's
admissions, deterministic:

1. `lo, hi = B6_WORDS_PER_CHOICE; target = (lo + 2*hi) // 3`;
   `limit = words_target or preset.words_total[1]`;
   `total = projected_total_words(g, preset)`; scratch = deepcopy(g).
2. Admit **segments first** (scene then small, longest first, then head id),
   while `projected_mean(scratch) > target`: scene segments also require
   `scene_fork_count(g, cap) + admitted_scene < TEXTURE_WORLDS_MAX`; marginal
   = `_stretch_words(g, seg, preset)`; skip if `total + marginal > limit`;
   probe-splice `insert_texture_world` into scratch; `arms=1`.
3. Then **seam edges** in bisection order per run, largest-remaining-run
   first (today's `cadence_plan` order), skipping edges incident to a beat of
   an admitted segment; shape from
   `preset.cadence_arm_cycle[(offset + j) % len(cycle)]` where `offset =
   count of cosmetic StateFlags in g`; marginal = arms ×
   `round(preset.words_for(intensity=SceneType.MICRO_BEAT)[1] * 0.9)`; skip
   if over limit; probe-splice (`insert_false_branch` 2-arm probe, or
   `insert_sidetrack` for arms=1) into scratch.
4. Stop when mean ≤ target or capacity/words exhausted. Order the returned
   sites by segment-head/`before` beat id (stable pass naming).
5. Each site's `keywords` = `offered_keywords(g, anchor)` where anchor is
   the segment head or `before`: cosmetic flags, unconsumed (no beat's
   `requires_flags` contains them), whose every grant beat is in
   `queries.ancestors(g, anchor)` (strictly upstream), sorted, first 8.
   Computed on `g` (the round-start graph), so offers are rounds < n by
   construction.

Also `offered_keywords(g, before_id) -> list[str]` as a named helper.

- [ ] Failing tests: (a) on a linear medium-ish synthetic graph the plan
      admits sites and two consecutive calls return identical plans;
      (b) words headroom blocks a scene segment but admits a cheaper edge
      site; (c) TEXTURE_WORLDS_MAX counts pre-existing worlds via
      `scene_fork_count`; (d) shape cycle offset shifts when cosmetic flags
      exist; (e) `offered_keywords` excludes consumed flags, non-upstream
      grants, and caps at 8; (f) a graph already at the B6 target returns [].
- [ ] Implement; run; commit.

### Task 5: I15 restated — statement, check, tests together

**Files:** Modify `src/questfoundry/graph/validate.py`
(`check_i15_texture_worlds`), `docs/design/01-story-model.md` §8 (I15 text);
test `tests/test_texture.py`.

Field half changes: mirror chains must be acyclic and ground out (follow
`mirrors` with a seen-set; cycle or dangling ⇒ error); the twin may itself be
a mirror beat (delete the "worlds do not nest" error); twin
gate/commit/ending and effective-annotation parity checks stay; arm beats
stay ungated. Shape half: per frozen decision 2 — build the contracted edge
set (bypass every `FALSE_BRANCH` beat that no beat mirrors), then for each
contracted edge incident to a mirror beat require the one-step projection to
be a contracted edge with `ps != pd`. Error messages keep the current
actionable phrasing, updated for the new rule ("…projects onto {ps} -> {pd},
which is not an edge of the decoration-contracted trunk; the rendering must
run parallel to its segment and rejoin exactly where it does").

01 §8 I15 restated (segment-relative, composition-closed, budget parity):
field half — every `texture_world` beat names a twin via `mirrors`; chains
are acyclic and ground out in non-mirror beats; the ground twin is ungated,
commits nothing, ends nothing; the beat carries its twin's *effective*
annotations and no gate of its own. Shape half — on the graph with un-mirrored
`FALSE_BRANCH` decoration contracted, every edge incident to a mirror beat
projects onto an edge of that graph. Structural choice-topology parity is
**retired** (ratified decision 1): each rendering grows its own forks and
per-walk B6 owns choice fairness (budget parity).

- [ ] Failing tests (violating constructions + acceptances): mirror cycle ⇒
      error; nested world (arm over an arm stretch) ⇒ validates; diamond
      spliced un-mirrored inside a mirrored trunk stretch ⇒ validates;
      diamond inside the arm ⇒ validates; arm that rejoins one beat early ⇒
      still an error; legacy twin-of-FALSE_BRANCH structure (build via the
      old shape: fresh twins mirroring a FALSE_BRANCH chain) ⇒ validates.
- [ ] Implement check + update 01 §8 in the same commit; run
      `uv run pytest tests/test_texture.py -q` and
      `uv run qf validate examples/letter-and-frontier`; commit.

### Task 6: I16 — cosmetic-gate locality

**Files:** Modify `src/questfoundry/graph/validate.py` (new check, POLISH
gate list), `docs/design/01-story-model.md` §8 (I16 text); test
`tests/test_invariants.py`.

`check_i16_cosmetic_gate_locality`: for every `StateFlag` with
`source == COSMETIC`: (a) every beat whose `requires_flags` contains it has
`purpose in (FALSE_BRANCH, TEXTURE_WORLD)`; (b) every CHOICE edge whose
`requires` contains it targets a passage all of whose beats carry a
rendering purpose. Message names the flag, the offender, and the rule ("a
cosmetic keyword may gate only a cosmetic-fork rendering — downstream must
never depend on it; a required callback is a dilemma in costume and belongs
in GROW"). 01 §8 gains the I16 statement verbatim from the plan (§4, "the
obligation boundary, made structural").

- [ ] Failing tests: a GROW-ish narrative beat gated on a cosmetic flag ⇒
      I16 error; a choice edge into an ordinary passage requiring one ⇒ I16
      error; a FALSE_BRANCH rendering beat gated on one ⇒ clean.
- [ ] Implement + 01 §8 text in the same commit; run; commit.

### Task 7: finalize:0 shrinks to residue

**Files:** Modify `src/questfoundry/pipeline/stages/polish.py`,
`src/questfoundry/pipeline/prompts/polish_finalize.j2`; tests
`tests/test_passages.py` / `tests/test_proposal_schemas.py` /
`tests/test_prompts.py` (wherever finalize schema/apply/prompt are covered).

- `FinalizeProposal` keeps only `residue`; delete `FalseBranchSpec`,
  `TextureWorldSpec`, `TextureBeatSpec`, `ArmSpec` (the `ForkSpec`/
  `FollowupSpec` residue models stay). `_finalize_apply` keeps only the
  residue half (drop the texture/cadence validation and splices and the
  `_texture_and_cadence` call). `_finalize_context` drops
  `cadence`/`texture_sites`/`reserve`; `_finalize_skip` skips iff no light
  needs; `finalize_proposal_schema` pins residue + entities only. Pass
  renamed `finalize:0`, role/template unchanged; its `expand` becomes the
  Task 8 round scheduler (this task may temporarily keep `_polish_expand`).
- `polish_finalize.j2`: delete the TEXTURE WORLDS, FALSE BRANCHES, and
  RESERVED MATERIAL blocks (they move to the fork prompt); keep residue +
  `_craft`/`_summary_brief`/`_shared` includes.

- [ ] Update the failing finalize tests to the residue-only contract (tests
      for the removed halves are rewritten in Task 8's per-site form, not
      deleted wholesale — shape enforcement, premise checks, beat-count
      checks all survive as fork-pass tests).
- [ ] Implement; run; commit.

### Task 8: the loop — round passes, per-site fork passes, minting, consumption

**Files:** Modify `src/questfoundry/pipeline/stages/polish.py`; create
`src/questfoundry/pipeline/prompts/polish_fork.j2`; tests in
`tests/test_passages.py` (or a new `tests/test_fork_loop.py`).

**Pass wiring:**

```python
def _round_spec(n: int) -> PassSpec:
    return PassSpec(
        name=f"finalize:{n}",
        role="writer",
        template="polish_fork.j2",      # never rendered; the pass always skips
        schema=FinalizeProposal,         # unused
        build_context=lambda project: {},
        apply=lambda proposal, project: [],
        skip_if=_round_skip(n),          # ALWAYS returns a reason string
        expand=_round_expand(n),
    )

def _round_skip(n):
    def skip(project):
        plan = pc.fork_plan(project.graph, project.vision.preset,
                            project.vision.words_target)
        if plan:
            return f"engine round {n}: {len(plan)} fork site(s) scheduled"
        return f"engine round {n}: terminal (B6 target reached or budget exhausted)"
    return skip

def _round_expand(n):
    def expand(project):
        plan = pc.fork_plan(project.graph, project.vision.preset,
                            project.vision.words_target)
        if not plan:
            return _polish_expand(project)   # the passage passes
        passes = [_fork_pass(n, k, site) for k, site in enumerate(plan)]
        passes.append(_round_spec(n + 1))
        return passes
    return expand
```

`finalize:0`'s `expand` returns `[_round_spec(1)]`. `audit`/`arcs` stay as
the following static passes.

**Per-site proposal** (schema pinned per site: `renderings` length ==
`site.arms`; `trunk_premise` required iff `site.segment`; `beats` length ==
`len(site.segment)` for segment-scale enforced in apply, 1–2 for edge-scale
via schema; `gated` forbidden (`None` only) when `site.segment` or no
`site.keywords`; `gated.keyword` enum-pinned to `site.keywords`; all
`entities` pinned via `refpin.pin`):

```python
class ForkBeatSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    summary: str
    entities: list[str] = []

class RenderingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    premise: str
    beats: list[ForkBeatSpec] = Field(min_length=1)

class GatedRenderingSpec(RenderingSpec):
    keyword: str

class ForkProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trunk_premise: str = ""
    renderings: list[RenderingSpec]
    gated: GatedRenderingSpec | None = None
```

**Apply (`_fork_apply(site)`)**, in order, all violations actionable:
1. Premise non-empty per rendering (+ trunk_premise when segment-scale;
   forbidden non-empty when edge-scale).
2. Beat counts: segment-scale ⇒ every rendering `len(beats) ==
   len(site.segment)` (I15 wording as today); edge-scale ⇒ 1–2 beats.
3. Build chains: segment-scale ⇒ purpose `TEXTURE_WORLD`; edge-scale ⇒
   `FALSE_BRANCH`; `texture_premise=premise` on every fresh beat; gated
   chain additionally `requires_flags=[gated.keyword]`.
4. Splice: segment-scale ⇒ `insert_cosmetic_fork(g, [SEGMENT_RENDERING,
   *fresh], segment=site.segment)`; edge-scale arms==1 ⇒ `[EMPTY_RENDERING,
   *fresh]` on `(before, after)`; arms ≥ 2 ⇒ `[*fresh]`. The gated chain
   rides as one more fresh rendering.
5. Trunk premise: `mutations.set_beat_texture_premise` on each segment beat.
6. Mint per non-empty rendering (rendering 0 included; the gated rendering
   included; the empty rendering excluded): flag id per frozen decision 5,
   `mutations.add_flag(g, StateFlag(id=..., created_by=Stage.POLISH,
   description=premise, source=FlagSource.COSMETIC))`, then grant on the
   rendering's head beat — fresh heads and rendering 0's segment head via
   `mutations.add_beat_flag_grant`.
7. Summary lines name the shape, the premises, and minted keywords.

**Prompt `polish_fork.j2`** (frontier prompt work — port the deleted
TEXTURE WORLDS / FALSE BRANCHES / RESERVED blocks into a single per-site
brief): vision + cast roster (the entity-id trap note), the site — either
the segment's beats with summaries ("re-express the SAME events, one beat
per trunk beat, in order, renderings are peers, both premises name the same
consequence-free axis") or the edge with `before`/`after` summaries and the
assigned shape spelled out (sidetrack/diamond semantics, the §5
residue-mark rule: every arm's summary states the mark its exit label will
carry, distinct from siblings'); reserve feedstock (graft, never advance);
offered keywords with their descriptions and the optional gated rendering
contract ("you MAY add one extra rendering visible only to readers holding
one offered keyword — same size budget as any rendering, acknowledges,
never rewards; consumption is optional, never assigned"); fresh-id coinage
rules verbatim from today's prompt; `_craft`/`_shared` includes.

- [ ] Failing tests: (a) segment-scale apply splices, sets both premises,
      mints 2 keywords (rendering 0 + fresh), grants sit on both heads;
      (b) sidetrack apply keeps the direct edge, mints 1; (c) 3-arm diamond
      mints 3; (d) wrong beat count / empty premise / trunk_premise on an
      edge site ⇒ ApplyError with corrective; (e) gated rendering: splices
      as extra arm, beats gated on the consumed keyword, its own keyword
      minted, I16 + I10 + I13 pass on the result; (f) the same keyword is
      absent from a later `fork_plan`'s offers (consumed); (g) pass-name
      determinism: `_round_expand(1)` twice on the same graph ⇒ identical
      names.
- [ ] Implement + write the prompt; `tests/test_prompts.py` renders
      `polish_fork.j2` for both site shapes; run; commit.

### Task 9: retirement sweep

**Files:** Modify `src/questfoundry/pipeline/passages.py`,
`src/questfoundry/pipeline/stages/polish.py`, `tests/scale.py`,
`tests/test_scale.py`, `tests/test_passages.py`, `tests/test_texture.py`,
`tests/test_refpin.py`.

Delete: `_texture_and_cadence` (polish.py), `cadence_plan`, `texture_plan`,
`texture_sites`, `insert_cadence_diamond`, `insert_cadence_sidetrack`,
`_arm_pairs`, `_twin_chain` (passages.py). Migrate `tests/scale.py`'s
structural simulation to drive `fork_plan` iteratively (splice each round's
plan with probe content until terminal) so the scale table's calibration
path still exists; update `test_scale.py` expectations only if the
simulation's numbers move (they measure the same machinery the pipeline now
runs — if bands shift, that is a real recalibration: flag it in the PR body
rather than silently retuning).

- [ ] Rewrite tests that exercised removed symbols to assert the new state.
- [ ] Verification (run, expect no hits in src/):
      `grep -rn "cadence_plan\|texture_plan\|texture_sites\|insert_cadence_\|_texture_and_cadence\|_twin_chain\|_arm_pairs" src/`
- [ ] Full suite; commit.

### Task 10: the offline loop fixture (acceptance)

**Files:** Create `tests/test_fork_loop.py` (or extend Task 8's file); uses
the DictLoader template seam (`runner._environment`) and a scripted mock
adapter (existing `test_runner.py` pattern).

Build a synthetic frozen medium-ish project (long linear runs, one soft
dilemma with light residue, a reserve dilemma), run `run_stage` for POLISH
end-to-end with a mock adapter that answers `finalize:0`, every
`fork:<n>:<k>` (round ≥ 2 answers consume one offered keyword), the
summary/labels/audit/arcs passes. Assert, per plan §6 acceptance:
- the loop reached a terminal round (a `finalize:<n>` report line says
  terminal, and passage passes ran after it);
- every projected walk's words-per-choice is inside `B6_WORDS_PER_CHOICE`;
- every non-empty rendering minted a keyword (count cosmetic flags ==
  count of granting heads; each fresh chain head and each rendering-0 head
  carries exactly one grant);
- at least one keyword was consumed by a gated rendering; I16 present in
  the gate set and clean; I13 clean;
- gate G4 returns no errors.

- [ ] Write fixture + assertions (fails before Tasks 7–8 complete, passes
      after); run; commit.

### Task 11: documentation half

**Files:** Modify `docs/design/01-story-model.md` §6,
`docs/design/02-pipeline.md` (POLISH), `docs/plans/cosmetic-forks.md`,
`docs/BACKLOG.md`, `docs/STATUS.md`, `docs/decision-log.md`.

- 01 §6: the shapes table gains the small two-worlds row as *built*; the
  mirrored-cadence sentence ("One asymmetry remains…until then this clause
  is current behavior") is replaced by the budget-parity statement; the
  finalize loop, minting (`flag:cw-*`, one per non-empty rendering, empty
  rendering unmarked — ratified decision 3), and v1 consumption
  (keyword-gated extra rendering, edge-scale, acknowledges-never-rewards,
  one consumer per keyword) are described as current behavior. (I15/I16 §8
  text landed with Tasks 5–6.)
- 02 POLISH: phase 1 rewritten — round 0 residue, budget rounds
  `finalize:<n>` expanding into per-site `fork:<n>:<k>` passes, engine
  shape/count assignment, termination conditions, keyword ledger ordering;
  the G4 row adds I16.
- cosmetic-forks.md: status line → PR-5 shipped; record the frozen
  decisions (this plan's list) under a "PR-5 build decisions" note; answer
  open question 4 (resume determinism: expansion is a pure function of the
  checkpointed graph — cite the determinism test) and mark 5 fixed.
- BACKLOG: add the FILL premise-stack loose end (frozen decision 7); close
  any B6-over-hold / 44-sidetracks entries this PR resolves.
- STATUS: PR-5 shipped, next steps (PR-6 deferred until a live run mints
  keywords; the medium exemplar thread).
- decision-log: dated entry for the build session.

- [ ] Make all edits; every 01/02 sentence true of the merged code; commit.

### Task 12: full verification

- [ ] `uv run pytest -q` — all green.
- [ ] `uv run ruff check src tests` — clean.
- [ ] `uv run qf validate examples/keepers-bargain` — green.
- [ ] `uv run qf validate examples/letter-and-frontier`,
      `examples/closed-circle-medium`, `examples/closed-circle-k2` — green
      (legacy structures under restated I15).
- [ ] Re-run the Task 9 retirement grep — no hits in `src/`.
- [ ] Commit any stragglers; open the draft PR (body: contract pointer to
      cosmetic-forks.md §6, the doc-truth checklist, the frozen decisions).
