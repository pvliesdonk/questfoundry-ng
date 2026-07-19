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

## Current epics (two threads, roadmap "Now")

**Prose quality at scale — DRESS at scale reached (2026-07-19)**: a fresh
comprehensive medium run on current `main` (`gpt-oss:120b-cloud`, unbilled)
completed **DREAM→DRESS gate-clean**, its HTML/PDF exports round-tripped
(0 problems), and it was then illustrated (20 Gemini images, 0 refusals) —
the first project ever taken all the way through DRESS + illustration +
export. Checked in as [`examples/closed-circle-oss/`](../examples/closed-circle-oss/)
(with rendered art — a first for the examples; exports stay out per
convention, the author holds the HTML/PDF). The run's real yield was
**five pipeline defects fixed** (#110 labels schema+nudge, #111 I13
powerset OOM, #112 cosmetic flags flooding FILL WORLD STATE, #113 scheme
treating `pov_hint` as law, #114 the I13 blowup's two export copies) plus
two operator-loop refinements — every one confirming the doctrine (never
the model). **Remaining for the epic's full exit:** a *corpus-grounded*
run (this one skipped research — no craft corpus) and an author prose read.

**POV sequences — run-unit viewpoint annotation** (design agreed with the
author 2026-07-17, from their read of the run-6 graph): annotate head-hops
at beat granularity and I14 shatters linear runs into thin no-choice
passages (76 of 172 passages are pure POV splits; heads held per run would
give −28% passages). The redesign — the **sequence** (maximal choice-free
run, computed) as the unit of viewpoint assignment, one head per sequence,
split/wide-cutaway as justified escape valves, a **head roster** resolved
from `pov_hint` pinning the viewpoint enum (also closes the off-scheme-head
gap), B11 advisory, `Voice` reads the roster — is specified in the roadmap
"Now" entry; numbers in the decision log (2026-07-17). **PR-A (#106) and
PR-B (#107) merged** (roster + sequence-unit annotate restructure, mini-ADR
A25). **PR-C (#108) merged**: the interlude register, which had never fired
live across three prior runs on two tiers, now fires — a three-probe live
series (`cc-int-probe`, moment-based criterion + an enforced commit-guard
apply check) took it from 0 marks to 14/14 correctly placed in one repair
round; recorded as a doctrine exhibit in the decision log (2026-07-17).
**Open: the live A/B itself** — the scheme half was validated on the
2026-07-19 comprehensive run (the `pov_hint`-as-law fix, #113); the formal
A/B measurement against the run-6 counterfactual is still owed (next steps).

**Shipped 2026-07-17 (author call): structural depth** (#77/#78/#79/#81;
texture-trial through DRESS gate-clean, `examples/letter-and-frontier`)
**and cosmetic forks** (#87–#103; run-6 author-read "a much better shape").
Details now live in the roadmap Shipped section and the plan docs.
**No residual: PR-6 (print acknowledgments) was scoped and closed without
building, 2026-07-17** — form 1 (keyword-gated rendering) already delivers
real print consumption end-to-end; an unconsumed keyword already gets zero
print footprint today, which is correct (decision log). The epic is
complete.

## Immediate next steps

1. **The comprehensive run: DONE (2026-07-19).** DREAM→DRESS gate-clean,
   exports round-trip, illustrated — checked in as
   [`examples/closed-circle-oss/`](../examples/closed-circle-oss/). It
   surfaced and fixed five pipeline defects (#110–#114, all merged) — the
   record is in the decision log (2026-07-18/19). **Still open** from the
   prose epic's exit: a *corpus-grounded* run (this skipped research) and
   an author prose read of the generated story.
2. **POV sequences — the scheme half validated, the A/B still owed.** The
   `pov_hint`-as-law defect (#113) was found and fixed on this run (the
   investigator was resolvable to carrier-only, leaving her own scenes
   bystander-headed); the fix's outcome was applied to this run's graph to
   let it finish. NOT yet done: the formal live A/B against the run-6
   counterfactual (B11 quiet/justified, passages toward −28%, interlude
   register firing) — a clean rerun-grow measurement, still owed.
3. **Then:** the recalibration items (BACKLOG) as calibration data
   accumulates.

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete, plus the two 2026-07-17-shipped epics: **structural depth**
and **cosmetic forks** (see "Current epics" above and the roadmap Shipped
section). Earlier post-M8 efforts: the administration restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
