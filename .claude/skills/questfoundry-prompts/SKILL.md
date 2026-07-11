---
name: questfoundry-prompts
description: >-
  Write, tune, and debug the LLM prompts and their JSON-schema contracts for the
  QuestFoundry NG story pipeline (DREAM→SHIP) so they express their intent
  explicitly and robustly for ANY model — not only whichever tier happens to be
  smart enough to infer what you meant. Use this skill whenever you touch
  `src/questfoundry/pipeline/prompts/*.j2`, add or change a proposal schema or the
  reference-pinning in `pipeline/refpin.py`, edit a stage's review rules, add a
  pass, or diagnose why a model fails, loops, or exhausts repairs at a stage. A
  failure on a weaker/local tier (gpt-oss, qwen, an Ollama model) is an especially
  sharp diagnostic — it exposes where a prompt is under-specified — but the goal is
  prompt quality for every tier. Reach for it for "the writer keeps breaking
  tense", "SEED triage invents ids", "the review is too strict", "make this prompt
  robust", or "add a new pass" — anything about how this pipeline talks to its
  models.
---

# Tuning QuestFoundry NG pipeline prompts

QuestFoundry compiles a premise into a gamebook through eight LLM-driven stages
inside a deterministic engine. Every LLM call is **one structured-output pass**:
the model returns a typed *proposal*, the engine validates it against a Pydantic
schema and then *applies* it to the graph. Models never mutate anything — they
propose, the engine disposes. So a prompt here is never a chat; it is a
**contract with two enforceable surfaces**, and tuning means deciding which
surface owns each rule.

Read `docs/design/02-pipeline.md` for stage contracts and `AGENTS.md` for the
iron rules before changing behavior. This skill is *how to write the words*; the
design docs are *what the words must achieve*.

## The goal: a prompt that doesn't depend on the model being clever

Tune prompts to **express their intent explicitly** — clear task, stated register,
enforced references — so they produce the right thing on *any* model, not only
whichever tier is smart enough to guess what you meant. A prompt that "works" only
because a frontier model infers the unstated intent is under-specified: it is
fragile (a provider swap or an off day breaks it), inconsistent (the strong model
fills the gap differently across runs), and hard to debug. Making the intent
explicit is simply good prompt engineering — it *also* happens to let a weaker
model follow, but that is a consequence, not the target.

This reframes what a weak-tier failure **is**. It is not "the cheap model is bad,"
and the fix is not "make it pass on gpt-oss." A weaker model is a **microscope for
under-specification** — it can't paper over a gap the way a frontier model does, so
it shows you exactly where the prompt left intent to inference. Fix that gap and the
prompt is better for *every* tier — the strong model's output usually gets more
consistent too. Use the weak tier to *find* the problem; judge success by whether
the prompt now says what it means, not by whether one model happened to pass.

One caveat, so this doesn't tip into over-engineering: **expressing intent is not
spoon-feeding.** Clarity, specificity, stated register, and enforced schemas help
every model. Worked exemplars, step-by-step scaffolding, and verbose hand-holding
help a weak model but tax a strong one — those belong on the *failure* path (A20),
never in the base prompt. The line: make the **intent** explicit for all; keep
**crutches** conditional on failure.

## The two surfaces — put each rule where it can be enforced

Every constraint you want the model to honor belongs to exactly one of these.
Choosing wrong is the single most common tuning mistake.

- **The schema (hard rails).** A Pydantic model in `pipeline/stages/<stage>.py`,
  offered to the provider as JSON Schema. Under grammar-constrained decoding
  (the Ollama `format` path, mini-ADR A20) a value outside the schema is
  **unrepresentable** — the model literally cannot emit it. Put here anything
  finite and checkable: enums for closed sets, `Literal` pins for id references
  (see below), list length bounds, required fields.
- **The prompt (soft guidance).** The `.j2` template. It owns everything the
  schema can't express: intent, register, craft, what an event *is*, how to
  render a mood. The prompt persuades; it does not enforce.

