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
is demonstrated twice (the *Closed Circle* run gate-clean on
`gpt-oss:120b`, author prose verdict "good for a 120b model"; the
kimi-k2.5 A/B). The open half is **DRESS at scale** — the current FILL
run (below) continues toward it.

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
**Open: the live A/B itself** — see "immediate next steps".

**Shipped 2026-07-17 (author call): structural depth** (#77/#78/#79/#81;
texture-trial through DRESS gate-clean, `examples/letter-and-frontier`)
**and cosmetic forks** (#87–#103; run-6 author-read "a much better shape").
Details now live in the roadmap Shipped section and the plan docs; PR-6
(print acknowledgments) is the one residual, in BACKLOG.

## Immediate next steps

**Both runs below were interrupted by a host session crash (found
2026-07-17 on session recovery) — neither failed on its own merits; both
are cleanly resumable from their checkpoints, not restarts.**

1. **FILL on the run-6 project — STALLED, needs resume.**
   `/mnt/code/qf-validation-runs/cc-struct-medium` (NOT committed;
   `gpt-oss:120b-cloud`, unbilled, 346 passes; run-6 scorecard in the
   decision log 2026-07-17) is the actual-read continuation of the
   cosmetic-forks exemplar, driven by a scratch operator loop
   (`fill-driver.py`, journaling stalls to `stall-journal-fill.md` —
   the roadmap "Later" pipeline-operator-loop prototype). It reached
   259/346 passes; `write:p-fork-cred` failed and the driver process
   died before logging the stall or re-rolling — the crash caught it
   mid-loop, not mid-repair. Resume by re-running the driver (or
   `qf run fill -C .` directly); the ledger/checkpoint make this free.
   When it completes: the author read (does it feel interactive?), then
   DRESS on the same project — the prose epic's DRESS-at-scale exit,
   unblocking PR-6 (print acknowledgments, BACKLOG).
2. **POV sequences live A/B — POLISH generation done, not finalized,
   needs resume.** `/mnt/code/qf-validation-runs/cc-seq-ab` (NOT
   committed; same tier/premise, GROW rerun on a copy of
   `cc-struct-medium` with every pass but scheme/annotate kept, per
   `plans/pov-sequences.md`) finished GROW and all 512/512 POLISH
   proposal-generation items (through `arcs`), then the process died
   before the finalize/gate step that commits the stage — `project.yaml`
   still reads `stage: grow`, so `qf run` will resume forward from
   POLISH cleanly. Acceptance once it lands: B11 quiet or justified,
   passages toward the −28% counterfactual, the interlude register
   firing (PR-C's fix, above, is already in the pipeline this run used).
3. **Then:** PR-6 once DRESS runs on a keyword-consuming project, and the
   recalibration items (BACKLOG) as calibration data accumulates.

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete, plus the two 2026-07-17-shipped epics: **structural depth**
and **cosmetic forks** (see "Current epics" above and the roadmap Shipped
section). Earlier post-M8 efforts: the administration restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
