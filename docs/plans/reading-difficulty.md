# Reading Difficulty — Assessment & Proposed Lever

> Status: **assessment** (2026-07-12). Answers next-up #1's research ask
> ("the prose reads too complex for a gamebook"): measure the problem, map it
> to the vendored craft corpus and gamebook/CYOA norms, name the root cause,
> recommend one lever. The build is gated on the author picking the lever and
> the register default (see *Open decisions*).

## The problem, measured

Flesch–Kincaid Grade Level (FKGL), Flesch Reading Ease (FRE), mean words per
sentence, mean **paragraphs per passage**, and two run-on proxies (sentences
over 30 words; sentences with ≥ 3 commas) across the preserved stories:

| Story | Author | FKGL | FRE | W/sent | paras/passage | >30w sents | ≥3-comma sents |
|---|---|---|---|---|---|---|---|
| `thaw-between` | LLM (`gpt-oss:120b`) | **9.5** | 64 | 20.9 | **1.1** | 33 | 35 |
| `keepers-bargain` | hand (golden) | 7.5 | 78 | 20.3 | **4.0** | 32 | 28 |
| `bubblegum-alibi` | LLM (Opus/Haiku) | 4.8 | 84 | 13.3 | 8.6 | 100 | 90 |
| `lamplighters-debt-craft` | LLM (Opus/Haiku) | 4.3 | 90 | 14.5 | 6.5 | 149 | 115 |

`thaw-between` is the sample that motivated the concern, and it is an
**outlier**, not the pipeline's norm: the two Opus-driven LLM stories are already
accessible (FKGL 4–5). Two findings fall out of the spread:

1. **Difficulty is two independent axes, not one.**
   - *Micro-readability* — vocabulary and sentence length (FKGL/FRE).
   - *Structural legibility* — how the prose lays out for a reader navigating
     choices on a screen: paragraph white-space and run-on density.

   `thaw-between` is bad on **both**. Its single most objective defect is
   structural: **1.1 paragraphs per passage** — every passage is one
   unbroken wall of text — against the hand-authored golden's 4.0. Its FKGL
   (9.5) is high but, taken alone, sits inside the corpus's *Adult (literary)*
   band; the wall-of-text is what makes it read as punishing.

2. **The number is driven by the coined Voice and the model tier, so a blanket
   "write simpler" directive is the wrong tool.** It would drag the already-in-band
   Opus runs down and flatten a `literary` audience the Vision explicitly asked
   for (`thaw-between`'s audience string is *"Adult readers (18+) who appreciate
   literary, morally ambiguous interactive fiction"*; its `voice.yaml` diction is
   *"salt-worn, literary, bleak"*). The lever must be **audience-relative and
   graded**, biting only when prose drifts out of the band its own Vision set —
   exactly the `word_budget` shape.

## What the corpus says (authoritative — not first-principles)

The vendored corpus speaks to this directly; the design does not have to derive it.

- **`audience-and-access/audience_targeting.md` § Reading Level Metrics** gives
  FKGL bands per audience — the target table this lever would enforce:

  | Audience | FKGL |
  |---|---|
  | Early Readers | 1–2 |
  | Middle Grade | 3–6 |
  | Young Adult | 7–10 |
  | Adult (accessible) | 8–10 |
  | Adult (literary) | 10–14+ |

  …plus per-audience sentence-length guidance (MG 10–20 words, ER 5–10) and the
  standing caution: *"Don't obsess — metrics are guides… Story first; never
  sacrifice story for score."* (Argues for a graded finding, not a hard gate.)

- **`prose-and-language/prose_patterns.md`** is emphatic on structural legibility
  and is the corpus's answer to the wall-of-text: *"Optimal Paragraph Length:
  Rarely more than 3–4 sentences. White space is your friend… **Dense literary
  prose that works in print can feel oppressive on screen. White space is
  structural, not decorative.**"* Also: vary sentence length (monotony kills
  rhythm), story-passage density 100–200 words.

- **`craft-foundations/quality_standards_if.md` § Bar 6 (Accessibility)** makes
  *"Reading level: prose matches target audience capability"* a named quality
  bar — the corpus already frames this as a check the work should pass.

## Root cause — where difficulty enters the pipeline

There is **no readability signal anywhere in the pipeline today.** Two entry points:

- **The Voice pass (`fill_voice.j2`)** coins `diction` / `rhythm` freely from the
  Vision's tone and audience. Nothing tells it the prose will be read on screen,
  mid-choice — so it optimizes for literary texture (`thaw-between`'s rhythm rule
  literally asks for *"a longer, layered"* sentence every other line) with no
  white-space or sentence-variation floor.
