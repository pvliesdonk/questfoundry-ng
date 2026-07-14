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
2. **Live *Closed Circle* re-run** from its POLISH checkpoint on the unbilled
   tier (`gpt-oss:120b-cloud`) — the acceptance test is clearing the FILL
   passage the 2026-07-14 run died on, with the rotation reading deliberately
   (one head per passage, journal interludes where the scheme asks).
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
