# Rotating limited POV — a wanted feature (new record of intent)

> Status: **WANTED / not yet designed** (2026-07-14). This records an author
> intent that a **prior agent overrode**: rotating limited POV — a viewpoint
> character that changes across the book (per passage or per section) while each
> unit stays inside one head — is a real, foreseen literary choice the author
> wants supported. It was previously written off as out of scope. This document
> reverses that **going forward**; it does not rewrite the earlier record.

## Why this exists (read this first)

The earlier POV work (`docs/plans/pov-narration-scope.md`, decision **1.a**,
under a heading titled *"Decisions locked (author-confirmed 2026-07-13)"*)
rejected *"a full per-beat viewpoint-character/distance field"* as something that
*"vastly exceeds the problem,"* and design doc 01 §562 files the whole
viewpoint-annotation family under a blanket *"deferred all of them under YAGNI."*

**That rejection was an agent scope-cut, not an author decision** — it was
recorded under the author's name, which it should not have been. The author has
since made clear that rotating POV was asked for and is wanted; the deferral was
an LLM defaulting to the smallest MVP and writing the choice down as the
author's. Per `AGENTS.md` §"Prompt and error-message quality" and the model's own
standing bias toward minimal change, this is a known failure mode, named here so
the next session does not inherit the false premise a third time.

**What this document does NOT do:** it does not edit or delete the earlier
record. `pov-narration-scope.md` and 01 §562 stay as written — they are the
historical account of what was built (single fixed POV + `narration_scope`).
This file is the forward-looking record that the direction has changed.

## The concrete trigger (live evidence)

A fresh **medium** live run of the *Closed Circle* premise (an Agatha-Christie
closed-circle murder that escalates Fargo-style) on `gpt-oss:120b-cloud`
(2026-07-14) reached POLISH clean, then **died on the first FILL passage**:

- The vision's `pov_hint` (author-authored, then refined at DREAM) asks for
  *"third-person limited rotating among the key suspects, with occasional
  first-person journal entries from the lead investigator"* — a rotating scheme.
- FILL's voice pass produced a matching rotating `Voice.pov`.
- But FILL fixes **one** `Voice.pov` for the whole book and enforces
  *"no other minds"* against it (`fill_write.j2` rule 1), with **no per-passage
  viewpoint assignment**. So on a passage whose three beats are all
  Eleanor-centric (she uncovers blackmail letters; she enters the hall *noting
  the uneasy atmosphere*), the writer picked a **suspect's** head (Charles) and
  could not render Eleanor's interior — the reviewer correctly rejected the beat,
  twice, and the stage halted at pass 1 of the prose.

This is not a model-weakness failure and not a review bug: the pipeline **accepts
a rotating POV in the vision and voice but cannot honor one at write time.** A
closed-circle-of-suspects mystery is exactly the shape rotating POV serves; the
gap is real and blocks the genre.

## What "supported" means (design sketch — NOT decided)

Rotating limited POV needs a **viewpoint character assigned per unit**, with the
*no-other-minds* rule scoped to that unit rather than to the whole book. The
pieces likely involved (all open):

- **Model**: how the viewpoint is represented. A per-passage `viewpoint` (an
  entity id) is the smallest thing that works; the beats already name their
  entities, so it may be largely *derivable* rather than a new authored field.
- **Where it's decided**: derive at POLISH from each passage's beats' entities?
  An explicit annotation (like `scene_type` / `narration_scope`, written by
  GROW's *annotate* pass)? Author-authored? Each has different coherence and
  cost trade-offs.
- **FILL**: `Voice.pov` describes the *scheme* (rotating limited, rotate at
  passage boundaries, one head per passage); the write context names **this
  passage's** viewpoint character; rule 1 (*no other minds*) is enforced against
  that per-passage head, not a single book-wide name. `narration_scope`
  (limited/wide) still composes on top per beat.
- **Constraints worth weighing**: the corpus warns against *mid-scene*
  head-hopping — that warning is about switching heads *within* a unit, which
  rotating-at-boundaries does not do; the two must not be conflated (the earlier
  rejection conflated them). Rotation cadence (every passage? only at section
  boundaries?) and the first-person-journal interludes the vision mentions are
  open.

## Open questions for the author (decisions are yours, not mine)

Deliberately unanswered here — recording the questions instead of inventing
answers and signing your name to them:

1. **Granularity**: viewpoint per passage, per POLISH-scene, or per author-chosen
   section/chapter?
2. **Who chooses the viewpoint**: derived from beat entities by the engine,
   annotated by an LLM pass, or authored?
3. **Cadence constraints**: may it rotate every passage, or only at marked
   boundaries? Any "stay with one head for a run of N" rule?
4. **First-person interludes**: the *Closed Circle* vision wants occasional
   first-person journal entries from the investigator amid third-person limited.
   In scope for v1, or a later layer?
5. **Scope of this change**: its own milestone/PR (recommended — it is narrative
   semantics, the hard core), and does the golden story gain a rotating-POV
   fixture to exercise it?

## Suggested next step

Treat this as **frontier narrative-semantics work**: an author-signed-off design
(answering the questions above) *before* any code, its own branch/PR, and the
golden story extended to exercise it. This file is only the record that the
feature is wanted; it is not a design and locks nothing.
