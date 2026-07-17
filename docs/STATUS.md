# Status — hand-off note

The current epic and the immediate next steps. **A page, not a scroll** — history
does not accrete here. Written and maintained by coding agents for hand-off
(AGENTS.md §"Documentation contract"); read it as an agent's account, not
author-ratified, unless it cites the author.

Where to look for the rest:
- **[`design/05-roadmap.md`](design/05-roadmap.md)** — the epic-scale arc
  (Shipped / Now / Next / Later).
- **[`BACKLOG.md`](BACKLOG.md)** — sub-epic loose ends.
- **[`decision-log.md`](decision-log.md)** — the dated "why it changed" archive
  (search it; don't read it end-to-end).
- **[`plans/`](plans/)** — per-effort design docs.
- **`design/00–04`** — the authoritative rules for each area (the history for
  *your* area is here, not in the decision log).

_Last updated: 2026-07-17._

## Current epics (two threads, roadmap "Now")

**Prose quality at scale — the remaining live validation**: FILL at medium
is demonstrated (the *Closed Circle* run, gate-clean on `gpt-oss:120b`,
author-read prose verdict "good for a 120b model"); the open half is
**DRESS**, plus proving the now-mandatory cadence budget live. The
kimi-k2.5 A/B of the same premise runs in a parallel session.

**Structural depth — material density & texture worlds** (author-directed
2026-07-14, started same day): the flat-book reading's deeper fix. The
milestone design is in
[`plans/structural-depth.md`](plans/structural-depth.md) — the
authoritative contract, PR-sliced. **PR-1 merged** (#77):
`Vision.words_target` couples the soft-dilemma budget to the words budget
(a scope earns its length or shrinks), and **B9** warns when bridges
exceed 25% of beats (the stretching tripwire; the flat exemplar trips it
at 37%, by design). **PR-2 merged** (#78): the `reserve` triage
disposition — brainstorm surplus kept as unwoven texture feedstock.
**PR-3 merged** (#79): the texture-worlds *engine* — the mirrored
parallel-world splice (`Beat.mirrors`, invariant **I15** with its
edge-projection rule), cap-aligned sub-stretch sites, `texture_plan`,
and cadence diamonds mirrored into arms. **PR-4 + the live-run fixes are on PR #81**: the pipeline wiring — POLISH
finalize offers the texture sites and *requires* them filled, the
words-budget cap on `texture_plan`, FILL's texture-premise lever (W4) —
plus everything the validation run surfaced: the I12 unit correction
(dilemma states, not flags) with the audit's `split_on` escape valve,
batched echo/apply feedback, the loosened review margins (author-directed
twice: never add more rules — check the existing write prompt for
clarity, the existing review prompt for over-strictness), the per-pass
repair budget (write passes get 4), and legible voice bans. **The live
validation completed 2026-07-15: the short-scope texture-trial ("The
Letter and the Frontier") is the first project ever through DRESS
gate-clean** — 0 errors, W1–W4 all exercised (scorecard in the decision
log); checked in as [`examples/letter-and-frontier/`](../examples/letter-and-frontier/)
(through DRESS — codex + art briefs included; exports stay out per
AGENTS.md, the author has the HTML/PDF). Previous epic **Rotating limited POV shipped in PR #74** (A22).

## Immediate next steps

0. **Live validation: PASSED** (2026-07-14, ~13:30Z). A fresh medium *Closed
   Circle* project on the unbilled tier (`gpt-oss:120b`, ollama.com; premise +
   rotating+journal `pov_hint` pinned verbatim, the hint re-pinned by editing
   the DREAM artifact post-DREAM per A17 — DREAM translates, it is not
   micromanaged; author decision 2026-07-14, decision log) completed FILL
   **gate-clean (0 errors)** — the first weak-tier medium ever to finish FILL
   — with the rotating scheme real at every level: 4 heads over 98 headed
   passages (60/14/12/12) + 14 headless texture/coda passages, one head per
   passage (I14 in the passing gate set), 112 passages / 239 beats, 844
   calls, ~2.8M in / 1.0M out, unbilled. Six advisory warnings (5× B5
   near-band, 1× B6 pacing). ~15 halts along the way, every one a
   pre-existing prompt/review defect or honest 2-round non-convergence —
   zero rotating-POV machinery failures; the fixes are on this branch and
   the stall journal is the record. NOT exercised: first-person interludes
   (the voice declared the register but annotate marked no beats — open
   follow-up) and DRESS. The finished project is checked in as
   [`examples/closed-circle-medium/`](../examples/closed-circle-medium/)
   (at FILL — no codex/art; exports stay out of the repo per AGENTS.md,
   the author has the generated HTML/PDF). **Caveat discovered on first
   reading (same day):** gate-clean but structurally flat — see "Current
   epic"; the exemplar predates the cadence-budget enforcement and stays
   checked in as the cautionary baseline. The prose itself passed the same
   author reading ("good for a 120b model" — the first author-ratified
   weak-tier prose verdict): the gap is confined to POLISH's choice layer.
   **The kimi-k2.5 A/B completed 2026-07-15** — gate-clean FILL, 54 branch
   points / 159 passages, words-per-choice IN band with the same advisory
   prompts (kimi filled the cadence budget voluntarily; full table in the
   decision log). Checked in as
   [`examples/closed-circle-k2/`](../examples/closed-circle-k2/) (at FILL,
   same conventions as the baseline exemplar; the author has the HTML/PDF). Interludes: **zero on both tiers** — the annotate gap is
   tier-independent. New loose end: kimi headed 4 passages with the victim,
   outside the declared rotation (scheme conformance is ungated; BACKLOG).
1. **The prose epic's next run — DRESS at scale, proving the enforced
   cadence budget on the way:** a fresh weak-tier medium run whose finalize
   fills the budget (or halts honestly trying), whose passage layer lands
   in the B6 band, and which then completes DRESS gate-clean. Watch for
   repair exhaustion: a ~60-site budget in one proposal is untested at the
   weak tier; if it exhausts, the fix is decomposing the finalize pass
   (per-run calls), not softening the requirement. (DRESS purely as
   machinery exercise could also run on the flat exemplar.) Setting a
   band-top `--words-target` on that run would also exercise PR-1's
   coupling live.
2. **Structural depth — short-scope live validation DONE (2026-07-15)**:
   the texture-trial (`gpt-oss:120b`, unbilled, short scope per author
   choice — micro offers no texture sites) ran DREAM→DRESS gate-clean:
   0 errors, 41 advisories (32× B4 arc-band + 1× B3 passage-band — the
   known post-modulation recalibration, BACKLOG; 8× B8 pacing; **B6, B7,
   B9 all silent**). W1 (1 hard + 4 soft coupled), W2 (2 reserved), W3
   (3 texture worlds planted, 34 arm beats, mirrored cadence), W4
   (premise-grounded arm prose — pines/moonlight vs plains/dust twins,
   no lifts) all exercised live. Seven operator halts, each a real
   defect fixed at root on PR #81 (stall journal + decision log). Still
   open for the milestone's full exit: the author read of the generated
   story (does it feel interactive?), and the **medium** run with a
   band-top `--words-target` — which doubles as step 1's DRESS-at-scale
   validation. Watch finalize there: texture arms are its largest
   proposal yet; exhaustion means decomposing the pass (A21 precedent),
   not softening the requirement.
3. **Current epic — cosmetic forks** (unified 2026-07-15; k ≥ 2 renderings
   of a trunk segment, renderings as peers, finalize as a loop, residue
   keywords). Contract + ratified decisions + PR slices in
   [`plans/cosmetic-forks.md`](plans/cosmetic-forks.md) (mini-ADR A24).
   **PR-0 through PR-4 are MERGED:** PR-0 exit-label residue §5 (#87), PR-1
   01 §6 one-mechanism framing (#90), PR-2 symmetry engine — one splice
   primitive `insert_cosmetic_fork` + premise per rendering incl. rendering
   0 (#97), PR-3 engine-assigned cadence shape mix + 3-arm diamonds (#98,
   resolves the 44/44-sidetracks finding), PR-4 the cosmetic **grant model**
   — `Beat.grants_flags`, `grant_beats`/`choice_grants`/I10 for cosmetic
   flags (#99). Plus the validation-run fixes: finalize entity-roster (#92),
   audit per-passage decomposition (#95), PR-0 shape-neutral vocab + BACKLOG
   close-outs (#96), and the findings record (#94).

   **The medium validation run completed gate-clean through POLISH** once
   the audit was decomposed (0 errors, 83 advisories; I12 71→0; 312 beats,
   277 passages incl. 132 audit-split variants). The exemplar lives at
   `/mnt/code/qf-validation-runs/cc-struct-medium` (NOT committed;
   `gpt-oss:120b-cloud`, unbilled). Confirmed on that run: **no ~60-site
   finalize exhaustion** (the whole proposal landed in one shot) — the
   plan's top loop-risk did not manifest.

**PR-5 MERGED (#101), and the stretch cap MERGED (#102)** — the author
   read of the first loop-built graph (run-5: one productive round, walks
   at ~2,700 words/choice, a 14-passage no-choice desert on every walk)
   directed: interruption is the metric, braided like the ending; words
   calibration later. #102 delivers `choice_stretch_max` (default 4), the
   DAG-wide conservative stretch metric, advisory **B10**, and the
   three-phase `fork_plan` admission (mandatory words-exempt stretch
   breaks → probe-priced depth → B6 fine-tuning). Recalibration flags
   still open (BACKLOG): B6 lands a few percent over its top at the words
   band top; arc-VIEW beat counts inflate with renderings a walk never
   traverses (B3/B4 post-modulation).

   **Run-6 (2026-07-16/17) — the stretch-capped loop live, author-read
   and approved:** rerun POLISH on the cc-struct-medium GROW checkpoint
   (`gpt-oss:120b`, unbilled), gate-clean — 0 errors, B10 ×1 (the one
   seam-less 5-stretch, reported as designed). Worst no-choice stretch 14
   → 5 (everything else ≤ 4, 1s–4s throughout); walk words/choice
   2,324–3,241 → 1,531–1,660; ~25 fork sites over 3 rounds (run-5: 7/1);
   35 keywords minted; zero repair rounds across all fork passes. Words
   62.8k, +14% over the 55k target (the ratified break surplus, to be
   reclaimed by calibration). Exemplar still at
   `/mnt/code/qf-validation-runs/cc-struct-medium` (NOT committed; graph
   SVG beside the project; run-5 kept as `.run5-pr5-loop-backup`).

   **Keyword consumption fixed and live-proven (PR #103, merged
   2026-07-17):** run-6 consumed zero of ~18 offers; diagnosis was the
   KEYWORDS section of `polish_fork.j2` structurally tilted toward
   declining (decision log). Rebalanced (payoff first, positive echo
   criterion, decline narrowed) and validated on a throwaway rerun of the
   run-6 checkpoint: round 2 consumed **8/8** offered sites (old prompt:
   0/~18). Consumption stays optional-never-assigned.

   **FILL is running on the run-6 project** (started 2026-07-17,
   `gpt-oss:120b-cloud`, unbilled, 346 passes) — the actual-read
   continuation. Then PR-6 (DRESS print acknowledgments — keywords now
   both mint and consume).

   **New findings from the author's read of the run-6 graph (2026-07-17,
   decision log + BACKLOG):** (a) annotate head-hops at beat granularity
   (58% of linear annotated pairs switch heads) and I14 then shatters
   linear runs — 76 of 172 passages exist only as POV splits; heads held
   per run would give 114 passages (−28%). **Next work item (author-
   agreed): restructure viewpoint annotation so the run, not the beat, is
   the unit** — design first, then build. (b) Drama-layer braiding: an
   unexplored dilemma weaves as a 6-beat consecutive capsule — epic-scale
   GROW question, recorded under roadmap "Later". GitHub *issues* are NOT
   used for this repo (author, 2026-07-15) — work is tracked here and in
   the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete. Recent post-M8 efforts merged: the administration restructure
(PR #73), the POLISH passages-pass decomposition (A21, PR #71, live-validated
at medium), `scene_type` / `narration_scope` beat annotations + the B8 pacing
report, the review contract, reference-pinning (`refpin.py`), and the Ollama
backend (A20).
