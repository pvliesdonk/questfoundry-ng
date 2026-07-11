# Case studies — real fixes, and what surface each belonged to

Each of these came from watching a real run (mostly the Ollama `gpt-oss:120b`
cloud tier — a deliberately-weaker model used as a **microscope**: it surfaces the
prompt gaps a frontier model silently infers past). They are the template for
diagnosis: **reproduce → inspect the graph → attribute fault → pick the surface →
restate, don't reinvent → verify.** Provenance lives in `docs/STATUS.md`'s decision
log.

Read them the right way: the point of each fix is **not** "make gpt-oss pass" — it
is to make the prompt *say what it always meant*. Every one of these was intent the
prompt had left to inference; stating it explicitly improves the output on any
model (and a frontier model, freed from guessing, tends to get more consistent
too). The weak tier only told us *where* to look.

## 1. Dangling id references → the schema, not the prompt (issue #40, generalized)

**Symptom.** SEED triage exhausted repairs: `explores` named an answer *slug* the
model invented, not a real answer id. Two unrelated strong families hit it; a
later cloud run hit the identical thing one field over (`locked[].dilemma`).

**Diagnosis.** The prompt *said* "use one of the answer ids listed above", but a
sentence is not enforcement. The valid set is finite and known at pass-build time.

**Surface: schema.** `pin(TriageProposal, …, {("PathSpec","explores"): answer_ids})`
makes the reference a `Literal` enum — a dangling value is unrepresentable under
grammar-constrained decoding, and the correction brief names the valid ids on a
miss. Generalized to *every* reference field across all stages
(`pipeline/refpin.py`).

**Lesson.** When the model picks a wrong value from a knowable set, stop rewording
the prompt — pin the schema. The prose still names the constraint (belt and
suspenders), but the schema is what holds.

## 2. Exact-vs-slug: pin to what the apply actually accepts

**Symptom (latent, caught in review).** Entity fields routed through
`resolve_entity_ref` accept a bare slug *and* the full `kind:slug` id; fields
checked by exact membership accept only the id.

**Surface: schema, precisely.** `entity_ref_ids` (ids + unambiguous slugs) for the
resolver-tolerant fields; `retained_entity_ids` (exact ids) for exact-membership
fields. Pinning ids+slugs on an exact-membership field would let a grammar-bound
model emit a slug the apply then rejects — trading one dangling failure for
another.

**Lesson.** An enum must match the apply's acceptance set *exactly* — looser is a
new bug, not a smaller one.

## 3. Finalize false branch → an *engine* bug wearing a prompt costume

**Symptom.** POLISH finalize rejected a cadence false branch at
`beat:spirit-post-2-burn -> bridge:gap-6`: "not inside a long linear run" — even
though the pinned `before`/`after` enum had accepted it.

**Diagnosis (against the graph).** The beat *was* in a long run at finalize-start
(what the model saw and the schema pinned), but `_finalize_apply` inserted residue
first and then recomputed long runs — residue splicing at a neighbouring
convergence had evicted the beat. The model was validated against a structure it
never saw.

**Surface: engine, not prompt.** Both residue and false branches are additions to
the *frozen* topology, so splice false branches against the pristine long runs
*before* residue. No prompt change.

**Lesson.** Before blaming the model, check whether a structurally-valid proposal
was rejected by an apply-ordering or recomputation bug. "The weak model does X" is
sometimes "the engine is inconsistent about X".

## 4. Tense drift → restate the constraint as a directive, handle the edge case

**Symptom.** Under a present-tense voice, the writer opened with simple past
("Mirren Arkwright **vanished**… **leaving** the coat"), failed review Rule 1
twice, couldn't self-correct.

**Diagnosis.** Tense was rendered as one inline field (`tense: {{ voice.tense }}`)
— true but weak. The specific trap: a *prior* event narrated in simple past.

**Surface: write prompt.** A prominent directive: every verb in the voice's tense,
prior events in that tense too (present voice → present perfect / simple present,
never simple past), read the first sentence back first (where the wrong tense
slips in). It restates an existing binding constraint — strong models already hold
it, so their output doesn't change.

**Lesson.** When a binding constraint is honored only by inference (tense was one
compact field), elevate it to an explicit directive and name the *specific* edge
case it trips on. Don't add a new rule — make the existing intent impossible to
miss. That helps any model; the weak tier is only what exposed that the field was
being inferred rather than stated.

## 5. Asserting `possible` state as fact → writer fault, WORLD STATE directive

**Symptom.** A cosmetic cadence arm (a single atmospheric beat, *all* flags
`possible`) was written as "the winter spirit watches" and "a flame licks the
coat" — asserting path-dependent flags as definite. Review Rule 4, twice.

**Diagnosis (against the flags).** Loaded the passage; confirmed every flag was
`possible` there, not `certain`. So the review was **right** — a reader on the
other route reads a contradiction. Writer fault, not reviewer fault.

**Surface: write prompt.** Under WORLD STATE, state it plainly: a POSSIBLE fact is
true on some routes and false on others, so never depict it happening or name its
result; write around it so the passage reads true either way; state only what is
CERTAIN — and name that this is checked. The writer weighs it while drafting, not
only in repair.

**Lesson.** Always confirm the flag status against the graph before deciding fault.
Here the reviewer was correct and the writer needed the firmer contract.

## 6. Reviewer laundering scenery as a missing event → reviewer fault, sharpen the rule

**Symptom.** FILL review failed a passage: "missing reference to morning light
revealing the cracks" — when the prose said the cracks were noticed downstream.

**Diagnosis (against the beat).** The beat was "**Morning light reveals** cracks…
threatening the water supply". The *event* is the crack; "morning light" is
time-of-day rendering. Rule 2 explicitly says rendering is craft, not fidelity —
the weak reviewer laundered a dropped adjective into a missing event, and the weak
arbiter upheld it.

**Surface: review prompt.** Sharpen Rule 2 with the exact distinction and the
failing phrase as the teaching example: the scenery a beat names (time, weather,
light, an incidental object) is rendering; a beat is unfulfilled only when its
ACTION or OUTCOME is absent; quote the action/outcome you claim is absent, never a
dropped adjective.

**Lesson.** When a review over-fails, verify against the beat/flags whether the
defect is real. If the reviewer is wrong, sharpen the rule with the exact
distinction it missed — use the real failing phrase as the example.

## 7. Where the incremental-prompt approach *stops*

Driving the weak tier through FILL moved from 0 to several clean passages with the
fixes above, then hit **residual stochastic inconsistency**: the writer sometimes
re-asserts possible-state content on the hardest passages (all-possible-flag
cosmetic arms), clearing Rule 4 in two rounds on some and exhausting on others.

**Lesson.** Not every gap is a prompt tweak. Sustained weak-tier prose quality is a
*milestone* (input-role framing, register rules, a rolling story-so-far summary,
character-arc metadata — see STATUS next-up #1), not a one-line fix. Know when to
stop tuning, record the honest state, and not fabricate a result (e.g. don't
preserve an "example" a run didn't actually earn).
