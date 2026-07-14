# Backlog — working loose ends

Sub-epic tasks that aren't owned by a roadmap epic. One line each; a task owned
by a future epic lives **under that epic in [`design/05-roadmap.md`](design/05-roadmap.md)**,
not here (that's the rule that stops this list and the roadmap from duplicating).
Close an item by **deleting** it — git history keeps the record; a lasting
decision it settled gets an [ADR](adr/).

> Written and maintained by coding agents for hand-off (see AGENTS.md
> §"Documentation contract"). An item's framing is an agent's, not the author's,
> unless it says otherwise.

## Structure & scale

- [ ] **Scale recalibration after modulation.** `scene_type` shortens
  sequel/micro passages, so the `words_total`/`passages` (B3/B7) bands read
  high. Now has data: the *Closed Circle* medium run came out **59 passages vs
  the 90–160 band**. Re-measure the preset bands against a modulated live run
  (`tests/scale.py`) and adjust. (Flagged when `scene_type` landed; no longer
  hypothetical.)
- [ ] **Intersections over post-commit (exclusive) beats** — M2 only groups
  shared pre-commit beats; exclusive-beat intersections are meaningful but
  interact with arc membership in ways the spine model doesn't cover. Same for
  **temporal hints inside atomic fork units** (a hint there has nothing to
  move). Revisit when a generated story demands one.
- [ ] **Cosmetic flags on false branches / locked storylines** — the machinery
  exists (`FlagSource.COSMETIC`); wire grants when a residue beat or print
  codeword actually wants one.

## Prose & annotations

- [ ] **`exit_mood` beat annotation** — deferred with the annotation family (01
  §10.3); add only on a demonstrated FILL quality gap (the `scene_type` /
  `narration_scope` precedent).

## Export & tooling

- [ ] **Non-digit codeword fallback** — derived fallback codewords may contain
  digits (slugs allow them; `^[A-Z]{3,12}$` binds only DRESS-stored codewords).
  Cosmetic; a print warning already tells authors to run DRESS.
- [ ] **`qf illustrate` style-reference conditioning** — feed a rendered image
  back as a reference for the rest of the batch (M7's documented escalation).
  The live run showed *style* drift, not character drift; wire the reference
  path when a run demands it.

## Validation & experiments

- [ ] **Local `qwen3.5`-class Ollama confirmation** — the cloud tier is
  validated end-to-end; a local-daemon run is still wanted when a host is
  reachable (needs a GPU box with the daemon logged in to ollama.com).
- [ ] **Subagents as an unbilled Claude for pipeline calls** (author idea) — can
  a provider adapter route `complete()` through a dev-session's own subagents,
  preserving schema-validation + determinism? A small targeted spike.
- [ ] **Corpus curation** — `corpus/interactive-fiction/` is the author's
  ongoing add/trim pass; `style-exemplars` stays out until M9 can consume it.

## Docs hygiene (fold into the STATUS slim-down)

- [ ] **Reconcile the stale "G4 pacing report is deferred" mentions** — it
  shipped as advisory **B8** (`check_b8_pacing`); older STATUS/roadmap text
  still calls it deferred.
