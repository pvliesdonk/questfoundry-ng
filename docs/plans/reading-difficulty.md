# Reading Difficulty — Assessment & Proposed Lever

> Status: **assessment, v2** (2026-07-12). Answers next-up #1 ("the prose reads
> too complex for a gamebook"). **v1 was wrong and is corrected here** — an
> author read of the preserved stories inverted its central claim (decision log,
> 2026-07-12). This version records what the correction taught: the fault is
> *over-stylization*, not high reading level, and grade-level metrics are
> **anti-correlated** with the author's readability judgment.
>
> **Update 2026-07-13 — fix #1 built.** The author greenlit the fix and sharpened
> the cause (*"the writer applied the style to every paragraph; it should apply to
> the whole story"*). Recommended-lever steps 1–2 (Voice restraint directive +
> write-prompt plain-baseline/clarity rule) landed as a prompt reframe; FKGL stays
> out per this assessment. Remaining: Ollama live validation, the author's
> real-gamebook exemplars (step 4, in flight), and the deterministic `overwriting`
> guardrail (step 3) once the exemplars calibrate its bands.

## What v1 got wrong (recorded so it is not repeated)

v1 measured Flesch–Kincaid (FKGL) and paragraph density, concluded the prose
skewed too *complex*, and recommended a **graded FKGL readability finding** with a
literary-vs-accessible Vision knob. The author's read of the actual stories
broke this: *"none of the examples is particularly okay… keepers-bargain and
closed-circle are the best; cartographers-debt and bubblegum are near
unreadable."* Ranking that against the metrics:

| Story | Author's read | FKGL | short (≤6-word) sentences | coined compounds / 1k words |
|---|---|---|---|---|
| `keepers-bargain` (hand golden) | best (but still "pretentious") | 7.5 | 22% | 5.5 |
| `closed-circle` | best | **18.4** | 1% | 5.6 |
| `cartographers-debt` | near unreadable | **2.5** | 42% | **21.2** |
| `bubblegum-alibi` | near unreadable | 4.8 | 45% | 6.2 |

**FKGL is inverted.** The author's *best* story scores grade 18 (graduate); the
*worst* scores grade 2.5 (early reader). A graded-FKGL finding would have flagged
the best prose and passed the worst — the exact opposite of the goal. Sentence
length and vocabulary are not the disease; a rich, long-sentence register
(`closed-circle`, `keepers`) reads *well* when it is controlled. v1 also over-
credited the golden as "the intended register" purely because it is hand-authored
— the author's verdict is that it too "reads difficult and pretentious." So this
is **systemic over-writing across the whole generative path, including the hand-
authored fixture**, not an outlier to catch.

## What actually makes the prose hard (from reading it)

Reading the four side by side, the axis that tracks the author's judgment is
**stylistic control / modulation**, not complexity. Two failure modes, sometimes
combined:

