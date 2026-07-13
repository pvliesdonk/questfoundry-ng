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
- **Over-stylization *can* compound across stages — but the current compiler
  already guards the upstream half** (correction, 2026-07-13; an earlier draft of
  this plan called it an "unaddressed second vector" — that was wrong, author-
  flagged, and is retracted here). The concern is real in principle: if the
  beat/passage *summaries* reach FILL already written as stylized prose, the writer
  inherits and amplifies that register. `bubblegum-alibi`'s beat summaries show the
  failure mode — *"In the ashless world where the ledger is gone…"*
  (`admired-and-alone--burn-ledger.yaml`), *"…the crowd pulls itself into a ragged
  circle, streamers drooping overhead while every glittering eye swings toward
  Juno…"* (`bridge-crowd-to-circle.yaml`) — atmospheric prose where a brief should
  state events plainly. **But `bubblegum-alibi` is a stale M5-era artifact**: the
  current pipeline already enforces exactly this discipline through
  `_summary_brief.j2`, a shared register contract `{% include %}`d by **SEED
  scaffold, GROW bridge/contextualize, and POLISH passages/finalize** — *"A summary
  is never the page itself. Plain declarative present tense… Name a mood instead of
  performing it ('The mentor is dead and the group blames Rell' is a brief; 'grief
  hangs over the camp like early winter' is prose)… Every image you spend here is
  stolen from the writer."* So the upstream half is already contracted (design doc
  01 §2); the FILL writer/voice reframe in this PR is the piece that was missing,
  **not the first of two**. Residual worth a look when convenient: whether the
  contract also reaches FILL's story-so-far notes, and whether it holds on weak
  tiers — but there is no known unaddressed upstream vector, and re-generating
  `bubblegum` on the current compiler would likely produce plainer summaries.

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
   in `fill.py`) — **design updated by the genre-diverse calibration below**:
   - **Coined-novelty density > ~15/1k words** is the one aggregate signal that
     survived six genres with zero false positives (`cartographers` 21.2; every
     competent work ≤ 7.2). Keep the *fail* line at 15 (the 7–15 region is
     unsampled — do not lower it), warn loose.
   - **Fragmentation ratio must NOT gate on its own.** Good noir (Grimnoir 49%) and
     good minimalist-literary (Great-grandmother 44%) sit in the same band as the
     bad stories — a rate cannot tell "the register is clipped" from "the prose is
     a strobe." Use it only paired with the novelty flag, or fold it into a
     modulation measure.
   - **Prefer a *modulation* measure over any mean** (the exemplars' real lesson):
     a plain baseline with a few peaks *across passages*, not a per-corpus average —
     because the discriminator is the distribution/variance of stylistic intensity,
     which a mean cannot see (see "What the exemplars are for").
   Recovery actions stay actionable ("you coined N compounds in this paragraph —
   keep one, say the rest plainly"), per the AGENTS.md error rule. **Do not build
   until the modulation measure is designed and a register-aware band is set** — the
   raw fragmentation rule would false-positive on good noir.

4. ~~**Establish a real target-register exemplar.**~~ **Done** — two published
   gamebooks (ALBA, Pirates) plus eight genre-diverse choice-based Twine works,
   all measured; profiles above are the north star and calibration. Validation
   of generated prose remains a **human read**, not a metric.

## Open decisions (author)

1. ~~**Is the diagnosis right?**~~ **Confirmed** (2026-07-13, author): the axis is
   control/modulation/clarity, not reading level — and the ALBA exemplar's FKGL 4.6
   (= a "bad" story's) settles that FKGL stays out of the lever entirely.
2. **Prompt-only first, or prompt + guardrail finding?** Recommendation (and the
   path taken): land the Voice + write-prompt restraint directives first (they
   attack the root cause and touch no schema); add the deterministic `overwriting`
   finding once bands are calibrated — the ALBA exemplar gives the first
   calibration (see *Target-register exemplar*). FKGL is dropped either way.
3. ~~**Target-register exemplar.**~~ **Supplied** by the author — *two* published
   gamebooks (ALBA, Pirates of the Splintered Isles), profiled above as the north
   star and the finding calibration (the two replicate each other closely).
4. **Is "modulation intensity" a Vision knob at all?** The old literary↔accessible
   framing was wrong (best story is the most literary). If any knob, it governs
   *maximalism/restraint*, not vocabulary grade — worth deciding whether that is a
   knob or just the always-on default.

## Target-register exemplars (author-supplied, 2026-07-13)

The author supplied **two** real published second-person gamebooks as the north
star: *ALBA* (~172k words, 587 numbered sections) and *Pirates of the Splintered
Isles* (Legendary Kingdoms Bk 3, O. Hulme; ~157k words of prose). Neither is
**vendored** (third-party text); recorded here are their measured profiles and
craft traits, which calibrate both the prompt reframe and the future `overwriting`
finding. Both are plain, concrete, functional second-person present — events and
observations in a clear grammatical spine, description that advances the scene,
dialogue with plain tags, emotion named lightly, almost no coined vocabulary, and
figuration used *sparingly* (Pirates: "the spar snaps like a match under the blow"
— one flourish in an otherwise plain action beat).

Measured against the assessment's stories (same script):

| Source | verdict | FKGL | W/sent | short (≤6w) | compounds /1k |
|---|---|---|---|---|---|
| **ALBA** (target) | good | 4.6 | 12.7 | 28% | **1.7** |
| **Pirates** (target) | good | 5.9 | 13.3 | 20% | **3.0** |
| `keepers` | good | 7.5 | 20.3 | 22% | 5.5 |
| `closed-circle` | good | 18.4 | 24.4 | 1% | 5.6 |
| `cartographers` | bad | 2.5 | 9.1 | 42% | 21.2 |
| `bubblegum` | bad | 4.8 | 13.3 | 45% | 6.2 |

Three conclusions, now **replicated** across two independent published books:

1. **FKGL is confirmed noise.** The targets score 4.6 and 5.9 — the same band as
   `bubblegum` (bad, 4.8) and *below* both other good stories (7.5, 18.4). Grade
   level does not separate good from bad. FKGL stays out of the lever, settled.
2. **Coined-novelty density is the clean discriminator.** Both gamebooks sit at
   ≤ 3/1k; every acceptable sample is ≤ 6.2; `cartographers` (worst) runs 21.2 —
   a **≥ 3× gap to the nearest acceptable sample and ~7–12× to the targets**,
   monotonic with the verdict. This is the primary guardrail signal.
3. **Fragmentation is secondary and needs a generous threshold.** The targets run
   20–28% short sentences and read fine; the bad stories sit at 42–45%. A plain
   gamebook *uses* plenty of short sentences — the defect is a *strobe* of them,
   not their presence — so the finding must fire only well above the target band.

Calibration for the deferred `overwriting` finding (step 3), from these two
samples (refine as more arrive): **compound density** — warn ≳ 8/1k, fail ≳ 15/1k
(targets 1.7–3.0, all acceptable ≤ 6.2, worst 21.2); **fragmentation** — warn
≳ 38%, fail ≳ 50% (targets 20–28%, worst 45%). Human read remains the acceptance
test; these only bound the egregious cases the metrics catch cleanly.

**Caveat — same genre, so the bands are provisional** (author, 2026-07-13). Both
exemplars are the same *kind* of gamebook (fantasy-adventure, plain functional
register). What generalizes safely: **FKGL is out** (also supported cross-genre —
the literary `closed-circle` is "good" at FKGL 18.4), and **the egregious extreme
is a defect in any register** (`cartographers`' 21.2 compounds/1k is not a genre
choice). What does *not* yet generalize: the **acceptable ceiling**. A legitimately
literary register (a gothic-horror gamebook, say) may sit higher on compound
density and sentence length and still read well — `keepers` (good, more literary)
already runs 5.5 vs the fantasy targets' ≤ 3.0. So the bands must **not** be fixed
from two same-genre samples: hold the fail line at the egregious extreme, keep the
warn line loose, and either widen the acceptable band per Vision register or
gather a different-genre exemplar before the finding is built.

### Genre-diverse choice-based calibration (2026-07-13)

The same-genre caveat is now largely resolved. Eight **choice-based** Twine works
from the IF Archive (the *right medium* — branching passage prose, not parser
room-text), spread across horror, noir, literary/historical, sci-fi, romance, and
crime, were extracted (passage prose only; macros/links/variables stripped) and
measured with the same script. Grimnoir was independently re-fetched and
re-measured to confirm the method (matched to the decimal).

| Work | Genre | words | FKGL | W/sent | short% | cmp/1k |
|---|---|--:|--:|--:|--:|--:|
| Bogeyman (XYZZY Best Game) | horror | 14.7k | 4.3 | 11.5 | 27 | 2.6 |
| Grimnoir | noir | 50k | 3.6 | 8.3 | **49** | 3.4 |
| Great-grandmother and the War | literary/historical | 20.9k | 3.6 | 8.9 | **44** | 3.9 |
| Stars Above | sci-fi | 10.7k | 4.3 | 11.5 | 25 | 3.8 |
| No Love Deep Space | sci-fi/action | 2.8k | 4.7 | 11.8 | 28 | 7.2 |
| Date Night | romance | 2.9k | 4.9 | 11.2 | 26 | 1.0 |
| Rough Velvet | crime | 4.8k | 6.5 | 10.3 | 38 | 4.3 |
| A Date With Logan Davenport (amateur) | romance | 3.9k | **9.6** | 27.2 | 13 | 2.0 |

Refined conclusions across genre:

1. **FKGL is noise — reconfirmed and inverted.** The XYZZY Best-Game horror
   (Bogeyman) scores 4.3, indistinguishable from "bad" `bubblegum` (4.8). The
   worst-written work (Logan Davenport — no punctuation, misspellings) scores the
   *highest* FKGL (9.6), because missing periods inflate words-per-sentence. FKGL
   tracks quality **backwards** here. Out, definitively.
2. **Compound density > ~15/1k stays a robust red flag.** No competent work in this
   diverse set exceeds 7.2/1k; only `cartographers` (21.2) trips 15 — zero false
   positives across six genres. *Caveat:* nothing sampled sits in 7–15, so the exact
   cutoff below 15 is untested; keep the fail line at 15, not lower.
3. **Fragmentation alone is NOT safe — real good counter-examples.** Two of the most
   competent works exceed 40% short sentences: **Grimnoir** (noir, 49%) and
   **Great-grandmother** (literary child-narrator, 44%). Clipped declaratives *are*
   those registers ("No use. Restless. And bored."). Because the bad examples sit in
   the same band (`cartographers` 42%, `bubblegum` 45%), fragmentation cannot
   separate good minimalist/noir from staccato failure on its own. It is confounded
   with genre and dialogue density, and **must not gate alone** — pair it with the
   compound flag, or (better) measure *modulation*, not the raw rate (below).

### What the exemplars are *for* — style distribution, not the medium

We are not replicating a medium (author, 2026-07-13). Parser IF, choice IF, and a
QuestFoundry gamebook differ in surface, but the exemplars answer a medium-
independent question: **how is stylistic intensity distributed across the many
partial snippets a story is made of?** Good work modulates — most snippets plain
and load-bearing, a few heightened; the register is felt across the *whole*, not
performed in every fragment. That is the "style belongs to the story, not the
paragraph" principle stated at the scale of the whole work — and it is why parser-IF
exemplars are not disqualified by the medium gap.

It also explains conclusion 3's failure: a **rate** (mean fragmentation, mean
anything) cannot see distribution. Noir is *uniformly* clipped and reads well;
over-styled prose is *uniformly* heightened and reads badly — the mean cannot tell
them apart; only the **variance/distribution of stylistic intensity across snippets**
can. That is the refined direction for the deferred `overwriting` guardrail:
prefer a *modulation* measure (a plain baseline with a few peaks, computed across
passages) over any per-corpus average — keeping **compound density > 15/1k** as the
one clean aggregate red flag that survived genre diversity.

### The structural mechanism NG lost — heritage beat annotations (2026-07-13)

Author observation, confirmed against heritage and the NG design docs: the
modulation problem is *completely* why the original QuestFoundry carried
**structural beats** and **beat annotations**, and the annotations were lost in
translation to NG.

Heritage (`docs/heritage/story-graph-ontology.md`, Part 3 "Beat Annotations")
distributed stylistic intensity **structurally, per beat**:

- `scene_type ∈ {scene, sequel, micro_beat}` (Swain) — *"Consumed by POLISH Phase 2
  for pacing detection and by FILL for prose intensity / target length derivation."* A
  `scene` (active conflict) earns heightened prose; a `sequel` (reactive) or
  `micro_beat` (transition) stays plain and short.
- `narrative_function ∈ {introduce, develop, complicate, confront, resolve}` —
  *"Consumed by FILL for prose pacing."*
- `atmospheric_detail` — sensory grounding for FILL.

This is exactly "style distributed across snippets": each beat carries a signal for
how intense its prose should be, so FILL is *told* where to stay plain and where to
rise. Strip it and every beat looks identical to the writer → uniform intensity →
over-stylization. The mechanism against the disease was **designed into the model**.

**NG kept the structural-beat class (`beat_class`, `purpose`) but the annotations
are gone — and the loss is half-recorded, half an undocumented gap:**

- Design doc 01 §10.3 ("Annotation trimming") deliberately trims the heritage set
  yet **commits to keeping two — `scene_type` (scene/sequel) and `exit_mood` — and
  adding more "only when a FILL quality gap demonstrably calls for one."**
- **Neither exists in NG code** — `Beat` (`models/structure.py`) has no
  `scene_type` and no `exit_mood`; the only mention anywhere is a POLISH comment,
  *"the pacing report stays deferred with scene_type."* The G4 pacing report
  (design doc 02 §3: *"no > N consecutive same-intensity passages"*) is unbuilt for
  the same reason — it needs the missing intensity signal.

  **This was not a mistake — it was an honest YAGNI call** (author, 2026-07-13).
  §10.3 says annotations are "cheap to add and expensive to maintain coherently,"
  so NG deferred building even the two it named until a FILL quality gap demanded
  them. The only stale artifact is §10.3's present-tense "NG starts with two"
  wording, which reads as though they exist; the resolution is to **build
  `scene_type` now** (the trigger has fired — see below) and update §10.3 to match,
  not to treat the deferral as an error. (Filed in STATUS "Known deferrals / open
  items", 2026-07-13.)

**The reading-difficulty gap is precisely the trigger §10.3 anticipated.** The
condition for (re)adding the annotation — "a FILL quality gap demonstrably calls
for one" — is now met, and the annotation §10.3 named (`scene_type`) is the
modulation carrier. So the primary modulation lever should be **structural, not a
metric**: implement `scene_type` as a beat annotation (populated where the DAG is
known — heritage put it at GROW Phase 4b; POLISH is also plausible), consumed by
FILL to set **both prose intensity and the target word band** (sequel/micro → plain,
short band; scene → allowed to rise). The `overwriting` finding then demotes to a
*guardrail* that checks the modulation actually happened (variance across
passages), with compound-density > 15/1k as the aggregate red flag. **Designing
modulation in beats measuring it after the fact.**

This is a frontier design effort (a new annotation field, a populate pass, FILL
consumption, the deferred pacing report, checked against the freeze — heritage
populated `scene_type` at GROW, i.e. before the topology freezes, so an annotation
added post-freeze at POLISH would need I-rule clearance). Milestone-sized, not this
PR. Recorded as the recommended direction; build gated on author go-ahead.

### Hand-off spec — the `scene_type` modulation build (for a fresh session)

Author-confirmed direction (2026-07-13): capture here, kick off in a new session.
Goal: give FILL a **per-beat prose-intensity signal** so style distributes across
passages (plain baseline + a few peaks) instead of every passage running hot.

Build order (each step is a checkpoint; a frontier session should re-resolve the
open questions before coding — this is a sketch, not a frozen contract):

1. **Model.** Add `scene_type: SceneType | None = None` to `Beat`
   (`models/structure.py`); `SceneType = {scene, sequel, micro_beat}` (Swain, per
   heritage). Write-once through the mutation layer (iron rule 1). Reconcile with
   the existing coarse notion `Beat.is_texture` (residue/false-branch → short band):
   `scene_type` should subsume it, or the two must be explicitly layered.
2. **Populate pass.** Assign `scene_type` per beat. Heritage did it at **GROW Phase
   4b** (order known after weave, before freeze). *Open:* GROW (pre-freeze, needs
   the woven order) vs POLISH (post-freeze, passages known — but a post-freeze
   annotation must be shown freeze-exempt: it is metadata, not topology; note it
   against I9 and the freeze rules). Likely LLM-proposed (scene/sequel is narrative
   judgment; utility or architect tier) with a heuristic seed from `purpose` /
   `dilemma_impacts` where safe.
3. **FILL consumption — the payoff.** (a) Word band: extend
   `ScopePreset.words_for` / `_word_budget_finding` (`stages/fill.py`) to key off
   `scene_type` (sequel/micro → short; scene → normal/long) alongside the current
   `texture`/`ending` axes. (b) Intensity directive in `fill_write.j2`: render the
   beat's `scene_type` and instruct — a **sequel/micro** beat is plain, brief,
   low-key (reactive processing / transition); a **scene** is where the prose may
   rise (active conflict). This makes "style belongs to the story, not the
   paragraph" concrete per beat.
4. **Pacing report (the deferred G4 piece, design doc 02 §3).** With `scene_type`
   present, implement the advisory "no > N consecutive same-intensity passages"
   check as the modulation guardrail (alternation, not all-scene/all-sequel).
5. **Guardrail metric, after.** The `overwriting` finding demotes to a check that
   modulation actually happened (variance across passages), compound-density > 15/1k
   as the one aggregate red flag (calibration above). Do **not** ship the raw
   fragmentation rule (false-positives on good noir).
6. **Docs + fixtures.** Update design doc 01 §10.3 (annotations built, not "will
   start with"), add the Beat-annotation subsection to 01, the populate pass + G4
   pacing report to 02, and — if `scene_type` ever gates — a numbered invariant
   (iron rule 6) with a violating-construction test. Annotate the golden story's
   beats; re-record e2e fixtures if the populate pass adds LLM calls.

Open questions to settle first: GROW-vs-POLISH placement (freeze interaction);
LLM-proposed vs heuristic `scene_type`; `scene_type`-alone-first vs also `exit_mood`
(§10.3 named both — `scene_type` is the modulation carrier, do it first); how
`scene_type` reconciles with `is_texture`.

## Scope guards / not doing

- **No FKGL/FRE gate.** It is anti-correlated with the goal here.
- Not adding a runtime "simplified mode" — a SHIP/export player feature, out of
  scope for the generation lever.
- No billed API calls to validate: a targeted Ollama (`gpt-oss:120b`) FILL re-run
  of a `cartographers`/`bubblegum` passage, read by a human for control/modulation,
  is the check — per live-run budget discipline.
