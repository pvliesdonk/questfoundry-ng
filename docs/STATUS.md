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

## Immediate next steps

The epic has a roadmap entry and a recorded design constraint but **no
build contract yet** — no `docs/plans/` doc exists. Next steps:

1. **Spec session (frontier lane)** — this is GROW/weave narrative-DAG
   semantics, the hard part of the codebase. Produce the build contract
   (`docs/plans/weave-linearization.md`): the braiding objective made
   countable (what "interleaved enough" means, on which graph), the
   legal-move set stated precisely against `pipeline/weave.py`'s
   current linearization, the policy knobs, and the validation plan
   (the run-6-era graph and `call-out-farmers` are the known bad
   exemplar to measure against).
2. Skim first: roadmap entry (05 §Now), the 2026-07-17 decision-log
   entries on capsule interleaving, `docs/plans/pov-sequences.md`
   (the sequence concept it builds on), and `pipeline/weave.py`.

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
**structural depth** and **cosmetic forks** (see "Current epics" above and
the roadmap Shipped section). Earlier post-M8 efforts: the administration
restructure (PR #73),
the POLISH passages-pass decomposition (A21, PR #71), `scene_type` /
`narration_scope` annotations + B8, the review contract, reference-pinning
(`refpin.py`), the Ollama backend (A20), rotating limited POV (A22, PR #74).
