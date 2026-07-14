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

## Current epic

**Structural interactivity holds at every tier** (roadmap "Now"; opened by
the author's first reading of the checked-in exemplar, 2026-07-14): the
gate-clean *Closed Circle* medium turned out "essentially a flat story" —
10 branch points over 112 passages (M8's run: 62/148), zero false-branch
beats, 3352 words per genuine choice vs the 250–800 band. Root cause found
and fixed the same day: finalize's engine-computed cadence budget was
requested in prose but never enforced — the live run proposed
`false_branches: []` four rounds straight, unchallenged (the kimi A/B
filled the same budget: a tier-dependent knob, hence an architecture bug —
author framing). The budget is now **mandatory at `_finalize_apply`**
(design 02; decision log 2026-07-14 "flat-book post-mortem"). Previous
epic **Rotating limited POV shipped in PR #74** (A22; roadmap "Shipped").

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
   weak-tier prose verdict): the gap is confined to POLISH's choice layer. A kimi-k2.5 A/B of the same
   premise is still running for the tier comparison.
1. **Prove the enforced cadence budget live:** a fresh weak-tier medium run
   whose finalize fills the budget (or halts honestly trying) and whose
   passage layer lands in the B6 band — the acceptance test for the current
   epic. Watch for repair exhaustion: a 60-site budget in one proposal is
   untested at the weak tier; if it exhausts, the fix is decomposing the
   finalize pass (per-run calls), not softening the requirement.
2. **Prose quality at scale — the remaining live validation** (roadmap "Now"):
   FILL at scale on a weak tier is now demonstrated (step 0); the missing half
   of the exit is **DRESS** — no weak tier has yet completed a clean DRESS at
   scale. Worth running on a post-enforcement project rather than the flat
   exemplar (or on it, purely to exercise the DRESS machinery).

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete. Recent post-M8 efforts merged: the administration restructure
(PR #73), the POLISH passages-pass decomposition (A21, PR #71, live-validated
at medium), `scene_type` / `narration_scope` beat annotations + the B8 pacing
report, the review contract, reference-pinning (`refpin.py`), and the Ollama
backend (A20).
