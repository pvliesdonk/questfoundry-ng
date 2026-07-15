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
  `polish_audit`, `polish_finalize`, `polish_labels`, `polish_summary`,
  `research`, `seed_order`, `seed_scaffold`, `seed_triage`. Known open
  question to fold in: DREAM's envision rewrote an authored rotating
  `pov_hint` into a single-head scheme (observed live 2026-07-14, root cause
  fixed: the prompt never saw the authored hint) — the audit bar for
  `dream.j2` is *visibility*, not preservation: the model must SEE the
  authored inclination as vision input; reinterpreting it is DREAM's job
  (author decision, 2026-07-14, decision log).

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
- [ ] **Intersections over post-commit (exclusive) beats** — M2 only groups
  shared pre-commit beats; exclusive-beat intersections are meaningful but
  interact with arc membership in ways the spine model doesn't cover. Same for
  **temporal hints inside atomic fork units** (a hint there has nothing to
  move). Revisit when a generated story demands one.
- [ ] **Cosmetic flags on false branches / locked storylines** — the machinery
  exists (`FlagSource.COSMETIC`); wire grants when a residue beat or print
  codeword actually wants one.

## Prose & annotations

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
