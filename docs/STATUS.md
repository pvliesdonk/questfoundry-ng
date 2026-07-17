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
kimi-k2.5 A/B). The open half is **DRESS at scale** — the prior run-6 FILL
attempt was abandoned mid-stall after a host crash (worktree pinned to a
now-merged commit; see "immediate next steps"); a fresh comprehensive run
on current `main` is next.

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
**Open: the live A/B itself** — the prior attempt was abandoned mid-run
after a host crash (worktree pinned to a now-merged commit); folded into
the next comprehensive run, see "immediate next steps".

**Shipped 2026-07-17 (author call): structural depth** (#77/#78/#79/#81;
texture-trial through DRESS gate-clean, `examples/letter-and-frontier`)
**and cosmetic forks** (#87–#103; run-6 author-read "a much better shape").
Details now live in the roadmap Shipped section and the plan docs; PR-6
(print acknowledgments) is the one residual, in BACKLOG.

## Immediate next steps

**The two in-flight validation runs found on session recovery
(2026-07-17) are ABANDONED, not resumed — author call.** Both
(`cc-struct-medium`'s run-6 FILL, `cc-seq-ab`'s POV-sequences live A/B)
were driven from a worktree pinned to a specific pre-merge commit
(`bridge-cse_01YVyfGboiN3WsuhY2BgfAVt`); since the crash, that branch
(pov-sequences-pr-c) and its siblings merged into `main` (#101, #102,
#108). Resuming a checkpoint against pipeline code that has since moved
— different prompts, schemas, gate logic than what produced the
checkpoint — risks silent, hard-to-attribute behavior; a resume is only
as trustworthy as "the code that continues it is the code that started
it," which is no longer true here. Cheaper and more honest to let both
lapse (directories left at `/mnt/code/qf-validation-runs/{cc-struct-medium,cc-seq-ab}`,
NOT committed, NOT resumed) and re-run clean once the next comprehensive
run is scoped (below).

1. **Quick win first: PR-6 — DRESS print acknowledgments** (cosmetic-forks
   §4 consumption form 3; the shipped epic's one residual, BACKLOG).
   "If you noted PINE: …" inline conditional paragraphs in print export.
   No live run needed to build it — the plumbing is already eager
   (`projected_flags` picks up tested cosmetic flags, `StateFlag.codeword`
   + DRESS naming exist); only the export form is new. Small, self-
   contained, unblocked (keywords already mint and consume live per PR
   #103 and the interlude-probe series). Good use of a session between
   live-run cycles.
2. **Then: one new comprehensive live run from a clean worktree on
   current `main`** (not a resume) — DREAM→DRESS at medium,
   `gpt-oss:120b-cloud` unbilled, exercising everything landed since the
   last clean run: the PR-5 finalize loop, the stretch cap (B10), the
   POV-sequences roster + sequence-unit annotate + interlude register
   (PR-A/B/C), and PR-6 above if it lands first. This single run replaces
   both abandoned ones and is this cycle's DRESS-at-scale exit for the
   prose-quality epic *and* the live A/B acceptance for POV sequences
   (B11 quiet or justified, passages toward the −28% counterfactual,
   interlude register firing) — no need to run them separately again.
3. **Then:** the recalibration items (BACKLOG) as calibration data
   accumulates from the new run.

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

M0–M8 complete, plus the two 2026-07-17-shipped epics: **structural depth**
and **cosmetic forks** (see "Current epics" above and the roadmap Shipped
section). Earlier post-M8 efforts: the administration restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
