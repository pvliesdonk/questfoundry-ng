# Rotating limited POV — Build Contract

> Status: **DESIGNED, building** (2026-07-14). The design decisions below are
> **author-confirmed 2026-07-14** — answered directly by the author in the
> session that wrote this file, via explicit per-question prompts (not an
> agent's scope call recorded under the author's name; cf. the provenance
> failure documented in [`rotating-pov.md`](rotating-pov.md)). That file is the
> record of intent and the live trigger; this file is the design and build
> plan. Frontier-authored (POV / freeze / collapse semantics). Sibling of
> [`pov-narration-scope.md`](pov-narration-scope.md) — same annotation
> machinery, same GROW-pre-freeze placement; this builds the per-unit
> viewpoint that work deliberately did not.

## The problem (one paragraph)

The pipeline accepts a rotating POV in the vision and voice but cannot honor
one at write time. `Voice.pov` is a single book-wide string; FILL's rule 1
(*no other minds*) is enforced against it with no per-passage viewpoint
assignment. The *Closed Circle* medium run (2026-07-14, `gpt-oss:120b-cloud`)
died on its first FILL passage exactly here: a rotating scheme in the vision
and voice, an Eleanor-centric passage, a writer that picked Charles's head,
and a reviewer that correctly rejected Eleanor's interiority twice. Full
account in [`rotating-pov.md`](rotating-pov.md).

## Decisions locked (author-confirmed 2026-07-14)

1. **Granularity: per passage.** Each passage has at most one viewpoint
   character ("head"); the head never switches *inside* a passage — a
   head-switch always coincides with a page-turn, the corpus's "clear
   structural marker". `narration_scope` composes on top unchanged: a
   passage's `wide` coda beats still step outside the head (the author
   explicitly kept this mixing).
2. **Assignment: GROW's annotate pass, per beat.** The existing pass (which
   already tags `scene_type` + `narration_scope`, sees `vision.pov_hint` and
   every beat) also names each beat's viewpoint character. Settled at the
   freeze like the other annotations. POLISH collapse then guarantees
   one head per passage (below). Not an engine heuristic (beat entity lists
   do not rank the perceiving center — guessing is the very bug), not a
   POLISH-time pass (too late to influence grouping), not author-authored
   (does not scale past fixtures).
3. **Cadence: no engine constraint in v1.** The annotate prompt carries the
   guidance (prefer runs — stay with a head while the drama stays with them);
   no validator. Tighten only if live runs show whiplash.
4. **First-person interludes: in scope for v1.** The *Closed Circle* vision
   wants occasional first-person journal entries amid third-limited; the
   annotation carries an `interlude` mark and the Voice gains an `interlude`
   register description. A passage is either base-register narration or an
   interlude, never mixed.
5. **Golden coverage: annotate `keepers-bargain` + the recorded e2e fixture.**
   The golden story's beats gain its one constant viewpoint (single POV is the
   trivial rotation — exercises the fields, fallbacks, and gates without
   distorting an intimate story); actual rotation is exercised by unit tests
   and the mock-replay e2e fixture. No second hand-authored golden.

## The model (`models/structure.py`, `models/concept.py`)

- `Beat.viewpoint: str | None = None` — the id of the **character entity**
  whose head narrates this beat. `None` = not annotated (bridge, residue,
  false-branch, pre-migration projects); never guessed beat-locally.
- `Beat.interlude: bool = False` — this beat belongs to the scheme's marked
  deviant register (the Voice's `interlude`, e.g. a first-person journal
  entry). Meaningful only when `viewpoint` is set; an unannotated beat is a
  wildcard for both fields.
- A `wide` beat carries **no viewpoint by construction** (the coda register
  has no head; the annotate apply normalizes any supplied one to `None`).
  This is also what lets a coda merge freely into any passage — the author's
  "mixing limited with wide must be possible".
