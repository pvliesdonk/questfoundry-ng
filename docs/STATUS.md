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
"Now" entry; numbers in the decision log (2026-07-17). Design docs next,
then offline-TDD implementation.

**Shipped 2026-07-17 (author call): structural depth** (#77/#78/#79/#81;
texture-trial through DRESS gate-clean, `examples/letter-and-frontier`)
**and cosmetic forks** (#87–#103; run-6 author-read "a much better shape").
Details now live in the roadmap Shipped section and the plan docs; PR-6
(print acknowledgments) is the one residual, in BACKLOG.

## Immediate next steps

1. **FILL on the run-6 project is RUNNING** (started 2026-07-17,
   `gpt-oss:120b-cloud`, unbilled, 346 passes) — the actual-read
   continuation of the cosmetic-forks exemplar
   (`/mnt/code/qf-validation-runs/cc-struct-medium`, NOT committed; run-6
   scorecard in the decision log 2026-07-17). When it completes: the
   author read (does it feel interactive?), then DRESS on the same
   project — which is the prose epic's DRESS-at-scale exit and unblocks
   PR-6 (print acknowledgments, BACKLOG).
2. **POV sequences: PR-A (the roster) is built** — scheme pass resolving
   `pov_hint` into `pov_head`/`interlude_carrier` marks, I17, the
   roster-pinned annotate enum + interlude-carrier apply rule, voice
   reading the roster; offline-green (contract:
   [`plans/pov-sequences.md`](plans/pov-sequences.md)). **Next: PR-B** —
   the sequence-unit annotate restructure + B11.
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
