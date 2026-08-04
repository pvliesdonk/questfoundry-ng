# Register Conformance — continuation framing, declared recurrence, richer notes (Build Contract)

> Status: **PR-1 + PR-2 BUILT.** PR-1: manuscript-first `fill_write.j2`,
> depth-2 window + fan-in cap, lookahead convergence rules, register
> budget on both writer and reviewer sides, `register_budget` warn rule;
> design doc 02 FILL section updated; acceptance harness re-run on the
> star-swabber opening (plain register, depth-2 window firing). PR-2:
> `Voice.recurring_devices` (escalate/verbatim/texture), the voice-pass
> declaration, the echo guard's declared-verbatim exemption with the
> laundering bound + violating-construction tests, writer/reviewer
> device rendering; design doc 01 Voice section updated. PR-3: the
> story-so-far ledger — `SummaryProposal.on_stage`/`devices_used`
> (validated against the declaration, repairable), entries carry
> "[on stage: …]", declared-device usage aggregates into route counts
> rendered as DEVICE USAGE SO FAR in the write prompt. Live validation
> pending. Spec ratified
> in-session 2026-08-04. Follows
> from the star-swabber prose read (decision log 2026-08-04; BACKLOG
> "Register conformance"): the author read the finished book as
> **over-stylized** and directed "primarily prompt engineering" on the
> writer side. Every design decision below was settled in the same
> session with the author; the experimental evidence is a six-arm rewrite
> experiment on the star-swabber opening passages (kimi-k2.6, unbilled,
> fresh samples — arms summarized in §2). Frontier-authored; the PR-1
> prompt work is frontier-lane (narrative semantics); PR-2/PR-3 are
> implementable mid-tier against this contract.

## 1. The problem (evidence, star-swabber run, 2026-08-04)

Every passage runs the full register. The `scene_type` machinery did not
prevent it, and the trace shows why (all verified in-session against the
run):

- The **signal is healthy**: 131 sequel / 63 scene beats, B8 firing. The
  hottest passages are tagged *plain* (the opening is three sequels; the
  hottest sampled passage is a `false_branch` micro-beat).
- `fill_write.j2` states restraint **once, abstractly**, against a vivid
  prop-inventory Voice; a deadpan-comedy Voice's "reserved for cosmic
  ironies" clause licenses ornament in every sentence.
- The **window block's anti-echo framing manufactures re-description**:
  a canonical object must appear again, its established wording may not
  be reused, so the writer is *pushed* to coin a fresh description —
  fresh ornament and continuity drift, both mandated by the guard
  against repetition.
- `fill_review.j2`'s register rule is **one-directional** ("do not fault
  a plain sequel as too spare" has no ornamented-sequel counterpart) and
  taste is warn-never-fail: nonconformance is free.
- `_overwriting_finding` counts **hyphen-compound coinage**; kimi-k2.6
  over-figures in plain syntax — 0 findings on a uniformly hot run.

Root shape: each of 141 independent write calls locally optimizes the
whole Voice contract; nobody optimizes the book. Restraint, recurrence,
and establishment are **book-level properties stated (or not stated) at
passage level**.

## 2. What the experiment established

Six arms, three opening passages, same context/schema/model, fresh
samples (harness: session scratch; outputs read by the author):

| Arm | Result |
|---|---|
| V0 unmodified prompt, fresh sample | as hot as the book, new figures — the defect is **systematic**, not sampling luck |
| V1 hard countable budget | **works** — plain passages come back plain; but re-mines established gags |
| V2 budget + ban-list of images | fresh, but **broke POV and drone continuity** — the block banned canonical props and world mechanics (defective block, not evidence against statistics) |
| V3 pacing rationale only (no constraint) | **fails** — as hot as baseline: *rationale doesn't ration; only constraint completeness does* (the repo's prompt doctrine, confirmed experimentally) |
| V2′ budget + established-referents ledger + spent one-shots | works — plain, fresh, contracts intact |
| V5 **continuation framing** + budget (manuscript-first, window replaced) | **best** — plain register, definite references ("The drone maintains its hover"), correct new-character introduction, comedy migrates into dialogue/situation; the 2-layer arm is the single best output |

