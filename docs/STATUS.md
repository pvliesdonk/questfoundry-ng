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

**Administration restructure** (in flight, PR #73): the single ~3,250-line
STATUS doc is split by lifecycle so no file grows unbounded and open items stop
hiding — this slim STATUS (current epic only), the Shipped/Now/Next/Later
roadmap, `BACKLOG.md`, and the decision log moved to its own file. Architecture
decisions stay in the 03 §9 mini-ADR table (an agent reads the table with the
doc; it would not open per-file ADRs). Provenance of agent-authored records is
handled for now by the AGENTS.md caveat; the real fix is the eventual move to
GitHub issues.

## Immediate next steps

1. **Land PR #73** (this restructure), then this hand-off note is the live one.
2. **Prose quality at scale — the remaining live validation** (roadmap "Now"):
   the engine half is built and offline-green; no weak tier has yet completed a
   full clean FILL/DRESS at scale. The *Closed Circle* medium run (2026-07-14)
   got POLISH clean at medium (validating the A21 passages decomposition) and
   surfaced the rotating-POV gap as its FILL blocker.
3. **Rotating limited POV** (design-first, author-gated): a wanted feature
   recorded in [`plans/rotating-pov.md`](plans/rotating-pov.md); the design
   questions (granularity, viewpoint derivation, cadence, first-person
   interludes) are the author's to answer before any code. Blocks
   closed-circle-of-suspects mysteries at FILL.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete. Recent post-M8 efforts merged: the POLISH passages-pass
decomposition (A21, PR #71, live-validated at medium), `scene_type` /
`narration_scope` beat annotations + the B8 pacing report, the review contract,
reference-pinning (`refpin.py`), and the Ollama backend (A20).
