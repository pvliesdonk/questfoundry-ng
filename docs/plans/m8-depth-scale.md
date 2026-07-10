# M8 implementation plan — depth & scale (scaffold deepening)

> **Working plan, not a design doc.** The authoritative contract lives
> in design docs [01 §2](../design/01-story-model.md) (scale table),
> [01 §5](../design/01-story-model.md) (structure layer),
> [02 §2](../design/02-pipeline.md) (SEED / GROW / POLISH contracts),
> and [05 §M8](../design/05-roadmap.md). This file sequences the build,
> records the planning-time decisions the design docs are silent on
> (each marked with where it must land during PR-1), and is the
> hand-off contract for implementing sessions. Delete or archive once
> M8 ships and STATUS records the outcome. Code references anchor on
> named functions; line numbers are as of the commit adding this file.

## Why this milestone is the risk milestone of the scale era

Every live run to date (runs 1–7) produced a *good, small* story:
8–22k total prose words, B6 (words per genuine choice) at ~1.07–1.25k
against the 250–800 feel band. The gap is structural — the SEED
scaffold's depth numbers are **prompt literals** (`seed_scaffold.j2`:
setup 1–2, pre-commit 2–3, post-commit 1–3, locked lead-in 1–3 /
aftermath 1–2) identical at every scope, so `micro` and `long` get the
same skeleton and differ only in dilemma count. M8 asks whether the
narrative/DAG mapping holds when the skeleton itself grows to book
scale — which is why it leads the remaining milestones (roadmap
ordering: riskiest creative bet first).

## Shape of the milestone

- **PR-0 — this plan** (the current PR).
- **PR-1 — engine work** (phases 0–4): words-primary scale table,
  preset-driven scaffold depth, words-aware cadence targeting, weave
  spread measurement/stratification, design-doc updates. All offline.