V5 wrinkle: it returned a passage-1 line **verbatim** as a refrain — good
craft, but an ≥8-token run the echo guard rejects. Recurrence needs a
declared contract (§4), not a loophole.

## 3. Decisions (author, in-session 2026-08-04)

1. **Primarily writer-prompt engineering** (verbatim quote in the BACKLOG
   item). The reviewer and the metrics are changed only where this
   contract says so — each exclusion in §7 is a design decision with a
   recorded trigger, not license to build less.
2. **Continuation framing** (author: "maybe the prompt just had to say:
   the preceding passages were these: read them. we are continuing the
   story as follows"): the write prompt is restructured manuscript-first;
   the writer is the book's author continuing their own manuscript, not a
   task-worker with a reference window. Continuation *implies* refer-
   plainly / don't-remake / match-register; the explicit rules become
   reinforcement, not the mechanism.
3. **Look-behind depth 2** (author: "adding a second layer is relatively
   cheap"): actual predecessor prose, up to 2 passages along each arriving
   route, nearest last, with a total cap (fan-in guard, §5). The
   story-so-far is "nice, but not a replacement for look behind" (author).
4. **Established referents are referred to plainly** (author: "the drone
   is mentioned and described, it can just be 'the drone'"): the disease
   is re-introduction itself. A new descriptive detail only when the
   passage's action changes the thing or turns on it.
5. **The lookahead mirrors this at convergences** (author): the sins
   reverse — *pre-emption* instead of repetition (the fixed next page's
   images/jokes/reveals are off-limits), plus the **establishment
   obligation** (anything the fixed text refers to plainly must be on
   stage before the handoff) and the register handoff.
6. **Recurring devices are genre quirks and need a declared contract**
   (author: "every story/style/genre will have its own quirks. so the
   reviewer will also have to be aware of this"): the Voice declares
   them; writer, reviewer, and echo guard read one declaration (§4).
   Per-passage device annotation is the *escalation*, only on a
   demonstrated live gap (the `scene_type` precedent) — recorded as an
   open question, not built now.
7. **The story-so-far enumerates more than story content** (author):
   entries gain "on stage" (referents introduced) and device-usage
   counts (§5) — statistics as counts, not bans, so later passages are
   steered to fresh material, never starved (a per-passage budget cannot
   be blown by an earlier passage; what is finite is tolerance for
   repetition, not the supply of jokes).
8. **The budget is the hard floor** (from V1/V3): a countable per-passage
   allowance rendered from the existing intensity tag, with a
   count-before-returning self-check. Rationale (pacing framing) is kept
   as one motivating sentence only — V3 proved it insufficient alone.

## 4. The Voice: declared recurring devices

`Voice` gains a `recurring_devices` list (name, description, rule),
written by the voice pass and author-editable like every Voice field:

- rule `escalate` — may recur only bigger/varied, **in new words** (the
  V5 wrinkle: a refrain that returns verbatim is still an echo defect
  unless declared verbatim).
- rule `verbatim` — a fixed utterance that MUST repeat exactly (Marta's
  alibi, a spell, a legal formula). **This absorbs the standing
  echo-guard "canonical utterances" BACKLOG gap**: the echo guard
  exempts declared-verbatim runs (bounded: the exemption covers the
  declared utterance only, not surrounding prose — the laundering guard
  stays).
- rule `texture` — vocabulary veins (warranty legalese) that may recur
  freely as diction, never as repeated *figures*.

Writer, reviewer, and echo guard all render the same declaration.
Undeclared recurrence stays a defect; declared recurrence is judged
against its rule — recurrence review becomes contract-based, not taste.

## 5. The context: manuscript window + richer notes

- **Window**: up to 2 predecessor passages of real prose per arriving
  route, nearest last, capped at 4 passages total (fan-in guard; nearest
  wins). Framed as THE MANUSCRIPT SO FAR, read as the writer's own.
- **Lookahead** (unchanged depth): reframed per decision 5 — no
  pre-minting, establishment obligation, register handoff.
- **Story-so-far entries** (summarize pass) carry the ledger: each
  entry gains an `[on stage: …]` line (referents this passage
  introduced), and each passage records which declared devices it used.
  Device usage is rendered ONLY as the aggregate route counts beside
  the story-so-far (DEVICE USAGE SO FAR, rule-annotated, with the
  well-mined caution scoped to `escalate` devices — `verbatim`/
  `texture` repeat by contract), not as a per-entry line: the counts
  are the actionable form, a per-entry device line would duplicate
  them, and entries stay short (built simplification, PR-3 review).
  Entries stay ≤ ~80 words.

## 6. The reviewer

`fill_review.j2` gets the same declarations: the manuscript frame, the
budget, and the recurring-devices contract. Its register rule gains the
symmetric clause — an ornamented `sequel`/`micro_beat` is a finding, and
with the budget it is *countable* ("N flourishes against a budget of 1",
quote them). The finding level is **warn, by design and not as a
shortcut**: the write prompt is the fix under test, and warn-level
findings feed the arbiter without manufacturing non-convergence (the
2026-07-15 doctrine: never fix a loop by adding reviewer strictness).
This is the *complete* reviewer change this contract specifies — build
all of it. Escalating register to fail is the recorded follow-up
decision if the prompt alone doesn't hold on a live run, taken then,
not pre-built now.

## 7. Deliberate exclusions (design decisions, not deferrals)

Nothing here is a corner cut or an "MVP" trim — each exclusion is a
decision with a reason and a trigger for revisiting. Everything the
contract *does* specify (§4–§6, §8) is to be built completely.

- `_overwriting_finding` stays as-is — **reason**: it mis-proxies this
  failure (hyphen coinage vs figurative density), and changing the
  measurement while changing the prompt confounds both. **Trigger**:
  re-measure after PR-1's live validation; a figurative-density metric
  is the recorded follow-up if the read still finds density the budget
  missed.
- Per-passage device/motif annotation stays unbuilt — **reason**: the
  `scene_type` precedent (annotations are added on a demonstrated live
  gap, never speculatively). **Trigger**: a live run where the
  Voice-level declaration + counts provably under-determines placement.
- No G-gate or invariant — **reason**: register conformance is
  prompt-level behavior under test; gating it before the prompt fix is
  measured would violate the fix-the-loop-without-adding-rules
  doctrine. **Trigger**: same live validation, if warn findings show
  systematic nonconformance surviving the new prompt.

## 8. Slices

- **PR-1 — the prompt restructure** (frontier): `fill_write.j2`
  manuscript-first frame + budget block + lookahead reframe; window
  depth 2 in `_neighbor_prose` (route-following, capped); review prompt
  gets the frame + symmetric-but-warn register clause. No model changes.
  *Acceptance*: the experiment harness re-run on the star-swabber
  opening reproduces V5-quality output; offline suite green; golden
  unchanged (fixtures re-recorded where prompts changed).
- **PR-2 — declared recurrence** (mid-tier against this contract):
  `Voice.recurring_devices`, voice-pass prompt, echo-guard verbatim
  exemption + tests (violating construction: an undeclared verbatim run
  still fails; a declared one passes), reviewer awareness.
- **PR-3 — richer story-so-far** (mid-tier): summarize prompt + entry
  format, count aggregation in the write context.
- **Validation**: a fresh short-scope live run (unbilled) + author read
  of its opening; then the star-swabber premise re-run at medium if the
  short read passes. Register distribution eyeballed against B8; echo
  exhaustions at seams compared against star-swabber's baseline (1).

## 9. Open questions

1. Budget numbers (plain=1, scene=3) are knobs from the experiment, not
   calibration — revisit against the live validation read.
2. Window cap (4) vs deep fan-in convergences — measure context size at
   medium scale before raising.
3. Device declaration quality on weak tiers: does the voice pass declare
   sensible devices unprompted, or does it need examples? (Prompt-audit
   lens, not new machinery.)
4. Whether the establishment obligation at convergences needs engine
   support (checking an arm actually staged what the fixed text assumes)
   — only if live runs show the seam.
