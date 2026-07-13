# Project Status

> **Living document — the session hand-off note.** Every PR updates this
> file: what changed, what's next, decisions made. If you are an agent
> starting a session, read this first; if you are ending one, leave it
> the way you'd want to find it.
>
> Last updated: 2026-07-13 · **`scene_type` structural prose-intensity
> modulation is built** (PR #65) **plus its G4 pacing report** (follow-up).
> A beat now carries an intrinsic `scene_type` (Swain scene/sequel/micro_beat)
> that GROW's new *annotate* pass writes pre-freeze and FILL reads to
> modulate prose across the story (per-passage word band + per-beat
> intensity directive); the deferral in 01 §10.3 is resolved. The pacing
> report followed as advisory **B8** (beat-level, `check_b8_pacing`). 540
> tests. Follow-ups still open: the `overwriting` guardrail, live
> validation on Ollama, and the scale recalibration. Before it: **#1a live validation ran and reframed
> the work as prompt quality** (author-directed; decision log has the full
> record): both fresh stories died at FILL review-exhaustion, so the
> scaled recurrence read is still open (13 passages can't discriminate)
> — but the failures were diagnosed as *blunt prompts/messages propped up
> by model intelligence*, now a standing rule (`AGENTS.md` §"Prompt and
> error-message quality"). Fixes: a store `GraphError` class + runner
> catch make every model-reachable graph write repairable and actionable
> (killing a latent crash class the finalize duplicate-id exposed);
> `fill_review.j2` forces rule-text matching (weak reviewer fabricated a
> rule); `fill_write.j2` gains a POV-limited block (writer head-hopped a
> non-viewpoint character). Prompt fixes designed against the failures,
> not yet live-validated. Also: the **vendored in-repo corpus's first
> real run worked** (structure clean). Before it: the prose-quality
> live-validation predecessors — corpus vendored
> (`corpus/interactive-fiction/`, 55 notes) and M10 progress reporting
> pulled forward. Before it: **The prose-quality-at-scale engine is built** (next-up #1's engine half — echo check, input-role framing, note register + richer Voice, rolling story-so-far, character-arc metadata; the decision-log entry has the design record; live validation remains, and the **review-contract redesign is now BUILT** — a pipeline-wide structured-finding contract ([`docs/plans/review-contract.md`](plans/review-contract.md), `pipeline/review.py`) shared by FILL prose + DRESS codex review: the engine gates only proceed-vs-rework on confident objective defects, the producer weighs the full-fidelity findings). Before it: M8 complete; Ollama backend built AND validated live. The triage referential-integrity gap (#40, `explores`) generalized into a **pipeline-wide reference-pinning discipline** (`pipeline/refpin.py`): every proposal field that names an existing id — across SEED, GROW, POLISH, FILL, DRESS — is pinned to a per-project `Literal` enum, so a dangling reference is unrepresentable under grammar-constrained decoding and named back on a miss. Re-confirmed live on the `gpt-oss:120b` cloud tier via `OLLAMA_API_KEY`: every reference-heavy stage (DREAM→BRAINSTORM→SEED→GROW) passes clean end-to-end. **A follow-up effort then drove the weak tier deeper** (open item 5 / decision log): the finalize false-branch gap turned out to be a real latent engine bug (false branches validated against post-residue rather than the pristine frozen topology) — **fixed, POLISH now clears live** — and three FILL prose-prompt hardenings (tense as a directive, POSSIBLE-state honesty, review event-vs-scenery precision) carry the run to its first clean FILL passages. A full clean DRESS on `gpt-oss:120b` remains gated by residual weak-tier prose inconsistency (the prose-quality-at-scale milestone, next-up #1), so no cloud example is preserved yet. **A full prompt-engineering audit then swept every template** (all 24 `.j2` files + each pass's render context, author-directed): context gaps closed (order-pass dispositions, taken codewords, premise at triage/voice, reviewer lookahead), prompt/spec mismatches fixed, and one latent engine bug caught by the audit's "the context must be true" clause — gate certainty now propagates to rival paths in FILL's flag statuses (decision log).

## Where we are

**`scene_type` structural modulation is built** (2026-07-13, PR #65; plan
[`docs/plans/scene-type-modulation.md`](plans/scene-type-modulation.md),
decision log below). The reading-difficulty effort traced over-stylization
to a missing structural signal — heritage distributed prose intensity per
beat, NG deferred it (01 §10.3) — and this restores it. Five checkpoints,
all landed:

- **Model** (`models/structure.py`): `SceneType{scene,sequel,micro_beat}` +
  `Beat.scene_type`; `effective_scene_type()` (annotation wins → structural
  transition/texture beats fall back to `micro_beat` → else `scene`);
  `passage_intensity()` (max over beats via an explicit `intensity_rank`
  map, never a bare `max` over the StrEnum); `set_beat_scene_type` mutation
  mirroring `set_beat_summary` (settable pre-freeze, rejected once frozen —
  scene_type is intrinsic beat content, why the beat exists).
- **GROW `annotate` pass** (`stages/grow.py`, `grow_annotate.j2`): a fifth
  pass after *contextualize*, before *bridge* (pre-freeze); one LLM call
  tags every beat present (SEED scaffold + clones); refpin-pinned beat
  enum; apply requires full coverage. Beats added later (bridge here,
  POLISH residue/false-branch) ride the purpose fallback.
- **FILL consumption**: `ScopePreset.words_for` keys off the passage's
  aggregate `scene_type` (scene → full, sequel → `lo+2·span/3`, micro →
  `lo+span/3` == the old texture band, so texture passages are unchanged;
  endings keep +100). The shared `passage_intensity` feeds all four
  callers — FILL's write context + word-budget finding, B5, and the
  cadence projection (both now modulation-aware; a lone-bridge group
  shortens). `fill_write.j2` tags each beat and makes "style belongs to
  the story" concrete per beat; `fill_review.j2` renders the same tags and
  is told a plain sequel is correct, not a defect.
- **Golden + fixtures**: 19 golden beats hand-annotated (commits/reveals →
  scene; reactive payoffs, aftermath, setup, locked-chain → sequel; the
  three residue arms left to the micro fallback); every passage keeps a
  scene beat so bands and the 0-error/0-warning validate are unchanged
  while per-beat modulation is real. The keeper e2e got the annotate call
  spliced in (a scene/sequel mix), fixtures renumbered, ledger counts
  bumped.
- **Docs**: 01 §10.3 (built, not "will start with") + a new "Beat
  annotations" subsection; 02 GROW Out/passes + the FILL G5 band mapping.

Advisory throughout — no new gating invariant; an unannotated beat falls
back, never fails. **Open** (deliberately deferred, see Next up): the G4
pacing report (now buildable — the signal exists), the `overwriting`
guardrail (modulation-variance metric + compound-density > 15/1k), and
live validation on Ollama (unbilled; a human read of whether prose now
modulates). One risk flagged, not preempted: modulation shortens
sequel/micro passages, so `words_total`/`passages` bands and
`tests/scale.py` may read slightly high — a *measure-after-a-live-run*
recalibration, not touched here. 536 tests.

**The live-validation predecessors are done** (2026-07-12,
author-directed; the decision log below has the design record). Two
items cleared before next-up #1a runs: (1) the **curated craft corpus
is vendored** at `corpus/interactive-fiction/` — the eight non-exemplar
clusters, 55 notes byte-faithful from the author's vault,
`corpus/README.md` for scope/provenance, `style-exemplars` excluded
until M9 — so corpus-grounded runs stop depending on hand-staged
out-of-repo exports; (2) **M10's progress reporting is pulled forward**
(explicit author call, not scope drift; the rest of M10 stays put): the
runner emits `PassProgress` events through a CLI-agnostic callback
seam, `qf run`/`qf rerun` print a flushed per-pass heartbeat on stderr
(pass m/n, attempts, running ledger totals), and `qf status` shows
spend and any interrupted stage's in-flight ledger state. 467 tests.

**The prose-quality-at-scale engine is built** (2026-07-11, the frontier
session next-up #1 called for; plan doc
[`docs/plans/prose-quality.md`](plans/prose-quality.md), decision log
below has the record). All five author-approved workstreams landed:
(1) a deterministic **echo check at the FILL apply** — prose restating a
rendered entity fact (≥ 4 tokens) or lifting a ≥ 8-token verbatim run
from adjacent prose is rejected repairably (`pipeline/echo.py`), and
micro-details are held to note form (≤ 12 words, no re-keying an
established fact under a new name — the `habit`/`stance_width` accrual);
(2) the **write prompt states every context block's role** — facts are
constraints, not choreography; the window is continuity, not a style
template; (3) the register rule generalized (01 §5): everything that is
not prose is a note, and the **Voice grew an imagery palette and
dialogue rules** so a writer short on style guidance has somewhere to
reach besides the styled text in its prompt; (4) a **rolling
story-so-far**: a utility-tier `summarize:<slug>` pass rides behind
every accepted write pass (≤ 60-word note on `Passage.prose_summary`),
and each write context renders the notes along one deterministic route
(reference-arc-preferred, window hop excluded, capped at 40);
(5) **character-arc metadata** — POLISH gained the fourth pass 02 always
contracted (`arcs`, writer role, refpin-pinned entity/beat/path enums,
set-once mutation, G4 fails a dangling reference loud), and FILL renders
the arc *position* per on-stage entity: the aspect in play now, the turn
this scene carries, where the entity is heading, path landings once
committed. The golden story models the shape (arcs for both leads,
story-so-far notes on all nine passages); the keeper e2e fixtures were
re-recorded with the two new passes spliced in (45 calls). Remaining
from the plan: live validation (strong-map recurrence read + a weak-tier
FILL re-attempt). The review-contract redesign for weak tiers is now
**BUILT** ([`docs/plans/review-contract.md`](plans/review-contract.md),
`pipeline/review.py`): a pipeline-wide structured-finding contract, not
FILL-only — its own weak-tier live validation is the one open item.
461 tests.

**Every prompt is audited** (2026-07-11, author-directed: "crystal-clear
intent and expectation, full context — never inferred"): all 24 shipped
templates, the review system prompts, the adapter's JSON instruction and
correction brief, and every pass's render context, against a rubric drawn
from the vendored semantic conventions (directive language, explicit
constraints, enums for finite sets) and standard prompt-engineering
practice. The yield is mostly *context* fixes — a prompt held to a rule
whose inputs it couldn't see — plus one real engine bug the audit's "the
context must be TRUE" clause caught: a gated residue or variant passage's
own truth rendered as merely "possible" in FILL's WORLD STATE, so the
Rule-4 honesty directive ordered the writer to stay neutral about the very
fact the passage exists to carry (and the review's rule 4 would fail prose
that asserted it). Gate certainty now propagates along the dilemma — beat
gates *and* choice-edge gates (how variants are wired) make the gated
path's flags CERTAIN and every rival path's flag FORECLOSED. Full findings
in the decision log. 433 tests.

**An Ollama backend is built** (author-directed, unplanned addition;
the decision-log entry below records the design discussion):
`llm.provider: ollama` runs local *and* Ollama-cloud models through the
same provider seam as the other three families. The adapter now derives
each call's JSON schema once and offers it to the provider (mini-ADR
A20): Ollama consumes it as `format` (grammar-constrained decoding —
what makes small local models emit schema-shaped JSON), the cloud
providers deliberately ignore it, and Pydantic validation + retry stays
the sole acceptance path everywhere. The retry itself was upgraded for
every provider: a correction brief (failing field paths, what was
wrong, values seen) instead of a raw exception dump — the legacy
retry-with-feedback lesson, engaged only on failure so strong models
never pay for it. The provider owns the local-model traps: explicit
`num_ctx` (project.yaml: `host`, `num_ctx`, `temperature`,
`keep_alive`, `think`), fail-loud truncation detection via
`prompt_eval_count`, streaming collection, `OLLAMA_API_KEY` for the
cloud tier, and a one-shot unconstrained fallback if a host *rejects*
`format` (cloud is documented to lack structured-output support and
expected to ignore it — verification is an open item). A lint test
holds every proposal schema inside the grammar-safe subset (all ~50
already were). **Validated live** (PR #42; the open item below has the
per-step results): A20 confirmed on both tiers — `gpt-oss:120b-cloud`
*accepts* `format` — and the run surfaced the SEED triage
dangling-reference gap as issue #40. **#40 is now fixed**: triage's
proposal schema is built per project with `explores` pinned to an enum
of the real answer ids (graph order — answers are strictly equal, the
enum must not read as a ranking), so every provider sees the referential
constraint in the schema, the correction brief names the valid ids on a
miss, and under grammar-constrained decoding a dangling reference is
unrepresentable at decode time. First dynamically-built proposal schema
(the FILL computed-passes seam, extended to schemas); the pattern's
generalization to other id-reference fields is now **realized across the
whole pipeline** (2026-07-11): a live `gpt-oss:120b` cloud `--to seed`
re-run — reached via `OLLAMA_API_KEY`, the exact model that first exposed
#40 — cleared the `explores` enum on the first attempt and then failed
triage the *identical* way on `locked[].dilemma` (an unprefixed dilemma
slug); rather than patch that one sibling, the discipline was lifted into
a shared helper (`pipeline/refpin.py`) and applied to **every** reference
field in every stage. `pin(model, name, resolvers)` recursively rebuilds a
proposal model — nested specs and all — pinning each leaf str/list[str]
reference field to a `Literal` enum of the real ids (`FieldInfo`,
`min_length`, defaults preserved; single-value enums render as grammar-safe
`const`). Coverage: SEED (triage `cut_entities`/`explores`/`locked`,
scaffold dispositions+paths+`entities`+hints, order relations), GROW
(intersection `members` **and the previously *unchecked* `location`**,
contextualize `beat`, bridge `entities`), POLISH (finalize
`dilemma`/`world`/`path`/`entities` + false-branch `before`/`after`,
passages variant `flag`, audit `passage`/`irrelevant`), FILL
(`micro_details.entity`), DRESS (all four passes). A field validated by
`resolve_entity_ref` pins to ids **+ unambiguous bare slugs** (preserving
that affordance); a field validated by exact membership pins to exact ids
only (`retained_entity_ids`) so the enum never admits a value the apply
rejects. Schemas that depend on an earlier same-stage pass's writes (SEED
scaffold needs triage's dispositions; POLISH audit needs the passages
pass) pass a *callable* schema the runner resolves at pass-run time
(`PassSpec.schema_for`). The apply-layer guards all stay — the enums narrow
the space; the guards still enforce joint constraints an independent enum
can't (finalize's (dilemma, world, path) triple). Two BRAINSTORM refs stay
**deliberately unpinned**: `anchored_to` references entities coined in the
same proposal (no pass-build-time set). 428 tests.

**M8 is complete** (PR #37 carried the run's engine findings; the
example PR carries the exit record). The exit run — live run 8,
"Closed Circle", from the author's seed "an Agatha Christie closed
circle murder mystery that escalates Fargo style" — generated a
corpus-grounded `medium` story end-to-end on Gemini
(gemini-3.1-pro-preview architect/writer + gemini-2.5-flash utility,
a third provider family) and met **every roadmap §M8 exit criterion**:
49,381 prose words (target 20-60k), 148 passages (B3 band 90-160),
114-123 beats per arc (B4 band 80-150), walk-B6 **644** mean
(618-663; target <= ~800), 32/32 arcs simulate complete, all four
exports round-trip clean including the 250+-section print PDF, at
~$17 (cap $20; pro 397 calls 0.93M in / 1.13M out, flash 292 calls).
The measured cosmetic:real choice ratio is 4.6:1 against the plan's
predicted ~5:1 and the simulation's ~4:1 — the calibration
methodology (bands set by structural simulation, live run confirms)
held. Preserved as `examples/closed-circle/`. Five engine findings,
each fixed in-flight with the live-run pattern (decision log). The
plan doc `docs/plans/m8-depth-scale.md` is retired with this entry
(its contract lives in 01 §2/§5-6, 02, 03 §9/A19; its record lives
here). 393 tests.

**Tensored residue arms are built** (M8 PR-1b, plan D5): a light
residue arm may fork into two same-gate branches — the reader who made
the matching upstream choice gets a texture-only choice in how to carry
it, and both branches rejoin where the arm does. Schema: `ResidueSpec`
gains an optional `fork`; splice: `insert_residue_diamond` (shared
frontier logic with the chain splice); either branch satisfies G4's
coverage and I10-I13 hold with no semantic change (asserted with
violating constructions, per the plan). Measured on the simulation:
tensoring medium's arms drops walk-B6 780 -> 690 with words still in
band — cadence that compounds where diamond seam capacity binds. The
golden story models the shape: the tell-side arm is now a real choice
(`counsel` | `honest-chart` — spend the last hour with Elias's counsel,
or over his finished chart), 9 passages, prose split into two texture
passages, still 0 errors / 0 warnings. 392 tests.

**The M8 engine is built** (PR-1; plan and record in
`docs/plans/m8-depth-scale.md` — its "PR-1 outcome" section is the
short version, the decision-log entry below the full one). The scale
table is words-primary (mini-ADR A19): every preset anchors on
`words_total`, scaffold depth is scope data (`ScaffoldShape`, enforced
repairably at SEED — micro pins the old literals so the golden story
and every recorded fixture hold unedited), collapse is capped
(`passage_beats_max`, the choice-free cutter that lets deep scaffolds
mint pages), POLISH's cadence budget is words-aware (engine-sized by
iterated playthrough projection, cap-aligned seams only, diamonds or
the new sidetracks), FILL enforces per-passage word bands
(texture/scene/ending), B6 measures a playthrough walk instead of an
arc view, B7 checks total words, and weave enumeration fair-splits
when lexicographic DFS would return near-identical orders (measured
at 63 units: all 64 candidates shared a 12-position prefix). The
dilemma mixes moved per the D4 simulation: medium 2H+3S, long 2H+4S
(+1 hard measured dominated: +78% words for zero real choices per
arc). Simulated exit projection at medium: 46-52.5k words, 124-142
passages, B6 780, all inside the recalibrated bands. The golden story
is band-clean (0 errors, 0 warnings) — one hand-authored texture
passage was trimmed to model the new register. 390 tests.

**M8 planning record** (frontier planning session; the plan doc
[`docs/plans/m8-depth-scale.md`](plans/m8-depth-scale.md) is the
hand-off contract, the decision-log entry below is the record). The
milestone in one line: the SEED scaffold's depth numbers are prompt
literals identical at every scope, so stories come out good but small
(8–22k words, B6 ~1.1–1.25k across runs 5–7); M8 makes depth preset
data, anchors the scale table on total prose words (mini-ADR A19,
lands with PR-1), and recalibrates the bands by structural simulation
through the real weave and collapse instead of against our own
generated stories. Build order: PR-1 engine (words-primary table,
`ScaffoldShape` per scope, words-aware cadence targeting, weave-spread
measurement), PR-1b tensored residue arms (+ golden-story extension),
PR-2 the live corpus-grounded `medium` exit run at 20–60k words
(budget est. $8–14, cap $20).

**M7 is complete** (PR #33; decision log below has the record).
`qf illustrate` renders DRESS briefs to `art/images/<slug>.png` —
a post-DRESS *command*, never a stage (mini-ADR A18: cloud providers
expose no seeds, so rendered bytes can't join checkpoint byte-stability
or A16 replay; idempotence is by file presence and a re-run costs zero
API calls). The provider seam is `image-generation-mcp` as a library
(`ImageService` + `register_provider`; placeholder / OpenAI / Gemini,
configured via a project.yaml `images:` block or `--provider`). The
engine owns what the library deliberately doesn't: deterministic prompt
assembly (art direction + per-entity visual-profile fragments, an
unprofiled citation fails loud), the sample-first gate,
`--budget`/`--priority` caps, `kind: image` ledger entries, one LLM
reformulation (utility role) on a typed content-policy refusal, and PNG
normalization at the single write site. The HTML player now inlines
rendered art as data URIs above the prose; the print PDF fills its
illustration slots. CI drives the full command hermetically through the
zero-network placeholder. The exit ran live on **both** cloud
providers: all 7 briefs of `examples/lamplighters-debt-craft` rendered
on Gemini (~$0.28, zero refusals, free rerun verified, HTML player and
the 78-page PDF embed all seven), and a gpt-image-2 sample of the
golden story landed dead-on its scratchboard art direction. Two latent
engine bugs surfaced live and were fixed with tests: typst resolves
`#image` paths from its *compilation root* (the M5 slot machinery
emitted absolute OS paths and had never met a real file), and Gemini
returns JPEG bytes regardless of the `.png` contract. 372 tests.

**The M6 engine is built** (PR #30; plan and design record in PR #29 /
`docs/plans/m6-craft-corpus.md`): configure a `craft:` block in
project.yaml and a **research pass** heads every stage — the librarian
proposes at most `max_queries` search strings (standing queries derived
from the vision are shown so it asks only for what's missing; DREAM
runs premise-only), the engine retrieves via `markdown-vault-mcp`'s
Python API (hybrid or keyword, per-folder, re-sorted deterministically)
and persists an author-editable `research/<stage>.md` whose body every
substantive pass reads as an advisory `_craft.j2` block. Review
prompts are structurally immune (they render themselves); the
feasibility audit and the mechanical picks are excluded deliberately.
The digest is checkpointed, fingerprinted (A16: corpus hash + craft
config join the knobs only when configured), and reused while fresh
(A17: `prepare_rerun` preserves the target's digest; a corpus or
vision edit re-retrieves; deleting the file forces it). Corpus-less
projects are untouched to the byte — the pass skips, positional
fixtures hold, and CI never installs the retrieval stack (tests drive
real hybrid search through a deterministic fake embedding provider).

**M6 is complete.** The exit run (live run 7, decision log): one fresh
`short` premise — "The Lamplighter's Debt", canal-town folk horror —
generated twice on the default Opus/Haiku map, run A bare and run B
grounded in the author's 80-note IF-craft corpus (fingerprint
`41d6e056…`, scoped to the eight non-exemplar clusters). Both stories
gate-clean, 8/8 arcs complete, all four exports round-trip, preserved
as `examples/lamplighters-debt-base/` and `…-craft/` (the pair is the
A/B record). Grounding is visible exactly where the corpus speaks:
run B opens in second person present (the corpus's stated gamebook
default; ungrounded run A chose third limited), reads
objects-carry-the-grief, and its research digests are on-topic per
stage. Every §PR-2 check passed live: digests at all seven stages,
snapshots accumulate them, reports name the fingerprint, run A's
reports show the skip; a deleted digest reproduced **byte-identically
with zero LLM calls** under `rerun --keep research`; a hand-edited
digest survived a rerun with the freshness skip firing; two real
mid-stage failures resumed through the A16 ledger with research and
triage replayed free. Costs: A ≈ $3.50, B ≈ $4.03 (including all
tuition). The run also delivered the pending locked-dilemmas live
validation — triage locked 2 of 5 dilemmas sensibly in both runs —
and five engine findings, each fixed in-flight with a
violating-construction test (decision log).

**Locked dilemmas + richer residue are built** (the structural
volume/depth effort, author-blessed 2026-07-09; decision log below has
the design record):

- **Locked dilemmas** end-to-end: BRAINSTORM overgenerates by the
  scope's new locked allowance (B1 checks a range pre-triage, branched
  equality after); SEED triage gives every dilemma a disposition —
  branched or locked-with-a-reason — and scaffolds locked storylines as
  lead-in / resolution / aftermath chains on the single explored path;
  the weave threads each chain through the story one movable unit per
  beat (wraps/serial anchor at first beat and resolution; locked beats
  may join intersection groups — they are on every arc); after a hard
  fork the chain clones per world like any unit and contextualize
  rewrites the clones. Invariants: I3 gained the locked-chain shape,
  I6 requires every arc to resolve every locked dilemma exactly once,
  and a locked outcome is a world fact — G3-FLAGS exempts its
  consequences and rejects flags granted from a locked path (mini-ADR
  A15: the disposition is derived from topology, no marker). A locked
  hard-role dilemma makes no worlds and cannot be the backbone.
