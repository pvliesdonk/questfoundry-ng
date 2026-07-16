# Backlog — working loose ends

Sub-epic tasks that aren't owned by a roadmap epic. One line each; a task owned
by a future epic lives **under that epic in [`design/05-roadmap.md`](design/05-roadmap.md)**,
not here (that's the rule that stops this list and the roadmap from duplicating).
Close an item by **deleting** it — git history keeps the record; a lasting
architecture decision it settled gets a mini-ADR row (design doc 03 §9), a
notable one a dated entry in [`decision-log.md`](decision-log.md).

> Written and maintained by coding agents for hand-off (see AGENTS.md
> §"Documentation contract"). An item's framing is an agent's, not the author's,
> unless it says otherwise.

## Prompt & error-message quality

- [ ] **Prompt-template audit (all 28 templates), author-requested 2026-07-14.**
  The repair-*message* audit is done (decision log, 2026-07-14: all 79
  `ApplyError` sites judged, 17 fixed) after a blunt finalize message survived
  earlier claimed audits; the *prompt* half has NOT had the same exhaustive
  pass and must not be assumed audited. Audit each template against AGENTS.md
  §"Prompt and error-message quality" (rules structurally enforced, intent
  explicit, no reliance on inference) and record per-template verdicts so the
  claim is checkable: `_craft`, `_shared`, `_summary_brief`, `brainstorm`,
  `dream`, `dress_briefs`, `dress_codewords`, `dress_codex`,
  `dress_codex_review`, `dress_direction`, `fill_review`, `fill_summary`,
  `fill_voice`, `fill_write`, `grow_annotate`, `grow_bridge`,
  `grow_contextualize`, `grow_intersections`, `grow_weave`, `polish_arcs`,
  `polish_audit`, `polish_finalize`, `polish_fork`, `polish_labels`, `polish_summary`,
  `research`, `seed_order`, `seed_scaffold`, `seed_triage`. Known open
  question to fold in: DREAM's envision rewrote an authored rotating
  `pov_hint` into a single-head scheme (observed live 2026-07-14, root cause
  fixed: the prompt never saw the authored hint) — the audit bar for
  `dream.j2` is *visibility*, not preservation: the model must SEE the
  authored inclination as vision input; reinterpreting it is DREAM's job
  (author decision, 2026-07-14, decision log).

- [ ] **Finalize/audit prompt defects surfaced by the structural-depth medium
  run (2026-07-15).** Concrete instances of the template-audit item above,
  found running DREAM→POLISH at medium on `gpt-oss:120b-cloud` (unbilled;
  scorecard in the decision log):
  - **Finalize entity roster — FIXED** (PR #92, merged):
    `_finalize_context` pinned `entities` to the retained cast's ids but never
    showed the roster, so the writer coined a name-derived id
    (`character:finch` for the sheriff whose id is `character:marshal`) and
    finalize halted. Fix: pass the cast, list `name (id): concept`.
    Live-validated.
  - **Cadence shape bias toward sidetracks — FIXED** (PR-3 #98: the
    engine assigns shape and count; PR-5: the loop's per-site schema pins
    the assigned rendering count, so the model never chooses a shape).
  - **PR-0 residue paragraph is sidetrack-only vocabulary — FIXED** (this PR):
    the exit-label residue paragraph PR-0 added ("the detour", "declined",
    "the arm rejoins the same road") was wrong for a diamond arm; rewritten
    shape-neutral (an arm rejoins a shared destination alongside its siblings,
    trunk or diamond arm), the SIDETRACK bullet keeping "detour" as its own
    shape. Render test guards it.
  - **Audit pass halt — FIXED** (PR #95): the `polish_audit` single call over
    every ambiguous-state passage (137 at medium, many near-identical texture
    renderings) degenerated into wholesale repetition — the A21 giant-call
    defect, confirmed against a clean prompt + message. Decomposed per passage
    (planner + `audit:<pid>` expand); a follow-up marks endings unsplittable
    in the prompt (the rule had lived only in the apply's error message).
    Live-validated: the resumed medium run completed POLISH gate-clean, I12
    **71 → 0**, 132 audit-split variants, 0 halts.
  - **Over-cap ending with every state relevant** (edge case, PR #95 review,
    not yet observed): the endings fix resolves an over-cap ending by marking
    a non-addressed dilemma irrelevant — which works only while such a dilemma
    exists. An ending that is over the I12 cap AND genuinely turns on every
    state has no honest audit resolution (endings cannot split, and marking a
    truly-relevant state irrelevant violates the audit's honesty rule). Per
    AGENTS.md "fix structure upstream, never patch with prose" that is a
    GROW/POLISH routing defect (too many soft threads collecting at one
    finale — route their payoffs into gated residue before it), which the
    audit should fail loudly on, not a prompt fix. Flag for a run that hits it.

- [ ] **Echo guard vs canonical utterances (two live instances, 2026-07-14).**
  The window-echo floor (8 shared tokens) collides with fixed statements the
  drama must repeat across adjacent passages: Jordan's theory declaration and
  Marta's alibi ("said I was alone in the library") both exhausted repairs in
  the *Closed Circle* medium run — the second WITH the restated-dialogue
  corrective already in the prompt and repair brief, so this is a design gap,
  not message bluntness. A weak writer cannot always paraphrase a short
  canonical utterance below 8 shared tokens when the beat mandates its
  content. Needs a designed allowance (e.g. a quoted-utterance exemption for
  short runs inside quotation marks in both passages), weighed against the
  laundering risk (a lifted run dressed as a quote) — frontier judgment, its
  own PR. Until then the operator move is a fresh re-roll of the stuck
  passage's cached call chain.

## Structure & scale

- [ ] **Scale recalibration after modulation.** `scene_type` shortens
  sequel/micro passages, so the `words_total`/`passages` (B3/B7) bands read
  high. **Tier confound to calibrate around** (author, 2026-07-14, restating a
  heritage QuestFoundry finding from the :4B era): floor-phrased counts ("at
  least N", open band positions) are tier-dependent sizing knobs — a small
  model reads the floor as the target, a strong model fills toward the
  ceiling when it can reason more fits; live 2026-07-14, the same medium
  premise produced a ~40% larger passage layer on kimi-k2.5 than on
  gpt-oss:120b. Calibration must state per-tier expectations or tighten the
  bands it wants respected. The material-density half of this item moved to
  the "Structural depth" milestone and its PR-1 is built (2026-07-14,
  `docs/plans/structural-depth.md` W1): the dilemma budget couples to
  `words_target` (B1), bridge share warns at 25% (B9), and the knob
  decision rule is recorded there — mandatory-at-apply only where the
  target is engine-computed, exact, *and* in-pass repairable; the remaining
  floor-phrased knobs (scaffold shape bands, intersection group counts,
  residue fork uptake) get judged against that three-part test when they
  next bite. What stays here: re-measure the preset `passages`/`arc_beats`/
  `words_total` bands against a modulated live run (`tests/scale.py`) and
  adjust — those bands do not yet scale with a coupled budget. Data point:
  the 2026-07-14 *Closed Circle* `gpt-oss:120b` medium run reached POLISH
  at **59 passages against the 90–160 band** (its B3 advisory). Provenance:
  observed live in that scratch run (not committed) — treat as an
  unverified agent observation until reproduced.
- [ ] **Texture worlds overshoot the words budget (medium run, 2026-07-15)
  — mechanism replaced, re-measure live.** The one-shot admission that
  produced +38% B7 is retired: PR-5's `fork_plan` charges every site's
  marginal story words against the headroom (`words_target` or band top)
  per admission with probe-measured exact pricing, edge shapes degrade at
  the boundary — but mandatory stretch-break sites are words-EXEMPT
  (author, 2026-07-16: interruption outranks the ceiling; calibration
  later), so B7 may exceed the target by the break surplus (~+14% on the
  live graph). The density calibration should restore honest headroom;
  re-measure then.
- [ ] **Intersections over post-commit (exclusive) beats** — M2 only groups
  shared pre-commit beats; exclusive-beat intersections are meaningful but
  interact with arc membership in ways the spine model doesn't cover. Same for
  **temporal hints inside atomic fork units** (a hint there has nothing to
  move). Revisit when a generated story demands one.
## Prose & annotations

- [ ] **FILL premise *stack* for nested renderings (cosmetic-forks §3,
  deferred at PR-5).** A beat carries one `texture_premise` (its own
  rendering's); a beat inside a nested construct — decoration inside an
  arm, a world within a world — should render under the host rendering's
  backdrop too (outer + inner, stacked like world truths after hard
  forks). Deferred: the words budget rarely buys depth ≥ 2 (plan open
  question 3) and the fork prompt shows the host premise so summaries stay
  world-consistent; FILL still reads only the beat's own premise. Build
  when a live read shows a nested passage contradicting its host world:
  derive the stack by chasing `mirrors` grounds and, for decoration, the
  construct's entry beat's premise.

- [ ] **Shadows: prompt what explicitly did NOT happen (author idea,
  2026-07-15, prose-quality scope).** FILL's write context already carries
  `_shadows` (every dilemma's answers, explored/unexplored, global to the
  book) with "let their weight color the prose, never name them". Worth
  exploring a route-local sharpening: at THIS passage, on THIS reader's
  route, the events that did not occur (the rival path's commits, the
  foreclosed flags' descriptions) stated explicitly as absences the prose
  can honestly shade around — negative space as a prose-quality lever.
- [ ] **Head-scheme conformance is ungated (live kimi A/B, 2026-07-15).**
  GROW annotate assigned the *victim* (Bernard Croft) as viewpoint head for
  4 passages while `Voice.pov` declares a four-head rotation without him —
  I14 (one head per passage) and G3 (head is a retained character) both
  pass; nothing checks head ∈ the declared scheme. Decide: gate it (the
  scheme is authoritative), or bless off-scheme heads as legitimate
  (prologue/epilogue/victim's-eyes passages are a real device) and make
  the voice pass *declare* what annotate assigned. Frontier judgment.
- [ ] **Interludes never fire at annotate (both tiers, 2026-07-14/15).**
  Two live mediums declared a journal interlude register in `Voice` and
  marked zero `interlude` beats at GROW annotate — tier-independent, so a
  prompt under-determination in `grow_annotate.j2` (the interlude option
  is offered but nothing states when taking it is expected). Fold into the
  prompt-template audit or fix directly; the register machinery itself is
  offline-tested and has never run live.
- [ ] **`exit_mood` beat annotation** — deferred with the annotation family (01
  §10.3); add only on a demonstrated FILL quality gap (the `scene_type` /
  `narration_scope` precedent).

## Export & tooling

- [ ] **Non-digit codeword fallback** — derived fallback codewords may contain
  digits (slugs allow them; `^[A-Z]{3,12}$` binds only DRESS-stored codewords).
  Cosmetic; a print warning already tells authors to run DRESS.
- [ ] **`qf illustrate` style-reference conditioning** — feed a rendered image
  back as a reference for the rest of the batch (M7's documented escalation).
  The live run showed *style* drift, not character drift; wire the reference
  path when a run demands it.

## Validation & experiments

- [ ] **Local `qwen3.5`-class Ollama confirmation** — the cloud tier is
  validated end-to-end; a local-daemon run is still wanted when a host is
  reachable (needs a GPU box with the daemon logged in to ollama.com).
- [ ] **Subagents as an unbilled Claude for pipeline calls** (author idea) — can
  a provider adapter route `complete()` through a dev-session's own subagents,
  preserving schema-validation + determinism? A small targeted spike.
- [ ] **Corpus curation** — `corpus/interactive-fiction/` is the author's
  ongoing add/trim pass; `style-exemplars` stays out until M9 can consume it.
- [ ] **Large style exemplar for weak-tier prose (author hypothesis,
  2026-07-15).** Reading the kimi-k2.5 A/B against the gpt-oss baseline:
  structure can be forced correct on any tier (the enforcement doctrine),
  but prose fluency — the sheer creativity and quality kimi shows — cannot
  (easily) be mitigated by prompts/engine. Hypothesis 2: a very LARGE
  exemplar of the specific style wanted might lift a small model by giving
  it something to copy. Note the deliberate tension with the M6 craft rule
  (exemplars are a contrasting spread, never a nearest-match target — the
  taste-laundering guard, design doc 02 §Craft context): this experiment
  would need an author-provided target style, distinct from the corpus
  channel, so conformance is the author's choice rather than laundered
  taste. Design the experiment before building anything.
