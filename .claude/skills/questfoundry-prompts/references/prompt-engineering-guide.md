# The Prompt Engineering Guide, distilled for this pipeline

Source: the dair-ai Prompt Engineering Guide (github.com/dair-ai/Prompt-Engineering-Guide,
rendered at promptingguide.ai). This file distills the parts that bear on a
**structured-output pipeline** and maps each to how QuestFoundry NG uses,
adapts, or deliberately avoids it. The guide is written mostly for chat/reasoning
prompting; the value here is the translation, not the raw technique.

## The four elements of a prompt (guide: `introduction/elements`)

The guide decomposes any prompt into: **Instruction** (the task), **Context**
(external info that steers), **Input Data** (what to act on), **Output
Indicator** (the type/format of output). QuestFoundry uses all four, and makes
the last one *enforceable*:

| Guide element | In a qf stage prompt |
|---|---|
| Instruction | The opening imperative ("Write the prose for ONE passage") |
| Context | The `VISION` line + `UPPERCASE` blocks (CAST, WORLD STATE, VOICE…) |
| Input Data | The graph state the stage's `_context` builder renders in |
| Output Indicator | **The Pydantic schema**, offered as JSON Schema — not a prose "return JSON like…" but a grammar the decoder is bound to |

The single most qf-specific idea: the Output Indicator is a *contract*, not a
suggestion. Everything the guide says about "specify the format" becomes "pin it
in the schema" here (see the SKILL body's two-surfaces section).

## General design tips (guide: `introduction/tips`, `guides/optimizing-prompts`)

All of these are already qf house style — the guide is the external corroboration:

- **Start simple, iterate.** Prompt tuning is experimental. qf does this the hard
  way: tune against a *real run's* failure, not in the abstract (the tuning loop
  in the SKILL body).
- **Use command instructions**, placed first, separated from context. The guide
  suggests `###` separators; qf uses `UPPERCASE:` block headers to the same end.
- **Specificity beats cleverness.** "The more descriptive and detailed the prompt,
  the better." The guide's own example — replace *"keep it short"* with *"Use 2-3
  sentences to explain to a high school student"* — is exactly why qf prompts
  carry counts (`exactly {{ scope.hard_dilemmas }} hard`), bands
  (`{{ words_min }}-{{ words_max }}`), and id formats.
