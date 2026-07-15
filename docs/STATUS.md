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

_Last updated: 2026-07-14._

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
and cadence diamonds mirrored into arms. **PR-4 is built on this
branch**: the pipeline wiring — POLISH finalize offers the texture sites
and *requires* them filled (site index + one-line premise + one
model-worded beat per trunk beat; splices texture → false branches →
residue, cadence sized on a graph carrying the forks so both budgets
agree), `texture_plan` is capped by the words budget (a parallel stretch
is printed twice and must fit `words_target`), and FILL's write prompt
names the passage's texture-world premise (W4 — persisted on the arm
beats, the `variant_flag` precedent). Every exemplar and recorded
fixture stays green (fixture stories offer no sites).
Previous epic **Rotating limited POV shipped in PR #74** (A22).

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
   decision log). Interludes: **zero on both tiers** — the annotate gap is
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
2. **Structural depth — only the live validation remains** (the
   milestone's exit, plan §PR slicing): a fresh weak-tier medium with a
   band-top `--words-target` — the budget derives more softs (W1),
   triage reserves feedstock (W2), finalize plants texture worlds and
   fills the cadence budget (W3), FILL grounds each world's premise
   (W4); exit is B6 mid-band, B9 quiet, gate-clean through DRESS, and an
   author read that finds actual interactivity. This run can double as
   the prose epic's DRESS-at-scale validation (step 1). All four PRs are
   built; watch the finalize pass closely on the weak tier — texture
   arms are its largest single proposal yet (a ~15-beat site in one
   entry) and repair exhaustion there means decomposing the pass
   (per-site calls, the A21 precedent), not softening the requirement.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete. Recent post-M8 efforts merged: the administration restructure
(PR #73), the POLISH passages-pass decomposition (A21, PR #71, live-validated
at medium), `scene_type` / `narration_scope` beat annotations + the B8 pacing
report, the review contract, reference-pinning (`refpin.py`), and the Ollama
backend (A20).