1. **Relentless, unmodulated stylization — every sentence strains for effect.**
   `bubblegum-alibi` is wall-to-wall hard-boiled aphorism ("That lands like a
   compliment. It costs me a breath." / "The dark came early, and a room can hold
   a lot of terrible things in twenty-two extra seconds nobody accounted for.").
   There is no plain connective prose to rest on, so the voice becomes exhausting
   monotony — Provost's "drone," in staccato. The "pretentious" quality the
   author names in the golden is the milder form: prose continuously reaching for
   the literary rather than earning it at intervals.

2. **Fragmentation and novelty-overload — the reader can't find footing.**
   `cartographers-debt` is a strobe of fragments (42% of sentences ≤ 6 words) with
   a coined compound or fresh metaphor jammed into nearly every phrase — 21
   hyphen-compounds per 1k words, ~4× the others ("the compass rose wetting its
   throat," "Oath-murmurs thread their teeth," "brine-lamps," "eel sheen"). Every
   noun is invented, every image is peak intensity, nothing is plain, so no scene
   assembles in the reader's head. It reads as a prose-poem in a made-up dialect.

By contrast the **readable** stories share what the unreadable ones lack:

- **A clear grammatical spine and connective flow** — complete sentences that
  carry the reader clause to clause (`keepers`: *"The boat comes in on the neap
  tide, low in the water with chart cases and a man who introduces himself before
  his feet have found the ladder."*). `closed-circle` has essentially **no**
  fragments (1%).
- **Modulation** — plain valleys between heightened peaks, not every line maxed.
- **Concreteness that advances the story**, not atmosphere that stalls it
  (`keepers`' wrong soundings and the blank line in the ledger *move* the scene;
  `cartographers`' images only decorate).
- **Ornament with restraint and purpose** — `closed-circle` is very ornate and
  still reads well because the overwriting is deliberate and controlled. Ornate ≠
  unreadable; *relentless* is unreadable.

## The corpus agrees (target is clarity/control, not simplicity)

- `prose-and-language/prose_patterns.md:52` — *"Don't sacrifice clarity for
  atmospheric tone — dream-like prose can leave readers lost."* This is exactly
  `cartographers`' failure.
- `prose-and-language/exposition_techniques.md:74` — *"Find the balance that
  paints a picture without overwriting or killing pacing."*
- `prose_patterns.md` § Cadence / Provost — *"Monotony kills rhythm… vary short,
  medium, and long."* Both bad stories are monotonous in one register (staccato).
- `prose_patterns.md` § Specificity — *specific nouns over piling on modifiers*
  (the corpus's answer to compound/adjective overload).
- Quality bars: **Clarity / Comprehension** (`quality_standards_if.md`) — *can a
  player summarize what happened?* — is the bar these stories miss, not a reading-
  level bar.

FKGL/FRE stay **out** of the lever. At most they are a sanity floor for a
genuinely childish target audience; they do not measure the defect here and must
never gate against a controlled literary register.

## Root cause — the pipeline rewards maximalism

- **The Voice pass (`fill_voice.j2`)** invites a maximal register and never asks
  for restraint or modulation. `thaw-between`'s coined `rhythm` literally asks for
  *"a longer, layered"* sentence every other line; nothing establishes a plain
  baseline, a fragment ceiling, or "clarity outranks atmosphere."
- **The FILL write pass (`fill_write.j2`)** tells the writer to reach for the
  voice's imagery palette "when you need a description" but sets no ceiling on
  *how often* — so a writer with a rich palette applies it every sentence. Nothing
  values a plain, load-bearing sentence.
- **No pass rewards modulation, flow, or clarity**, and the review has no axis for
  over-stylization — so relentlessly mannered prose passes clean.
- **The golden fixture over-writes too**, so the pipeline has *no clean in-repo
  exemplar of the target register* to imitate — it is learning from its own
  over-written outputs.

## Recommended lever (corrected)

Primary lever is **generative and prompt-side** (restraint + modulation), because
the defect is a register the pipeline is *choosing*, not a metric it is missing.
Deterministic guardrails ride the proven `word_budget` shape but on the **right**
signals — never FKGL.

1. **Voice-pass restraint & modulation directive (`fill_voice.j2`).** Before any
   prose exists, require the coined voice to commit to: a **plain, complete-
   sentence baseline** that carries the scene; heightened style and figuration
   **reserved for selected peaks**, not every line; a **clear grammatical spine**
   (subject–verb, connective flow — not a strobe of fragments); *clarity outranks
   atmosphere* (corpus prose_patterns:52). Reframe `rhythm`/`imagery` so they can't
   be read as "maximize every sentence."

2. **Write-prompt modulation rule (`fill_write.j2`).** State that most sentences
   should be plain and load-bearing; the imagery palette is for *occasional*
   emphasis, not continuous decoration; do not coin a new compound or fresh
   metaphor in every clause; a scene must be *summarizable* after reading (the
   Clarity/Comprehension bar). Show the good/bad contrast (modulated vs relentless)
   the way the corpus notes do.

3. **A graded `overwriting` finding at FILL apply** (beside `_word_budget_finding`
   in `fill.py`), on signals that *tracked the author's ranking*, graded warn→fail
   by distance out of band:
   - **Fragmentation ratio** — share of very short (≤ ~6-word) sentences. Both
     unreadable stories run 42–45%; the readable ones 1–22%. An out-of-band ratio
     is the staccato-monotony catch.
   - **Novelty/figuration density** — coined-compound (and, if cheaply
     detectable, fresh-metaphor) rate per 100 words. `cartographers` is a 4×
     outlier; a ceiling catches the "no plain prose to rest on" failure.
   Recovery actions are actionable ("this passage is 44% fragments — join the
   staccato lines into 2–3 flowing sentences"; "you coined N compounds in this
   paragraph — keep one, say the rest plainly"), per the AGENTS.md error rule.

4. **Establish a real target-register exemplar (companion task).** Because even the
   golden reads as over-written, the pipeline has no north star. Either the author
   supplies/blesses a short passage in the target register, or we rewrite a golden
   passage to model *modulated, clear* prose — so voice/write prompts can point at
   it and reviews can calibrate against it. Validation is a **human read**, not a
   metric.

## Open decisions (author)

1. **Is the diagnosis right?** Confirm the axis is control/modulation/clarity (not
   reading level), so FKGL stays out of the lever entirely.
2. **Prompt-only first, or prompt + guardrail finding?** Recommendation: land the
   Voice + write-prompt restraint directives first (they attack the root cause and
   touch no schema), add the deterministic `overwriting` finding once its bands are
   calibrated on more stories. FKGL is dropped either way.
3. **Target-register exemplar.** Do you want to supply/bless a passage in the
   target register, or should I draft a rewrite of one golden passage (plain,
   modulated) for you to react to? This sets the north star everything calibrates
   against.
4. **Is "modulation intensity" a Vision knob at all?** The old literary↔accessible
   framing was wrong (best story is the most literary). If any knob, it governs
   *maximalism/restraint*, not vocabulary grade — worth deciding whether that is a
   knob or just the always-on default.

## Scope guards / not doing

- **No FKGL/FRE gate.** It is anti-correlated with the goal here.
- Not adding a runtime "simplified mode" — a SHIP/export player feature, out of
  scope for the generation lever.
- No billed API calls to validate: a targeted Ollama (`gpt-oss:120b`) FILL re-run
  of a `cartographers`/`bubblegum` passage, read by a human for control/modulation,
  is the check — per live-run budget discipline.