- **PR-1b — tensored residue arms** (phase 5), separate for review
  tractability; built after phase 2's cadence projection sizes the
  need (the roadmap pulls the shape into M8's scope).
- **PR-2 — exit-criterion validation**: the live corpus-grounded
  `medium` run at 20–60k words (roadmap §M8 exit).

Session pattern per AGENTS model economics: the scale-table semantics,
scaffold-depth bands, cadence math, and anything touching I3/I7/G4 are
frontier-tier; preset plumbing, template wiring, and tests against the
contracts below are mid-tier delegable; frontier reviews the diff.

## Measured baseline (planning-time, 2026-07-10)

From the preserved example projects (prose words = `prose/*.md`;
passages/beats = graph node counts). B6 figures from the runs' own
gate reports (STATUS decision log).

| Run | Scope | Words | Passages | Beats | w/passage | beats/passage | B6 |
|---|---|---|---|---|---|---|---|
| bubblegum-alibi (run 5, pre-locked-dilemmas) | medium | 10,570 | 20 | 52 | 529 | 2.60 | ~1206 |
| small-kindnesses (run 6) | micro | 8,810 | 22 | 31 | 400 | 1.41 | ~1072 |
| lamplighters-debt-base (run 7A) | short | 22,083 | 48 | 69 | 460 | 1.44 | ~1248 |
| lamplighters-debt-craft (run 7B) | short | 15,418 | 35 | 60 | 440 | 1.71 | ~1138 |

Current-shape ratios to carry into derivation: **~400–530 words per
passage** (bands cap at 450–650 by scope), **~1.4–1.7 beats per
passage** post-locked-dilemmas (bubblegum's 2.6 predates locked chains
and per-path residue arms and is not representative). Short-scope runs
already land 35–48 passages against an 18–30 band — the overshoot is
deliberate structure (two locked chains), which is exactly why bands
and scaffold depth must move together.

## Design decisions (the contract)

Numbered so PR-1 review can check each landed. D1 is a new mini-ADR
(A19).

1. **A19 — the scale table anchors on total prose words.** Each scope
   preset gains a primary `words_total: (min, max)` band; the passage
   band (B3), arc-beat band (B4), and cast/dilemma budgets become
   *derived, recalibrated* quantities — still stored explicitly on the
   preset (gates read plain numbers; no derivation magic at runtime)
   but documented in 01 §2 as derived from `words_total` via the
   measured ratios above, with the derivation recorded so the next
   recalibration is arithmetic, not archaeology. Rejected
   alternatives, for the A19 row: *playthrough-words primary* (the
   feel of size is B6's job — words per choice already measures the
   traversal experience; the thing the author holds, prints, and pays
   for is total prose, and cost scales with it); *passage-count
   primary* (the status quo — passages are an artifact of collapse,
   already redefined once under the old numbers; words are the only
   unit that survives structural refactors). Words-per-playthrough is
   *estimated* in 01 §2 per scope (traversal fraction from the
   structural simulation, phase 0) but is not a preset field and no
   gate checks it.
2. **Scaffold depth is preset data, not prompt literals.** A frozen
   `ScaffoldShape` sub-model on `ScopePreset`: `setup: (min, max)`,
   `pre_commit: (min, max)` (shared chain per branched dilemma),
   `post_commit: (min, max)` (per path; soft paths additionally bound
   below by `min_payoff_beats`, I7), `locked_lead_in: (min, max)`,
   `locked_aftermath: (min, max)`. `seed_scaffold.j2` renders its
   numbers from the shape; `_scaffold_apply` (stages/seed.py) enforces
   the bands as repairable `ApplyError`s, extending the existing
   min-payoff/ending-shape checks (the Sonnet-evaluation lesson:
   scaffold contract violations must die at SEED, repairably, never at
   GROW's unrepairable gate). Violating-construction tests per band.
   **Micro's shape pins today's literals** so the golden story, the
   e2e fixtures, and every preserved example remain valid without
   edits; positional fixture replay keys on call order, not prompt
   bytes, so the template change is fixture-safe (the one-time cache
   re-spend on old recorded runs is the known, accepted cost).
3. **Bands are calibrated by structural simulation, not by our own
   generated stories.** Phase 0 builds synthetic SEED output at the
   proposed shape bands (deterministic construction through the
   mutation layer), runs it through the *real* `weave.candidates` /
   `weave.realize` and the *real* passage collapse (`pipeline/passages.py`)
   — all deterministic, LLM-free — and counts: total beats, beats per
   arc, passages, cadence-diamond sites (`_long_runs`), and projected
   words (passage count × the measured words-per-passage mid). Bands
   for B3/B4 and the `words_total` targets are set from those counts
   plus the corpus-external 300–600 words-per-choice band — breaking
   the calibration circularity named in the roadmap risk table
   (bands tuned on stories generated under the old bands). The live
   run then *confirms*; it does not *define*.
4. **Cadence targeting becomes words-aware.** POLISH's false-branch
   pass currently asks for a diamond "every 3–5 beats of a choice-less
   run" (`polish_finalize.j2`); at deep scaffolds the beat-count
   heuristic and the B6 band drift apart (beats got longer runs, words
   per passage stayed put). The engine computes the diamond-site
   budget from the B6 target directly: sites per run ≈ run's projected
   words / target words-per-choice, using the scope's words-per-passage
   mid — the prompt receives concrete per-run site counts instead of a
   universal rhythm. **The honest arithmetic, recorded:** a deep
   `medium` playthrough (~18–21k traversed words at ~65% traversal of
   a ~30k story) needs ~23–30 choice points for B6 ≤ 800, of which
   only ~4 are branched-dilemma forks — a ~5:1 cosmetic:real ratio.
   That ratio is the milestone's central creative risk (the corpus's
   false-choice-tax warning is inverted only while cosmetic choices
   stay texture, roadmap risk table). Mitigations, in order: tensored
   residue arms make post-convergence choices *state-flavored* rather
   than purely cosmetic (D5); sidetrack false branches (01 §6, built
   but rarely proposed) get equal billing with diamonds in the prompt;
   and **the dilemma budgets themselves are a first-class phase-0
   lever** (author call, 2026-07-10 — promoted from the fallback this
   plan originally made it). Given a fixed `words_total`, volume can
   come from deeper chains per dilemma (few real choices, long runs —
   cosmetic diamonds carry the cadence; the 5:1 arithmetic above
   assumed this, at current counts) or from *more dilemmas* — more
   real forks consuming the same word budget. The two raises price
   differently and phase 0's simulation must weigh both: **+1 soft**
   buys one real fork per arc plus a convergence and residue site at
   modest beat cost (arcs double, but arcs are computed — free);
   **+1 hard** buys real volume and ending differentiation but
   multiplies worlds (medium 4→8; everything after the first fork
   instantiates per world) for only one more real choice per arc.
   Soft raises are the efficient choice-density lever, hard raises a
   volume/ending-richness lever. The simulation compares the
   candidate mixes (below) on projected B6, cosmetic:real ratio,
   beats, and cost; the winning mix lands in the scale table, and
   cast bands and locked allowances re-derive with it.
5. **Tensored residue arms** (PR-1b; the shape deferred from the
   locked-dilemmas effort, pulled into M8 by the roadmap). A light
   residue arm (one per path per world, G4) may carry its own cosmetic
   diamond: the arm's 1–2-beat chain forks into two same-gate arms
   that rejoin at the shared frontier. Model-wise nothing new — the
   arm beats stay `residue`-purpose, gated identically, and the
   diamond inside them is choice topology; the collapse rule
   ("identical gates merge") already breaks passages at the fork/join,
   so a tensored arm yields 2–3 gated passages and **one genuine-feeling
   choice that exists only for players who made the matching upstream
   choice** — cadence that compounds instead of diluting. Engine work:
   the finalize schema's residue-arm entry accepts an optional second
   arm chain; splice wiring generalizes (both arms inherit the tail
   edge into every frontier beat); I13's satisfiability check and
   G4's per-path coverage need no semantic change (assert with
   violating-construction tests, not assumption). The golden story
   grows a tensored arm (the 2-beat tell-side arm `counsel` +
   `honest-chart` is the natural candidate) per the documentation
   contract — golden coverage, hand-authored prose, print PDF
   renumbering accepted.
