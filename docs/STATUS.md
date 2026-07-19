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

_Last updated: 2026-07-19._

## Current epics — Now is open

**Both "Now" epics shipped 2026-07-19 (author call)** — details in the
roadmap Shipped section:

- **Prose quality at scale — engine + DRESS at scale.** A weak-tier
  medium (`gpt-oss:120b-cloud`, unbilled) completed DREAM→DRESS gate-clean,
  exports round-tripped, and was illustrated — the first project through
  DRESS + illustration + export, checked in as
  [`examples/closed-circle-oss/`](../examples/closed-circle-oss/) (the
  first example with rendered art). Yield: **five pipeline defects fixed**
  (#110–#114) + two operator-loop refinements. Remainders in BACKLOG: a
  corpus-grounded run + author prose read.
- **POV sequences — run-unit viewpoint annotation.** Machinery merged
  (roster/annotate/interlude, #106/#107/#108, A25); the scheme half
  validated + hardened live (#113, the `pov_hint`-as-law fix). Remainder in
  BACKLOG: the formal live A/B against the run-6 counterfactual.

Earlier: **structural depth** and **cosmetic forks** shipped 2026-07-17.

**Now is unscoped** — the next milestone hasn't been chosen. Small
follow-on work is in flight (author); the roadmap "Next" candidates
(weave linearization, M9 retrieval refinement) are the standing options.

## Immediate next steps

The next milestone is unscoped; the author has small follow-on work in
flight first. When a milestone is chosen, the standing options are the
roadmap "Next" candidates (weave linearization, M9 retrieval refinement),
and the shipped epics' BACKLOG remainders (the prose-quality corpus-grounded
run + author read; the POV-sequences live A/B) are pick-up-able measurement
work needing no new machinery.

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete, plus the two 2026-07-17-shipped epics: **structural depth**
and **cosmetic forks** (see "Current epics" above and the roadmap Shipped
section). Earlier post-M8 efforts: the administration restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
