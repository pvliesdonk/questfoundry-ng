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

## Current epic — weave linearization (drama-layer braiding)

**Weave linearization — drama-layer braiding** is the current epic
(author call, in-session 2026-08-05: "we will move on to the braiding
epic"). The problem, from the author read of the run-6 graph
(2026-07-17): an unexplored dilemma's beats weave as one consecutive
capsule (`call-out-farmers`: 6 uninterrupted beats right after setup,
no other thread interleaved) — the fork loop braids the *choice* layer;
nothing braids the *drama* layer. The epic: use the weave's
linearization freedom deliberately — interleave capsule blocks
thread-by-thread, and reorder for head-candidate contiguity. Legal
moves are stable cross-thread interleavings: within-thread order,
intersection adjacencies, and temporal hints stay pinned. **Recorded
design constraint (2026-07-17): linearization policy is weave-side and
pre-contextualize** — after contextualize the summaries chain
narratively and reordering would force re-contextualization; before
it, reorder is a pure engine step. Builds on the POV-sequences
sequence concept; touches the scaffold shape, intersections, and the
capsule placement the shape presets encode. Roadmap entry: 05 §Now.

**The build contract is ratified** (in-session 2026-08-06):
[`plans/weave-linearization.md`](plans/weave-linearization.md) — the
heritage phase model as the objective (clusters at the ends, dense
interleaving in the middle, commits distributed), countable per-arc
metrics (introduction latency, middle run-length ≤ 3, commit spacing,
block shape), one commutation algebra across three moments (weave /
POLISH entry / during POLISH) with a monotone move-cost gradient,
moment 1 load-bearing, prefer-don't-prune candidate scoring with the
LLM keeping the pick, soft diamonds atomic, block-shaping for head
contiguity. Includes the author's freeze clarification: the frozen
thing is the **branching topology**; linear-stretch order is
linearization state, mutable under the pin algebra (iron rule 4 and
design doc 01 get their letter sharpened in PR-1).

## Immediate next steps

Done: **PR-1 — the braid decided** (2026-08-06): per-candidate
arc-order induction, the scorer, ranked+scored candidates with the
phase doctrine in the chooser prompt, B12 at the gate (live signal on
both medium examples), the freeze-clarification doc letter. **PR-2 —
the repair primitive** (2026-08-06): `swap_linear_beats` with every
pin enforced at the mutation layer, returning the stale beats (the
re-contextualization price); invariant I18 (group contiguity) + gate
check + violating constructions.

1. **PR-3 — braid-respecting POLISH** (mid-tier): collapse boundary
   preference, fork-loop site preference, insertion placement.
2. **Validation**: unbilled GROW-from-weave rerun on the
   cc-struct-medium checkpoint (acceptance: worst-arc middle run ≤ 3
   where run-6 scored 6), B12 before/after, author read of one arc —
   also the calibration read for the metric knobs (N, K, S).

Also still standing: the BACKLOG POV-sequences live A/B; the
export-styling residual (upstream
[#337](https://github.com/pvliesdonk/image-generation-mcp/issues/337),
handled in a separate session — full-bleed covers take the inset
fallback until it lands).

GitHub *issues* are NOT used for this repo (author, 2026-07-15) — work is
tracked here and in the BACKLOG.

## Recently shipped (see roadmap "Shipped" + the decision log)

**Export styling: DONE (author call, in-session 2026-08-05: "I'm
calling both epics done for now. with the high resolution pending an
update of upstream").** All five layout directions as selectable
styles over the shared style layer, alt text + PDF/UA-1 end-to-end,
ratio-as-data, axe-core in CI, image compression (lossless at the
render write site, `qf illustrate --compress` lossy opt-in), and the
live styled read on `examples/closed-circle-oss` with real art. Full
record: roadmap Shipped entry; mini-ADR A26; design doc 04 §7.

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
**structural depth** and **cosmetic forks** (see the roadmap Shipped
section). Earlier post-M8 efforts: the administration
restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