- `passage_viewpoint(beats) -> PassageViewpoint` (a small NamedTuple:
  `viewpoint: str | None`, `interlude: bool`) — the single derivation
  authority, mirroring `effective_scene_type`/`effective_narration_scope`:
  the unique viewpoint among member beats that carry one (uniqueness is
  I14's job, the helper asserts it), `interlude` likewise; a passage whose
  beats carry none derives `(None, False)`. **Computed at consumption, never
  stored on `Passage`** (iron rule 2's spirit: derivable state is not
  duplicated; `Passage.entities` stays what it is).
- `Voice.interlude: str = ""` — the scheme's marked deviant register in one
  description (form, person, tense, whose voice: "first-person past-tense
  journal entries in Eleanor's voice"); empty when the scheme has none.
  Defaults empty so author-provided `voice.yaml` files load unchanged.
- `Voice.pov` stays the **scheme** description ("third limited, rotating among
  the suspects at passage boundaries"); the per-passage head is what rule 1 is
  enforced against.

## The mutation (`graph/mutations.py`)

`set_beat_viewpoint(g, beat_id, viewpoint, *, interlude=False)` — one mutation
for the annotation pair (they travel together). Mirrors `set_beat_scene_type`:
reject a non-beat; reject a frozen beat (settled at the freeze); reject
`interlude=True` without a viewpoint. Referential existence is the gate's job
(G3, below), not the mutation's — same division as the other annotations.

## GROW `annotate` pass (`stages/grow.py`, `grow_annotate.j2`)

Extend the existing pass — no new pass, no new LLM call.

- **Schema:** `BeatScene` gains `viewpoint: str` and `interlude: bool`.
  `annotate_proposal_schema` pins `viewpoint` to the retained **character**
  entity ids plus `""` (= no head, for `wide` beats) — grammar-safe like the
  beat-id pin, so an invalid id is unrepresentable.
- **Context:** each beat row gains its `entities` (the model needs who is on
  the page to pick the perceiving center); the character roster with names is
  rendered once. `vision.pov_hint` is already rendered.
- **Prompt:** a VIEWPOINT block beside the scope block, per AGENTS.md prompt
  quality (state the rule, anchor the cases):
  - Every `limited` beat names the one character whose head narrates it —
    the character whose perception, stakes, and interiority the summary
    lives in (who *uncovers*, who *notices*, who *decides*), not merely
    whoever is present.
  - A single-viewpoint story names the same character on every beat; that is
    correct, not a failure to rotate. A rotating scheme (per the POV hint)
    rotates where the drama's center moves.
  - Prefer runs: consecutive beats that stay with the same drama stay in the
    same head; rotate at a real shift of dramatic center, not per beat
    (cadence guidance, decision 3 — prompt-only).
  - A `wide` beat has no head: set viewpoint `""`.
  - `interlude` marks a beat belonging to the scheme's stated deviant
    register (only when the POV hint calls for one — journal entries,
    letters); it requires a viewpoint and is never `wide`.
- **Apply:** validates per beat (all repairable `ApplyError`s with
  recovery actions): a `limited` beat must name a viewpoint (recovery: the
  valid character ids); a `wide` beat's viewpoint is normalized to `None`;
  `interlude` requires a viewpoint and `limited` scope. Writes via
  `set_beat_viewpoint` in the same loop as the other two mutations. The run
  log gains the head distribution ("heads: eleanor 12, charles 8; 3
  interludes") beside the scene/scope counts.

## POLISH collapse (`pipeline/passages.py`) + invariant I14

- `collapse_groups` gains `split_viewpoints: bool = False`. When set, the
  `merges` predicate additionally requires viewpoint compatibility: two beats
  merge unless **both carry a viewpoint and disagree** on `(viewpoint,
  interlude)`. `None` is a wildcard (bridge/residue/false-branch/`wide` beats
  merge anywhere) — this is what lets a coda ride in a limited passage and
  POLISH-added texture ride anywhere, and what cuts a passage exactly at a
  head-switch.
- **Only the passage-building call sites** pass `split_viewpoints=True`
  (`passages.py` passage collapse, `polish.py` group building). The raw-runs
  mode (cadence planning, `long_linear_runs`) stays uncut: a head-switch
  chunks *prose*, it does not change the choice-less stretch that cadence
  diamonds meter (B6) — same reasoning as the `max_beats` cap being absent
  there.
- **Invariant I14 (gate G4):** among a passage's member beats that carry a
  viewpoint, all agree on `(viewpoint, interlude)` — one head per passage,
  the author's hard rule, structural and numbered per iron rule 6 (01 §8
  entry + `validate.py` check + violating-construction test).
- **Gate G3** gains a referential check (unnumbered, like the arc-reference
  check): a beat's `viewpoint`, when set, resolves to a retained character
  entity.

## FILL consumption (`stages/fill.py`, prompts)

The write/review context computes `passage_viewpoint(beats)` and resolves the
entity; both prompts key the POV rules to it.

1. **Write context** gains `viewpoint` (the resolved entity or `None`) and
   `interlude`. Window/lookahead entries gain their own passage's head so the
   writer sees a switch ("from p-x, told from Charles's viewpoint") and does
   not bleed the previous head's interiority forward.
2. **`fill_write.j2`:** the VOICE block keeps `voice.pov` as the scheme; a
   passage with a head gets one added line of binding context — *THIS
   passage's viewpoint character is {{ name }}* — and rule 1 (*no other
   minds*) is phrased against that head. Rule 2 (distance may widen) and the
   per-beat `wide` coda license are unchanged. An `interlude` passage renders
   the Voice's `interlude` register as the passage's binding form — its
   person/tense/form override the book defaults (the TENSE block and POV
   rules key to it for that passage).
3. **`fill_review.j2`:** the `voice_pov` rule names the passage's head as the
   required viewpoint (a departure = wrong person for the head, or another
   mind entered); an interlude passage's `voice_pov`/`voice_tense` judge
   against `voice.interlude` instead of the book defaults. The `wide`-coda
   carve-out is unchanged.
4. **Voice pass:** `VoiceProposal` gains required `interlude: str` (`""` when
   the scheme has none); `fill_voice.j2`'s `pov` bullet now covers schemes —
   a single fixed head *or* a rotating scheme ("third person limited,
   rotating at passage boundaries among NAMES from the cast") — and a new
   `interlude` bullet (describe the deviant register only if the vision's
   scheme calls for one; name its narrator from the cast, its person, its
   tense, its form).

**Graceful degradation:** a passage whose beats carry no viewpoint (pure
texture/bridge passages; whole projects from before this change) renders
exactly today's prompts — rule 1 against `voice.pov` book-wide. No migration,
old projects and the current golden behavior are the degenerate case.

## Golden story + fixtures + tests

- **`examples/keepers-bargain`:** annotate every beat's `viewpoint` with the
  story's one head in the per-beat YAML (constant single POV — the trivial
  rotation); `voice.yaml` untouched (`interlude` defaults `""`). Gates stay
  clean; I14 is exercised in its all-one-head form.
- **Recorded fixtures:** MockProvider replays by call order, so prompt
  wording changes need no re-record — but the **annotate** recorded proposal
  must gain the new fields (apply rejects missing coverage) and the **voice**
  recorded proposal must gain `interlude` (required field). Refresh the
  affected snapshots; the FILL prose fixtures hold.
- **Tests** (mirroring the narration-scope suite):
  - model: `passage_viewpoint` derivation table (unique head; wildcards;
    empty → `(None, False)`), mutation write-then-frozen-reject,
    interlude-without-viewpoint reject;
  - annotate apply: limited-without-viewpoint repairable, wide normalizes to
    `None`, interlude requires limited+viewpoint, coverage errors unchanged;
  - collapse: cut at a head-switch, wildcard beats merge, interlude never
    merges with base-register, raw-runs mode uncut;
  - I14 violating construction (two heads grouped into one passage → G4
    error) per iron rule 6;
  - G3 referential: dangling viewpoint id → error;
  - FILL context: head + window-head rendering, interlude register selection,
    degenerate no-head passage renders today's context.

## Docs

- **01**: §5 beat annotations — `viewpoint`/`interlude` beside
  `scene_type`/`narration_scope`; §8 — **I14**; §10.3 — the viewpoint
  annotation family entry is superseded *for the viewpoint field* by this
  build (cite `rotating-pov.md` for why the YAGNI blanket was wrong — an
  agent scope-cut, not an author decision).
- **02**: GROW annotate out-contract (four signals); POLISH collapse contract
  (viewpoint cut, I14 at G4); FILL contract (per-passage head, interludes).
- **03 §9**: one mini-ADR row (rotating POV via per-beat viewpoint annotation
  + collapse cut + per-passage FILL enforcement; alternatives rejected:
  engine heuristic, POLISH-time assignment, per-beat head-switching).
- **STATUS.md / 05-roadmap**: this effort is the "Now" epic's third item;
  record as in-flight, then shipped.
- **[`rotating-pov.md`](rotating-pov.md)**: status header flips to
  "designed/building — see rotating-pov-build.md"; the intent record itself
  stays as written.

## Risks / follow-ups (flag, do not preempt)

- **Over-rotation.** A model handed a per-beat head could rotate per beat and
  shred passages into single-beat runs. Mitigation is prompt-only in v1
  (prefer runs; rotate at shifts of dramatic center) per the author's cadence
  decision; if a live run shows whiplash, tighten the prompt first (AGENTS.md:
  the prompt is the first suspect), and only then consider a validator.
- **Interlude sprawl.** `interlude` is licensed by the scheme (the POV hint);
  a story without one should never mark it. The annotate prompt gates it on
  the hint; the voice pass emits `""` when unused.
- **Window inflation.** Rendering neighbor heads adds a few tokens per window
  entry — negligible; no context budget change.
- **Live validation** (unbilled, per budget discipline): re-run the *Closed
  Circle* medium on `gpt-oss:120b-cloud` from its POLISH checkpoint — the
  acceptance test is the run clearing the passage it died on, with the
  rotation reading deliberately (one head per passage, journal interludes
  where the scheme asks). This PR ships offline-green; the live re-run is the
  follow-up, same as narration-scope's.

## Build order (checkpoints)

1. Model: `Beat.viewpoint`/`Beat.interlude`, `PassageViewpoint` +
   `passage_viewpoint`, `Voice.interlude`, `set_beat_viewpoint`. + tests.
2. Gates: I14 (G4) + the G3 referential check. + violating-construction tests.
3. GROW annotate: schema pin, context, prompt block, apply validation +
   head-distribution log line. + tests.
4. POLISH collapse: `split_viewpoints` + call-site flags. + tests.
5. FILL: context (head, window heads, interlude), `fill_write.j2` /
   `fill_review.j2` keying, `VoiceProposal.interlude` + `fill_voice.j2`.
   + tests.
6. Golden annotation; fixture re-record; full `pytest`/`ruff`/golden
   `validate` green.
7. Docs (01, 02, 03 §9, STATUS, roadmap, rotating-pov.md header).
8. (Follow-up, not this PR) Live *Closed Circle* re-run from the POLISH
   checkpoint.