- **The FILL write pass (`fill_write.j2`)** enforces a word band and voice
  fidelity, but nothing about paragraphing or sentence complexity. The review
  (`fill_review.j2`) has no readability rule. So a wall-of-text passage passes
  clean.

The `word_budget` finding (`fill.py:_word_budget_finding`, and its integration in
`_review_for`) is the proven precedent: a **graded, engine-injected
`ReviewFinding`** whose `confidence` scales with distance out of band, riding the
same findings list the reviewer produces — blocks when confidently out of band,
weighed-not-mandated on a near-miss.

## Recommended lever

**A graded `readability` finding, audience-relative, mirroring `word_budget`** —
plus the two supports that make it land. Preferred because it (a) reuses a shape
already validated in the codebase, (b) leaves in-band prose untouched (the Opus
runs never see it fire), and (c) is deterministic and citable — the reviewer
never has to *judge* reading level, the engine measures it.

1. **A structured Vision register field (the knob).** Replace reliance on the
   free-text `audience` string with a typed `reading_register` on `Vision`
   (`early` | `middle_grade` | `young_adult` | `accessible` | `literary`),
   defaulting from `audience` at DREAM but author-overridable. It maps to a target
   FKGL band and sentence-length ceiling straight from the corpus table above.
   This is the *"literary-vs-accessible Vision knob"* next-up #1 asks to consider —
   made concrete and finite (an enum, refpin-style), not a second free-text field.

2. **A graded `readability` finding at FILL apply** (`fill.py`, beside
   `_word_budget_finding`). Deterministic per passage; `confidence` scales with
   distance beyond the band's slack, `assessment` warn→fail like `word_budget`.
   It measures **three signals, structural-first** (structural legibility is the
   universal, tier-independent defect; FKGL is register-relative):
   - **Paragraph count / white-space** — a texture/scene passage collapsed to
     1 paragraph is a confident FAIL regardless of register (the corpus rule is
     absolute for screen IF). *This alone catches `thaw-between`.*
   - **Run-on density** — share of sentences over the register's word ceiling or
     with ≥ 3 comma-joined clauses; graded.
   - **FKGL vs the register band** — graded, and only *above* the band (literary
     Visions are never punished for being rich; the floor is legibility, not dumbing down).

   Recovery actions are actionable per the AGENTS.md error-message rule ("break
   this 6-sentence block into 2–3 paragraphs at the natural beats"; "split the
   run-on at *X*"), not a bare score.

3. **A Voice-pass directive (`fill_voice.j2`).** Ground the coined voice in the
   screen-reading norms *before* prose exists: state that passages are read on
   screen mid-choice, that white space is structural (3–4 sentences/paragraph),
   and that `rhythm` must include short/fragment sentences for variation — so the
   voice the pipeline invents doesn't fight the readability finding downstream.
   Register-scaled from the same knob.

Deterministic FKGL/paragraph measurement is ~15 lines (demonstrated during this
assessment); **no new dependency** (avoid `textstat`), consistent with the repo's
hand-rolled-check posture (`echo.py`).

## Open decisions (author)

1. **Scope of the first lever.** Ship all three (register field + finding +
   voice directive), or start with the finding's **structural** signal only (the
   wall-of-text catch — highest-value, register-independent, no schema change) and
   defer the FKGL band + Vision knob to a follow-up? *Recommendation: structural
   finding + voice directive first (no Vision schema change, fixes the actual
   `thaw-between` defect), FKGL band + `reading_register` knob as PR-2.*
2. **Register default.** Should DREAM default `reading_register` to `accessible`
   (gamebook-legibility-first — the corpus's screen-reading argument), letting a
   Vision opt *up* to `literary`? Or honor the audience string as-is? This is the
   literary-vs-accessible product call.
3. **Gate vs finding-only.** Keep it a FILL-review finding (repairable, no new
   gate), or also surface an advisory **B-check** at G5 (like B5 word budget) so
   `qf validate` reports out-of-band prose on hand-authored stories too?

## Scope guards / not doing

- Not adding a runtime "simplified mode" toggle or per-reader text-complexity
  setting (corpus `accessibility_guidelines.md` lists it as a *player* feature; it
  is a SHIP/export concern, out of scope for the generation lever).
- Not touching the already-accessible behavior of strong-tier runs — the finding
  is graded precisely so it does not fire on in-band prose.
- No billed API calls to validate: the recommended validation is a targeted FILL
  re-run of `thaw-between`'s wall-of-text passages on **Ollama** (`gpt-oss:120b`,
  unbilled), confirming the finding fires and the paragraph split repairs cleanly —
  per the live-run budget discipline.
