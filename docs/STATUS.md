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

**Rotating limited POV** (built offline-green, PR pending on
`claude/rotating-limited-pov-hikty0`): the author answered the five design
questions directly (2026-07-14 — per-passage head, GROW-annotate assignment,
no cadence engine constraint, first-person interludes in v1, golden coverage
via keepers-bargain's constant head + the e2e fixture) and the engine half is
built per [`plans/rotating-pov-build.md`](plans/rotating-pov-build.md):
per-beat `viewpoint`/`interlude` settled at the freeze, invariant **I14** (one
head per passage) + a G3 referential check, the collapse head-switch cut,
per-passage POV enforcement in FILL's write/review, `Voice.interlude`, and
mini-ADR **A22**. Unblocks closed-circle-of-suspects mysteries at FILL.

## Immediate next steps

1. **Land the rotating-POV PR** (this branch), then:
2. **Live *Closed Circle* validation on a fresh medium project** on the
   unbilled tier (`gpt-oss:120b`, ollama.com) — fresh because the prior
   session's medium project died with its ephemeral container (the checked-in
   `examples/closed-circle` is the older *completed* M8 project, not the one
   that hit the FILL blocker). The new vision pins the same premise and the
   rotating+journal `pov_hint` verbatim. The DREAM quirk this surfaced —
   envision rewrote the authored hint to an invented single-head scheme,
   twice, on two model tiers — resolved per the author (2026-07-14): DREAM
   **translates** the vision and is not micromanaged; the only engine
   guarantee is *visibility* (the authored hint now renders in the dream
   prompt as vision input — both rewrites happened because the prompt never
   saw it), and the override path when a scheme must be pinned (as in this
   validation) is the existing one: edit the DREAM artifact after DREAM,
   before BRAINSTORM (A17; the validation's operator loop automates the
   stop-and-check). Acceptance: FILL clears the rotating-scheme passages, with the
   rotation reading deliberately (one head per passage, journal interludes
   where the scheme asks). (For a project that *does* survive, the resume
   point is `qf rerun grow` — heads are minted at annotate; a pre-viewpoint
   POLISH checkpoint is headless by construction.)
3. **Prose quality at scale — the remaining live validation** (roadmap "Now"):
   the engine half is built and offline-green; no weak tier has yet completed a
   full clean FILL/DRESS at scale. The *Closed Circle* medium run (2026-07-14)
   got POLISH clean at medium (validating the A21 passages decomposition); its
   FILL blocker was the rotating-POV gap this epic closes.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete. Recent post-M8 efforts merged: the administration restructure
(PR #73), the POLISH passages-pass decomposition (A21, PR #71, live-validated
at medium), `scene_type` / `narration_scope` beat annotations + the B8 pacing
report, the review contract, reference-pinning (`refpin.py`), and the Ollama
backend (A20).