- **Avoid impreciseness — be direct.** Don't over-clever a prompt into vagueness.
- **Say what to do, not what not to do.** The guide's movie-bot example (a
  `DO NOT ASK FOR INTERESTS` instruction that made the bot ask for interests) is
  the canonical warning. qf follows it — with one deliberate addition: after the
  positive directive, *name the consequence* of the failure once ("this is
  checked and fails review"), so the model weighs it while drafting.
- **Don't pad.** "Including too many unnecessary details is not necessarily good."
  Keep each context block earning its tokens.

## LLM settings (guide: `introduction/settings`)

Temperature/top-p: **low for factual/deterministic, higher for creative** (alter
one, not both). Frequency/presence penalties reduce repetition. This matters
concretely: qf configures `temperature` per project (the Ollama provider passes
it through). Structural passes (SEED/GROW/POLISH proposals — right-or-wrong
against the graph) want it low; prose (FILL write) tolerates warmth. If a
structural pass is *erratic* across identical inputs, suspect temperature before
rewording the prompt. (The repetition penalties are the tidy knob for the
book-scale verbatim-detail problem noted in STATUS — a settings lever, not a
prompt one.)

## Techniques — and whether qf uses them

### Prompt chaining (guide: `techniques/prompt_chaining`) — qf's whole architecture
"Break a task into subtasks; one prompt's output feeds the next." The guide sells
it for **transparency, controllability, reliability, and debuggability**. The
entire eight-stage pipeline *is* prompt chaining, and each multi-pass stage
chains internally — with the crucial qf twist that a **deterministic engine sits
between links**, validating and transforming, so a bad link is caught at its own
gate rather than propagating. When a stage is unreliable, this is the guide's
license to split a pass rather than pile more into one prompt.

### Generated knowledge (guide: `techniques/knowledge`) — qf's research pass
"Generate/retrieve knowledge before predicting" to ground the answer. qf's
research/craft-corpus pass is exactly this: a librarian retrieves craft notes,
and the digest becomes the advisory `_craft.j2` block that heads substantive
passes. Keep it *advisory* — the guide shows generated knowledge can also mislead
(its golf example flipped the answer), which is why qf's review prompts exclude
`_craft.j2` and never let the digest override the contract.

### Reflexion (guide: `techniques/reflexion`) — qf's review + repair loop
Reflexion = **Actor** (produces output) + **Evaluator** (scores it) +
**Self-Reflection** (turns the failure into verbal feedback fed to the next
attempt). This is precisely qf's FILL/DRESS shape: the **write** pass is the
Actor, the **review** pass is the Evaluator, and `repair_errors` rendered by
`_shared.j2` on the next attempt is the verbal self-reflection. Two design
consequences the guide's "limitations" section predicts and qf must respect:
- Reflexion "relies on the agent's ability to accurately evaluate" — a **weak
  Evaluator poisons the loop**. This is exactly the "weak reviewer laundered
  scenery as a missing event" case: fix the Evaluator (review prompt) precision,
  not just the Actor.
- Reflexion uses a **bounded memory / trial budget**. qf's "≤2 rounds then halt:
  the structure is wrong, not the words" is that bound — don't raise it to paper
  over a weak Actor; that's the guide's warning, not a workaround.

### Factuality / reducing hallucination (guide: `risks/factuality`)
Levers: **ground truth in context**, **lower probability params**, **let the
model say "I don't know."** qf's analogue is *state honesty*: a passage reachable
with a flag either way must not assert it (the write prompt's POSSIBLE-state rule
is "when you don't know, don't assert" in narrative form), and the craft corpus
is the ground-truth grounding.

### Zero-shot (guide: `techniques/zeroshot`) — qf's default
Instruction-tuned models do these tasks with no exemplars, and qf prompts carry
none. But be honest about *why* they're spare: they are largely **uninvested** —
written to state intent directly, and they work because a strong model infers the
rest, not because they were tuned for that (STATUS: "NG's blunt prompts haven't
made that investment"). So "zero-shot" here is the starting condition, not a
finished optimization — and it is why a weak tier's failures diagnose the prompt.
The genuinely deliberate part is A20's rule for *when you invest*: add help on the
failure path, not the base (see Reflexion).

### Few-shot exemplars (guide: `techniques/fewshot`) — qf mostly AVOIDS, on purpose
Few-shot steers format by showing input/output pairs. qf deliberately does **not**
embed worked exemplars in most prompts, for two project reasons: (1) an exemplar
answer is a *bias vector* — the "answers are strictly equal, no canonical marker"
iron rule forbids nudging the model toward one option; (2) A20's principle that
"help must be conditional on failure" — baking demonstrations into the base
prompt taxes strong models for a weak model's benefit. The oracle lives in the
*tests* (the golden story), not in the prompt. Note the guide's own finding
(Min et al. 2022): with few-shot, **format and label distribution matter more
than label correctness** — so *if* you ever add an exemplar, its shape teaches
more than its content.

### Chain-of-Thought / zero-shot CoT (guide: `techniques/cot`) — qf AVOIDS in the pass
"Think step by step" via intermediate reasoning. qf's structured passes are
**single-pass**: no discuss-then-serialize (A20 explicitly rejected legacy's
two-pass shape as 4B-era scaffolding). When a model supports separate "thinking",
it streams apart from the content and must never pollute the JSON payload. Reason
belongs in the *engine's* determinism, not in the model's scratchpad here.

### Self-consistency (guide: `techniques/consistency`) — unused, but a known lever
Sample multiple reasoning paths, take the majority answer. qf doesn't do this
today, but it is the textbook remedy for the **residual stochastic weak-tier
inconsistency** documented in the case studies (a writer that clears a rule on
some samples and not others): sample the passage N times and keep the one that
passes review. Heavier and costlier — a milestone-scale option, noted so it isn't
reinvented.

### ReAct (guide: `techniques/react`) — partial, at the pipeline level
Reason + act + retrieve from an environment. qf's research pass retrieves; the
`qf illustrate` / tool seams act. But the per-stage proposal passes are
deliberately *not* interleaved reason-act loops — the engine owns the "act", the
model only proposes.

## What to take from all this

The guide validates qf's instincts (specificity, directives, delimiters,
decomposition, grounding) and names two frameworks qf already embodies (prompt
chaining, Reflexion). Its most useful gift for *tuning* is the vocabulary to
locate a failure: is it an **Instruction** problem (unclear task), a **Context**
problem (missing/greedy grounding), an **Output Indicator** problem (fix the
schema), an **Evaluator** problem (Reflexion — the review is wrong), or a
**settings** problem (temperature/penalty)? Name the layer, then fix that layer —
don't reword the Instruction when the Output Indicator is what's unenforced.
