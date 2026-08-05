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

_Last updated: 2026-08-05._

## Current epic — export styling

**Export styling — gamebook layout directions** is the current epic
(author call, 2026-07-30): the author's Claude Design layout project,
imported as [`plans/gamebook-layouts.md`](plans/gamebook-layouts.md),
becomes selectable print/HTML export styles with a shared WCAG contract
and PDF/UA-1 output. The contract's open decisions were **ratified by
the author in-session 2026-07-30** (art-ratio menu bounded by provider
support; alt + kind + document metadata; large print as a modifier;
first build 1a Paperback + 1d Shelf) — see the plan's "Ratified
decisions".

**The first slice is built (2026-08-05).** Alt text runs end to end
(brief → DRESS → runtime → both templates) and print compiles with
`pdf_standards=("ua-1",)`, so the Typst compiler refuses a build with a
missing alt or title. Ratio is per-image data (2:3/3:2/1:1) from the
brief through `qf illustrate` to each style's placement rule. The shared
layer is `export/style.py` — contrast-checked ramps whose failure blocks
the build, the ratio/placement tables, large print as a modifier. Two
styles ship: **1a Paperback** (`--style paperback`, now the default —
A5, continuous flow, running heads carrying the spread's section range,
turn-to numbers bold at the right margin) and **1d Shelf**
(`--style screen` — title screen with the cover inset, reading-mode
control, WCAG semantics as real elements). Durable rules: design doc
[04 §7](design/04-export-and-play.md); mini-ADR **A26**.

Earlier epics — prose quality at scale, POV sequences (2026-07-19),
structural depth, cosmetic forks (2026-07-17) — are in the roadmap
Shipped section; their measurement remainders live in the BACKLOG.

## Immediate next steps

Continue the epic (contract: `plans/gamebook-layouts.md`, and its "What
is built" section for what the first slice deliberately left):

1. **The remaining directions as variations** — **1b Bound** (marginal
   numerals, italic instruction blocks, Codex as a spoiler-safe
   appendix) and **1c Compendium** (band cover, type-driven front
   matter) for print; **1e Room** (`--style table`, cover filled to the
   viewport) for HTML. The style layer is proven on 1a/1d, so each is a
   record plus its own furniture.
2. **axe-core in CI** over a handful of exported sections per style —
   the one part of the WCAG contract still checked by reading rather
   than by a machine.
3. **The `image-generation-mcp` resolution adapter task**
   ([#337](https://github.com/pvliesdonk/image-generation-mcp/issues/337)):
   until it lands, cloud covers sit below the 300dpi full-bleed floor
   and take the inset fallback the export already reports.

A **live styled export has not been run** — the slice was validated on
the golden story with the placeholder image provider (both media driven
end to end, the HTML in a real browser). Reading a full styled book is
the natural next check, and needs no billed calls beyond a `qf
illustrate` batch on an existing run.

Still standing as later options: the roadmap "Next" candidates (weave
linearization, M9 retrieval refinement) and the BACKLOG POV-sequences
live A/B.

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

**Register conformance: BUILT AND VALIDATED (2026-08-05).** The
star-swabber run (medium, kimi-k2.6, corpus-grounded) completed
DREAM→DRESS gate-clean but the author read the prose as over-stylized;
the fix — manuscript-first continuation framing, countable register
budget, depth-2 look-behind, Voice-declared recurring devices, richer
story-so-far — was spec'd, built as a three-PR stack, and validated
live on `runs/register-short` (same premise, short scope): 122/122
passes, zero repair exhaustions, register fixed on the author's read.
The author closed the loop **without a medium-scope A/B** (verbatim:
"we have plenty of evidence this is an improvement") and designated
the run as the **register exemplar** — the full validation record with
exemplar passages is `plans/register-conformance.md` §10. A staccato
rhythm defect found during the read was tuned with one clause (PR
#127, "plain does not mean short").

M0–M8 complete, plus the two 2026-07-19-shipped epics **prose quality at
scale** and **POV sequences**, and the two 2026-07-17-shipped epics
**structural depth** and **cosmetic forks** (see "Current epics" above and
the roadmap Shipped section). Earlier post-M8 efforts: the administration
restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
