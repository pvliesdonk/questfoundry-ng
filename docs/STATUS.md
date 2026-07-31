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

_Last updated: 2026-07-30._

## Current epic — export styling

**Export styling — gamebook layout directions** is the current epic
(author call, 2026-07-30): the author's Claude Design layout project,
imported as [`plans/gamebook-layouts.md`](plans/gamebook-layouts.md),
becomes selectable print/HTML export styles with a shared WCAG contract
and PDF/UA-1 output. The contract's open decisions were **ratified by
the author in-session 2026-07-30** (art-ratio menu bounded by provider
support; alt + kind + document metadata; large print as a modifier;
first build 1a Paperback + 1d Shelf) — see the plan's "Ratified
decisions". Template work is next.

Earlier epics — prose quality at scale, POV sequences (2026-07-19),
structural depth, cosmetic forks (2026-07-17) — are in the roadmap
Shipped section; their measurement remainders live in the BACKLOG.

## Immediate next steps

Build the epic's first slice (contract: `plans/gamebook-layouts.md`):

1. **Alt-text plumbing** — `alt` on the DRESS brief + runtime JSON art
   entries + both templates; compile print with
   `pdf_standards=("ua-1",)` (typst 0.15.0 supports it).
2. **The shared style layer** — tokens (contrast-checked ramp) + Typst
   template module + HTML template hooks; then **1a Paperback** (A5,
   continuous flow, running heads) and **1d Shelf** (title screen,
   reading modes, WCAG semantics) as the first two styles.
3. **Ratio-as-data** — per-image ratio (menu: 2:3/3:2/1:1) through
   brief → illustrate → runtime → placement rules.

Still standing as later options: the roadmap "Next" candidates (weave
linearization, M9 retrieval refinement) and the BACKLOG measurement
remainders (prose-quality corpus-grounded run + author read — being
served by the in-flight star-swabber run — and the POV-sequences live
A/B).

In flight now (2026-07-30): the **star-swabber live run** — a
corpus-grounded medium run on `kimi-k2.6` (Ollama cloud, unbilled),
premise "pulp space opera in the style of the 'space quest' computer
games", serving the corpus-grounded-run BACKLOG remainder. DREAM→POLISH
gate-clean (103 beats frozen; POLISH: 143 passages), FILL in progress.
Scratch project under `runs/` (gitignored, PR #121).

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete, plus the two 2026-07-19-shipped epics **prose quality at
scale** and **POV sequences**, and the two 2026-07-17-shipped epics
**structural depth** and **cosmetic forks** (see "Current epics" above and
the roadmap Shipped section). Earlier post-M8 efforts: the administration
restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
