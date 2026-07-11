# Prompt inventory

Every LLM pass in the pipeline, its template, what it must produce, and where its
schema/apply live. Read the stage module in `src/questfoundry/pipeline/stages/`
for the authoritative schema + apply; this map tells you where to look and what
each pass owes.

Shared includes: `_shared.j2` (author steering + repair briefs — always last),
`_craft.j2` (advisory research digest — substantive passes only), `_summary_brief.j2`
(the "summaries are a brief, not your style" note — beat-consuming passes).

## DREAM — `dream.py`
- **envision** (`dream.j2`): the creative contract (`Vision`: genre, subgenre,
  tone, themes, audience, content notes, pov hint). Free text, no id references.
  Framing rule already applied: a vision is texture and intent, never countable
  coverage.

## BRAINSTORM — `brainstorm.py`
- **populate** (`brainstorm.j2`): the CAST (entities, with `pronouns`) and the
  DILEMMAS (each with answers, role, residue weight). Ids are **coined** here —
  do not pin them. `anchored_to` references entities coined in the same proposal,
  so it is deliberately **unpinnable**.

## SEED — `seed.py`  (schemas built per-project; triage runs before scaffold/order)
- **triage** (`seed_triage.j2`): dispositions — cut entities, branch vs lock each
  dilemma, one path per explored answer with consequences (WORLD STATE, not player
  action). Pins: `paths[].explores`→answer ids, `locked[].dilemma`→dilemma ids,
  `cut_entities[].id`→retained entity ids. Enum reference is stated in the prose
  ("the schema enumerates the only legal values").
- **scaffold** (`seed_scaffold.j2`): beats per path (pre-commit / commit /
  post-commit; locked chains; setup). Callable schema — pins dispositions, explored
  paths, `BeatSpec.entities`, `HintSpec.dilemma` against **triage's** writes.
- **order** (`seed_order.j2`): dilemma timeline relations (wraps/serial/concurrent).
  Pins `relations[].a/.b`→dilemma ids.

## GROW — `grow.py`  (schemas depend on weave's rewrites → mostly callable)
- **intersections** (`grow_intersections.j2`): co-occurrence groups over shared
  pre-commit / locked-chain beats. Pins `members`→shared beats, `location`→entity
  ids + "" (the no-anchor default).
- **weave** (`grow_weave.j2`): **choose among** engine-enumerated interleavings
  (an integer index). The model does not invent order — say so.
- **contextualize** (`grow_contextualize.j2`): rewrite per-world clone / de-ended
  tail beat summaries (multi-hard only; skipped otherwise). Pins `rewrites[].beat`.
- **bridge** (`grow_bridge.j2`): structural bridge beats across entity-disjoint
  adjacencies (skipped when no gaps). Pins `bridges[].entities`.

## POLISH — `polish.py`  (callable schemas; audit needs the passages pass's output)
- **finalize** (`polish_finalize.j2`): required light-residue arms (one per path
  per convergence) + optional cadence false branches in long choice-free runs.
  Pins residue `dilemma`/`world`/`path`/`entities`, false-branch `before`/`after`
  (to the **pristine** long runs — see case study), and forbids `false_branches`
  when no long run exists. NOTE: `_finalize_apply` splices false branches before
  residue so both validate against the frozen topology.
- **passages** (`polish_passages.j2`): the model contributes only *words* —
  summaries, choice labels, ending titles, variant summaries. The engine fixes
  groups and choice wiring. Pins `variants[].flag`.
- **audit** (`polish_audit.j2`): prose-feasibility — mark irrelevant flags per
  passage; the engine caps the rest (I12). Pins `passage` (ids + slugs) and
  `irrelevant` (that passage's active flags). No `_craft.j2` (mechanical pick).

## FILL — `fill.py`  (per-passage work queue)
- **voice** (`fill_voice.j2`): the singleton `Voice` (pov, tense, diction, rhythm,
  banned, notes). Locked before any prose; skipped when author-provided.
- **write** (`fill_write.j2`): the prose for ONE passage, in the binding voice,
  realizing the beats in order, honest about `possible` flags, within the word
  band. Optional `micro_details` (universal entity facts, brief register). Pins
  `micro_details[].entity`. The most heavily tuned prompt — see case studies.
- **review** (`fill_review.j2`): the legibility contract (numbered FAIL rules,
  quote-the-text, taste-passes, arbitration). No `_craft.j2` (renders itself).

## DRESS — `dress.py`  (eager per-project schemas — no pass changes another's set)
- **direction** (`dress_direction.j2`): art direction + one visual profile per
  retained entity. Pins `profiles[].entity` (exact ids).
- **briefs** (`dress_briefs.j2`): prioritized illustration briefs. Pins
  `briefs[].passage` and `briefs[].entities` (scoped to the passage's entities).
- **codex** (`dress_codex.j2`): one diegetic codex entry per dilemma-anchoring
  entity; spoiler safety enforced by a paired review (`dress_codex_review.j2`).
  Pins `entries[].entity`.
- **codewords** (`dress_codewords.j2`): one memorable print codeword per
  gate-tested flag (utility role). Pins `codewords[].flag`.

## RESEARCH — `research.py` (heads every substantive stage when a craft corpus is configured)
- **research** (`research.j2`): the librarian proposes ≤ `max_queries` search
  strings for what the standing queries don't already cover. Free-text queries; no
  id references. The retrieved digest becomes the `_craft.j2` advisory block.
