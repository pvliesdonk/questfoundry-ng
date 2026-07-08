# 00 — Vision

## The problem

Interactive fiction with real agency is brutally expensive to author.
Every meaningful choice multiplies the story: ten binary choices is up to
1,024 distinct journeys. Human authors solve this with years of craft —
branch-and-bottleneck structures, state tracking, careful reconvergence.
Most give up and ship either a linear story with cosmetic choices or a
sprawling mess with dead ends.

LLMs look like the answer — they write fluent prose cheaply — but they
fail at exactly the part that matters: *structure*. Left to generate a
branching story free-form, a model forgets flags, contradicts earlier
scenes, writes unreachable passages, and lets choices evaporate. Long-form
coherence and combinatorial bookkeeping are the two things LLMs are worst
at.

## The product

QuestFoundry NG is a **story compiler**. The author supplies a premise and
taste decisions; the system supplies structure, discipline, and volume.

- **Input:** a premise ("a lighthouse keeper strikes a bargain with
  something in the sea"), a scope (micro → long), and genre/tone
  preferences.
- **Output:** a complete gamebook — 20 to 150+ prose passages wired with
  choices, where every playthrough is a complete, coherent story and every
  choice leaves residue the reader can feel — exported as Twee, standalone
  HTML, machine-readable JSON, and a print-ready numbered-sections PDF.
- **In between:** an eight-stage pipeline where LLMs do the creative work
  inside structural rails, a deterministic engine enforces the rails, and
  the author reviews and steers at every stage boundary.

The finished gamebook is a *static artifact*. Nothing is generated at play
time; a reader needs no AI, no account, no connection. This is what makes
print export possible and what makes quality auditable — the whole story
exists and can be validated before anyone plays it.

## Who it is for

1. **Writers who want agency-rich stories without wiring hell.** They care
   about DREAM/BRAINSTORM-level decisions and prose review; the pipeline
   does the graph bookkeeping.
2. **Hobbyists and game jammers** who want a complete playable gamebook
   from a premise in an afternoon, steering lightly.
3. **Tinkerers and researchers** who want a testbed for structured LLM
   generation — every stage has typed inputs/outputs and a validation
   suite, so it doubles as a harness.

The same pipeline serves all three; they differ only in how many review
checkpoints they engage with.

## Goals

- **G1 — Complete stories, always.** Every reachable playthrough has a
  beginning, middle, and end. No dead ends, no orphan content, no
  contradictions. Enforced by validation, not hoped for.
- **G2 — Choices that matter.** Every real choice produces structural or
  textual consequence (residue). The reader of any single playthrough
  should feel they read *the* story, and sense the roads not taken.
- **G3 — Bounded cost.** Token spend and story size are predictable from
  scope up front. Branching cost is controlled structurally (see
  [01 — Story Model](01-story-model.md)), not by truncating stories.
- **G4 — Author sovereignty.** Every stage output is a human-readable,
  diffable file the author may edit; the engine re-validates edits exactly
  like LLM output. The pipeline never overwrites an author decision.
- **G5 — Resumability and reproducibility.** A run can stop at any point
  and resume; a project directory under git is the complete state. Cached
  LLM calls make re-runs cheap.
- **G6 — Format-complete export.** Twee 3, standalone HTML, canonical
  JSON, and print PDF with a player-facing codeword system.

## Non-goals (v1)

- **No play-time generation.** No AI dungeon-master mode, no dynamic
  prose. Out of scope permanently for this product shape.
- **No n-way dilemmas.** Dilemmas are strictly binary — two dilemmas beat
  one three-way choice (sharper contrast, four arcs instead of three).
  False branches provide multi-option *feel* where wanted.
- **No distributed commits.** A dilemma commits at a single dramatic
  moment. Accumulated "Witcher-style" commits are a documented future
  extension, not v1.
- **No stats/inventory/combat mechanics.** State is boolean flags only.
  Numeric RPG systems are a different product.
- **No collaborative real-time editing, no hosted service.** v1 is a
  local-first CLI (with a local review UI later); the project directory is
  the collaboration surface (via git).
- **No fine-tuning.** The pipeline works with off-the-shelf frontier
  models through a provider-agnostic adapter.

## Guiding principles

These decide arguments. Every design decision downstream should be
traceable to one of them.

1. **Story first, graph second.** Every node, edge, and field in the data
   model exists because a narrative concept requires it. If a structure
   can't be traced to a storytelling purpose, it goes.
2. **LLMs propose, the engine disposes.** Models emit typed proposals;
   only the mutation layer writes to the story graph, and it enforces
   every invariant. A model cannot corrupt the structure, only fail to
   improve it.
3. **Branch on dilemmas, tame by convergence.** The combinatorial
   explosion is controlled by story shape — backbone dilemmas commit late,
   subplots reconverge, serial subplots never interact — not by arbitrary
   caps.
4. **Fail at the cheapest stage.** Validation gates between stages catch
   problems where fixing them is cheap. A structural flaw found during
   prose writing costs 100× what it costs at seeding. Prose is never used
   to patch structure.
5. **Everything is a file.** The project is a directory of human-readable
   files. Diffable, editable, versionable. No opaque databases, no state
   that can't be inspected with `cat`.
6. **The author outranks the pipeline.** Checkpoints are real: the
   pipeline halts, the author reviews or edits, validation re-runs. In
   unattended mode the checkpoints auto-approve, but the artifacts and
   audit trail are identical.

## Relationship to the original QuestFoundry

NG inherits the original's central insight — the layered model of
*dilemmas → paths → beats → passages* with a frozen-topology pipeline —
because it is genuinely good: it names the combinatorial problem precisely
and beats it with story craft rather than tricks.

NG diverges freely in data model details, stage boundaries, and all
implementation choices. Divergences are called out in each design doc
(look for **"Departures"** sections). The two inherited documents are
inspiration and prior art, not requirements.