6. **Weave spread is measured before it is fixed.** Deep `medium`
   scaffolds put ~25–40 units into the weave (locked chains contribute
   every beat as a unit) against `CANDIDATE_CAP = 64` with
   lexicographic DFS that varies the tail first (STATUS open item;
   first data at 13 units). Phase 4 adds a spread metric to
   enumeration — distinct units appearing at each of the first K
   positions across the candidate set — and a synthetic test at
   deep-medium unit counts. If the metric shows early-position
   clustering (expected), enumeration stratifies: the cap is allocated
   across distinct first-position (then first-two) prefixes,
   deterministically, before depth-first filling — same contract (the
   LLM still picks an index; multi-hard nesting shares still split
   evenly first). Cap raises are cheap and acceptable; the shown-to-
   model count stays 8.
7. **Deep scaffolds are fed by the research pass, not by longer
   instructions.** SEED's research prompt (librarian queries) gains a
   depth-aware nudge at `medium`+ scopes: ask the corpus for mid-story
   escalation, subplot braiding, and payoff pacing craft — the
   material a deeper Y actually needs. Frontier-written (prompt
   framing is bias-sensitive); no new machinery — the M6 digest
   already reaches every scaffold pass.
8. **Words-per-passage bands hold.** Scale comes from more beats and
   passages, never from inflating passage word caps (iron rule 5's
   spirit: fix volume in structure, don't pad prose). `medium` stays
   (200, 650).

### Proposed numbers (finalized by phase 0's simulation, not here)

Scaffold shape per scope — micro pins the current literals:

| Scope | setup | pre-commit | post-commit/path | locked lead-in | locked aftermath |
|---|---|---|---|---|---|
| micro | 1–2 | 2–3 | 1–3 | 1–3 | 1–2 |
| short | 1–2 | 3–4 | 2–4 | 2–4 | 1–3 |
| medium | 2–3 | 4–6 | 3–5 | 3–5 | 2–3 |
| long | 2–3 | 5–8 | 4–7 | 4–6 | 2–4 |

`words_total` proposals: micro 3–9k (runs 3/4/6 measured 3.9–8.8k),
short 12–24k (run 7 measured 15.4–22.1k), medium 20–45k, long 45–90k.
The roadmap exit's "20–60k" is the acceptance envelope for the PR-2
run; the preset band is the tighter target the simulation confirms.
`min_payoff_beats` likely rises with post-commit depth (medium 2→3,
long 3→4) — decide in phase 0 with the I7 implications in view.

Candidate dilemma mixes for the D4 comparison (current: medium 2H+2S,
long 2H+3S): medium 2H+3S (the cheap real-choice raise) and 3H+2S
(worlds 4→8 — simulate before believing the cost); long 2H+4S and
3H+3S. Locked allowances scale alongside (they buy volume and cast
anchoring with no fork, so a mix that raises branched counts may keep
or trim them). Deep chains at current counts stay in the comparison as
the baseline — the point is to *measure* the trade, not presume it.

## Phases

- **Phase 0 — structural simulation & calibration** (frontier):
  synthetic-scaffold yield counts through the real weave + collapse;
  finalize the scale table, shape bands, and B3/B4 derivations;
  rewrite 01 §2 (words-primary table + derivation record + estimated
  words-per-playthrough), add the A19 row to 03 §9.
- **Phase 1 — preset & scaffold plumbing** (mid-tier against this
  contract): `ScaffoldShape` on `ScopePreset`, template wiring,
  `_scaffold_apply` band enforcement, violating-construction tests,
  02 §2 SEED contract update (scaffold numbers come from scope).
- **Phase 2 — words-aware cadence** (frontier math, mid-tier
  plumbing): per-run diamond-site budgets from the B6 target,
  sidetracks in the finalize prompt, a projection test asserting the
  simulated deep-medium story lands ≤ ~800 B6 with the computed site
  budget filled.
- **Phase 3 — SEED research nudge** (frontier, small): D7.
- **Phase 4 — weave spread** (mid-tier + frontier review): metric,
  synthetic clustering test at deep-medium unit counts, stratified
  enumeration if (expected: when) clustering shows.
- **Phase 5 / PR-1b — tensored residue arms** (frontier: G4/I13
  surface; golden-story extension per D5).
- **PR-2 — the exit run**: fresh premise, corpus-grounded `medium` on
  the default Opus/Haiku map, budget estimate **$8–14, cap $20**
  (scaling run 7's $4.03 at 35–48 passages to ~60–80 passages with
  larger FILL contexts); acceptance = roadmap §M8 exit verbatim
  (20–60k words, B3/B4 inside the recalibrated bands, B6 ≤ ~800, all
  arcs simulate complete, exports clean incl. print PDF), preserved
  under `examples/`. Record the cosmetic:real choice ratio in the
  run's decision-log entry either way (D4's honest arithmetic needs
  its live data point).

## Watch items / contingencies

- **SEED payload size**: a deep-medium scaffold proposal is one JSON
  document covering ~2× today's beats; if live repair rounds show the
  moving-target failure mode again, split the scaffold pass per
  dilemma (better repair locality, same contract) — a runner-visible
  change, flag before building.
- **FILL cost superlinearity**: the sliding prose window bounds
  context growth, but convergence lookahead and entity state grow with
  story size; the PR-2 budget cap is the tripwire.
- **B4's meaning under worlds**: beats-per-arc counts traversed beats,
  so world multiplication doesn't inflate it directly — but deep
  post-commit chains inside worlds do; the simulation must count arcs
  exactly as `queries.arc_view` does, not approximate.