**Rule of thumb: if a failure is a wrong *value* from a knowable set, fix the
schema. If it is wrong *judgment*, fix the prompt.** A model inventing a dangling
id is a schema problem. A model writing flat prose is a prompt problem.

### Reference pinning is the sharpest tool you have

Any proposal field that must name an **already-existing** id (an entity,
dilemma, answer, beat, path, flag, passage…) should be pinned to a `Literal`
enum of the real ids via `pipeline/refpin.py` — `pin(model, name, resolvers)`.
This makes a dangling reference unrepresentable, and the correction brief names
the valid ids on a miss. Two live model families independently invented
dangling slugs at SEED triage until this landed (issue #40, then generalized).

- Pin to **exactly the set the apply accepts** — no looser. A field validated by
  `resolve_entity_ref` accepts bare slugs too, so pin to `entity_ref_ids` (ids +
  unambiguous slugs); a field checked by exact membership pins to
  `retained_entity_ids` (exact ids only). An enum that admits a value the apply
  rejects just trades one dangling failure for another.
- **Never** pin a field the model *coins* (a new beat/path/consequence id) — only
  references to things that already exist.
- A schema whose enums depend on an earlier same-stage pass's writes must be a
  **callable** `PassSpec.schema` (resolved at pass-run time via `schema_for`),
  because the runner builds the pass list once, before those writes exist.

See `references/case-studies.md` for the worked examples.

## Nine rules for the words themselves

Synthesized from the dair-ai Prompt Engineering Guide, this project's own
`docs/heritage/semantic-conventions.md`, and live runs. The guide decomposes any
prompt into four elements — **Instruction, Context, Input Data, Output Indicator**
— and a qf prompt uses all four (directive open = Instruction; `UPPERCASE` blocks
= Context; the rendered graph state = Input Data; **the Pydantic schema =
Output Indicator, made enforceable**). `references/prompt-engineering-guide.md`
distills the guide and maps each of its techniques to how this pipeline uses,
adapts, or deliberately avoids it — read it before a substantial prompt redesign;
it is the *why* behind these rules.

1. **Open with a directive.** Every stage prompt starts with an imperative naming
   the job: "Write the prose for ONE passage", "Triage the brainstormed
   material", "Choose the story's scene order". Not "You might consider…".
2. **Be specific and measurable.** Replace "keep it short" with a band
   (`{{ words_min }}-{{ words_max }} words`); replace "a few" with a count from
   the scope preset (`exactly {{ scope.hard_dilemmas }} hard`). Vague asks get
   vague proposals.
3. **Say what to do, not what not to do.** Positive directives land; prohibitions
   get half-followed. "Narrate every verb in {{ voice.tense }}" beats "don't use
   past tense" — though naming the *consequence* of a ban ("this is checked and
   fails review") is worth adding once, so the model weighs it while drafting.
4. **Delimit context with UPPERCASE block headers.** `VISION:`, `CAST:`,
   `WORLD STATE AT THIS PASSAGE:`, `VOICE (binding):`. The visual boundary tells
   the model what is instruction vs. what is material to work from.
5. **State the register of every field.** "Everything that is not prose should
   not be prose." A summary, a micro-detail, a codex entry, a consequence — each
   carries its own register, and the prompt must say so, or the model voices them
   like story and the style leaks. Consequences are WORLD STATE ("the mentor is
   hostile"), never player action ("the player distrusts him").
6. **Keep the model in its lane.** State plainly what the engine owns and the
   model does not touch: "the topology is frozen — nothing moves, nothing is
   deleted", "you only *choose among* the interleavings the engine offers". A
   model that thinks it can restructure will try to.
7. **Diegetic, never mechanical.** Gate/flag language faces the reader as story:
   "the door is locked", not "requires flag:has-key". Ids and the words
   flag/beat/dilemma/path/arc must never reach player-facing prose — the review's
   leakage rule enforces this, so the write prompt must pre-empt it.
8. **Ground, then constrain.** Lead each pass with the `VISION` line (genre,
   tone, themes) so proposals cohere, then give the numbered, budgeted tasks.
   Context first, task second.
9. **Help conditionally, on failure only (A20).** Be honest about the starting
   point: the base prompts today are *blunt and largely uninvested* — they state
   the intent directly and work because a strong model is smart enough to infer
   the rest, **not** because they were tuned for strong models. That is exactly
   why a weak tier exposes them — a gate failure on a cheap model usually
   diagnoses the prompt, not the model (STATUS: "NG's blunt prompts haven't made
   that investment"). When you *do* invest, put the help on the *failure* path,
   not the base: `_shared.j2` renders `repair_errors` as a correction brief on the
   next attempt — the guide's **Reflexion** loop (Actor → Evaluator → verbal
   self-reflection). Micromanagement baked into the base prompt taxes strong
   models for a weak model's benefit, so keep it out of there. Two avoidances
   *are* deliberate design, not mere thrift: no few-shot exemplars (an exemplar
   answer is a bias vector under the strictly-equal-answers iron rule) and no
   chain-of-thought / discuss-then-serialize (single-pass structured output —
   A20). See `references/prompt-engineering-guide.md`.

## Anatomy of a stage prompt

Match the house style (see any file in `src/questfoundry/pipeline/prompts/`):

```
<one imperative sentence naming the job and what the engine already did>

VISION: {{ vision.genre }}, {{ vision.tone }}. Themes: {{ vision.themes | join("; ") }}.

<UPPERCASE CONTEXT BLOCK>:
{% for … %}- {{ … }}{% endfor %}

YOUR TASKS:
1. <task with explicit constraint, count, id-format, and enum reference>
2. …
{% include "_craft.j2" %}      {# advisory craft-corpus digest, when configured #}
{% include "_shared.j2" %}     {# author steering + repair briefs — always last #}
```

Shared includes (don't duplicate their content into a stage prompt):
- `_shared.j2` — author steering (`notes`) + `repair_errors`. Every prompt ends with it.
- `_craft.j2` — the advisory research digest; substantive passes include it, review/mechanical passes deliberately don't.
- `_summary_brief.j2` — the "summaries are a brief, not your style" reminder for passes that consume beat summaries.

`references/prompt-map.md` is the full inventory: every template, what it must
produce, its schema, and its includes. Read it before adding or relocating a
prompt.

## Review prompts have their own contract

Passes with an LLM `review` (FILL write, DRESS codex) judge prose against rules.
A review prompt is legible or it is a taste-launderer. Follow `fill_review.j2`:

- **Numbered, objective FAIL rules** — "things a second reviewer would flag the
  same way." Each rule names what it checks; the model must **quote the offending
  text** and cite the rule number.
- **Fail on defects, pass on taste.** State outright that register, rhythm,
  metaphor quality, "too literary/too spare" are NOT failures — a writer can't
  converge on taste in two rounds. Weak reviewers relabel taste as a rule
  ("a weak metaphor is not state dishonesty"); say so explicitly.
- **Exclude hedged findings.** "If your sentence needs 'risks', 'could be', or
  'attempts to', it is not an objective defect — do not list it."
- **Arbitration for persistence.** After two first-line failures a senior arbiter
  upholds only what *persists* and outright violates a numbered rule — this is
  what stops a weak reviewer from failing forever on fresh nitpicks.

When a review over-fails, first decide **writer-vs-reviewer fault** against the
actual graph (see the loop below) before touching either prompt.

## The tuning loop (this is how the real fixes happened)

Prompts are not tuned by taste; they are tuned by watching a real run fail and
diagnosing *why*. When a stage fails or loops on a model:

1. **Reproduce and read the exact error.** `uv run qf run --to <stage> --dir
   <proj> --yes`. The repair/review message tells you the rule and quotes the
   text. Note the pass name and attempt count — repair burn *is* the signal.
2. **Diagnose against the graph, not by guessing.** Load the project and inspect
   the real state: is the flag the reviewer flagged actually `possible` here, or
   `certain`? Is the beat actually in a long run? (`uv run python` +
   `load_project`, `queries`, the stage's own `_context`/`_apply` helpers.) This
   decides *who is wrong*.
3. **Attribute fault, then pick the surface.**
   - Wrong id / finite value → **schema** (pin it, bound it).
   - Writer asserted something false or dropped a required event → **write
     prompt** (restate the binding constraint forcefully; handle the edge case
     the model tripped on).
   - Reviewer flagged a non-defect → **review prompt** (sharpen the rule with the
     exact distinction it missed; add the failing phrase as the teaching example).
   - The proposal was structurally valid but the *engine* rejected it → it may be
     an **engine** bug, not a prompt one (the finalize false-branch fix was an
     apply-ordering bug, not model error — always consider this).
4. **Make the change a restatement, not a new rule.** Make an existing contract's
   *intent* explicit — the thing the prompt already meant but left to inference;
   don't invent a new obligation a strong model already meets. Explain *why* in
   the prompt — smart models generalize from the reason, not from ALL-CAPS, and a
   reason is what makes the fix hold across models rather than patching one.
5. **Verify.**
   - `uv run pytest -q` and `uv run ruff check src tests` — green.
   - `uv run qf validate examples/keepers-bargain` — 0/0 (the golden is the oracle).
   - Mock-replay fixtures are **not** keyed on prompt bytes, so prompt edits don't
     break them — but the **LLM cache key includes the schema JSON**, so a schema
     change re-runs live while a prompt-only change replays a cached response
     (handy: fix a review prompt and the cached *writer* response replays, so you
     test the reviewer in isolation and cheaply).
   - Re-run the failing stage on the target model and confirm the error is gone
     and no *new* one took its place.
6. **Record it.** Update `docs/STATUS.md` (the hand-off note) and, if you changed
   a gate/invariant/schema contract, the relevant `docs/design/*` section — per
   the documentation contract in `AGENTS.md`. Report the outcome honestly: if a
   full run still doesn't complete on the tier, say so; don't claim a milestone.

## Pitfalls / pre-commit checklist

- [ ] Did you put a finite/referential rule in the **prompt** that the **schema**
      should own? (If the model can pick a wrong value from a known set, pin it.)
- [ ] Does an entity/id pin match **exactly** what the apply accepts (exact vs.
      slug-tolerant)?
- [ ] Is a schema whose enums depend on an earlier pass a **callable** schema?
- [ ] Did you add scaffolding to the base prompt that only a weak model needs
      (belongs in `_shared.j2`'s repair path instead)?
- [ ] Does a review change fail on **defects** and pass on **taste**, with a
      quoted example and a rule number?
- [ ] Did you restate an existing constraint (good) or invent a new obligation a
      strong model already meets (usually a smell)?
- [ ] Green: `pytest`, `ruff`, golden `validate` 0/0. Fixtures unaffected.
- [ ] `docs/STATUS.md` (and any affected design doc) updated; outcome reported
      honestly.

## Optional: measure a change instead of eyeballing it

For a subjective writing change, live re-runs plus the golden gate are usually
enough. If you want a rigorous before/after (e.g. "did this make the prompt more
robust, or did it just fix this one story on this one model?"), the `skill-creator`
eval harness can benchmark two prompt versions across several premises — and ideally
more than one model tier — with a human-review viewer. That cross-model spread is
the real test of the goal here: a good change helps everywhere, not just where it
was found. Ask for it; it's heavier than most tuning warrants.

When a *prompt* can't fix a failure because the weak model is simply
inconsistent (passes a rule on some samples, fails on others), the prompt is not
the lever — the guide's **self-consistency** (sample N, keep the passing one) or
higher model tier is. Recognise that boundary and say so, rather than tuning the
prompt in circles; the case studies end on exactly this wall.