- **Richer residue**: light residue now demands the full diamond — one
  flag-gated residue arm per path per world (G4 + finalize apply,
  repairable), and an arm may carry a `followup` beat; passage collapse
  merges identically gated adjacent beats, so a 2-beat arm reads as one
  gated passage, not click-through singletons.
- **The golden story exercises both**: `dilemma:second-keeper` (what
  ended the previous keeper's watch — locked, resolved on every arc,
  no flags, woven pre-fork), a hide-side residue arm (`beat:unspoken`,
  new passage, codeword UNSPOKEN now that the detour gate tests
  `flag:lie-between`), and a 2-beat tell arm (`counsel` +
  `honest-chart` collapsing into `p-counsel`). 8 passages, all exports
  round-trip clean, PDF compiles with zero numbering warnings (the old
  7-passage impossibility dissolved at 8). 256 tests.

Exercised live in run 7 (both A and B): triage locked 2 of 5 dilemmas
with sensible reasons twice, locked chains wove through the story and
survived the dense relation webs they created, and residue arms landed
per path (run A's second G4 finding was an engine bug in multi-flag
coverage, not a model miss — decision log).

**M5 is complete.** Both halves of the exit criterion are met: the
golden story prints as a real gamebook (PR #20), and the pipeline
generated its first live `medium`-scope story end-to-end within budget
(PR #23) — "The Bubblegum Alibi", a closed-circle murder mystery in a
bubblegum high-school setting, on the default model map
(claude-opus-4-8 architect/writer + claude-haiku-4-5 utility):

- **The medium run** (preserved as `examples/bubblegum-alibi/`):
  4 dilemmas (2 hard nested by the live multi-hard weave, 2 soft — one
  rejoining at the other's fork), 10 entities, 46 frozen beats across
  two worlds, 20 passages (~10.4k words), 16 arcs all simulating
  complete, 4 titled endings, full DRESS enrichment (direction, 10
  profiles, 4 briefs, 7 codex entries, 4 on-diction codewords:
  CRACKED, SILENT, SNAPPED, MURKY), 0 gate errors, all four exports
  round-trip clean including the print PDF. Budget: **~$3.25** — 187
  calls (99 live: opus 259k in / 74k out; haiku 82k in / 3k out; 88
  free cache replays across crash-resumes), ~24 min wall-clock summed
  over eight attempts. The run surfaced **six engine/contract bugs**,
  each fixed in-flight with a violating-construction test (decision
  log); the crash-resume machinery (content-addressed cache + per-stage
  checkpoints) is what made eight attempts cost ~one clean run. 221
  tests. Stage output was committed per checkpoint on PR #23 — a useful
  pattern for future live runs.

- **Multi-hard weave expansion** (PR #22) (the tensor model, design doc 01 §5,
  mini-ADR A14): `weave.realize` walks the chosen order tracking
  *worlds* — the climax hard resolve is always the final unit; every
  unit placed after the first hard fork is instantiated once per world
  (world-suffixed ids, `belongs_to` copied, the template Y removed
  symmetrically so no world owns the "original"), each further hard
  resolve multiplies the worlds, and the earlier forks' tails stop
  being endings (2 hard → 4 endings). Candidates enumerate per viable
  nesting (an even share of the 64 cap each) so the weave LLM chooses
  the nesting like any interleaving; `wraps`/`serial` between hards
  constrain it — `serial(hard, soft)` now legitimately places a whole
  soft dilemma inside the worlds, cloned per world with per-world
  convergence. A new GROW pass *contextualize* (skip_if single-hard)
  rewrites each clone's summary for its world and each de-ended tail
  to leave the climax question open. Invariants refined: I3 is now
  "commit beats occupy pairwise distinct worlds" (worlds are made by
  *other* dilemmas' forks), I6 checks exactly one commit per path per
  arc, I7 checks hard non-reconvergence pairwise across commit sets
  and soft payoff per world; `queries.commit_beats`/`grant_beats` are
  list-valued with any-grant semantics; `FreezeRecord.convergences`
  records one beat per world (legacy single-beat files coerce on
  load). POLISH gained per-world variant support: a heavy-residue soft
  dilemma rejoining at a hard fork now requires variants at every
  frontier beat (the old G4 "unsupported" error is gone), and light
  residue coverage is checked per world. Intersections stay
  constrained to the truly shared region before every hard fork.
  215 tests; the 2-hard topologies are built through the real weave,
  never hand-wired.

- DRESS (`pipeline/stages/dress.py`), four passes sharing gate G6:
  *direction* (art direction + one visual profile per retained entity;
  `skip_if` keeps an author-approved direction on reruns), *briefs*
  (prioritized illustration briefs, `max(3, min(20, passages//5))`, the
  engine checks every cited entity is in the passage and profiled),
  *codex* (one diegetic entry per dilemma-anchoring entity, spoiler
  safety enforced by a paired utility review whose contract follows the
  review-legibility lessons: numbered FAIL rules, quote the offending
  text, hedged findings excluded), *codewords* (one memorable word per
  gate-tested flag — suggested at DRESS, not POLISH, because "drawn from
  the story's diction" needs voice and prose to exist; mini-ADR A12).
  Enrichment lives on the Project like the Voice (`art/direction.yaml`,
  `art/briefs/`, `codex/*.md`), never in the graph; gates see it via
  `run_checks(enrichment=…)` — one validation path. Codewords are graph
  data on flags via `mutations.set_flag_codeword` (stable once set).
- Print gamebook (`export/gamebook.py`, `qf export pdf`): consumes the
  canonical runtime JSON only; codeword projection (= gate-tested
  flags; slug-derived fallback + warning for pre-DRESS projects),
  grant lines hoisted to a section iff every arriving choice grants the
  flag, variant lowering ("if you have X, turn to N; otherwise …"),
  seeded numbering under anti-spoiler constraints (start=1, linked and
  variant and ending sections non-adjacent; best-effort + warnings when
  unsatisfiable — the 7-passage golden provably cannot satisfy all
  three families, verified by brute force), Typst layout (title,
  how-to-play, codeword log, sections, codex appendix, titles-only
  ending index) compiled to PDF in-process via typst-py (CI-hermetic),
  and a paper-specific lint (turn-to resolution, codeword granted
  before every test, no orphaned or dead section) that blocks export.
  `print_seed` persists in project.yaml on first export, like the IFID.
- `qf rerun <stage> [--keep <pass>]` (design doc 02 §3): checkpoints now
  persist each pass's accepted proposal; rerun rewinds stage artifacts
  (graph, prose, art, codex, voice) to the predecessor checkpoint while
  preserving the author's knobs (steering, vision edits — editing those
  is *why* you rerun), then re-runs the stage with kept passes
  re-applied without an LLM call; stale keeps fail loud. The runner's
  failed-apply restore now covers enrichment too (and the PR review
  caught that kept passes must restore on failure like live ones).
- HTML player gained the codex panel (design doc 04 §2); runtime JSON
  now ships codex + art (art entries only for briefs whose
  `art/images/<slug>.png` actually exists) and validates them in the
  round-trip check.
- The golden story is at stage `dress` with hand-authored enrichment
  (direction + 4 profiles, 3 briefs, 4 spoiler-safe codex entries,
  `CONFESSED` on the one gate-tested flag) and exports a complete
  14-page PDF; e2e now runs `--to dress` offline (36 ledger calls, one
  staged codex-review-fail/revise round). 203 tests total.

**M4 is complete.** FILL writes the prose and the story ships to its
first playable formats — `qf run --to fill` then `qf export html` puts
"The Keeper's Bargain" in a browser:

- FILL (`pipeline/stages/fill.py`) rides two small runner extensions:
  `StageImpl.passes` may be computed from the project (the work queue —
  one write pass per passage, reference-arc-first; the reference arc is
  seeded FILL-local scheduling state, `fill_seed` in project.yaml), and
  `PassSpec.review` runs a post-apply LLM judgment whose issues re-enter
  the ordinary repair loop — so "≤2 revision rounds, then halt: the
  structure is wrong, not the words" is `max_repairs`, not bespoke
  orchestration (mini-ADR A10)
- Per-passage write context: voice, beats, entities (base + overlays),
  flag statuses (certain / possible / foreclosed — gated residue
  passages count their gate as certain), shadows, window of
  already-written predecessor prose, convergence lookahead, choice
  labels, word budget (deterministically enforced at apply, repairable)
- Voice is a singleton `voice.yaml` (locked before any prose; skipped
  when author-provided); prose lives on the Passage node in memory and
  as sibling `prose/<slug>.md` files on disk; universal entity
  micro-details merge into base state through the mutation layer and
  never overwrite established facts
- Gate G5: prose presence (error), B5 word budget (advisory), voice
  presence (checked in the stage gate)
- First exports (`export/`): canonical runtime JSON with a
  self-contained round-trip validator (re-walks the exported document
  alone — I10/I13 at the export boundary), standalone HTML player
  (dependency-free, gated choices hidden, journey recap, one save
  slot), Twee 3 / SugarCube (entry `<<set>>` grants, `<<if>>`-guarded
  links, IFID persisted in project.yaml without rewriting the project);
  `qf export json|html|twee`, always round-trip-checked first
- The golden story now carries hand-authored prose (7 passages + voice,
  stage: fill) and was played **in an actual browser** (headless
  Chromium over the exported HTML) start to "The Long Watch" — the M4
  exit criterion
- e2e: `run --to fill` writes all 8 passages offline with one staged
  review-fail/revise round exercised (29 ledger calls), exports
  validate clean, and the runtime document alone replays all four
  journeys (132 tests total)

**M3 is complete** (PR #10). POLISH compiles the frozen beat DAG into the passage
graph, and the story is playable in the terminal with zero prose:

- Deterministic passage core (`pipeline/passages.py`): maximal-linear-run
  collapse (boundaries at forks/joins; flag-gated beats are singleton
  passages), choice topology with engine-computed endpoints, gates
  (target head's `requires_flags`) and grants (commit beats contained in
  the target), residue/false-branch splicing, convergence-need and
  long-run detection, I12-style active-flag computation. **The golden
  story is the oracle**: collapse and choice derivation reproduce its
  hand-authored passage layer exactly (tested).
- POLISH stage (`pipeline/stages/polish.py`), three passes: *finalize*
  (LLM writes flag-gated residue beats for every light-residue soft
  convergence — required, repair-checked — and may propose false-branch
  diamonds on long runs; skipped when nothing is needed), *passages*
  (engine fixes groups and choice wiring; LLM contributes only words:
  summaries, labels, ending titles, and variant summaries for
  heavy-residue convergences, which the engine wires behind disjoint
  gates, skipping variant choices whose gate is unholdable from a
  source — I10), *audit* (feasibility: LLM marks irrelevant flags;
  I12 enforces the cap on the rest)
- Gate G4 additions: `G4` label checks (non-empty; sibling duplicates
  only behind different gates, for variants) and residue coverage
  (light convergence → gated residue beat; heavy → variant passages)
- `qf play` (`play/engine.py` + `play/tui.py`): flag-tracking traversal
  with hidden-not-disabled gated choices (design doc 04 runtime
  semantics), rendering beat summaries pre-FILL; `--show-state` for
  structural debugging. The golden story plays end-to-end — four
  distinct journeys, gated counsel detour, both endings (tested
  headlessly and via the CLI)
- e2e: `run --to polish` on the Keeper's Bargain premise reaches POLISH
  with 0 gate errors — 8 passages (residue beats on both truth paths),
  two titled endings, four distinct playable journeys (109 tests total)

**M2 is complete** (PR #9). GROW weaves SEED's disconnected Y scaffolds into one
frozen beat DAG; `qf run --to grow` goes premise → four complete,
validated arcs, fully offline against recorded fixtures:

- Deterministic interleaving core (`pipeline/weave.py`): each dilemma
  becomes movable shared pre-commit units plus one atomic *resolve* unit
  (commits + post-commit chains — a reconverging diamond for soft, the
  terminal split for hard); constraints from `wraps`/`serial`, temporal
  hints (advisory: dropped with a report note if unsatisfiable), and
  intersection adjacency; bounded candidate enumeration; realization is
  a full PREDECESSOR edge-set recompute through the mutation layer
- GROW stage (`pipeline/stages/grow.py`), three passes: *intersections*
  (LLM proposes co-occurrence groups over shared pre-commit beats, which
  merge into one interleaving unit), *weave* (LLM only **chooses among**
  engine-valid interleavings; engine rewires the DAG and derives one
  flag per consequence, granted at the path's commit), *bridge* (engine
  finds entity-disjoint adjacencies; LLM writes structural bridge beats;
  pass skipped when there are no gaps — `PassSpec.skip_if`)
- Topology freezes on a clean gate G3 (`freeze.yaml` written); G3 gained
  `G3-FLAGS` (flag derivation total, error) and `B4` (beats per arc
  within scope, advisory like B3); presets carry `arc_beats_min/max`
- SEED now emits **temporal hints** and **flexibility annotations**
  (M1 deferral resolved): `Beat.temporal_hints` / `Beat.flexibility`,
  scaffold schema + prompt updated, hints validated against known
  dilemmas
- `qf simulate --all-arcs` (`play/simulate.py` + CLI): walks every
  computed arc with commit/flag/ending markers, exits non-zero on
  incomplete arcs; golden story and generated story both walk 4/4
  complete
- Golden story gained a natural intersection (`ledger-landing`), so I8
  disk I/O is exercised end-to-end
- e2e: `run --to grow` on the Keeper's Bargain premise reaches GROW with
  0 gate errors — 16 beats, single root, the soft dilemma converging on
  the shared `beat:the-offer` (90 tests total)
- Documentation hardening after the multi-hard episode: the original
  QuestFoundry source documents now live in `docs/heritage/` (reference-
  only, NG design docs remain the single authority) and design doc 01
  gained §9 "Where the mapping breaks" — the danger zones that stranded
  the original or nearly stranded NG

**M1 is complete** (PR #8). The front of the pipeline runs end-to-end,
fully offline against recorded fixtures:

- Uniform stage runner (`pipeline/runner.py`): context → render →
  complete → apply (repair ≤2, graph restored on failed applies) →
  gate → checkpoint (snapshot + report); `run_pipeline` chains stages
- LLM adapter (`llm/`): schema-validated structured output with retry-
  on-invalid, content-addressed cache, JSONL cost ledger; providers:
  Anthropic (thin SDK wrapper) and Mock (fixture replay/record)
- Stages DREAM, BRAINSTORM, SEED (`pipeline/stages/`) with Jinja2
  prompts; proposals carry content, the engine derives all structure
  (beat classes, impacts, `belongs_to`, intra-dilemma Y ordering)
- Gate G0 (vision completeness) added to the validator registry;
  `Stage.NEW` marks a scaffolded-but-unstarted project
- CLI: `qf run <stage>` / `qf run --to seed [--yes]`; project.yaml
  gained `llm:` (provider, role→model map) and `steering:` (per-stage
  author notes injected into prompts)
- e2e: `run --to seed` on the Keeper's Bargain premise via MockProvider
  reaches SEED with 0 gate errors (53 tests total)

**M0 is complete** (merged: PR #3). The foundation exists and is green:

- Typed models for all five layers with scope-preset budgets
  (`src/questfoundry/models/`)
- Story graph with a single validated write path
  (`graph/store.py` + `graph/mutations.py`)
- Invariants I1–I13 + budget checks wired to gates G1–G4, run
  cumulatively by project stage (`graph/validate.py`)
- Computed arcs, DAG walks, flag grant positions (`graph/queries.py`)
- YAML-per-node project format with lossless round-trip (`project/io.py`)
- CLI: `qf new / validate / status / graph` (`cli.py`)
- Golden story `examples/keepers-bargain/`: 2 dilemmas (1 hard, 1 soft),
  17 beats, 7 passages, 4 arcs; exercises freeze semantics, a post-freeze
  residue beat, and a flag-gated choice
- 32 tests + Hypothesis property test; CI runs ruff + pytest + golden gates

**Design docs** (`docs/design/00-05`) were merged in PR #1 and are
authoritative. Repo also carries `REVIEW.md` (automated-review norms,
PR #5) and this agent/doc infrastructure (PR #6).

## Milestones

- [x] **M0 — Skeleton & graph engine** (PR #3)
- [x] **M1 — Front of pipeline (DREAM → BRAINSTORM → SEED)** (PR #8)
- [x] **M2 — GROW** (the risk milestone: interleaving, intersections, freeze) (PR #9)
- [x] **M3 — POLISH & structural play** (`qf play` on beat summaries) (PR #10)
- [x] **M4 — FILL & first exports** (JSON, HTML player, Twee)
- [x] **M5 — DRESS, print gamebook, scope hardening** — DRESS/G6,
  `qf export pdf`, `qf rerun --keep` (PR #20); multi-hard weaving
  (PR #22); the live `medium`-scope run within budget (PR #23)
- [x] **M6 — Craft-corpus research** (added 2026-07-09; roadmap §M6,
  design docs 02 §1 and 03 §10) — engine (PR #30, plan: PR #29) + the
  live A/B exit run "The Lamplighter's Debt" (PR #31, live run 7)
- [x] **M7 — Illustrations** (added 2026-07-10, pulled up front at
  the author's call; roadmap §M7) — `qf illustrate` renders DRESS
  briefs via `image-generation-mcp` as a library (OpenAI/Gemini +
  hermetic placeholder); live exit run on both cloud providers
  (PR #33)
- [x] **M8 — Depth & scale** (added 2026-07-10; roadmap §M8) —
  deeper/tensored scaffolds, words-primary scale table (A19), presets
  recalibrated by structural simulation — plan PR #34, engine PR #35,
  tensored arms PR #36, live-run findings PR #37, exit run "Closed
  Circle" (live run 8, this PR)
- [ ] **M9 — Retrieval refinement** (added 2026-07-10; roadmap §M9) —
  reserved exemplar mechanism + standing-query shape
- [ ] **M10 — SHIP & the author loop** (added 2026-07-10; roadmap
  §M10) — SHIP stage with Twee lint, interactive checkpoint review,
  `qf simulate --random`

## Next up

> **`scene_type` structural modulation is BUILT (2026-07-13, PR #65)** —
> the kickoff below is done (see "Where we are"). Plan:
> [`docs/plans/scene-type-modulation.md`](plans/scene-type-modulation.md).
> The build landed the model field, GROW's *annotate* pass (populate at
> GROW pre-freeze, not POLISH — scene_type is intrinsic beat content), and
> FILL's per-passage band + per-beat intensity directive; 01 §10.3 is
> resolved. **The G4 pacing report is now also BUILT** (follow-up, same
> branch): advisory **B8** (`graph/validate.py check_b8_pacing`) — along
> each playthrough, a run of more than `PACING_MAX_SAME_INTENSITY` (=3, the
> golden's own ceiling) same-`scene_type` *beats* warns. Deliberately
> beat-level, not the design doc's original "passages": `passage_intensity`
> is a max, so passages read scene-heavy (the golden runs 4 scene passages
> but only 3 scene beats) — beats are the rhythm the reader feels and what
> heritage measured (02 G4 updated). Skips unannotated graphs (all-scene
> fallback is missing data, not flat pacing). **Remaining follow-ups**
> (deferred by design, in order): (1) the **`overwriting` guardrail** — the
> modulation-variance metric (plain baseline + a few peaks across
> passages) with compound-density > 15/1k as the one clean aggregate red
> flag (calibration in `reading-difficulty.md`); (2) **live validation on
> Ollama** (`gpt-oss:120b`, unbilled) — a targeted FILL re-run read by a
> human for whether prose now modulates; (3) the **scale recalibration**
> (measure-after: modulation shortens sequels, so `words_total`/`passages`
> and `tests/scale.py` may read slightly high). Historical hand-off spec:
> [`docs/plans/reading-difficulty.md`](plans/reading-difficulty.md)
> § "Hand-off spec — the `scene_type` modulation build" (the exemplar
> calibration there still governs the guardrail: FKGL is out;
> compound-density > 15/1k is the one
> clean aggregate flag; fragmentation-rate false-positives on good noir).

> **Predecessor context (2026-07-12): the prose reads too complex for a
> gamebook.** The pipeline now completes a weak-tier run **end to end**
> (FILL → DRESS; decision log below, and the preserved sample
> `examples/thaw-between/`), so *quality*, not completion, is the frontier.
> The LLM prose — and maybe the coined Voice — skews to high reading
> complexity: artful, but poor for a reader navigating choices. **The
> assessment is done, and its v1 thesis was corrected by an author read**
> ([`docs/plans/reading-difficulty.md`](plans/reading-difficulty.md) is now v2;
> decision log below). v1 measured FKGL and recommended a graded-readability
> finding; the author's ranking of the stories (**keepers + closed-circle
> best; cartographers + bubblegum near-unreadable**) **inverted** it — FKGL is
> *anti-correlated* (best story `closed-circle` = grade 18, worst
> `cartographers` = grade 2.5), and even the hand-authored golden reads
> "pretentious." The real fault is **over-stylization**: relentless,
> unmodulated prose (bubblegum's wall-to-wall aphorism) and fragmentation +
> coined-compound overload (cartographers: 42% tiny sentences, 4× compound
> density). The readable stories have a plain baseline, grammatical flow, and
> modulation (ornate ≠ unreadable — `closed-circle` is both). **The first fix
> is now BUILT** (2026-07-13, author-directed — the author's sharpening: *"the
> writer tried to apply the style to every paragraph, while it should apply to
> the whole story"*; decision log below): the generative lever landed as a
> prompt reframe — `fill_voice.j2` now frames the voice as characterizing the
> **whole story, not every paragraph** (plain baseline, restraint, clarity over
> atmosphere; `rhythm`/`imagery` reworded so they can't read as a per-sentence
> quota), and `fill_write.j2` gained a **"STYLE BELONGS TO THE STORY, NOT TO
> THIS PARAGRAPH"** directive (most prose plain and load-bearing; heightened
> register at a few charged moments; names the two measured failure modes —
> compound-per-clause, fragment-strobe — and states clarity outranks
> atmosphere). Design doc 01 §2 records the principle (style intensity is taste,
> the fence is the framing). 513 tests. **The first real exemplar has landed**
> (2026-07-13): the author supplied a published second-person gamebook (*ALBA*,
> ~172k words) as the target register. Measured, it **confirms the thesis
> outright** — FKGL 4.6 (statistically the same as "bad" `bubblegum`'s 4.8, so
> grade level is settled noise) but coined-compound density **1.7/1k** vs
> `cartographers`' 21.2 (a 12× gap — the cleanest discriminator), fragmentation
> a modest 28%. Its profile + craft traits are recorded in the plan as the north
> star and the first calibration for the `overwriting` finding. **A second
> exemplar confirms it** (*Pirates of the Splintered Isles*, ~157k words): FKGL
> 5.9, compound density **3.0/1k**, fragmentation 20% — two independent published
> gamebooks now replicate the profile. **Then two author cautions + a
> genre-diverse study refined the picture (2026-07-13):** (a) the two gamebooks
> are the **same genre**, so eight **choice-based** Twine works (the right medium)
> across horror/noir/literary/sci-fi/romance/crime were measured (Grimnoir
> independently re-verified). Result: *FKGL is noise* is **reconfirmed and even
> inverted** (XYZZY-winning horror `Bogeyman` FKGL 4.3 = "bad" bubblegum; worst
> amateur work highest at 9.6); *compound density > 15/1k* is a **robust red flag**
> (zero false positives across six genres; only `cartographers` trips it); but
> *fragmentation alone is NOT safe* — good noir (Grimnoir 49%) and good
> minimalist-literary (44%) sit in the bad band, so it must not gate alone. The
> real lesson (author): the exemplars are about **how style distributes across the
> partial snippets**, not the medium — so the guardrail should measure *modulation*
> (a plain baseline with a few peaks across passages), not a per-corpus mean. (b) I
> had claimed an "unaddressed upstream vector" (beats arrive over-stylized); that
> was **wrong and is retracted** — `bubblegum` is a stale M5 artifact, and the
> current compiler already enforces plain briefs via `_summary_brief.j2` (SEED
> scaffold, GROW bridge/contextualize, POLISH passages/finalize: *"a summary is
> never the page… name a mood instead of performing it"*). So the FILL reframe in
> this PR is the piece that was missing, not the first of two. **The modulation
> mechanism has a name, and NG lost it** (author, 2026-07-13): heritage
> distributed prose intensity *structurally* via beat annotations — `scene_type`
> (Swain scene/sequel: FILL derives "prose intensity / target length" from it) and
> `narrative_function`. Design doc 01 §10.3 explicitly **kept `scene_type`
> (scene/sequel) + `exit_mood`**, but **neither was ever built** (0 code
> references; POLISH notes "pacing report stays deferred with scene_type") — a
> doc↔code divergence, and exactly the "lost in translation" the author named. The
> reading-difficulty gap is the "demonstrable FILL quality gap" §10.3 said would
> justify (re)adding it. So the primary modulation lever should be **structural**
> — implement `scene_type` as a beat annotation driving FILL's per-passage
> intensity + word band — with the `overwriting` metric demoted to a guardrail
> (details in the plan). **Still open (follow-ups):** the `scene_type`-annotation
> modulation build (frontier, milestone-sized, gated on author go-ahead); the
> `overwriting` guardrail after; live validation on Ollama. **NB — item 1 below ("a
> completing FILL run") is now ACHIEVED:** the compounding review/rework chain
> (#57→#58→#59→#60→#61) carried `gpt-oss:120b` through DRESS, codex review
> included.

1. **A completing FILL run — the recurrence read is still open, and the
   prompt fixes need live validation** (2026-07-12 decision log has the
   findings): #1a ran but both stories died at FILL review-exhaustion, so
   (a) the scaled recurrence verdict is unproven (13 passages can't
   discriminate — need ~100), and (b) the two prompt-quality fixes
   (`fill_review.j2` rule-text matching, `fill_write.j2` POV
   externalization) are *designed against* the live failures but not yet
   validated. **Do this within the new budget discipline** (open items,
   `AGENTS.md` §"Live-run budget discipline"): validate on **Ollama**
   (`gpt-oss:120b`, unbilled) first — a targeted FILL of just the
   passages that failed, resumed from a checkpoint, not a fresh
   end-to-end run — and spend a billed strong-map call only on the one
   thing the weak tier provably can't answer. Note the review loop's
   brittleness: even Gemini exhausted two rounds on one hard passage
   (group-13).
2. **Review-contract redesign — BUILT; live validation is what's left**
   (`docs/plans/review-contract.md`, signed off + implemented 2026-07-12;
   `pipeline/review.py`). The full `gpt-oss:120b` run drove it: the binary
   `pass/fail` + free-text `issues` verdict false-positive-halts the
   producer in three successive shapes (rule fabrication → voice-ban
   footgun → Rule-2 over-literalism), a class over **every** review pass,
   not prose only. Now a structured multi-axis finding schema (rule /
   assessment / confidence / quote / reason / recovery_action) shared by
   FILL prose + DRESS codex review; the engine gates only proceed-vs-rework
   on confident objective defects; the producer receives full-fidelity
   findings and decides (a `warn`/low-confidence finding is weighed, not
   mandated). **Open**: a gpt-oss:120b run to confirm the weak tier stops
   false-positive-halting FILL and, for the first time, exercises DRESS
   codex review under the contract (unbilled — budget discipline permits a
   full run here).
3. **Finish the error-message audit** (`docs/plans/error-message-audit.md`):
   Class 2 (store `KeyError` crash class) is fixed; Class 1 (raw-exception
   dumps, `f"invalid X: {e}"`) is graded acceptable-but-improvable and
   deferred. Sweep it when next in those files; always diagnose
   prompt/message quality first (`AGENTS.md`).
4. **M9 — retrieval refinement** (roadmap §M9): the reserved exemplar
   mechanism + standing-query shape rework, both from live run 7's
   findings (exemplar leak in the decision log; standing-query
   boilerplate in the open items).
5. **M10 — SHIP & the author loop** (roadmap §M10): the SHIP stage
   with the Twee lint, real interactive checkpoint review behind
   `qf run --yes`, `qf simulate --random N`, and stage-level
   auto-resume (per-pass progress reporting was pulled forward and is
   built — 2026-07-12, decision log).

## Known deferrals / open items

- ~~**`scene_type` / `exit_mood` beat annotations: an honest YAGNI deferral whose
  trigger has now fired**~~ **`scene_type` is now BUILT** (2026-07-13, PR #65; the
  reading-difficulty / over-stylization gap was the "demonstrable FILL quality gap"
  01 §10.3 anticipated). `scene_type` (scene/sequel/micro_beat) is the modulation
  carrier: an intrinsic beat property GROW's *annotate* pass writes pre-freeze and
  FILL reads for per-passage word band + per-beat intensity; §10.3's wording is
  updated to match, and a "Beat annotations" subsection was added to 01. The G4
  pacing report (02 §3) is now buildable on that signal but stays deferred as a
  follow-up (see Next up). **`exit_mood` remains deferred** — it is not the
  intensity lever; add it only when a demonstrated need appears (the same YAGNI
  discipline).

- **Live-run budget discipline is now a working norm** (author call,
  2026-07-12, after a session that exhausted the token budget on repeated
  full pipeline runs): billed API keys (Anthropic/Gemini/OpenAI) are
  scarce and spend-capped — the Claude Max / OpenAI subscriptions are not
  available to the pipeline. Never run a whole pipeline "just to see if it
  finishes"; every billed call must serve a stated need, on the smallest
  run that answers it, and exploration/reproduction goes on **Ollama**
  (unbilled). Codified in `AGENTS.md` §"Live-run budget discipline".

- **Unexplored: subagents as an unbilled Claude for pipeline calls**
  (author idea, 2026-07-12: "in theory your own subagents are identical —
  you can experiment"). A dev-session's own Claude Code subagents may be a
  way to drive the pipeline's LLM calls without a pay-per-credit key. Not
  attempted this session (would itself cost tokens); worth a *targeted*
  spike — can a provider adapter route `complete()` through a subagent,
  and does it preserve schema-validation + determinism? Design it small.

- ~~Arc-worthiness scope is narrower than the heritage ontology~~
  **Settled by the author** (2026-07-12, decision log): every retained
  entity is arc-eligible — a character without an arc is an extra, a
  location a backdrop, an object a mcguffin, a faction a link.
  `_arc_entities` widened, prompt carries the doctrine and the
  per-category flavors, golden lighthouse carries an atmosphere arc.
  Still derived, never stored: `arc_line`/`arc_type` (unchanged — take
  storage only with a demonstrated gap).

- ~~**Ollama backend live validation is pending**~~ **Validated live**
  (2026-07-11, on `athena.int.liesdonk.nl:11434` — RTX 4060/8GB + 128GB;
  daemon logged in to ollama.com; the decision-log entry below is the
  record). **The A20 mechanism is confirmed on both tiers; the blocker
  to a full local story is two provider-agnostic prompt gaps, not the
  backend.** Checklist results:
  1. `uv run pytest -q` → **403 passed** on this host; `ollama>=0.6` SDK
     present, lazy import works.
  2. Three model maps ran `--to seed` on one shared micro premise (a
     canal lockkeeper + a stranger's coat). **DREAM→SEED completed on
     none of them** — and that is the experiment's result, per the
     "prompts are the suspect if repair burn is high" contract:
     - `llama3.1:8b` (GPU): failed BRAINSTORM `populate`, exhausted
       repairs — emitted **underscore slugs** (`location:canal_town`);
       `format` grammar enforces the `kind:slug` colon but not
       kebab-case *within* the slug (GBNF ignores string `pattern`), and
       the 8B never corrected. Model-tier weakness.
     - `qwen3.5:35b-a3b` (CPU, 11m40s): **passed** BRAINSTORM (kebab
       clean, 2 attempts) but failed SEED `triage` — `explores` named an
       answer *slug* it invented, not an existing answer *id*.
     - `gpt-oss:120b-cloud` (~84s): **passed** BRAINSTORM (kebab clean, 1
       attempt), failed SEED `triage` the **identical** way.
     Two unrelated strong families (one local, one cloud) converge on
     the same triage dangling-reference; Gemini-pro/Claude-opus cleared
     it in runs 7/8 → a **model-capability threshold on an
     under-specified prompt**, exactly the class A11's enum discipline
     governs. → filed as issue #40 (pin `explores` to an enum of real
     answer ids; fixes every provider and lets Ollama's grammar enforce
     it for free). **Built** (same day): `triage_proposal_schema` pins
     the enum per project at pass-build time — see "Where we are".
  3. **Cloud `format` question — answered:** `gpt-oss:120b-cloud`
     **accepts** `format` cleanly (valid JSON, no ResponseError; a raw
     `_generate_once` probe and a full BRAINSTORM run both confirm) — we
     are in the "call succeeds, schema satisfied" world, the
     reject→unconstrained fallback is **not triggered**. `qwen3.5:cloud`
     is paywalled (403 "requires a subscription" — a *subscription* 403,
     not a `format` rejection; the fallback guard correctly ignores it),
     so its handling was untestable. **Fallback verdict: unexercised,
     NOT proven dead** (only one accessible cloud family) — **kept** as
     cheap insurance; revisit if a cloud family that rejects `format`
     turns up. Left it in place; did not delete.
  4. `OllamaContextError`: `num_ctx=2048` + an over-long prompt raised
     the exact "raise llm.num_ctx" message — fail-loud, no silent
     truncation. ✅
  5. ~~No `--to dress` completed on a local model (triage gap above)~~
     **SEED now completes on a cloud model.** Re-confirmed 2026-07-11
     from this hosted environment (which supplies `OLLAMA_API_KEY` for
     the cloud tier but no local daemon): a fresh micro premise ran
     `--to seed` on `gpt-oss:120b` cloud. The `explores` enum (#40)
     cleared on the first attempt — then triage failed the *identical*
     dangling-reference way on `locked[].dilemma` (the model named
     `ice-watcher`, not `dilemma:ice-watcher`). Pinned that sibling to a
     dilemma-id enum (`triage_proposal_schema` now takes `dilemma_ids`);
     the re-run passed SEED first attempt (`locked: dilemma:hand-locket`,
     valid and prefixed). `qwen3.5:397b` cloud is paywalled (403
     subscription), so `gpt-oss:120b` stood in — the same family that
     first exposed #40. Continuing the run then hit the *identical*
     dangling-reference class one stage deeper (POLISH finalize named an
     invented `world`), which motivated pinning the whole class
     pipeline-wide (decision log; `pipeline/refpin.py`). **Reference-pinning
     is validated live through GROW:** a fresh `--to dress` run cleared
     every reference-heavy stage on `gpt-oss:120b` cloud — DREAM,
     BRAINSTORM, SEED (triage/scaffold/order all first-attempt), and GROW
     (intersections, weave, flag derivation, bridges). **A follow-up
     effort (the DRESS-chase branch) then drove the weak tier deeper.** The
     POLISH finalize failure turned out to be a *real latent engine bug*,
     not a model quirk: `_finalize_apply` inserted residue first and then
     recomputed the long runs it validates false branches against, so a
     beat the model was correctly shown inside a long run (and the pinned
     `before`/`after` enum accepted) could be evicted by residue splicing at
     a neighbouring convergence — the enum said valid, the post-residue
     apply said no. Both additions target the frozen pre-finalize topology,
     so finalize now splices false branches against the pristine long runs
     *before* residue, and **POLISH clears live** (the exact
     `beat:spirit-post-2-burn -> bridge:gap-6` diamond that failed now
     applies). FILL then surfaced three genuine weak-tier prose gaps, each
     diagnosed against the graph before deciding writer-vs-reviewer fault
     and each a firmer restatement of an existing contract (strong models
     already hold them): (1) tense as an explicit directive handling
     narrated-past events (Rule 1); (2) POSSIBLE-state honesty stated
     plainly under WORLD STATE, so the writer stops asserting path-dependent
     flags as fact to fill a scene (Rule 4); (3) the review's Rule 2
     sharpened so a weak reviewer stops laundering dropped *scenery*
     (time-of-day, light) as a missing *event*. These carry `gpt-oss:120b`
     from 0 to several clean FILL passages. **Still open:** a full clean
     DRESS on `gpt-oss:120b` is gated by residual weak-tier prose
     inconsistency — the writer stochastically re-asserts possible-state
     content on the hardest passages (cosmetic all-possible-flag cadence
     arms), clearing Rule 4 in two rounds on some, exhausting on others.
     That is the prose-quality-at-scale milestone (next-up #1: input-role
     framing, register rules, a rolling story-so-far summary, character-arc
     metadata), not a prompt tweak — so no cloud example is preserved yet
     and the chase stopped at diminishing returns rather than grinding
     expensive re-runs. The companion `max_length=0` fix (forbid
     `false_branches` when no long run exists) still stands. The local
     `qwen3.5`-class confirmation still wants a run when a daemon host is
     reachable.

- ~~The craft corpus should live (curated) in the repo~~ **Vendored**
  (2026-07-12, author-directed — see "Where we are" and the decision
  log): `corpus/interactive-fiction/` carries the eight non-exemplar
  clusters (55 notes, byte-faithful from the author's vault;
  `corpus/README.md` records scope, provenance, and the
  fingerprint-as-input contract). `style-exemplars` stays out until
  M9's reserved exemplar mechanism exists to consume it. Curation
  (adding/trimming notes) remains the author's ongoing pass.

- **Transient transport failures kill the run** (author call, live
  run 8): a provider disconnect exits `qf run` even though the A16
  ledger makes resumption free — run 8 needed four manual re-invokes.
  Mitigated in-run: the Gemini provider streams and retries transport
  drops and 5xx server errors per call (3 attempts, linear backoff;
  4xx stays fatal), which absorbs most transience; a sustained failure
  still exits the run.
  Stage-level auto-resume owned by M10 (roadmap §M10, run resilience).
- ~~Long runs report no progress~~ **Built, pulled forward from M10**
  (2026-07-12, author call — decision log): `qf run`/`qf rerun` emit a
  flushed one-line heartbeat per pass on stderr (pass m/n, attempts,
  running ledger totals — the stderr choice is what survives piping),
  and `qf status` reads spend from the cost ledger and interrupted-run
  state from the A16 in-flight ledger. Live proof on the next long
  run; stage-level auto-resume stays with M10.

- ~~A Gemini provider is unbuilt~~ **Built and validated** (PR #18):
  `llm/providers/gemini.py` over the google-genai SDK, wired into the
  CLI (`llm.provider: gemini`; the SDK reads `GEMINI_API_KEY` itself).
  First Gemini-driven generation ran 2026-07-08 — results in the
  "live run 4" decision-log entry. All three provider families
  (Anthropic, OpenAI, Gemini) have now produced a complete story.

- ~~Crash-resume replay of FILL was leaky~~ **Both halves are now
  fixed.** The cache half (byte-stable prompts) was fixed 2026-07-08,
  and `save_project` pruning closed the stale-file leak (PR #23). The
  artifact half is resolved by the **in-flight proposal ledger**
  (2026-07-10, mini-ADR A16 — see the decision log): every accepted
  pass journals its proposal to `inflight/<stage>/` as it lands, and
  re-entering an interrupted stage replays those passes through the
  kept-pass machinery with zero LLM calls, independent of the cache.
  Prose files still reach the working tree only at the gate-passing
  checkpoint — the ledger is not a checkpoint, so 02's semantics hold.
  Residual (recorded, accepted): a crash *inside* `_checkpoint` itself
  can leave a partial snapshot — pre-existing, unrelated to the
  ledger, and recoverable by rerunning the stage.

- ~~Prompt framing: early stages claim certainty they don't have~~
  **Addressed** (calibration batch, see decision log): DREAM's prompt
  now states that a vision is texture and intent, never countable
  coverage; BRAINSTORM's states it supplies ingredients for triage and
  that every entity must anchor a dilemma. Validated on the next live
  run.

- ~~Established entity attributes don't reliably survive FILL~~
  **Addressed** (calibration batch): `Entity.pronouns` is an explicit
  field, BRAINSTORM fills it, FILL's write context renders it
  prominently ("PRONOUNS: they/them, exactly"), and the FILL review
  gained numbered rule 6 — pronoun contradiction, quote the offending
  text — the checkable, taste-free shape the review contract demands.
  Validated on the next live run.

- ~~Medium preset ranges don't match what the pipeline builds~~
  **Recalibrated** (calibration batch, author-confirmed: the original
  numbers were *beat* counts from the one-beat-one-passage era — see
  decision log). Passage bands now state structural yield (medium
  25–40; others extrapolated pending runs), medium's word cap is 650,
  and the *feel* of size has its own advisory: **B6, words traversed
  per genuine choice per arc** (target 250–800, from the craft
  corpus's 300–600 "balanced agency" band). The Bubblegum Alibi reads
  at ~1206 — the cadence gap is real and now measured. POLISH's
  false-branch pass is cadence-targeted to close it (diamond every
  3–5 beats of a choice-less run, arms of 1–2 beats). Deeper scaffolds
  are the structural fix — next item.

- ~~Multi-hard weaving is not implemented~~ **Built** (PR #22) **and
  exercised live** (PR #23, the Bubblegum Alibi): hard forks nest,
  every unit after the first fork is instantiated per world, endings
  multiply, and the tensor model (design doc 01 §5) is realized in
  `weave.realize` + GROW's contextualize pass — all of it ran against
  a real model with the contextualize prompt performing first-shot.
- **M2 intersections group shared pre-commit beats only.** Intersections
  involving exclusive (post-commit) beats are structurally meaningful
  but interact with arc membership in ways the spine model doesn't
  cover; revisit when a generated story demands one. Same for temporal
  hints: only hints on shared beats are consumed (a hint on a beat
  inside an atomic fork unit has nothing to move).
- ~~The weave's 64-candidate spread heuristic needed watching at
  scale~~ **Measured and fixed in M8 PR-1, exercised live in run 8**:
  at deep-scope unit counts plain lexicographic DFS returned 64
  near-identical orders (63 units: all candidates shared a
  12-position prefix); enumeration now fair-splits when the plain
  sample is truncated inside one subtree, recorded stories keep plain
  enumeration byte-stable, and run 8's weave chose among genuinely
  distinct orders at 40+ units and realized first-shot.
- ~~Locked dilemmas (heritage's "unexplored dilemmas") are the designed
  next structural effort~~ **Built** (2026-07-10, this PR — see "Where
  we are" and the decision-log entry): overgeneration + locked
  dispositions + fork-less weave units + I3/I6/G3-FLAGS refinements,
  and richer residue (per-path arms, followup beats, same-gate
  collapse). ~~Still deferred from that item: tensoring a shape inside
  a diamond arm~~ **Built as M8 PR-1b** (tensored residue arms — see
  the decision-log entry); **cosmetic flags on locked storylines**
  remain unbuilt like all cosmetic grants (below).
- **The G4 pacing report is deferred** (design doc 02 lists it: "no >N
  consecutive same-intensity passages"). It needs the `scene_type`
  annotation, which per design doc 01 §10 arrives only when a FILL
  quality gap demonstrably calls for it — implement both together in
  M4+ if the gap shows.
- ~~Character-arc metadata remains unbuilt~~ **Built** (2026-07-11,
  the prose-quality effort — see "Where we are"): POLISH's `arcs` pass
  drafts per-entity arcs (begins / pivots anchored to beats / ends per
  path), the mutation layer holds them stable-once-set, G4 fails
  dangling references loud, and FILL renders the per-passage arc
  position. The deferral (design doc 01 §10.3's "when a FILL quality
  gap demonstrably calls for it") resolved exactly as designed —
  shaped by its consumer.
- ~~The HTML player has no codex panel yet~~ **Built** with DRESS
  (PR #20): a `<details>` codex panel, server-rendered, omitted when no
  entries exist.
- ~~Image generation is unbuilt~~ **Built and exercised live as M7**
  (PR #33; decision log): `qf illustrate` renders briefs via
  `image-generation-mcp` as a Python library, with the heritage design
  (entity visual fragments for consistency, sample-first cost gate)
  engine-side. Still deferred from the milestone's own scope:
  **style-reference conditioning** (feeding a rendered image back as a
  reference for the rest of the batch — the documented escalation if
  samples show character drift). The live run showed *style* drift,
  not character drift: 1 of 7 Gemini renders went photographic against
  the painterly direction, while gpt-image-2 followed the direction
  closely — watch it, wire the reference path when a run demands it.
- **Derived fallback codewords may contain digits** (slugs allow them;
  `^[A-Z]{3,12}$` binds only DRESS-stored codewords). Cosmetic at
  worst — a print warning already tells authors to run DRESS.
- ~~M6's retrieval library is an external bet~~ **Largely retired at
  planning time** (2026-07-10 decision-log entry): as of 3.1.0 the
  library ships a documented Python API (`Vault` facade with
  reader/index facets, hybrid `search(query, mode, folder)`, a public
  `EmbeddingProvider` ABC with a local pinned `FastEmbedProvider`, an
  `[embeddings]` extra). The phase-0 spike then passed everything
  (PR #30 decision-log entry): hybrid ranking deterministic across
  repeats and rebuilds, warm-cache embeddings fully offline, custom
  provider accepted — the item is closed.
- **Standing queries retrieve boilerplate** (live run 7's digests,
  observed post-merge): verbatim vision fields make poor search
  strings — the 30-word tone sentence pulled the same
  audience-targeting age-band notes into the GROW and FILL digests,
  while the librarian's condensed queries were consistently on-topic.
  The value split is librarian ≫ standing today. Owned by M9
  (roadmap §M9): condense standing queries to keyword form or
  rebalance toward the librarian.
- **Twee prose mapping is bounded and unlinted** — the lint step that
  flags constructs that don't survive SugarCube conversion arrives with
  SHIP (design doc 04 §3, roadmap §M10).
- **False branches carry no cosmetic flags yet** (choice-feel diamonds
  only). The flag machinery exists (`FlagSource.COSMETIC`); wire grants
  when a residue beat or print codeword actually wants one.
- **`qf simulate --random N` (false-branch/detour coverage, design doc
  04 §5) is not implemented** — `--all-arcs` covers dilemma
  combinations; random walks become interesting once false branches
  actually occur in generated stories.
- Fixture passage count (7) is below the `micro` target (15–25); B3 is
  an advisory warning by design — as is B4 (arc beat count), whose
  preset ranges are uncalibrated until generated stories exist.
- `export/` package and the rest of `play/` (engine, TUI) arrive with
  M3–M4; `play/simulate.py` landed early because M2's exit criterion
  needs it.
- ~~Live-provider recording is wired but unexercised~~ **Exercised**:
  the first live generation ran on 2026-07-08 (OpenAI gpt-5 architect/
  writer + gpt-4.1-mini utility via the new `providers/openai.py`) and
  produced a complete, gate-clean, export-valid story — results, three
  hardening lessons, and budget data in the decision log. Anthropic
  live runs work via the `QF_ANTHROPIC_API_KEY` passthrough (hosted
  environments strip the reserved `ANTHROPIC_API_KEY` name); billing
  was resolved 2026-07-08 and the first Claude-driven generation ran
  the same day — results in the "live run 3" decision-log entry.
- **`qf run --yes` is a stub.** Interactive checkpoint pauses (design doc
  02 §3) are not implemented; batch is currently the only mode. The flag
  is accepted for forward compatibility. Wire real interactive review
  when the review UX milestone lands.

## Decision log

- **2026-07-13 (reading-difficulty fix #1 — over-stylization is per-paragraph
  style saturation; prompt reframe, author-directed):** The author greenlit the
  fix and sharpened the root cause: *"the writer tried to apply the style to
  every paragraph, while it should apply to the whole story."* That is exactly
  what the assessment measured — the readable stories keep a plain, load-bearing
  baseline and surface style at a few charged moments; the unreadable ones max
  every sentence. The lever is generative (the fence is framing — style
  intensity is taste, not a gate; design doc 01 §2), so it landed as a
  two-prompt reframe, no schema/engine change: (1) `fill_voice.j2` gained a
  **"THE VOICE CHARACTERIZES THE WHOLE STORY, NOT EVERY PARAGRAPH"** principle
  (plain baseline, restraint, clarity over atmosphere) and reworded `rhythm`
  (a default to depart from, not a maximal pattern) and `imagery` (spent at a
  few moments, "never a coat of paint for every sentence"); (2) `fill_write.j2`
  gained a **"STYLE BELONGS TO THE STORY, NOT TO THIS PARAGRAPH"** directive —
  most prose plain and load-bearing with a clear grammatical spine, the
  heightened register at only a few charged moments (opening image / the turn /
  last line), and it names the two failure modes the assessment found
  (a fresh metaphor or coined compound *per clause*; a *strobe of short
  fragments*) plus "clarity outranks atmosphere." Design doc 01 §2 records the
  principle and the FKGL-inversion finding. Deliberately **not** touched: the
  review — adding an over-stylization *rule* would reopen the false-positive-halt
  class the review-contract redesign fixed (the review keeps "TASTE IS A WARN,
  NEVER A FAIL," with figurative language named as taste). Tests: two new
  prompt-source assertions; 513 pass, ruff clean, golden 0/0. The FILL e2e
  fixtures did **not** need re-recording — MockProvider replays in call order,
  not by prompt hash, so wording changes don't shift the sequence. **Follow-ups:**
  Ollama live validation; the author's real-gamebook exemplars (in flight) as
  the target-register north star; and the deterministic `overwriting` guardrail
  (fragmentation + novelty density; FKGL stays out) once the exemplars set its
  bands.

- **2026-07-12 (reading-difficulty assessment — v1 thesis WRONG, corrected by
  an author read; plan doc
  [`docs/plans/reading-difficulty.md`](plans/reading-difficulty.md) is now v2):**
  v1 measured FKGL/paragraph-density, called the prose too *complex*, and
  recommended a graded-FKGL readability finding + a literary↔accessible Vision
  knob. The author read the stories and **inverted it**: *"none of the examples
  is particularly okay… keepers + closed-circle best; cartographers + bubblegum
  near unreadable,"* and the hand-authored golden itself "reads difficult and
  pretentious." Checked against the metrics, **FKGL is anti-correlated with the
  author's judgment**: best story `closed-circle` = FKGL 18.4 (graduate), worst
  `cartographers` = FKGL 2.5 (early reader). A graded-FKGL finding would have
  flagged the best prose and passed the worst. **The real fault is
  over-stylization, not reading level:** (1) relentless, unmodulated prose —
  every sentence strains for effect, no plain connective baseline (`bubblegum`
  is wall-to-wall aphorism; the golden's "pretentious" is the mild form); (2)
  fragmentation + novelty overload — `cartographers` runs 42% ≤6-word sentences
  and ~21 coined compounds/1k words (4× the others), a strobe of fragments with
  a fresh metaphor per phrase and no plain prose to rest on. The **readable**
  stories share a clear grammatical spine + connective flow, modulation (plain
  valleys between heightened peaks), story-advancing concreteness, and ornament
  used with restraint — `closed-circle` proves ornate ≠ unreadable. Corpus
  backs the corrected target (clarity over atmosphere: prose_patterns:52; "paint
  a picture without overwriting": exposition:74; Clarity/Comprehension bar).
  **Root cause:** the Voice pass invites maximalism (no restraint/modulation
  ask — `thaw-between`'s rhythm asks for a "longer, layered" sentence every
  other line), the write pass sets no ceiling on figuration frequency, no pass
  rewards modulation/clarity, and the golden over-writes too so the pipeline has
  **no clean target-register exemplar** to imitate. **Corrected lever:**
  generative-first — `fill_voice.j2` restraint/modulation directive +
  `fill_write.j2` plain-baseline/clarity rule — plus a deterministic
  `overwriting` finding on the signals that *tracked* the author (fragmentation
  ratio, novelty density), **FKGL dropped from the lever**, and a companion task
  to establish a real target-register exemplar (human-read validation, not a
  metric). Gated on the author confirming the diagnosis + exemplar approach
  (plan's *Open decisions*). No billed calls spent. **Lesson (AGENTS.md prompt-
  quality spirit): a metric that looks objective can be anti-correlated with the
  actual goal — read the artifact, don't trust the number.**

- **2026-07-12 (word budget → a graded review finding, not a hard apply gate;
  author-directed):** The rework-convergence run reached pass 21/22 but the
  *ending* (group-9) failed the word budget: gpt-oss:120b writes its 4-beat
  ending in ~114–119 words vs a 120 floor, consistently. Two things drove the
  fix. **(1) We asked the writer why** (we never had — the adapter discards its
  reasoning): forced to explain + plan the expansion, it cleared the floor 3/3
  (~200 words), and named the real cause — *"the voice demands long sentences
  AND short jolts while staying strictly in past tense; expanding without
  slipping tense or filler is hard."* So the "explain your fix" lever
  generalizes to mechanical repairs. **(2) The author's architecture call**:
  fold the mechanical check into the **same findings list** the reviewer
  produces, with **confidence graded by distance from target** — because "not
  making the target with really good reasons is better than bad prose or a
  forced failure." Implemented: the word-budget check moved out of
  `_write_apply_for` (no longer a hard `ApplyError`) into
  `_word_budget_finding`, a `word_budget` finding merged into the review's
  findings and gated by the same `evaluate_review` (a confident mechanical
  defect overrides an LLM `approved`; a near-miss is a low-confidence finding
  the engine accepts). Confidence bands: inside → clean; slack margin → warn;
  beyond slack low/medium/high by distance (one tunable knob). The write prompt
  now frames every rejection uniformly (finding OR label-less mechanical) and,
  for a length finding, makes the writer name which beat to deepen (not pad).
  511 tests, ruff clean, golden 0/0. **VALIDATED (gpt-oss:120b, unbilled): the
  first complete weak-tier FILL → DRESS run.** group-9 cleared in 3 attempts —
  the writer *expanded* the ending from ~114 to **169 words** (in band; the
  rejected-draft feedback + per-finding accounting made it converge rather than
  re-roll short, and the graded finding made converging safe instead of a hard
  fail). **`fill: ok`**, then **`dress: ok`** — direction, briefs, and for the
  first time ever the **codex pass and its review ran live and clean** (5
  entries), the one stage never exercised on a weak tier across this whole
  effort. The compounding chain that got here: review contract (#57) → verdict
  (#58) → micro-detail redesign cleared group-3 (#59) → rework convergence
  cleared group-1/2 (#60) → word-budget-as-finding cleared the group-9 ending
  (#61). Still deferred: beat over-choreography (never needed — the levers
  carried it). Remaining before a preserved cloud example: SHIP (M10) and a
  read of the produced prose quality at length.

- **2026-07-12 (rework convergence — writer sees its rejected draft + must
  respond per finding; the adapter is stateless, author-directed):** The
  micro-detail validation run cleared the old blocker but died at
  `write:group-1` on `beat_infidelity` — the writer never rendered "steps back
  *toward* the locked log" across two rounds. Diagnosed empirically (exact
  group-1 prompt, `gpt-oss:120b`, N=4): the recovery_action is explicit enough
  that a single clean finding is fixed every time, but under the *real*
  multi-finding load (beat + 2× state_dishonesty, as round-2 carried) the plain
  baseline fixes the beat only **2/4** and never both findings, while forcing a
  **per-finding response lifts it to 4/4**. Root cause named: the LLM adapter
  is **stateless** — `complete()` is one `provider.generate(user_prompt)` per
  call with no assistant history, and across rework rounds the runner re-renders
  a fresh prompt carrying only the accumulated findings; the writer never sees
  its prior draft or its reasoning tokens (gpt-oss's thinking is generated then
  discarded). So it re-derives blind and re-lands a losing draft. Two writer
  levers built (FILL-local, no runner change): (1) a per-passage box carries the
  **rejected draft** from the review of one round into the write prompt of the
  next ("revise it, don't repeat it"); (2) `WriteProposal.revision_notes`
  (list of `{finding, how_addressed}`) — on a rework the writer states the
  change it made per finding, and `fill_review.j2` has the reviewer **verify
  each claim against the prose** (a claimed-but-absent fix is itself a defect).
  `revision_notes` are reviewer-facing only — not applied, so replay stays
  deterministic. **Validated live (gpt-oss:120b): FILL went from dying at
  group-1 to reaching pass 21/22** — every review-based rework converged
  (group-1 cleared, group-2 reworked-and-passed). It then died at `write:group-9`
  on a *mechanical* word-budget apply failure (114 words vs a 150-550 band),
  which exposed that the rejected draft was fed forward only on *review*
  rejections, not *apply* ones. Fixed in the same PR: the draft is now stashed
  in `_write_apply_for` **before any check raises**, so an apply-stage rejection
  (word budget, echo) shows the writer its draft to expand/edit rather than
  re-derive blind. 509 tests, ruff clean, golden 0/0. **Open**: rerun to confirm
  group-9 now converges into DRESS codex review. Deferred: beat
  over-choreography (a GROW/POLISH granularity question) — only if the writer
  levers prove insufficient.

- **2026-07-12 (micro-detail system redesigned — it fired too often for
  *adding*, author-directed):** The live gpt-oss:120b run's FILL death
  (`write:group-3`, `object:old-lens already has 'material'`) was *not* a weak
  model — gpt-oss:120b saw old-lens's keys in its prompt and re-keyed anyway,
  because the micro-detail feature *solicited* a detail every scene ("up to 2")
  and a well-specified recurring hero-object (The Great Lens) has no genuinely
  new universal fact to offer by scene 4, so the model filled the invitation
  with a re-observation the single-assignment guard then hard-failed — killing
  the *required* prose over an *optional* annotation. Author call: the feature
  is still good, but (1) **at most one** detail, framed as the exception ("you
  are not expected to add — most passages add none"), so the model stops
  feeling obliged; (2) a detail may **update/extend** a listed fact (re-use its
  key) as long as it does not contradict — the single-assignment *hard* guard
  is removed; (3) the "does it genuinely add / does it conflict" judgment moves
  to the **reviewer** (a new `micro_detail` rule on the FILL review contract:
  contradiction → `fail`, gratuitous restatement → `warn`). Apply now never
  blocks prose on a micro-detail: the only apply check is the note-form length
  cap, and an over-long value is *dropped*, not repaired. `add_entity_detail`
  allows same-key updates; the schema caps at one. 503 tests, ruff clean,
  golden 0/0. Rides the review-contract machinery (#57/#58) — no new plumbing.
  **Live validation (gpt-oss:120b, unbilled): the micro-detail blocker is
  gone** — FILL cleared the old `write:group-3` re-key death; group-0 wrote
  clean with no collision. Two review-wiring bugs the redesign's own reviewer
  caught (PR #59 review) were fixed in the same PR: `fill_review.j2` never
  rendered the entity's base facts, and apply overwrote a same-key update's
  prior value before review read it — so the `micro_detail` rule had nothing
  to compare against. Fixed by threading a per-passage `prior_facts` box from
  apply to review and rendering each proposal as *proposed vs prior + the
  entity's other facts* (`_micro_review`); a review-context test now guards it.
  504 tests. **New blocker (separate, not micro-detail)**: FILL now dies at
  `write:group-1` on a **beat_infidelity** review call — the reviewer read
  "stepped back … the logbook loomed behind her" as movement *away* when the
  beat wants *toward* (a plausible over-literal spatial reading). That is a
  review-quality question on the *beat* rule, not the micro-detail system;
  DRESS codex review still unexercised live.

- **2026-07-12 (review-contract live-validated + a top-level `verdict`
  refinement; a new FILL blocker surfaced):** An unbilled gpt-oss:120b run
  (Ollama cloud, scratch `examples/thaw-between/`) validated the contract on
  the weak tier: **six FILL prose reviews accepted first-try with well-formed
  structured verdicts — no fabricated rule, no false-positive halt** (the
  failure this redesign targeted). The voice-ban footgun is also gone live
  (the coined `banned` list was all literally-matchable). Author refinement
  off the run: the empty-review signal `{"findings": []}` is semantically thin
  — a considered "clean" and a lazy default look identical — so `ReviewVerdict`
  gained a required top-level **`verdict` (`approved` / `needs_work`)**.
  `approved` auto-accepts; `needs_work` defers to the engine, which reworks
  only on a confident `fail` and otherwise approves anyway ("a needs-work can
  still be approved by the engine"). This does not restore the removed binary
  verdict: the reviewer can affirm a clean read but still cannot *block* on its
  own say-so (a block needs `needs_work` + a `fail` at `medium`+ confidence).
  The asymmetry makes it safe (a wrong `approved` only accepts marginal prose;
  the danger was a wrong halt). 500 tests, ruff clean, golden 0/0. **New open
  item**: FILL still died before DRESS — but on an *unrelated* cause, the
  micro-detail single-assignment guard (`object:old-lens already has
  'material'`) exhausting repairs when the weak writer kept re-observing an
  established fact. The message is already exemplary (reason + subject +
  recovery_action), so it is a weak-tier fixation, not a message defect — a
  prose-quality follow-up, and it means **DRESS codex review is still
  unexercised live**.

- **2026-07-12 (review-contract redesign BUILT — signed off, implemented,
  pushed):** The author marked the spec PR ready and signed off ("start
  implementing"). The pipeline-wide structured-finding contract is now live:
  a new `pipeline/review.py` owns `ReviewFinding` / `ReviewVerdict`, the
  per-review `rule` enum builder (`build_verdict_schema`), the engine gate
  (`needs_rework` = any `fail` at `high`/`medium` confidence), and the
  producer-facing renderer. Adopted by **FILL prose** (`fill.py`,
  `fill_review.j2`) and **DRESS codex** (`dress.py`, `dress_codex_review.j2`);
  both templates now ask for the structured verdict instead of `pass/fail` +
  free-text issues, and the producer prompts (`fill_write.j2`,
  `dress_codex.j2`) gain the "weigh warns, don't over-correct" framing. The
  crux, per the author's correction: the engine gates only proceed-vs-rework
  on confident objective defects; the producer receives every finding
  (full fidelity, labeled `[rule · ASSESSMENT · confidence]`) and decides —
  a `warn` or low-confidence finding is weighed, not mandated. Cross-tier
  arbitration on a second rework is unchanged in shape (same schema, stronger
  judge). `PassSpec.review` keeps its `-> list[str]` contract, so the runner
  is untouched; the e2e keeper review fixtures (013 FILL, 041 DRESS, + 9
  passes) re-recorded to the finding schema, preserving the one-rework flow.
  New `tests/test_review.py` covers schema/enum/gate/renderer; the two
  prompt-source rule-matching tests were replaced with structured-verdict +
  "weigh warns" guards. 499 tests, ruff clean, golden `qf validate` 0/0.
  **Open**: unbilled gpt-oss:120b live validation (stop the FILL
  false-positive halt; first exercise of DRESS codex review under the
  contract). Supersedes the audit's `fill_review` three-part-matching
  prompt approach (`docs/plans/error-message-audit.md`).

- **2026-07-12 (full gpt-oss:120b run → a new failure class:
  model-coined constraints enforced downstream):** A full weak-tier run
  (unbilled, per the budget discipline) to see where we stand after the
  sweep. **The whole structural pipeline now clears on pure gpt-oss** —
  DREAM→POLISH including finalize *and* arcs, the exact passes that killed
  the earlier all-gpt-oss run on this premise (the residue beat-id
  collision): the fresh-id prompt + the `GraphError` engine fix cleared it
  in one attempt. The review contract also behaves — the reviewer quotes
  rule + prose + match, no fabrication. **FILL then exposed a new *class*
  of failure**, distinct from the sweep's withheld-data class: a model
  coins a value in one pass that a later pass enforces literally, and a
  weak model coins an over-broad/unsatisfiable one that traps the writer.
  Live instance: the voice pass coined `banned: ["similes using 'as' or
  'like'", "direct metaphor", …]`; `fill_review` matches banned patterns
  verbatim, so the ban on "as" outlawed ordinary prose and the vague
  "direct metaphor" was unactionable — every passage failed review. It
  only surfaced *because* the review-fix made the reviewer honest (the
  failure moved up-chain from "reviewer fabricates" to "voice coins a bad
  rule the honest reviewer enforces"). Fixed: `fill_voice.j2` forbids
  common-word and vague bans and states the verbatim enforcement. The
  class + the other coined-constraint sites to audit (POLISH arcs, DRESS
  direction, flag descriptions, micro-details) are recorded in
  `docs/plans/error-message-audit.md`. A gpt-oss re-run is validating the
  voice fix (in progress). 486 tests. **Follow-up (same day): the
  review-contract redesign this failure motivated is now spec'd** at
  `docs/plans/review-contract.md` — the honest-reviewer footgun is one
  face of a pipeline-wide class (binary verdict + free-text issues
  false-positive-halts the producer), so the spec replaces the verdict
  with a structured multi-axis finding schema shared by every review pass;
  locked for review, implementation held for sign-off.

- **2026-07-12 (pipeline-wide prompt-quality sweep — "FILL was a
  symptom", author-directed):** After the FILL fixes landed, the author's
  point: the same blunt-prompt disease runs through every stage. Five
  parallel graders swept all pipeline prompts + context + apply against
  the `AGENTS.md` rule. **The pattern is confirmed pipeline-wide**: a rule
  is stated but the enabling data is withheld from the context, or the
  rule is not enforced at apply — trusting the model to reconstruct what a
  strong tier can and a weak one can't. High-severity fixes landed:
  `polish_finalize.j2` states coined beat ids must be fresh/unique (the
  prompt-side twin of the engine fix); `grow_contextualize.j2` renders the
  entities its "keep the same entities" rule required but withheld;
  `dress_codex_review.j2` gets `fill_review`'s three-part rule-matching;
  `brainstorm.j2` states the output dilemma count plainly; FILL's voice
  pass now validates the pov's named character against the cast (the
  Maren/Marin bug, enforced with token — not substring — matching);
  `dream.py` bounds themes to 2-4; and the Class 1 raw-`ValidationError`
  dumps route through one shared `format_validation_error` (owned by the
  adapter, re-exported to the apply layer, so the two never drift — a
  review caught that duplicating it was the very failure the sweep is
  about). Full graded inventory + the deferred medium apply-guards in
  `docs/plans/error-message-audit.md`. **The live medium Gemini run that
  was meant to validate these + finish the recurrence read hit the
  project's Gemini spend cap (`RESOURCE_EXHAUSTED`) mid-FILL** — a billing
  limit, not a code failure — so the scaled recurrence verdict and live
  validation of the prompt fixes both remain open (next-up #1). It did
  clear POLISH finalize cleanly on Gemini and wrote several FILL passages
  before the cap. 485 tests.

- **2026-07-12 (#1a live validation → the prompt-quality reckoning,
  author-directed):** The prose-quality live validation ran two fresh
  stories — `thaw-between` (medium, Gemini strong map, grounded on the
  **newly vendored in-repo corpus** — its first real run, which worked:
  DREAM→GROW completed clean) and `weir-coat` (short, `gpt-oss:120b`
  cloud). Neither reached a complete FILL, and *how* they failed is the
  result. **Recurrence read (the headline metric): inconclusive but
  qualitatively encouraging.** On the 13 thaw passages written, max
  cross-passage 6-gram recurrence = 2 (0 six-grams in ≥5 passages) — but
  run 8's *first 13* passages also max at 2, so at that sample size the
  metric can't discriminate; the stamp only proves out at book scale
  (run 8: 23/148). The qualitative tell is real, though: run-8's early
  repeats are already the entity-identity stamps that compound ("his left
  eye develops a minute rhythmic twitch", "highly polished patent leather
  oxfords"), whereas thaw's are generic sensory collocations ("cloud of
  vapor spills from his lips") that won't compound the same way. A
  definitive verdict needs a completing run. **The blocker — and the
  bigger finding — is FILL review-exhaustion on BOTH tiers:**
  - `weir` (gpt-oss:120b) died at passage 1: the same-model reviewer
    **fabricated a rule** — cited "Rule 1" (POV/tense) to reject a simile
    ("wilted like frost on wheat"), which no rule forbids — and the writer
    could not clear the phantom objection. This sharpens the #1b brief
    beyond "sub-clause literalism" to **rule-number fabrication**: a
    reviewer citing a real rule number for an objection that rule does not
    cover, which a prose contract on a same-model arbiter cannot prevent.
  - `thaw` (Gemini) failed at group-13 **twice** (systematic, not
    stochastic): the reviewer flagged a POV head-hop (the writer narrated
    a non-viewpoint character's plotting interiority) and a beat-location
    infidelity, and the strong writer couldn't self-correct in two rounds.
    Root traced to the write prompt: the new ARC POSITION block (W5) hands
    the writer other characters' intentions with **no POV externalization
    guard**.

  **The author's reframing (recorded as a standing rule):** the recurring
  bottleneck is *blunt prompts and error messages propped up by model
  intelligence* — I patch symptoms and lean on the model being smart
  enough to reconstruct loose intent, until a weaker tier isn't and it
  reads as a model limit. Directive: **always diagnose prompt/message
  quality first** (now `AGENTS.md` §"Prompt and error-message quality"),
  and **audit all error sites** — there are many. Acted on:

  1. **The finalize duplicate-id failure was an engine + feedback bug, not
     a weak model.** gpt-oss coined a residue beat id colliding with a
     commit beat and couldn't recover from the bare `duplicate node id 'X'`
     message. Root: `store._add_node`/`_add_edge` raise a bare `KeyError`
     that only `add_beat` converted, and the message carried no
     recovery_action (heritage `semantic-conventions.md` §Error Messages).
     Worse, it was a **latent crash class**: a colliding *false-branch* id
     escaped as an uncaught `KeyError` (the residue path caught it, the
     symmetric false-branch path did not). Fixed at the boundary —
     `store.GraphError(KeyError)` with recovery_action for duplicate
     id / missing endpoint / duplicate edge, and the runner catches
     `GraphError` so **every** model-reachable graph write is repairable
     and actionable. (`add_beat` still adds its beat-specific message;
     finalize residue/false-branch both repairable.)
  2. **`fill_review.j2` forces rule-text matching**: each objection must
     quote the rule's *own wording* and show the text breaks THAT rule
     (naming a number is not enough), and figurative language is named as
     taste, not a violation — designed against the weir fabrication.
  3. **`fill_write.j2` gains a POINT OF VIEW IS LIMITED block** (symmetric
     to the existing TENSE IS ABSOLUTE): only the narrator's interiority
     may be stated; other characters are rendered through observable
     behavior, and the ARC POSITION block is guarded the same way —
     designed against the thaw group-13 head-hop.

  **Audit finding**: most stage `ApplyError`s already carry a
  recovery_action (refpin-era work). The systematic gaps were the store
  `KeyError` class (fixed) and raw-exception dumps (`f"invalid X: {e}"`,
  Class 1 — graded acceptable, pydantic-structured, deferred). Plan +
  rubric: `docs/plans/error-message-audit.md`. The two prompt fixes are
  *designed against* the live failures but **not yet live-validated** (the
  runs died before completing) — a completing FILL run on both tiers is
  the next step, and it doubles as the scaled recurrence read. 473 tests.
  The scratch validation runs were not preserved (incomplete); their
  configs live in this entry.

- **2026-07-12 (the #1a predecessors, author-directed: corpus vendored
  + M10 progress reporting pulled forward):** Two items the author
  called before the prose-quality live validation runs. (1) **The
  curated craft corpus now lives in the repo**: the eight non-exemplar
  clusters (55 notes) copied from the author's vault to
  `corpus/interactive-fiction/`, byte-faithful with frontmatter;
  `corpus/README.md` records scope, provenance, and the
  fingerprint-as-input contract; `style-exemplars` stays out until
  M9's reserved exemplar mechanism can consume it (03 §10 gained the
  bullet). Closes the open item below — runs stop hand-staging vault
  exports. (2) **M10's progress reporting is built early** (scope
  discipline note: an explicit author pull-forward, not drift; the
  rest of M10 stays put). Design: the runner grew a `progress`
  callback seam (`PassProgress` in `pipeline/types.py` — stage, pass
  name, 1-based m/n over the full pass list including skips, status
  start/done/skipped/kept/resumed/failed, attempts) so the engine
  stays CLI-agnostic; `qf run`/`qf rerun` wire it to a one-line
  heartbeat on **stderr** with explicit flush (stdout stays the
  report stream; stderr is what survives piping — the live run 8
  block-buffering complaint), each resolution line carrying running
  ledger totals; `qf status` now prints spend (calls, cached, tokens
  in/out — tokens, not dollars: the ledger records no prices and a
  CLI price table would rot) and detects an interrupted run from the
  A16 `inflight/<stage>/` ledger (journaled pass count, last pass,
  "re-run to resume free"). Tests: runner event-sequence + failure
  tests, `qf status` live-state CLI tests (`tests/test_status.py`).

- **2026-07-12 (arc-worthiness settled by the author):** "A character
  without an arc is an extra, a location without an arc is a backdrop,
  an object without an arc is a mcguffin, a relation without an arc is
  a link — all of those can be given *choices*." Every retained entity
  is now arc-eligible (`_arc_entities` drops the category filter),
  matching the heritage ontology's scope; the polish_arcs prompt
  carries the doctrine — leaving an entity unarced deliberately
  declares it scenery — and the per-category flavors (transformation /
  atmosphere / significance / relationship) as guidance, not schema.
  01 §10 departure 5 updated (the pivot-shape departure stands; the
  narrower-scope clause is gone). Golden story: the Stilt Light gains
  an atmosphere arc pivoting at `beat:tremor`, so a location arc is
  exercised through FILL's arc-position rendering. e2e fixtures
  untouched — the recorded arcs proposal stays valid under a widened
  enum.

- **2026-07-11 (arc shape vs the heritage ontology — author challenge,
  post-merge of #49):** The author didn't recognize the built
  character-arc shape against `docs/heritage/`. Verified: the effort's
  design consulted heritage's `semantic-conventions.md` (the file
  next-up #1 named as reference input) but **not**
  `story-graph-ontology.md` §"Character Arc Metadata", which specifies
  the original's richer form — one pivot per path, per-path `arc_line` +
  `arc_type` (character→transformation, location→atmosphere,
  object→significance, faction→relationship), dual-indexed with a
  must-agree constraint. Comparison: NG's shape agrees on everything
  structural (entity-node annotation, POLISH-created, FILL-consumed
  pre/at/post-pivot, never exported, begins + per-path ends) and
  diverges on pivot indexing (NG: one ordered beat-anchored list —
  strictly more expressive: shared-spine turns stated once, multiple
  turns per route, per-path turns via path-exclusive beats; no dual
  index to keep consistent), on stored `arc_line`/`arc_type` (NG
  derives them), and on arc-worthiness (NG: characters+objects only;
  the original also arcs locations and factions). The divergence was
  real but **unrecorded** — that is the bug (undocumented divergence,
  AGENTS.md). Recorded now as 01 §10 departure 5. Left open for the
  author: widen arc-worthiness to locations/factions, and whether
  `arc_line`/`arc_type` earn storage (see open items).

- **2026-07-11 (prose-quality-at-scale engine — the frontier session
  next-up #1 called for; plan doc `docs/plans/prose-quality.md`):**
  Built all five workstreams of the author's design brief (the "live
  run 8 reading findings" entry below) in one PR. Design decisions
  worth the record: **(echo)** thresholds are deliberately modest and
  named constants with rationale (`pipeline/echo.py`): a fact value of
  ≥ 4 tokens restated verbatim is the stamp, a ≥ 8-token run shared
  with adjacent prose is a lift; both repairable ApplyErrors, and the
  prompt framing — not the check — is the real fix. The near-duplicate
  guard compares a proposed detail against the entity's existing values
  (≥ 4-token overlap names the existing key), closing the
  `habit`/`stance_width` accrual the key-level single-assignment guard
  walked around. **(story-so-far)** summaries are per-passage notes
  (`Passage.prose_summary`, ≤ 60 words, on-node YAML, never exported)
  written by a utility pass that rides directly behind each accepted
  write pass — so the in-flight ledger resumes them free and prompt
  bytes stay cache-stable; the write context walks ONE deterministic
  route back to the root (prefer reference-arc predecessors, else
  lowest passage id), excludes the window hop (its full prose is
  already shown), caps at 40 entries, and the prompt states the honesty
  rule: one route among several, WORLD STATE governs what may be
  asserted. Writing order (reference arc first, then story order)
  guarantees every route predecessor is already summarized.
  **(arcs)** realized exactly as 02 contracted ("begins X, pivots at
  beat Y, ends Z per path"), stored on `Entity.arc` via a stable-
  once-set mutation (rewind, not overwrite, is how an arc revises);
  the arcs pass pins entity/beat/path enums via refpin and validates
  pivot story-order at the mutation layer; FILL consumption uses plain
  ancestry (the same convention flag certainty uses for grants) — a
  pivot on a branch-only beat may read slightly early on routes that
  skirted it, accepted for a pacing channel and documented in code;
  path `ends` render only once that path's commit is upstream. A new
  G4 check fails dangling arc references loud (this session's own
  authoring slip — `beat:the-offer` for `beat:offer` — sailed through
  validation and motivated it; violating-construction test included).
  **(voice)** grew `imagery` and `dialogue` (defaults empty so
  author voice.yaml files load unchanged; required in the proposal so
  the pass always supplies the palette). **(fixtures)** the keeper e2e
  fixtures were re-recorded by positional splice (the keeper-craft
  pattern): 36 → 45 calls, the two new pass responses hand-written in
  the note register; two recorded micro-details were re-registered to
  note form (they were 15-word performed sentences — exactly the
  contract this effort imposes) and the recorded voice gained the two
  new fields. Deliberately NOT built: the review-contract redesign
  (per-beat checklist / cross-tier arbitration) — next-up #1(b),
  design-against-failures; and no mini-ADR — every piece rides
  contracts 01/02 already state. 461 tests, golden 0/0.

- **2026-07-11 (audit follow-up — the flag-status fix validated live; a
  voice example-name bleed found and fixed):** Re-ran the `gpt-oss:120b`
  cloud DRESS chase (fresh micro premise, canal lockkeeper register, all
  three roles on the weak tier) to measure the audit's `_flag_status` fix
  against yesterday's failure signature. **Result: the Rule-4
  possible-state failure class did not recur** — zero occurrences; the
  first passage (which carries possible flags) cleared in two attempts
  with a legitimate micro-detail, and every structural stage
  (DREAM→POLISH: refpin enums, finalize ordering, cadence diamonds,
  residue arms) ran clean on the weak tier. The run instead died one bug
  deeper, on a prompt defect of exactly the audited class: `fill_voice.j2`'s
  pov example — `"third person limited (Maren)"` — planted a concrete
  name while the voice pass was shown **no cast**, and the model copied
  the example's name over the real protagonist ("Marin Voss"). Cascade:
  the first passage's accepted prose says "Maren", the next writer used
  "Marin" (matching the cast), review failed it for name-mismatch/POV,
  the writer flip-flopped, and the same-tier arbiter finally
  hallucinated a "beat absent" verdict against prose containing the beat
  nearly verbatim (an all-one-model map gives arbitration no tier
  escalation — a structural limit worth remembering). Fixes: the voice
  context renders the retained characters with canonical spellings
  ("any name the voice uses must match one of them exactly"), the pov
  bullet demands the exact cast spelling with the bleedable example name
  removed (a test pins the template source clean of concrete pov example
  names), and the review's Rule 2 gained the texture-beat clause — a beat
  whose only content IS scenery is fulfilled by any wording delivering
  the impression (attempt 1 was genuinely failed for paraphrasing
  "quiet reminder of the tunnel's age"). 434 tests. **Re-run outcome
  (same session): the voice fix works** — the voice came back
  `third person limited (Marin Voss)`, exact cast spelling, and the name
  cascade is gone. FILL then failed on the residual class, now isolated
  cleanly: the *writer* is compliant (two successive attempts contained
  every beat's content, including the disputed "including her own
  obligations" clause — once nearly verbatim, once as "they bind her in
  equal measure"), but the utility reviewer quoted a single sentence and
  declared content absent that sat in the adjacent sentence — and the
  same-model arbiter upheld it verbatim. With the deterministic causes
  removed (Rule-4 flag statuses, voice name), the weak-tier blocker is
  now precisely **reviewer sub-clause literalism + one-sentence
  quoting**, unfixable by another rule tweak on a map whose arbiter is
  the same weak model. Stopped at diminishing returns (the author's
  precedent from yesterday's chase); this failure signature is the
  sharpest input yet to next-up #1's review-contract design (beat
  checklist framing, echo check at apply, or a cross-tier arbitration
  requirement).

- **2026-07-11 (prompt-engineering audit — author-directed: "a full audit
  of all prompts against best practices; perfectly clear in intent and
  expectation, with the full context they need — never inferred"):** Every
  shipped template (24 `.j2` files), the review system prompts, the
  adapter's JSON instruction and correction brief, and each pass's render
  context were audited against a rubric drawn from
  `docs/heritage/semantic-conventions.md` (directive language, explicit
  constraints, enums for finite sets, axis separation) and standard
  prompt-engineering practice: intent stated directively up front, terms of
  art defined in-prompt, context complete AND true, output shape explicit,
  prompt consistent with what the apply actually enforces. The prompts were
  already strong (two hardening batches preceded this); the audit's yield:
  1. **A real engine bug** (`fill._flag_status`, the "context must be TRUE"
     clause): gate certainty did not propagate along the dilemma. A gated
     residue passage sits at a convergence with *both* commits upstream, so
     ancestry read the rival path's flag as "possible" (golden story:
     `p-unspoken`, gated on hide's flag, showed tell's flag as possible);
     a variant passage was worse — its gate lives on the *choice edge*,
     which the status never consulted, so its own defining flag read as
     possible. Under the fresh Rule-4 honesty directive the writer was
     ordered to stay neutral about the very fact the passage exists to
     carry, and the review's rule 4 would fail prose that asserted it. Now
     a beat gate or a gate every incoming choice requires makes the gated
     path's flags CERTAIN and every rival path's flag of the same dilemma
     FORECLOSED (dropped from the writer's WORLD STATE). Two regression
     tests, golden-anchored.
  2. **Context gaps** — a prompt held to a rule whose inputs it couldn't
     see: *seed_order* never showed dispositions, yet its central rule
     ("the story ends at a **branched** hard resolution") turns on them —
     it now renders branched/locked per dilemma, states that an omitted
     pair is unconstrained and that `concurrent` adds no constraint (the
     weave consumes it nowhere — declaring otherwise invited false
     expectations), and warns about serial(hard, locked) up front instead
     of only in the repair error; *dress_codewords* demanded global
     uniqueness ("old or new") while showing only pending flags — it now
     renders the codewords already in use; *seed_triage* and *fill_voice*
     get the premise (the author's one-paragraph ask governs what triage
     keeps and what the voice serves; it was rendered only at DREAM /
     BRAINSTORM); the FILL reviewer's rule 3 was asked to judge continuity
     against adjacent prose but shown only the *preceding* excerpts — it
     now sees the following ones too; grow_weave's step notation
     (COMMITS / worlds / "(in each world)" / intersections / locked) is
     glossed, the worlds part only when multi-hard.
  3. **Prompt/spec consistency**: polish_finalize's residue entry format
     omitted "fork" (described in prose above it) and the world-omission
     case; fill_write's micro_details never stated its shape; polish's
     variant ids weren't said to be passage ids; scaffold now states that
     every non-setup/non-commit beat carries an effect (it was phrased as
     pre-commit-only, but the apply reads it on post-commit and locked
     beats too) and that hints/flexibility are consumed only on movable
     beats (weave reads hints from pre-commit and locked-chain beats
     only); intersections' `location` omission case stated; brainstorm
     states the total dilemma arithmetic and dream names the locked
     allowance; research states an empty query list is valid (standing
     queries always run); `VoiceProposal.tense` is now the
     `Literal["past","present"]` the prompt promises (A11 — the write
     prompt builds sentences around the value); `_shared.j2`'s repair
     block stops implying the model can "fix" a proposal it can never see
     (single-shot renders — it now asks for a fresh proposal avoiding the
     accumulated problems, newest last); fill_review guards the banned
     block when a voice bans nothing.
  Deliberately unchanged: the review prompts' numbered-rule register
  (fresh from the DRESS-chase hardening), cadence's directive framing over
  an advisory budget, and the write prompt's input-role framing — that
  rewrite belongs to the prose-quality effort (next-up #1), which this
  audit sharpens but does not replace. Design docs untouched: they are
  silent on all surfaces changed here (flag-status semantics live in
  `fill.py`; prompt wording is implementation).

- **2026-07-11 (DRESS-chase follow-up — finalize engine bug + weak-tier
  FILL prose hardening; author-directed "pursue the full cloud dress as a
  follow-up PR"):** Picked up after #44 merged, on a branch reset onto the
  merged `main`. Two kinds of result. **(1) A real latent engine bug.**
  The POLISH finalize failure that blocked the cloud DRESS was not a model
  quirk: `_finalize_apply` spliced residue first, then recomputed the long
  runs it validates false branches against — so a beat the model was shown
  inside a long run (and the pinned `before`/`after` enum accepted) could
  be evicted by residue splicing at a neighbouring convergence, and its
  cadence diamond wrongly rejected against a structure the model never saw.
  Both residue and false branches are additions to the frozen pre-finalize
  topology, so both must validate against it: finalize now splices false
  branches against the pristine long runs before residue. POLISH clears
  live — the exact failing `beat:spirit-post-2-burn -> bridge:gap-6`
  diamond now applies — and a regression test asserts the ordering. This
  is tier-independent correctness, worth landing regardless of the chase.
  **(2) Weak-tier FILL prose is a milestone, not a bug.** Three genuine
  prose gaps, each diagnosed against the graph/flags before deciding
  writer-vs-reviewer fault: tense as a directive (narrated-past events in
  the voice's tense, Rule 1); POSSIBLE-state honesty stated plainly so the
  writer stops asserting path-dependent flags as fact to fill a scene
  (Rule 4); the review's Rule 2 sharpened so a weak reviewer stops
  laundering dropped scenery as a missing event. Each is a firmer
  restatement of an existing contract (strong models already hold them),
  and they moved `gpt-oss:120b` from 0 to several clean FILL passages. But
  a full clean DRESS stayed out of reach: the writer stochastically
  re-asserts possible-state content on cosmetic all-possible-flag cadence
  arms, passing Rule 4 in two rounds on some and exhausting on others.
  That residue is the prose-quality-at-scale milestone (next-up #1), so the
  chase stopped at diminishing returns rather than grinding expensive
  re-runs, no cloud example was fabricated, and the honest state is
  recorded. 431 tests, ruff clean, golden 0/0.

- **2026-07-11 (reference-pinning generalized pipeline-wide —
  author-directed: "we want all of this class over all stages fixed"):**
  The #40 → `locked[].dilemma` re-confirmation (entry below) showed the
  dangling-reference class recurs field by field as model capability drops,
  so instead of patching siblings one at a time the discipline became a
  shared helper (`pipeline/refpin.py`) applied to every reference field in
  every stage. An Explore-agent audit catalogued the class across all
  proposal schemas — ~25 pinnable reference fields plus two correctly
  *unpinnable* ones (BRAINSTORM `anchored_to`, which references entities
  coined in the same proposal), and flagged one latent hole: GROW
  intersection `location` was a semantic entity reference with **no
  validation anywhere** — now pinned, closing it. Design decisions worth
  keeping: (1) one recursive `pin(model, name, resolvers)` rebuilds nested
  specs and preserves every `FieldInfo` (min_length, defaults), so a stage
  is a one-liner and `$defs` stay minimal; (2) the exact-vs-slug split —
  `resolve_entity_ref` fields pin to ids **+ unambiguous slugs**
  (`entity_ref_ids`), exact-membership fields to exact ids only
  (`retained_entity_ids`), so a grammar-constrained model can never emit a
  schema-valid value the apply then rejects; (3) `PassSpec.schema` may now
  be a **callable** resolved at pass-run time (`schema_for`), because a
  pass's enums can depend on an earlier same-stage pass's graph writes
  (SEED scaffold ⇐ triage dispositions, POLISH audit ⇐ the passages pass) —
  the runner builds the pass list once, before those writes exist; (4) the
  apply guards stay as defense in depth and to enforce joint constraints
  (finalize's (dilemma, world, path) triple) the independent enums can't
  express. Tests: a `pin` unit suite (scalar/list/nested/const/empty/
  constraint-preservation), the exact-vs-slug helpers, a per-stage
  violating-construction test on the golden (incl. the exact live
  `world='share-legend'` finalize failure, now rejected), a GROW
  pre-weave intersection test, and the grammar-subset lint extended to the
  dynamic builders. 430 tests, ruff clean, golden 0/0. Live validation:
  a full `--to dress` run on `gpt-oss:120b` cloud cleared every
  reference-heavy stage (DREAM→BRAINSTORM→SEED→GROW, all first-attempt) —
  the pinning holds live where it matters. It then wedged at POLISH
  finalize on a *non-reference* gap (a cadence false-branch the model
  proposed at a beat residue later breaks out of its long run; strong
  models don't over-propose there), so no cloud example is preserved yet.
  That gap belongs to the prompt-quality effort (next-up #1), not this
  class; the full record is in open item 5.

- **2026-07-11 (Ollama cloud tier — #40 re-confirmed live + its sibling
  `locked[].dilemma` pinned):** From this hosted environment (supplies
  `OLLAMA_API_KEY` for the cloud tier via `host: https://ollama.com`, no
  local daemon), re-ran the pending #40 confirmation on a fresh micro
  premise (canal lockkeeper + a stranger's coat). `qwen3.5:397b` cloud is
  paywalled (403 subscription — same guard-ignored case as
  `qwen3.5:cloud` before), so `gpt-oss:120b` — the exact family that
  first exposed #40 — stood in. First `--to seed`: the `explores` enum
  cleared on attempt 1 (the #40 fix works as built), and triage then
  failed the **identical** dangling-reference way one field over, on
  `locked[].dilemma` (the model named `ice-watcher`, dropping the
  `dilemma:` prefix). This is #40's own "generalization to other
  id-reference fields" deferral firing on its nearest sibling, so I took
  it: `triage_proposal_schema` now also pins `locked[].dilemma` to an
  enum of the real dilemma ids (graph order — dilemmas carry no
  strict-equality marker, unlike answers, so ordering is free). Same
  three-part discipline as #40: schema-level constraint for every
  provider, the correction brief names valid ids on a miss, and under
  grammar-constrained decoding (A20) the dangling reference is
  unrepresentable at decode time. The apply-time guard stays (defense in
  depth). The re-run passed SEED first attempt (`locked:
  dilemma:hand-locket`, valid + prefixed). Three violating-construction
  tests added (reject dangling, accept real, stage wires the enum),
  mirroring the #40 trio; 412 tests, ruff clean, golden green. Onward to
  GROW→DRESS to earn a cloud-tier example is the remaining open item.

- **2026-07-11 (Ollama backend — live validation on a real daemon;
  closes #41):** Ran the STATUS hand-off checklist against
  `athena.int.liesdonk.nl:11434` (RTX 4060/8GB + 128GB, daemon logged in
  to ollama.com) from a Claude Code session with `OLLAMA_HOST` reach.
  **The A20 mechanism is validated; the blocker to a full local story is
  prompt legibility, not the backend — exactly the thesis the design
  discussion predicted.** Suite green (403). Cloud `format` question
  answered: `gpt-oss:120b-cloud` **accepts** `format` cleanly (raw
  `_generate_once` probe + a full BRAINSTORM run agree; no ResponseError)
  — the hoped-for "call succeeds, schema satisfied" world; the
  reject→unconstrained fallback stayed unexercised. `qwen3.5:cloud` is
  paywalled (a *subscription* 403, which the fallback guard correctly
  ignores since the message has no "format"), so a rejecting cloud family
  was never observed — **fallback kept as insurance, not deleted, not
  proven dead**. `OllamaContextError` fires fail-loud at `num_ctx=2048`.
  The seed experiment ran three model maps on one shared micro premise
  and **none completed DREAM→SEED** — the repair-burn *is* the result:
  `llama3.1:8b` exhausted repairs at BRAINSTORM `populate` emitting
  underscore slugs (`format` grammar enforces the `kind:slug` colon but
  not kebab-case *within* the slug — GBNF drops string `pattern`), a
  model-tier weakness; `qwen3.5:35b-a3b` (local, 11m40s on CPU) and
  `gpt-oss:120b-cloud` (~84s) both **passed** BRAINSTORM with clean
  kebab-case and then failed SEED `triage` the **identical** way —
  `explores` naming an invented answer slug, not an existing answer id.
  Two unrelated strong families converging on one failure that
  Gemini-pro/Claude-opus clear (runs 7–8) is a model-capability threshold
  on an under-specified prompt, not model-tier noise; the fix (pin
  `explores` to an enum of real answer ids, class A11) resolves it for
  every provider and lets Ollama's grammar enforce it for free — **filed
  as #40**. No `--to dress` completed on a local model, so no example is
  preserved yet; a hardened triage prompt should let a `qwen3.5`-class
  local run reach DRESS and earn one. Net: the local-model gate failures
  diagnose NG's prompts, precisely as the backend's design entry claimed
  they would.

- **2026-07-11 (Ollama backend — native structured output at the
  provider seam; the design discussion is the record):** Author-directed
  unplanned addition, designed in discussion before any code. The core
  decision is mini-ADR A20: the adapter derives each call's JSON schema
  once and *offers* it to the provider — Ollama consumes it as `format`
  (grammar-constrained decoding), Anthropic/OpenAI/Gemini deliberately
  ignore it (each for a documented, provider-specific cost: streaming +
  extended-thinking incompatibility; strict-mode schema-subset
  conflicts; deep-schema rejection risk), and Pydantic validation +
  retry remain the sole acceptance path for every provider. Governing
  principle, from the author's read of the legacy engine: **help must
  be conditional on failure** — micromanagement tuned for weak models
  actively hurts smarter ones, so constrained decoding changes no
  prompt bytes and the new correction-brief retry (field paths, what
  went wrong, values seen — legacy's retry-with-feedback lesson)
  appears only when validation actually fails. Rejected: flipping all
  providers to native modes (costs above, zero observed retry burn on
  frontier models), and legacy's discuss→serialize two-pass shape
  (4B-era scaffolding NG shouldn't bake in). Context that framed it,
  worth keeping: **the legacy engine is a failed attempt at
  maintainability, not at efficiency** — it ran this pipeline's
  equivalent on small local models (legacy #552: qwen3:4b through the
  full pipeline at 8.0/10 prose, with weaknesses exactly where
  origination and arc judgment live), at the price of hand-tuned
  prompts and repair loops threaded through everything; NG's blunt
  prompts haven't made that investment, so **local-model gate failures
  diagnose NG's prompts, not the model tier** — the same read from the
  opposite direction as legacy #551 independently wanting character-arc
  metadata for small models while NG's deferral trigger fired at
  frontier scale. Single provider per project stands (no per-role
  provider map; the author's target is one reasonably strong family —
  gpt-oss:120b / qwen3.5-class — plus Ollama's cloud tier
  (`glm-5.2:cloud`, `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`) as a
  new experimentation line through the same seam). 4B is a non-goal;
  ~70B+ is the experiment. Live validation is the open item above.

- **2026-07-11 (live run 8 reading findings — stylistic repetition;
  the author's design direction for the prose-quality effort):**
  Reading "Closed Circle" at book scale surfaced the first
  quality gap only a 49k-word read could: **verbatim recurring
  descriptions** — Beaumont takes "the wide lateral stance of a
  classical fencer" in 25 of 148 passages, near word-for-word; his eye
  twitch in 12; the velvet smoking jacket in 16. Diagnosis (traced,
  not guessed): the entity micro-detail machinery works as built and
  stamps the prose — FILL discovers a vivid detail once, every later
  write context renders it verbatim whenever the entity is on stage,
  the writer performs the phrase already sitting in its prompt, the
  window doubles the exposure, and the review *rewards* it (each
  passage is judged in isolation, where repetition reads as the
  consistency the rules check). The key-level single-assignment guard
  also let near-duplicate details accrue under different keys
  (`habit` vs `stance_width`, both the fencer stance), and details
  were stored as performed sentences — the pre-voiced-summary bias
  vector, now in the entity layer. The author's direction, recorded
  as the design brief for the effort: (1) the deterministic echo
  check at FILL apply (long verbatim n-gram overlap with rendered
  detail values or window prose, repairable) is approved — modest
  expectations, cannot hurt; (2) most of the fix is **prompt
  engineering: tell the writer how to interpret each context block
  and what to do with it** (facts are constraints, not choreography;
  the window is continuity, not a style template); (3) the rule of
  thumb, generalizing the summary-register lesson: **everything that
  is not prose should not be prose** — micro-details and every other
  LLM-written non-prose field carry the brief register; relatedly,
  a too-thin Voice record may itself cause copying (a writer short on
  style guidance leans on whatever styled text is at hand); (4) a
  deeper look-back helps only to a point and blows up tokens — a
  **rolling story-so-far summary by a utility-tier summarizer** is
  worth building instead; (5) **high hopes for character-arc
  metadata** (the POLISH output deferred under 01 §10): it turns each
  scene's focus onto pacing *specific aspects* of a character or
  object instead of pushing all details into all scenes — the
  deferral's trigger condition ("a FILL quality gap at short+ scope
  demonstrably calls for it") has now demonstrably fired. Sequencing
  relative to M9 is the author's call; the effort is frontier-tier
  (prompt framing and the arc-metadata contract are bias-sensitive).

- **2026-07-11 (M8 exit: live run 8 — "Closed Circle"):** From the
  author's seed "an Agatha Christie closed circle murder mystery that
  escalates Fargo style", a corpus-grounded `medium` story generated
  end-to-end on Gemini (3.1-pro-preview architect/writer + 2.5-flash
  utility — the M8 machinery's third provider family), preserved as
  `examples/closed-circle/`. **Every §M8 exit criterion met, and the
  calibration methodology validated**: 49,381 words (20-60k), 148
  passages (90-160), B4 114-123 (80-150), walk-B6 644 mean / 618-663
  (<= ~800; the simulation projected 690-780 — live texture passages
  wrote leaner than projected), 32/32 arcs complete, four exports
  round-trip clean, ~$17 vs the $20 cap (above the $8-14 estimate:
  ~1.1M of the pro output tokens are billed thinking, plus re-spend
  across four transport interruptions). The cosmetic:real choice
  ratio measured **4.6:1** against the plan's predicted ~5:1 —
  recorded as promised; whether it reads as texture or tax is a
  play-through judgment for the author. Structure: 260 beats, 2
  worlds, 4 endings, 3 locked storylines woven through the spine,
  8-beat locked chains, full DRESS enrichment (20 briefs, 10 codex
  entries, crosshatched line-art direction). Five engine findings,
  each fixed in-flight: (1) *jointly-infeasible order relations* —
  pairwise-acyclic wraps/serial webs left no valid climax (a locked
  chain serial-after every hard resolve); SEED's order apply now
  probes the weave repairably, with a violating-construction test —
  the model restructured correctly on the first repaired attempt.
  (2) *the Gemini provider held silent non-streaming connections* —
  idle-intolerant middleboxes killed them; it streams and collects
  now (the Anthropic provider's rationale, extended). (3) *thinking
  gaps kill even streams* — a bounded per-call transport retry.
  (4) *5xx ServerError sailed past the transport class* — the retry
  covers it; 4xx stays fatal. (5) Two author roadmap calls landed on
  M10: stage-level auto-resume and per-pass progress reporting (the
  run needed four manual re-invokes and its only live telemetry was
  counting cache files). Also exercised live, worth the record: the
  FILL halt fired once and *correctly* — the writer twice asserted an
  undecided flag's state in a texture arm (Rule 4), arbitration
  upheld — and was resolved through the designed author knob (a
  beat-brief edit + revalidate), with cache replay making the resume
  nearly free; `qf rerun seed --keep triage --keep scaffold` replayed
  both expensive passes free after finding 1; A17 freshness preserved
  every research digest across five process restarts; the SEED depth
  nudge visibly steered the librarian ("intersecting subplots
  consequence compounding"). M8 closes; M9 is next.

- **2026-07-10 (M8 PR-1b: tensored residue arms):** The shape deferred
  from the locked-dilemmas effort, built to plan D5 with the PR-1
  findings sharpening its purpose: diamond seam capacity binds the
  cadence budget at deep scopes, and a tensored arm adds choice
  density exactly where plain diamonds cannot — behind a flag, so the
  choice is state-flavored rather than purely cosmetic (the reader
  who made the matching upstream choice chooses how to carry it).
  Mechanics as predicted, asserted rather than assumed: both branches
  gate identically and rejoin at the frontier, each collapses into
  its own gated passage, either satisfies G4's location-free coverage
  predicate, and I10/I13 need no semantic change. Simulation: medium
  walk-B6 780 -> 690 with tensored arms, words still in band.
  The finalize prompt offers the fork with the taste fence stated
  ("one strong arm beats two thin ones"; neither branch may decide
  anything the other doesn't). The golden story models the shape —
  the tell-side arm split into `counsel` | `honest-chart` as sibling
  gated branches off `beat:offer` (a texture choice only tell-side
  readers ever see), p-counsel's prose divided into two texture-band
  passages, p-tremor gaining the second gated choice. 9 passages,
  gate-clean with zero warnings; the four count-expectation tests
  updated. 392 tests.

- **2026-07-10 (M8 PR-1: the depth & scale engine):** Built to the
  plan (phases 0–4); the calibration surfaced four findings that
  reshaped the work, each now engine behavior. (1) **B6 measured the
  wrong thing**: the arc-view sum counts both arms of every cosmetic
  diamond — words no single reader traverses — which is why run 6 saw
  diamonds barely move it. B6 now walks a deterministic playthrough
  per arc (first live choice staying on the arc, decisions offered
  counted); the preserved runs re-measure at 682–1130 vs the old
  1072–1248 — the feel gap was real but half the metric's size.
  (2) **Deep chains alone mint no words**: an unbroken N-beat run
  collapses into one passage with one word budget, so pre-M8 the only
  page-cutter was the cadence diamond and words were rigidly coupled
  to cosmetic choices. Collapse is now capped per scope
  (`passage_beats_max`; micro pins 5 so the golden story's largest
  hand-authored group and every recorded fixture hold); the cadence
  budget offers only cap-aligned seams, because a mid-chunk split
  mints a whole extra passage per choice — the sizing loop saturates
  at exactly that marginal cost instead of converging (observed:
  93–149 diamonds, 87–133k words before the seam restriction).
  (3) **Arm prose inflation is half the false-choice tax**: live runs
  wrote residue/false-branch passages at ~0.95x narrative weight
  (measured 392/412, 511/537, 451/472, 430/452). Texture passages now
  take a short band (~lo + a third of the span, FILL-enforced with
  the usual 20% slack), endings get +100 headroom, and the
  medium/long scene caps tightened to what models measurably write
  (~0.9x cap). (4) **The D4 mix verdict** (author's lever, measured):
  at equal depth, medium 3H+2S costs +78% words over 2H+2S for zero
  additional real choices per arc (worlds 4→8) — dominated; +1 soft
  costs ~+23% and buys a real fork per arc. Medium is 2H+3S, long
  2H+4S, hard counts stay 2. Also per the plan: weave enumeration
  fair-splits only when plain lexicographic DFS exhausts its cap
  inside one subtree (measured degeneracy: 63 units → all 64
  candidates shared a 12-position prefix; recorded micro stories keep
  plain enumeration, so the e2e fixtures replay unchanged), the
  research prompt carries a sustaining-craft nudge at deep scopes,
  and sidetracks (1-arm false branches keeping the direct edge) join
  diamonds as cadence shapes. Projection at medium, both band
  corners: 46–52.5k words, 124–142 passages, B4 99–141, B6 780,
  cosmetic:real ≈ 4:1 — every band self-consistent
  (`tests/test_scale.py` asserts this against the presets). The
  cosmetic:real ratio is capacity-bound, not density-tunable: beyond
  seam capacity the only honest feel lever is more real forks. The
  golden story is band-clean (0 errors, 0 warnings; README transcript
  updated); its 2-beat texture arm was trimmed 314→241 words to model
  the texture register, anchoring micro's B7 floor. 390 tests.

- **2026-07-10 (M8 planned — the depth & scale implementation
  contract):** Full milestone plan written to
  `docs/plans/m8-depth-scale.md` (frontier planning session; the plan
  is the hand-off contract, this entry is the record). Five decisions
  worth logging. (1) **The scale table anchors on total prose words**
  (mini-ADR A19, lands with PR-1): each preset gains a primary
  `words_total` band; B3/B4 and the other budgets become derived,
  recalibrated quantities — stored plainly (gates read numbers), with
  the derivation recorded in 01 §2 so the next recalibration is
  arithmetic. Playthrough-words-primary was rejected (feel is B6's
  job; the author holds, prints, and pays for total prose), as was the
  passage-primary status quo (passages are a collapse artifact,
  already redefined once under the old numbers). (2) **Scaffold depth
  becomes preset data** — a `ScaffoldShape` per scope replaces
  `seed_scaffold.j2`'s universal literals, enforced repairably in
  `_scaffold_apply` (the Sonnet-evaluation lesson: scaffold contract
  violations die at SEED, never at GROW's unrepairable gate); micro
  pins today's literals so the golden story and every fixture hold
  unedited. (3) **Bands are calibrated by structural simulation** —
  synthetic scaffolds at the proposed bands run through the *real*
  weave and collapse, LLM-free, and the counts plus the corpus's
  external 300–600 words/choice band set B3/B4/`words_total`; this
  breaks the calibration-circularity risk (bands tuned on stories
  generated under the old bands) and the live run confirms rather
  than defines. (4) **The cadence arithmetic is the milestone's
  central creative risk, stated honestly in the plan**: a deep medium
  playthrough needs ~23–30 choice points for B6 ≤ 800 and only ~4 are
  real forks — a ~5:1 cosmetic:real ratio. POLISH's diamond targeting
  becomes words-aware (site budgets computed from the B6 target, not
  "every 3–5 beats"), tensored residue arms (PR-1b) make
  post-convergence choices state-flavored rather than cosmetic, and —
  the author's call, same day, promoted from the plan's original
  fallback — **the dilemma budgets themselves (hard and/or soft) are a
  first-class phase-0 lever**: the simulation compares deep chains at
  current counts against +1-soft and +1-hard mixes per scope, with the
  economics stated (soft raises buy real forks cheaply, arcs are
  computed; hard raises buy volume and ending richness but multiply
  worlds for one more real choice per arc). The exit run must record
  the measured ratio either way. (5) **Weave spread is measured before it
  is fixed**: enumeration gains a spread metric and a synthetic
  clustering test at deep-medium unit counts (~25–40 units against
  the 64 cap); stratified enumeration (cap allocated across distinct
  early-position prefixes) ships only when the metric shows the
  expected clustering. Sequencing per the tiering policy: phase 0
  and everything touching I3/I7/G4/cadence math at frontier tier;
  preset plumbing, template wiring, and tests mid-tier against the
  plan's numbered decisions.

- **2026-07-10 (M7 complete: `qf illustrate`, live on both cloud
  providers — PR #33):** Built to the roadmap §M7 contract; what the
  record needs beyond it. (1) **Mini-ADR A18 landed as designed** (03
  §9): a command beside `qf export`, presence-keyed idempotence,
  library seam (`ImageService` + `register_provider` import with no
  fastmcp code, verified), engine-side orchestration. The `images:`
  project.yaml block (provider / model / aspect_ratio / quality) and
  `--provider` select the backend; keys ride `OPENAI_API_KEY` /
  `GEMINI_API_KEY`. (2) **The live exit run**: all 7 briefs of
  `examples/lamplighters-debt-craft` rendered on Gemini
  (`gemini-3.1-flash-image`, ~$0.04/image ≈ $0.28 total, zero content
  refusals), rerun confirmed free (no ledger growth), `qf export html`
  inlines all seven as data URIs, `qf export pdf` compiles 78 pages
  with 7 image XObjects; a gpt-image-2 sample of the golden story
  (budget 1, ~$0.07) landed dead-on the scratchboard art direction.
  (3) **Two latent engine bugs found live, both fixed with tests**:
  the M5 PDF illustration slot had never met a real image file — typst
  resolves `#image` paths from its *compilation root*, so the absolute
  OS paths gamebook emitted could never compile (now root-anchored
  `/art/images/…`, and `build_gamebook` requires the root whenever
  images are in play); and Gemini returns JPEG bytes no matter the
  `.png` contract everything keys on (now normalized to PNG at the
  single write site — PIL is a core dependency of the image library).
  (4) **Style adherence is the watch item, not consistency**: the
  protagonist stayed recognizably himself across Gemini's seven
  renders (fragments do their job), but 1 of 7 drifted photographic
  against the painterly direction, where gpt-image-2 followed the
  same-shaped prompt faithfully. The escalation (style-reference
  conditioning through the library's edit path) stays unbuilt until a
  run demands it — recorded on the open item. (5) **Refusal handling
  is built but unexercised live** (zero refusals in 8 paid renders):
  one utility-role reformulation on a typed `ImageContentPolicyError`,
  then report-and-continue, batch never dies for one brief — CI covers
  it with a refusing stub provider. Total live spend for the
  milestone: ~$0.35.

- **2026-07-10 (illustrations pulled up front as M7):** The author's
  call: the image backend moves from "Later" to the next milestone —
  the consuming plumbing has existed since M5 and both cloud keys are
  in the dev environment. Research across the two source repos
  settled the approach. (1) **The provider seam is a re-adoption, not
  a new bet**: `image-generation-mcp` is the hardened fork of the
  original QuestFoundry's own image providers ("Ported from
  questfoundry" in its docstrings) — consuming it as a library
  (`ImageService` + `register_provider`, importable without touching
  fastmcp code; OpenAI gpt-image-2 lineup, Gemini
  3.1-flash-image, deterministic zero-network placeholder for CI)
  returns the original's provider work with the upgrades on top,
  mirroring the markdown-vault-mcp precedent. (2) **`qf illustrate`
  is a command, not a stage pass**: OpenAI and Gemini expose no
  seeds, so rendered bytes are non-reproducible and can never join
  checkpoint byte-stability or A16 fingerprint replay — generation
  sits beside `qf export`, idempotent by file presence (mini-ADR when
  built). (3) **Orchestration stays engine-side** — the library
  deliberately has no prompt cache, budget, or ledger: NG owns
  skip-if-exists, sample-first (the heritage cost gate), `--budget` /
  priority filtering, cost accounting, and one reformulation attempt
  on a typed content-policy refusal (the failure mode the original
  swallowed). (4) **Heritage carries the consistency design**: prompt
  assembly injects art direction + per-entity visual profile
  fragments (DRESS already produces both since M5); the library's
  reference-image edit path is the escalation if sample images show
  character drift. Known trade recorded: NG keeps slug-named files
  (`art/images/<passage-slug>.png`, human-readable, presence-keyed
  skip) over the original's content-addressed store (free dedup) —
  the export plumbing already keys on slugs. Depth & scale, retrieval
  refinement, and SHIP shift to M8–M10.

- **2026-07-10 (roadmap extended: depth & scale, retrieval, SHIP):** The post-M6 deferred and
  future items across STATUS were consolidated into three milestones,
  risk-first per the roadmap's own ordering principle (numbering
  final after the illustrations insertion above: §M8–§M10).
  **Depth & scale** leads the creative-risk order because it is the riskiest remaining creative bet —
  whether the narrative/DAG mapping holds at book scale (20–60k
  words, deeper/tensored Ys, words-primary presets); every live run's
  B6 sits ~1.4–1.6× over the feel band and the fix is structural.
  **M9 retrieval refinement** packages live run 7's two retrieval
  findings (reserved exemplar mechanism, standing-query shape — the
  standing half retrieves audience boilerplate from verbatim vision
  prose, recorded as a new open item). **SHIP & the author loop**
  collects the SHIP-tied deferrals (Twee lint), the `qf run --yes`
  stub (real interactive checkpoint review), and `qf simulate
  --random` — whose documented trigger ("once false branches occur in
  generated stories") is now met on every run since calibration. The
  risks table refreshed: GROW interleaving quality and convergence
  prose coherence are retired (seven live runs, three provider
  families), replaced by the scale-era risks (cadence math under deep
  scaffolds, preset-calibration circularity, candidate-spread
  thinning) and the exemplar-leakage risk the retrieval milestone
  closes. Demand-triggered
  items (pacing report + scene_type, character-arc metadata,
  exclusive-beat intersections, cosmetic flags, non-digit codeword
  fallbacks) stay out of milestones by design — 01 §10's annotation
  discipline — and the roadmap now names them as such.

- **2026-07-10 (M6 exit: live run 7, the A/B — "The Lamplighter's
  Debt", PR #31):** One fresh `short` folk-horror premise generated
  twice on the default Opus/Haiku map: run A bare (~$3.50), run B
  grounded in the author's IF-craft corpus (~$4.03, 80 notes,
  fingerprint `41d6e056…`), both preserved under `examples/`. **The
  grounding delta is real and traceable**: run B's voice is second
  person present — the corpus's stated gamebook default — where
  ungrounded A chose third limited; B's prose leans on
  objects-carry-the-grief craft the digests surfaced; B6 reads
  slightly tighter (1138 vs 1248 words/choice). All §PR-2 mechanical
  checks passed live, including a deleted digest reproduced
  byte-identically with zero LLM calls and an edited digest surviving
  a rerun behind the freshness skip. Five engine findings, all fixed
  in-flight with violating-construction tests: (1) *the intersections
  repair error named no culprit* — groups now probe one at a time;
  (2) **a one-validation-path violation**: `queries.dilemma_flags`
  collapsed a multi-flag path to an order-dependent winner, so the
  DRESS gate passed in memory while `qf validate` failed the reloaded
  project — now list-valued and sorted, G4 accepts any of a path's
  flags, POLISH gates deterministically on the sorted-first;
  (3) *scaffold shape errors arrived one per repair round* — the model
  fixed the named arm while a sibling had the same defect and lost the
  stage chasing the moving target; all shape violations now batch into
  one error; (4) **intersections are advisory** like temporal hints
  (02 §2 amended): on run 7's dense webs (one dilemma wrapping
  everything + two serial-locked chains) even culprit-naming repairs
  couldn't converge — unsatisfiable groups are now dropped with a
  report note naming the group and why, never failing the stage;
  (5) *the exemplar leak*: unscoped retrieval filled early-stage
  digests wall-to-wall with style exemplars (atmospheric queries
  nearest-match atmospheric prose) — the 02 §1 bias vector; mitigated
  by scoping `craft.folders` to the eight non-exemplar clusters, with
  the first-class mechanism recorded as next-up #2. Calibration data:
  both runs overshoot `short`'s B3/B4 bands (35-48 passages, 48-55
  beat arcs; two locked chains add real volume) and B6 still reads
  ~1.2k words/choice — the scaffold-deepening effort owns both. The
  plan doc `docs/plans/m6-craft-corpus.md` is retired with this entry
  (its contract lives in 02 §1 / 03 §9-10; its record lives here).

- **2026-07-10 (M6 engine: research pass, A17, spike findings —
  PR #30):** Built to the PR #29 plan; what the record needs beyond it:
  (1) **The library spike passed everything** — `markdown-vault-mcp`
  3.1 hybrid ranking was deterministic across repeats *and* fresh
  index rebuilds, warm restart is O(1), a custom `EmbeddingProvider`
  ABC implementation drives hybrid search (needs `numpy` even with a
  custom provider — dev group carries library core + numpy, never
  fastembed), and fastembed loads from a warm cache in ~0.5s fully
  offline (first use downloads the model once). No upstream issues
  filed; `>=3.1,<4` pinned. (2) **Retrieval runs inside apply**, so
  kept-pass replay and A16 resume re-retrieve identically; the vault's
  tracker state routes into `cache/research/` (its default would
  pollute a read-only corpus checkout). (3) **A17 shipped as designed**
  (03 §9): freshness = digest frontmatter's corpus fingerprint +
  standing queries match current values, checked in `skip_if`, which
  the runner dispatches before keep/resume — that ordering is what
  lets a fresh digest beat a stale ledger. (4) **Injection is one
  runner-level render variable** (always defined, StrictUndefined-safe)
  — review templates never receive it, making the no-taste-laundering
  rule structural; `polish_audit` joined the exclusion list as
  review-shaped. (5) The automated reviewer caught a dangling
  citation (planning-doc-internal hazard numbering leaking into code
  comments) — worth keeping in mind when code is built from a plan
  document: cite repo artifacts, not the plan's internal labels.

- **2026-07-10 (M6 planned — the craft-corpus implementation
  contract):** Full milestone plan written to
  `docs/plans/m6-craft-corpus.md` (frontier planning session; the
  plan is the hand-off contract, this entry is the record). Four
  decisions worth logging. (1) **The library bet is largely retired
  on paper**: `markdown-vault-mcp` 3.1.0 publishes a documented
  Python API — `Vault` facade, hybrid `search(query, mode, folder)`,
  a public `EmbeddingProvider` ABC with a pinned local
  `FastEmbedProvider`, an `[embeddings]` extra — so the feared
  upstream API work shrinks to a phase-0 spike on two questions:
  hybrid tie-break determinism (the plan re-sorts `(-score, path,
  heading)` itself either way) and offline behavior on a warm
  embedding cache. (2) **A17, the plan's one real design find — rerun
  semantics for author-edited digests**: as specced, "author-editable
  artifact" would be vacuous (a rerun rewinds to the *predecessor*
  snapshot, which never contains the target stage's digest, and
  re-retrieval would clobber the edit). Resolution: `prepare_rerun`
  preserves the working tree's `research/<target>.md`; the research
  pass skips when the digest is *fresh* (frontmatter-recorded corpus
  fingerprint + standing queries match current values — corpus or
  vision edits re-retrieve, unchanged worlds reuse for free); forcing
  re-retrieval = deleting the file. Mirrors the vision.yaml
  precedent; the mini-ADR row lands in 03 §9 with the engine PR.
  (3) **DREAM's research runs premise-only** — no vision exists at
  the stage head, so standing queries start at BRAINSTORM (02 §1
  amendment with the PR). (4) **Digest injection is one runner-level
  render variable**, so review templates are structurally immune
  (they render themselves) rather than immune by convention; the
  exclusion list gains `polish_audit` (review-shaped — the same
  taste-laundering channel 02 §1 already closes). Sequencing per the
  tiering policy: contracts and prompt framing at frontier tier,
  mechanical phases delegable; engine PR first, live A/B exit run as
  a second PR once the author exports the IF-craft corpus from his
  vault (the locked-dilemmas live validation rides that premise).

- **2026-07-10 (crash resume: the in-flight proposal ledger, mini-ADR
  A16):** The open artifact-half question is decided: **not** per-pass
  prose flushing but a per-pass **proposal ledger** — every accepted
  pass journals its proposal to `inflight/<stage>/proposals/` the
  moment apply + review succeed, and re-entering an interrupted stage
  replays those passes through the existing `rerun --keep` machinery
  (schema-validate → apply through the mutation layer, no LLM call).
  Prose flushing was rejected on three grounds: a write pass produces
  more than prose (entity micro-details; the voice pass produces the
  Voice — files alone lose graph state), partial prose in the working
  tree breaks 02 §1's checkpoint definition, and reloading flushed
  prose before re-running from pass 0 can leak later-written
  predecessor prose into earlier windows (writing order is
  reference-arc-first, not globally topological), silently breaking
  the byte-stability fixed on 2026-07-08. Two hardenings shipped with
  it, both found in design stress-testing: (1) a **stage-input
  fingerprint** (vision/voice/graph/prose/art/codex bytes + steering +
  fill_seed + llm config) voids the whole ledger on any author edit —
  without it the ledger would silently replay stale proposals where
  the cache would have regenerated, a regression against "review =
  edit + revalidate"; (2) ledger writes are atomic (`os.replace`) and
  reads tolerant — a torn entry is stale, never fatal. The staleness
  contract splits by intent: auto-resume degrades to a live run with a
  report note; explicit `--keep` stays fail-loud and takes precedence.
  The checkpoint consumes the ledger; `prepare_rerun` discards all of
  `inflight/` (a rewind ends every interrupted run); a gate failure
  retains it, so unchanged-input retries reproduce the failure free.
  Uniform across all stages (A4) — DRESS and GROW passes are now as
  crash-resumable as FILL's — and independent of the LLM cache, which
  remains the second net for a pass that died before its ledger write.
  Also fixed in passing: `.gitignore` now actually ignores `cache/`
  (design doc 03 §6 claimed it already; the drift would otherwise have
  extended to `inflight/`). 13 new tests including an e2e that kills
  FILL mid-stage at a pass boundary and proves the resumed story is
  byte-identical to an uninterrupted run with zero re-spent calls.

- **2026-07-10 (summary register: briefs, not prose):** The author
  flagged that generated beat summaries arrive as finished prose ("her
  heart the last casualty of the lock-in" — a GROW contextualize
  rewrite in the Bubblegum Alibi), though FILL owns the words. The
  diagnosis: every summary-writing prompt injects the vision's tone two
  lines above a "events, not prose" instruction, and a prohibition
  loses to that pull every time. The fix follows the author's insight —
  tell the model what its output is *for* instead of what it must not
  be: a shared prompt block (`_summary_brief.j2`, included by SEED
  scaffold, GROW contextualize/bridge, POLISH finalize/passages) frames
  every summary as a brief for the prose writer who comes later, with
  one stated-vs-performed contrast pair ("the mentor is dead and the
  group blames Rell" is a brief; "grief hangs over the camp like early
  winter" is prose) and the incentive spelled out (imagery spent in a
  summary is stolen from the page). FILL's write prompt gets the
  mirror-image line: summaries are the brief, not the style — the
  Voice owns how anything sounds. Design doc 01 §5 now names the
  register authoritatively and files pre-voiced summaries in the
  bias-vector family (a style anchor smuggled past the Voice — the
  canonical-answer trap again). Deliberately NOT a gate or review
  rule: "flowery" is taste, and the review-legibility lessons say a
  cheap reviewer given a taste rule will launder it. The golden story's
  own summaries were swept to model the register (three similes and a
  personification removed; prose untouched). Validation rides the next
  live run (next-up #2).

- **2026-07-10 (locked dilemmas + richer residue):** The structural
  volume/depth effort, built as designed with five decisions worth the
  record. (1) **The disposition is topology, not a marker** (mini-ADR
  A15): a locked dilemma is exactly "one explored path" — heritage's
  own definition (an answer with no `explores` edge is the permanent
  shadow) — so nothing can drift; `queries.locked_dilemmas` /
  `branched_dilemmas` partition by explored-path count, and arc math
  never sees locked dilemmas at all (no selection, no multiplication).
  (2) **Locked outcomes are world facts, never flags**: every reader
  holds them, so a flag could gate nothing and would only bloat I12's
  universe — G3-FLAGS now rejects in both directions (a locked
  consequence needs no flag; a flag on a locked path is an error), and
  FILL reads the outcome from the beats. (3) **A locked chain weaves
  one movable unit per beat** under chain constraints — the storyline
  threads through the story instead of lumping — with wraps/serial
  anchored at its first beat and its resolution; only *branched* hard
  dilemmas make worlds or qualify as the climax (a locked hard-role
  question is texture, not backbone). Locked beats are on every arc,
  so they became intersection-eligible alongside shared pre-commit
  beats. (4) **No dilemma cuts at triage**: BRAINSTORM's overgeneration
  (branched budget + locked allowance, B1 as a pre-triage range) is
  absorbed entirely by locking — every dilemma gets a disposition, all
  arithmetic enforced repairably at triage apply so a bad disposition
  costs a repair round, not a dead stage. (5) **Richer residue is the
  diamond**: one gated arm per path per world (G4 strengthened from
  "any arm" to per-path — the story must remember whichever side was
  chosen), arms of 1–2 beats via `followup`, and the collapse rule
  refined from "gated beats are singletons" to "identical gates merge",
  so a multi-beat arm is one gated passage (the gate boundary is where
  the passage breaks, not every gated beat). Deferred, recorded on the
  open item: tensoring a shape inside a diamond arm. The golden story
  grew to exercise everything (locked second-keeper subplot, both
  residue arms, the 2-beat arm) and, at 8 passages, the print
  numbering constraints became satisfiable — the documented 7-passage
  impossibility is gone, and the README transcript no longer shows a
  numbering warning. Not yet run against a live model; folded into the
  next-up list.

- **2026-07-09 (Sonnet 5 evaluation — closed, keep Opus):** Question under test:
  can `claude-sonnet-5` ($3/$15 per MTok, $2/$10 intro through
  2026-08-31) replace `claude-opus-4-8` ($5/$25) as architect/writer in
  the default model map? Method: the same Bubblegum Alibi premise +
  dream steering, fresh project (`medium`, recalibrated presets), full
  DREAM→DRESS run on an all-Sonnet map, judged against the preserved
  Opus run on cost, repair rounds, gate cleanliness, and prose. Two
  adapter findings before GROW even started, both fixed here: (1)
  Sonnet 5 runs *adaptive thinking by default* and thinking tokens
  bill/count against `max_tokens` — the 8192 default starved a writer
  call into an empty response after ~7.5k-token thinks on architect
  calls (Opus never exceeded ~3k output). Adapter default is now 32768;
  unused budget costs nothing. (2) The Anthropic SDK rejects
  non-streaming requests whose `max_tokens` implies a >10-minute worst
  case — the provider now streams and collects the final message, same
  contract otherwise. **Default-config verdict: not faster, not
  cheaper.** Aborted mid-run (author's call) at the GROW/POLISH
  boundary — at the abort decision, 11 Sonnet calls had emitted 88k
  output tokens (single GROW calls at 18–22k, ~90% billed thinking)
  versus 74k for the *entire* 63-call Opus run; one more in-flight
  call completed before the kill, putting the run's final ledger at
  12 calls / 107k output / $1.18 intro. Pace projected $5–8 intro
  for the full story versus Opus's $3.24,
  and slower wall-clock. Second experiment in flight: the provider now
  takes an optional `llm.thinking` config ("disabled" opts out of
  Sonnet 5's thinking-on default; unset sends nothing, so the Opus
  default map is untouched), and the same premise is rerunning
  thinking-off through FILL — enough to judge structure + prose
  quality at the config where Sonnet actually is cheap (~$1–1.5 per
  medium story at intro pricing). First thinking-off finding, and the
  first engine improvement a cheaper model has bought us: it violated
  the scaffold prompt's explicit ending contract (endings on one hard
  dilemma's tails but not the other's) and under-built one soft arm —
  neither caught until GROW's unrepairable gate, ~10 wasted calls
  later (I6 ×16, I7 ×1). `_scaffold_apply` now rejects both shapes as
  repairable `ApplyError`s at SEED (hard tails must be endings, ending
  nowhere else, soft arms carry the scope's `min_payoff_beats`), with
  violating-construction tests (`tests/test_seed.py`) and the SEED
  contract paragraph in design doc 02 extended. Opus never tripped
  this; a model that does now costs one repair round instead of a dead
  stage. The rerun then repaired SEED on the first live round, passed
  GROW's gate, and cleared POLISH — before FILL died on the next
  finding: thinking-off Sonnet writes *literal newlines* inside JSON
  strings (prose payloads), which strict JSON rejects as control
  characters, and it repeated the mistake on retry. The adapter now
  parses with `strict=False` — that relaxes only control-chars-in-
  strings (unambiguous intent in a prose payload); structural errors
  still raise and retry.

  **Final verdict (author's call, run aborted in FILL): keep
  `claude-opus-4-8` as the default architect/writer.** Thinking-on
  Sonnet is strictly worse here: 2–3× the cost (billed thinking
  dominates: 107k output tokens in 12 calls vs 74k for Opus's whole
  63-call run) and slower. Thinking-off Sonnet is genuinely cheap
  ($0.65 through POLISH; a full run would land ~$1–1.5 intro vs Opus
  $3.24) but needed three engine interventions in one partial run —
  a scaffold-contract violation Opus never made, repeated
  JSON-discipline failures, plus the shared adaptive-thinking/
  streaming adapter fixes — and still never produced a passage to
  judge. The failure profile fits the model-economics table's
  prediction for sub-frontier tiers on narrative/DAG semantics; the
  three hardening fixes (SEED apply-time scaffold rules, max_tokens
  headroom + streaming, lenient string parse) are the evaluation's
  lasting value and stay regardless of model choice. Total tuition:
  ~$1.83 intro ($1.18 thinking-on final ledger + $0.65 thinking-off
  through its FILL abort). Evaluation projects left at
  `/home/user/stories/bubblegum-sonnet{,-nothink}` (session-local,
  not committed).

- **2026-07-09 (live run 6, validation micro — "The Cartography of
  Small Kindnesses", PR #24):** Fresh micro premise (they/them
  protagonist by design) validating the calibration batch. Results:
  framing prompts held (4 entities, all anchored, zero G1 warnings —
  the medium run had three), pronouns held (Wren consistently
  they/them through every passage and micro-detail; the field renders
  as "PRONOUNS: they/them, exactly"), cadence diamonds engaged hard
  (22 passages at micro vs 7–17 in every earlier run), and B6 measured
  ~1072 words/choice even so — the diamonds each add prose along with
  their choice, so the marginal rate improves slowly; closing the feel
  gap needs the locked-dilemmas effort, exactly as planned. Five
  findings, all fixed in-flight: (1) *review rule 1 misread POV* — a
  scene opening on another character's actions was failed as "third
  person"; rule 1 now defines a departure (narrator in the wrong
  person, or narration beyond their perception) and names the
  non-cases. (2) *the amnesiac reviewer never converges* — after the
  writer fixed round 1's genuine defect, round 2 failed on brand-new
  taste; review rounds now carry prior rounds' issues into the prompt
  (persistence is signal, novelty is usually taste). (3) *the halt
  verdict needed an arbiter* — prompt fences hit the cheap reviewer's
  ceiling (somatic rendering flagged as "naming emotion"; a rule-4
  complaint about a state that is no listed flag), and every stage
  halt across every run has been reviewer noise: a second failure now
  escalates once to an architect-tier arbitration whose strict verdict
  is final (design doc 02 FILL; tiering policy: escalate rather than
  improvise). (4) *the id contract had a hole at beat applies* — a
  diamond arm carrying entity display names ('Wren') sailed through
  every gate until DRESS's brief check collided with it; a shared
  `resolve_entity_ref` (types.py) now guards every apply that stores
  entity refs on a beat (SEED scaffold, GROW bridge, POLISH residue
  and arms) — FILL's micro-detail resolver generalized, per mini-ADR
  A11. (5) *the codex review had the same disease as FILL's* — it
  double-failed spoiler-safe entries by quoting the conditional-
  material list from its own context as "the entry's assertion" (the
  entry explicitly left the question open, which is what spoiler-safe
  means); the anchored+arbitrated contract generalized to DRESS
  (passes become per-run computed so review state can't leak), and
  rule 1 now defines assertion. Final: **complete at ~$2.75** over all
  attempts (174 calls, 41 cached; opus 231k in / 58k out) — 22
  passages, 8,810 words, 4 arcs, 2 endings, full enrichment (codewords
  KNOTTED / UNFOLDS), all exports round-trip clean; preserved as
  `examples/small-kindnesses/`. Meta-lesson for the record: the
  reviewer-contract failure class (live runs 1, 3, and now 6) kept
  yielding to wording fixes one instance at a time; the arbitration
  mechanism ends the class by making the expensive judgment structural
  instead of textual.

- **2026-07-09 (scope recalibration: the passage numbers were beats):**
  The author identified why B3 missed by 3x: the original scale numbers
  (medium 60–90) were *beat* counts from the era when one beat was one
  passage; the passage collapse silently redefined the unit under them,
  and heritage's surplus passages came from window-dressing choices.
  The author's second insight: how big a story *feels* is how many
  choices you make and how many passages you traverse — not inventory.
  The craft corpus agrees and supplies the band (scope-and-length note:
  ~300–600 words per choice reads as balanced agency; 1000+ reads as
  a book). Decisions: (1) passage bands recalibrated to structural
  yield (medium 25–40, measured; others extrapolated), documented as
  such in design doc 01 §2; (2) **B6** added — average words traversed
  per *genuine* choice per arc, target 250–800; a choice is offered
  when its gate is satisfiable, not when its target is on the same arc
  (the first draft under-counted exactly the real forks); (3) POLISH's
  false-branch pass is cadence-targeted (a diamond per ~3–5 beats of
  choice-less run, arms of 1–2 beats via an optional followup beat) —
  safe as dressing precisely because the dilemma structure guarantees
  the real choices, which inverts the corpus's false-choice-tax
  warning; (4) medium word cap 650 (opus climax endings run ~600);
  (5) DREAM/BRAINSTORM prompts reframed to their epistemic position
  (vision = texture not inventory; brainstorm = ingredients, anchor
  what you invent); (6) `Entity.pronouns` explicit end-to-end with a
  numbered FILL-review rule. The structural volume fix — locked
  dilemmas (heritage lookup confirmed: a triaged dilemma may explore
  one answer as a woven linear storyline) plus richer residue diamonds
  — is the designed next effort (open items); corpus-medium word
  totals (20–60k) wait for scaffold deepening after M6.

- **2026-07-09 (M5 exit: live run 5, the first medium — "The Bubblegum
  Alibi", PR #23):** Closed-circle murder mystery in a bubblegum
  high-school setting; claude-opus-4-8 architect/writer +
  claude-haiku-4-5 utility; premise → complete DRESSed story with all
  exports (incl. print PDF) for **~$3.25 / ~24 min** across eight
  attempts — the first live exercise of multi-hard weaving, fork-rejoin
  under bridges, and crash-resume at scale. Six findings, all fixed
  in-flight with violating-construction tests, all in territory only a
  multi-hard live run could reach: (1) *bridge into a fork commit* —
  the bridge pass spliced a shared bridge into one commit of a fork,
  dead-ending sibling arcs (I6 ×4); a gap into a fork commit is a gap
  into the fork — the bridge now spans the whole frontier and `_gaps`
  verifies coverage against real arc views. (2) *POLISH couldn't see
  through bridges* — new `queries.frontier_feeds` makes bridges
  transparent for arrival questions; the residue splices on the tail's
  side. (3) *`save_project` never deleted files of removed nodes* —
  the weave's removed template beats resurrected on reload as orphan
  roots with commit impacts; every per-node directory now prunes to
  the live node set on save (the single-process e2e could never see
  this; only a real crash-resume could). (4) *I12 counted upstream
  grants, not ambiguity* — at a 2-hard climax ending every upstream
  flag is a world fact; I12 now caps only ambiguous flags (grant and
  opposing commit both upstream), one computation
  (`queries.ambiguous_flags`) shared by gate and audit; design doc 01
  §8 refined. (5) *micro-detail keys are single-assignment* — the
  writer kept proposing a second `tell` for the character the scene
  was about; the prompt now states the rule and the refusal names the
  corrective action (the review-contract lesson again: write for the
  cheapest reader — including repair errors). (6) *exact word windows
  are unhittable* — 553 then 613 words against a 200–550 cap exhausted
  repairs; apply now enforces with 20% slack (band catches runaway/
  skimpy, review owns quality; G5 row updated), and whether medium's
  cap should rise is preset calibration (open items). Calibration
  data recorded in open items: prompt framing (vision/BRAINSTORM
  overpromise — the author's sharper diagnosis: early stages speak
  with certainty their pipeline position doesn't grant), medium preset
  ranges (20 passages vs B3's 60–90 comes from SEED's scaffold depth,
  not a prompt miss), and the weave/`world_of` first data point.
  Tooling note: committing each stage checkpoint to the PR as it
  landed made the run reviewable in-flight — the automated reviewer
  independently confirmed finding 3 from the committed artifact.

- **2026-07-09 (M5: multi-hard weave):** The tensor model (design doc
  01 §5) is realized with four decisions confirmed with the author.
  (1) **The nesting order is an interleaving choice**: candidates are
  enumerated once per viable climax (each hard resolve as final unit,
  an even share of the cap), the weave LLM picks; `wraps`/`serial`
  between hards constrain the enumeration — no new SEED contract.
  (2) **Between-fork placement is in scope**, not just the climax
  resolve: any unit after the first hard fork (inner pre-commit
  development, whole soft dilemmas via `serial(hard, soft)`) is
  instantiated per world — this is the heritage-canonical reading
  ("an inner-dilemma beat materializes once per world"), and it made
  soft-convergence, residue coverage, payoff, and heavy variants
  per-world concepts throughout. (3) **Symmetric instantiation**: the
  template Y is removed and every world gets a fresh world-suffixed
  copy — keeping the SEED beats as "world one" would be a
  canonical-world bias vector, the same trap as the removed canonical
  answer (mini-ADR A14). (4) **GROW de-ends and rewrites**: SEED still
  authors every hard Y complete with endings (the mini-story
  property); realization clears `is_ending` on the earlier forks'
  tails and the new *contextualize* pass rewrites clone summaries per
  world and de-ended tails to leave the climax open — structure is
  copied by the engine, words never are. Two check subtleties worth
  remembering: worlds are made by *other* dilemmas' hard forks (a
  dilemma's own commits are its fork, never its coordinate — otherwise
  a duplicate commit downstream of the first looks like "another
  world" and I3 goes blind), and G4's light-residue coverage matches
  residue beats to worlds by hard-commit ancestry, not adjacency.
  Deferred: units after the *last* hard fork (nothing may follow the
  endings — the climax resolve is always final), and intersections
  inside worlds (groups stay in the truly shared region; a cloned
  "shared scene" isn't shared).

- **2026-07-09 (M6 added: craft-corpus research):** The author's IF
  craft corpus (once `if-craft-corpus`, now living and much extended in
  his Obsidian vault; its indexing engine evolved into
  `markdown-vault-mcp`) should ground the pipeline's LLM calls. The
  original QuestFoundry exposed the corpus as a *tool* the model called
  mid-generation, because what a stage needs is content-shaped and hard
  to predict programmatically. That mechanism is incompatible with NG's
  one-shot adapter, content-addressed cache, and fixture replay (A3) —
  so NG splits the judgment from the fetch: a **research pass** at each
  stage head emits queries (an ordinary typed proposal), the engine
  retrieves via hybrid search and **persists the digests as a
  checkpointed artifact** later passes read (mini-ADR A13). Two design
  corrections from the discussion, both author pushback: (1) no
  exact-key retrieval anywhere — vision genre/tone are open vocabulary
  ("maritime folk horror" keys to no note), so even the engine's
  standing queries are search-ranked over several related notes;
  (2) **corpus material may widen or ground, never bind** — style
  exemplars appear at the voice pass as a contrasting spread, never a
  nearest-match target (clone risk compounds through the prose window),
  fade from write contexts once neighboring prose exists, and never
  enter review prompts (a third taste-laundering channel, declined).
  Milestone M6 in the roadmap; M5 finishes first.

- **2026-07-09 (M5 slice: DRESS, print, rerun — PR #20):** Codeword
  *suggestion* moved from POLISH (design doc 04's original wording) to
  DRESS pass 4 — "drawn from the story's diction" needs the voice and
  prose to exist, and neither does until after FILL; *projection*
  (which flags become codewords) stays a SHIP-side deterministic rule:
  exactly the gate-tested flags (mini-ADR A12; docs 02/04 updated).
  Enrichment (direction, profiles, briefs, codex) lives on the Project
  like the Voice, not in the graph — DRESS describes the story rather
  than being story structure — and gates see it via an explicit
  `run_checks(enrichment=…)` parameter, keeping the one-validation-path
  property. The runner's failed-apply restore set widened to include
  enrichment (apply functions may now mutate it), and the automated PR
  review caught that kept-proposal replay (`rerun --keep`) needed the
  same restore — the fix carries a partial-mutation regression test.
  Rerun semantics: rewind restores what the stage and its successors
  *produced* (graph, prose, art, codex, voice) and preserves what the
  author *steers with* (steering, vision.yaml, seeds) — editing those
  is the reason to rerun. Print facts worth remembering: typst-py
  compiles fully offline with embedded fonts but refuses input files
  outside its project root (the temp `.typ` is created inside the
  project); the 7-passage golden story provably cannot satisfy all
  three numbering-constraint families at once (brute-forced — minimum
  one violation), so the best-effort-plus-warning path is its expected,
  tested behavior, and the README transcript shows the warning. Built
  per the tiering policy: two mid-tier subagents implemented DRESS and
  the gamebook against written contracts; this session owned the
  contracts, the spine (enrichment models/IO/gate plumbing,
  `projected_flags`, rerun machinery), integration, and review.

- **2026-07-08 (crash-resume replay made exact):** The leak recorded
  after live run 4 is fixed at its root: `fill.py::_neighbor_prose`
  now returns window/lookahead entries in canonical (passage id,
  label) order instead of raw edge-store order. Store order was the
  only context ingredient that differed between a live run and a
  reloaded project (choice edges reload grouped by source file; beats
  were already topo-sorted, flags already id-sorted, out-edge order is
  file-order-stable), so the write-context prompt is now byte-stable
  across save/load and cache replay of a crashed FILL is exact and
  free. Parallel predecessors are alternative branches with no
  narrative order to preserve, so id order is as principled as any.
  Two violating-construction tests: same window regardless of wiring
  order, and in-memory context == reloaded-project context with
  wiring deliberately reversed from filename order. One-time cost:
  cache entries recorded before this change key on the old prompt
  bytes, so replays of pre-fix runs (e.g. the Salt-Glass Choir cache)
  re-spend at multi-predecessor passages once. The per-pass prose
  flush question stays open (see open items).

- **2026-07-08 (live run 4 — the first Gemini-driven generation):**
  "The Salt-Glass Choir" (fresh premise, micro scope) on the new
  `providers/gemini.py` — gemini-3.1-pro-preview architect/writer +
  gemini-2.5-flash utility — completed **first attempt, end-to-end,
  with zero engine or prompt bugs surfaced**: 24 beats, 14 passages
  (two false-branch diamonds, residue beats on both soft-dilemma
  paths, two bridge beats, and a `wraps` relation exercised), 4 arcs,
  0 gate errors, 4/4 arcs simulate complete, all three exports
  round-trip clean; preserved as `examples/salt-glass-choir/`.
  Budget: 46 calls, pro 42k in / 80k out, flash 23k in / 35k out —
  roughly ~$1 at pro-tier list pricing; one adapter schema retry
  total, FILL repair rounds on two passages (2 and 3 attempts),
  everything else first-shot — the hardened review contract held on a
  third reviewer family with no new lessons. Provider notes: Gemini's
  thought tokens are billed as output, so the provider counts
  candidates + thoughts as `output_tokens`; the models API still
  *lists* `gemini-3-pro-preview` but calling it returns 404 "no longer
  available" — probe a model id before pinning it in a model map.

- **2026-07-08 (live run 3 — the first Claude-driven generation):**
  "The Orchard of Hours" (fresh premise, micro scope) on the default
  model map — claude-opus-4-8 architect/writer + claude-haiku-4-5
  utility — is **the first story the pipeline generated on Claude**:
  24 beats, 10 passages (incl. a false-branch diamond and two
  fork-frontier residue beats — this premise also produced the
  fork-rejoin topology, handled cleanly by the PR #15 fix), 4 arcs,
  0 gate errors, 4/4 arcs simulate complete, all three exports
  round-trip clean; preserved as `examples/orchard-of-hours/`.
  Budget: 43 calls, opus 76k in / 22k out, haiku pennies —
  **~$0.95**, with **one repair round total** (intersections), the
  cleanest live run yet; opus needed ~4x fewer output tokens than
  gpt-5 for the same shape of work (no reasoning-token inflation on
  chat completions). One attempt failed mid-FILL and yielded the
  taste-laundering review-contract lesson (entry below); under the
  hardened contract all ten writes converged with haiku reviewing.

- **2026-07-08 (live run 2 — id-contract validation):** Second live
  generation ("The Cartographer's Debt", fresh premise, micro scope,
  gpt-5 architect/writer + gpt-4.1-mini utility — chosen because the
  Anthropic account has no credits, see open items, and gpt-5 is the
  distribution that produced the original id failures). Outcome: **a
  complete story — 24 beats, 7 passages, 4 arcs, ~350-word passages —
  0 gate errors, 4/4 arcs simulate complete, all three exports
  round-trip clean.** The id contract **held**: zero id-shaped repairs
  anywhere — the POLISH audit cited every passage and flag by full id,
  and all 10 FILL micro-details arrived with exact entity ids, so the
  retired display-name matcher was never missed. The run took four
  attempts and each failure was a real engine/prompt bug now fixed
  with its own entry and test (fork-rejoin convergence; finalize
  repair errors that didn't name expected values; a review contract
  the utility model misread). Budget across all four attempts: 40
  calls, gpt-5 46k in / 83k out, utility pennies — **~$0.90 total**;
  repair rounds: finalize 3 attempts, everything else first-shot.
  The project is preserved as `examples/cartographers-debt/` (like
  the Winding House, PR #14): project/vision/voice, graph, prose —
  snapshots, ledger, cache, and exports excluded. Structurally it is
  the fork-rejoin story: both residue beats splice before both hard
  commits, the topology the fix exists for.

- **2026-07-08 (review contract legibility):** Fourth live-run lesson,
  extending the first run's reviewer-discipline fix: the utility
  reviewer failed a passage twice *for being written in the voice's own
  required POV* — it misread the review prompt's one-line rule ("a
  banned pattern appears (banned: ...), or the POV (...) or tense (...)
  is broken") and treated the required first person as banned, so the
  write pass could never converge. `fill_review.j2` now separates
  REQUIRED (pov, tense — prose in them is correct; fail only on
  departure) from BANNED (a bulleted list), and narrows leakage to
  naming the machinery itself (ids, or "flag"/"beat"/"path" used
  mechanically) — in-world objects that flags merely describe are
  story, not leakage. Prompt-only; positional fixture replay is
  unaffected. The pattern across both reviewer lessons: contract text
  that a frontier model reads correctly can still be ambiguous to the
  small model actually holding the pen — write review contracts for
  the cheapest reader. *Extended same day (first Claude run):* the
  haiku reviewer laundered taste through the objective categories —
  a cliché became "state dishonesty", the ordinary verb "beats"
  became "potential leakage". The contract now says taste must not be
  relabeled as a rule, requires each issue to cite its rule number
  and quote the text, and rules out hedged findings ("risks",
  "potential", "could be") outright.

- **2026-07-08 (fork-rejoin convergence):** The id-contract validation
  run surfaced a real structural bug: when the weave places a soft
  dilemma's resolve unit directly before the hard resolve (a legal,
  common interleaving), the soft diamond rejoins at the hard fork and
  there is no single convergence beat. `soft_convergence` ("first beat
  reachable from both commits, in topo order") returned one **hard
  commit** — a beat not on every arc — and the residue splice then
  dead-ended every arc on the other hard branch (two I6 errors at
  POLISH's gate). Fix, per the tensor model (design doc 01 §5): the
  rejoin is a *frontier* — the minimal shared descendants of the two
  commits — usually one beat, one per world at a hard fork. New query
  `soft_rejoin_frontier`; `soft_convergence` returns a beat only when
  the frontier is single; the residue splice inherits the tail's edge
  into every frontier beat, so the residue exists in every world; G4
  reports heavy residue at a fork-rejoin as explicitly unsupported (M5
  per-world variants) instead of wiring variants at a wrong beat. The
  freeze record still stores only single-beat convergences — a fork
  frontier is the hard dilemma's commits, already frozen under forks.
  Violating-construction tests build the fork-rejoin story through the
  real weave. Design doc 01's convergence definition updated.

- **2026-07-08 (id contract):** The PR #12 open item is resolved as
  agreed (mini-ADR A11, design doc 03 §5): the adapter's JSON
  instruction now states the id contract once, globally — every node
  reference is the full `kind:slug` id exactly as it appears in the
  prompt — and `_resolve_entity`'s display-name branch is retired;
  micro-detail apply accepts only exact ids and the unambiguous bare
  slug (prefix restoration is parsing, not prediction). Repair errors
  keep naming the expected ids — and the validation run exposed one
  straggler: POLISH's finalize residue errors named only the offending
  value, so the repair loop couldn't converge when the model echoed a
  prompt annotation ("(residue: light)") into the dilemma field; both
  errors now enumerate the expected set, with a test mirroring the
  live failure. The violating-construction test for `_resolve_entity`
  now asserts display names are *rejected*. Validation: the intended
  Anthropic live run is blocked on billing (see open items), so the
  prompt-side fix was validated with a second live gpt-5 run — the
  distribution that produced the original id failures — on a fresh
  premise ("The Cartographer's Debt", micro scope); results in the
  "live run 2" entry above.
  Positional fixture replay is unaffected by the instruction change
  (fixtures key on call order, not prompt bytes), and the recorded
  fixtures already cite entities by full id.

- **2026-07-08 (live run):** First live generation: fresh premise
  ("The Winding House"), micro scope, gpt-5 architect/writer +
  gpt-4.1-mini reviewer, record mode. Outcome: **a complete story — 30
  beats (22 frozen + 8 POLISH-added, incl. live false branches), 17
  passages, 4 arcs — with 0 gate errors and 0 runtime
  problems**, end-to-end in ~1h wall-clock and ~$2.50 (95 calls; gpt-5
  124k in / 219k out incl. reasoning; the utility reviewer cost
  pennies). The run surfaced and fixed three robustness gaps, each now
  a violating-construction test: (1) models drop id namespaces — the
  POLISH audit accepts slug-form ids and repair errors name the
  expected set; (2) **a taste-based reviewer under the two-round limit
  can never converge** — each round finds a fresh stylistic opinion, so
  the "structure is wrong" halt tripped on style nits; the review
  prompt now confines *failure* to objectively checkable defects, and
  post-fix the loop demonstrably converges (fail → fix → pass); (3)
  models cite entities by display name — micro-detail apply resolves
  any unambiguous id/slug/name reference. Repair-round rates for budget
  planning: DREAM/BRAINSTORM 1 attempt, SEED ~2, GROW intersections up
  to 3, FILL writes averaged ~1.7 attempts. The three failures cost
  ~$0.60 of the total — cheap tuition.

- **2026-07-08 (M4):** FILL's review is a post-apply hook on the
  uniform repair loop (mini-ADR A10) and its pass list is computed from
  the project — the runner stays the only orchestrator. The reference
  arc is `fill_seed`-selected, stage-local, and tested to be genuinely
  seed-sensitive. Prose is stored on Passage nodes in memory and as
  sibling `prose/*.md` on disk (the YAML never carries it). Micro-
  details go through `add_entity_detail`, which refuses to overwrite
  established facts. Exports: the runtime JSON validator re-walks the
  exported document with no graph access, so export-only bugs can't
  hide behind graph validators; `qf export` refuses to write anything
  that fails it; the Twee IFID is persisted by touching project.yaml
  only (an export must not rewrite the project). Golden prose and the
  e2e prose fixtures were drafted by mid-tier subagents against written
  contracts and reviewed here — the tiering policy's intended shape.
  Voice's design-doc field "register" is `diction` in code (pydantic
  shadow warning); recorded here so nobody "fixes" it back.

- **2026-07-08 (M3):** Passage collapse is fully deterministic and the
  golden story is its oracle — the engine reproduces the hand-authored
  grouping and choice topology (endpoints, gates, grants) exactly; the
  LLM writes only words (summaries, labels, ending titles, residue and
  variant content, feasibility judgments). Choice grants derive from
  commit beats contained in the target passage; gates from the target
  head's `requires_flags`. Variant passages for heavy-residue
  convergences are wired behind disjoint per-flag gates, and a variant
  choice is only offered from sources where its gate is holdable
  (otherwise I10 would rightly reject it). Gated (residue) beats are
  always singleton passages. Same-label sibling choices are legal only
  behind different gates (the runtime hides all but one). `qf play`
  implements design doc 04's runtime semantics directly on the graph;
  the runtime JSON arrives with SHIP in M4.

- **2026-07-08 (PR #1):** Design docs merged as authoritative; departures
  from the original QuestFoundry recorded per-doc.
- **2026-07-08 (PR #1, revision):** No canonical/default answer marker in
  the data model — known bias vector; FILL uses a stage-local seeded
  reference arc instead.
- **2026-07-08 (PR #3):** `requires-python >= 3.11` (design said 3.12;
  nothing needed it; CI runs 3.12). No `networkx` — toposort/reachability
  hand-rolled (~10 lines each at this scale).
- **2026-07-08 (PR #3 review):** Intersection groups got disk I/O
  (`graph/intersections/*.yaml`); embedded answers/consequences preserve
  non-default `created_by`.
- **2026-07-08 (PR #5):** Automated PR review is CI-gated and follows
  `REVIEW.md` (no CI reproduction, `file:line` citations, converge).
- **2026-07-08 (PR #6):** `AGENTS.md` is the single source of agent
  instructions (`CLAUDE.md` imports it); this file is the living
  hand-off; PR template enforces the documentation contract.
- **2026-07-08 (PR #8):** SEED wires *intra-dilemma* Y ordering edges
  itself (the Y's internal order is a scaffold fact); GROW owns only the
  cross-dilemma weave. Design doc 02 updated. Also: `Stage.NEW` for
  scaffolded projects; G0 joined the validator registry; proposals carry
  content while the engine derives structure. M1 built per the tiering
  policy: two Sonnet subagents implemented `llm/` and `runner.py`
  against written contracts; frontier session owned stage semantics,
  prompts, fixtures, and integration.
- **2026-07-08 (M2):** The weave treats each dilemma's fork as one
  atomic unit (diamond / terminal split) on a linear spine of shared
  units, and realization *recomputes the whole ordering edge set* rather
  than patching SEED's seams — idempotent, and the only way splices stay
  honest. Intersections are proposed *before* the interleaving choice so
  member adjacency is a constraint, not a hope. Temporal hints are
  advisory by design (dropped + reported when unsatisfiable) — SEED
  cannot see the whole weave, so its hints must not be able to wedge it.
  The LLM never emits an order, only an index into engine-enumerated
  candidates. Flag ids reuse their consequence's slug
  (`consequence:elias-knows` → `flag:elias-knows`). Freeze happens
  inside GROW's gate callable, after checks pass and before checkpoint
  save. Multi-hard weaving deferred to M5: per the original source
  documents and review discussion, the settled model is the weave as a
  **tensor of Y graphs**: soft dimensions collapse at convergence into
  flags/residue; hard dimensions stay expanded, so an inner beat's
  dilemma-relative meaning is copied per world while the realized
  beats stay distinct (content follows the full coordinate). M2's
  spine is the flattened one-hard special case; the weave rejects >1
  hard dilemma until M5 builds true expansion — see open items for the
  invariant refinements it needs. (This entry was revised three times
  — "impossible" → "duplication machinery" → tensor-of-graphs — a real
  misunderstanding corrected against the source documents; kept here
  as the record.) Hardening from the episode: heritage source docs
  imported reference-only under `docs/heritage/`, danger zones recorded
  as design doc 01 §9, and AGENTS.md now directs doc-silent questions to
  heritage before first-principles derivation — the stranding mode of
  the original was exactly this understanding decaying across sessions.
  M2 was frontier-authored
  end-to-end: the weave semantics *are* the narrative/DAG mapping, and
  every module touched them (per the tiering policy's escalation rule,
  not despite it).
- **2026-07-08 (PR #7):** Model-tiering policy in `AGENTS.md`: frontier
  models (Fable/Opus) own semantics/design/integration/final review;
  mid-tier (Sonnet) implements against written contracts; small tier
  (Haiku) does mechanical work. Expensive sessions delegate typing;
  cheap sessions escalate semantics instead of improvising. Mirrors the
  pipeline's own `architect`/`writer`/`utility` roles (design doc 03 §5).
