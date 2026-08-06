# Weave Linearization — drama-layer braiding (Build Contract)

> Status: **SPEC RATIFIED, in-session 2026-08-06. PR-1 + PR-2 BUILT.**
> PR-1: the braid decided at the weave (`graph/braid.py` metrics,
> per-arc candidate scoring, ranked+scored candidates in the chooser
> prompt, B12 at the gate, the freeze-clarification doc letter). PR-2:
> the repair primitive — `swap_linear_beats` with every §4 pin enforced
> at the mutation layer (interior-pair, same-storyline, intersection,
> hint-crossing), returning the stale beats whose re-contextualization
> is the move's price; invariant **I18** (group contiguity) with its
> gate check and violating constructions. PR-3 (braid-respecting
> POLISH) pending; validation (cc-struct checkpoint rerun) after it.
> Follows from the author read of the run-6 graph (2026-07-17, decision
> log; the `call-out-farmers` capsule) and the epic call of 2026-08-05
> ("we will move on to the braiding epic"). Every decision below was
> settled in a brainstorm session with the author, 2026-08-06; the
> author's rulings are quoted verbatim where they carry the design.
> Frontier-authored; PR-1 is frontier-lane (weave/narrative-DAG
> semantics); PR-2/PR-3 are implementable mid-tier against this
> contract.

## 1. The problem (evidence, run-6 graph, 2026-07-17)

The fork loop braids the *choice* layer; nothing braids the *drama*
layer. On the run-6 read the author saw a dilemma "very quickly playing
out" in a straight line; session analysis pinned it: the
`call-out-farmers` capsule — **6 consecutive beats right after setup,
no other thread interleaved**. An entire storyline introduced,
developed, and resolved in one lump.

The code trace (`pipeline/weave.py`, 2026-08-06 session):

- Pre-commit beats and locked-dilemma chains are **individually movable
  units** — the capsule was not forced by atomicity. Nothing *prevents*
  interleaving; nothing *prefers* it either. The enumerators
  (lexicographic DFS, fair-split) have no braiding objective, and the
  chooser prompt carries no braiding doctrine. Consecutive lumping is
  what falls out.
- Soft and hard **resolve units are atomic** (commit + all post-commit
  chains, `_resolve_unit`) — structurally so: a shared beat cannot sit
  inside a fork region without being cloned into each branch.
- The LLM only chooses among candidate topological orders (up to 64);
  it never invents an order. That seam stays.

## 2. The doctrine (heritage phase model)

`docs/heritage/how-branching-stories-work.md` §Interleaving states the
braiding doctrine, and it is **not uniform alternation** — it is a
phase model:

> Introduction beats from all paths cluster near the beginning — set up
> every storyline. Development and reveal beats interleave through the
> middle — build tension across storylines. Commit beats are
> distributed for pacing — don't resolve everything at once.
> Consequence beats cluster toward the end — pay off the choices.

Clustering at the openings and endings is *correct*; the middle is
where interleaving must be dense; commits spread out. The heritage also
keeps the exception representable: "a twist dilemma might introduce
late in the story, and that is a valid creative choice."
`call-out-farmers` is precisely a middle-phase violation.

## 3. Decisions (author, in-session 2026-08-06)

1. **The freeze is the branching topology; linearization is a distinct,
   mutable degree of freedom.** Author, verbatim, on iron rule 4's "the
   topology freeze is absolute... POLISH adds only": "yes, but with
   this we meant the tensor of the dilemmas; the shape after grow. in a
   sense all the main choices are fixed then and polish only adds minor
   fake choices and other flourish. this is what was intended. and in a
   sense we meant (modulo these linear stretches) because they don't
   really change the branching topology." Consequence: forks,
   convergences, beat membership, and the world tensor are frozen after
   GROW; the *order of beats inside a linear stretch* is linearization
   state, legal to change under the pin algebra (§4) at any moment, at
   that moment's price. This is a clarification of intent, not an
   amendment — but the letter of AGENTS.md iron rule 4 and design doc
   01's freeze invariant must be sharpened to say it (PR-1, same PR).
2. **Three moments of interest, one algebra.** Author: "1. near the
   beginning of grow when we have just tensored the Y-shaped. 2. at the
   very start of polish. 3. during polish", and "in a linear sequence
   of beats, their positions can be switched (up to a point). and that
   holds for all three of those moments." The move set is identical at
   every moment; what differs is the price: free at the weave,
   re-contextualization per swap at POLISH entry (summaries chain
   narratively — the recorded 2026-07-17 constraint), plus passage
   rework once collapse has run.
3. **Moment 1 is load-bearing.** Author: "while it doesn't change the
   branching topology, it does have major impact... hence moment one is
   load-bearing." The braid is decided globally and for free exactly
   once. Moments 2–3 exist because the substrate keeps growing — "grow
   and polish introduce more beats, e.g. for pacing, which can lead to
   *new* linear stretches" (author) — so late moments place new
   material into the braid and repair locally; they never re-decide it.
4. **Per-arc ground truth.** The phase model describes what a reader
   reads, and a reader reads an arc. On any arc each soft diamond
   contributes one branch's chain, so spine interleaving is not
   experienced interleaving: gaps shrink, alternation thins, and a
   well-braided spine can hand some arc a lump. All braid metrics (§5)
   are computed over the **induced arc orders** (arcs are computed,
   `graph/queries.py`), scored by worst arc — at the weave (over each
   candidate) and at POLISH entry (over the realized graph) alike.
5. **Prefer, don't prune** (agent-proposed, author-ratified): the
   enumerators are biased to spread candidates across the braid-score
   range, the engine scores every candidate (§5), the chooser prompt
   shows the scores and states the phase doctrine, and the LLM keeps
   the pick. A chosen order that busts a cap draws a warn-level report
   line, never a gate failure — hard pruning would make the late-twist
   exception unrepresentable.
6. **Soft diamonds stay atomic** (agent-proposed, author-ratified).
   They participate in the braid through *placement* — the
   commit-distribution metric — never by cloning shared beats into
   branches (heritage "The Cost of Branching": cloning multiplies
   exactly the words the design conserves). A story so diamond-heavy
   that atomicity caps its braid is a SEED scaffold-shape signal — fix
   structure upstream.
7. **Head contiguity via block-shaping** (agent-proposed,
   author-ratified). The braid targets runs of 2–3 same-thread beats —
   never beat-by-beat ping-pong, never lumps — which serves drama
   alternation and head contiguity at once. Beat `entities` overlap is
   the tiebreaker between equally legal orders. The annotate pass
   remains the head authority; no head model enters the weave.

## 4. The algebra (one move set, three prices)

Two adjacent beats in a linear stretch **commute** unless a pin
separates them. The pin inventory (identical at every moment):

- **Within-thread chain order** — a storyline's own beats keep their
  scaffold order (heritage: each path's beats read coherently alone).
- **Intersection adjacency** — group members stay adjacent (the unit is
  atomic in the weave; the collapsed passage pins it later).
- **Temporal hints** — adopted hints stay satisfied.
- **Commit/convergence walls** — no beat crosses into or out of a fork
  region; resolve units are atomic (§3.6).
- **Setup precedence** — setup precedes everything (existing weave
  constraint).

What changes per moment is the **price**, not the legality:

| Moment | Where | Granularity | Price per move |
|---|---|---|---|
| 1 | weave, at tensor time | units on the spine | free (pure engine step, pre-contextualize) |
| 2 | POLISH entry | beats in realized linear runs (per world, clones included) | re-contextualize every beat whose neighbors changed |
| 3 | during POLISH | what remains linear between passages | re-contextualization + re-opening the collapse across the boundary |

Moments 2–3 also govern **insertion**: bridges and pacing beats added
after the weave create new linear stretches, and where new material
lands in the existing braid is itself a braid decision under the same
pins.

## 5. The metrics (countable, per-arc)

Phase-aware, computed on each arc's induced beat order; a candidate's
score is its worst arc. Numbers are knobs from this analysis, not
calibration — the live validation read revisits them (the register
budget precedent).

- **Introduction latency**: every dilemma's first beat lands within the
  first N positions of the arc (default: N = ceil(arc length / 3)).
  The late-twist exception is representable because nothing enforces
  (§3.5): a deliberate late intro scores lower and the chooser may
  still pick it, eyes open.
- **Middle run-length**: in the arc's middle phase — after every
  storyline present on that arc has introduced, before the climax
  region — the longest same-dilemma consecutive run is at most K
  (default K = 3). `call-out-farmers` scores 6 today; this is the
  number to beat.
- **Commit spacing**: at least S non-resolve beats between consecutive
  commit beats on the arc (default S = 2) — "don't resolve everything
  at once", countable.
- **Block shape**: same-thread runs of 2–3 preferred; runs of 1
  (ping-pong) and runs above K both penalized in the score, so the
  optimum is blocks, not maximal alternation (§3.7).

The phase boundaries are structural and deterministic: the middle
starts at the arc position where the last storyline present on that arc
has introduced, and ends at the arc's climax-region tail (the final
resolve unit's span). No LLM involvement in measurement.

## 6. The moments (what builds where)

- **Moment 1 — the weave.** The scorer (§5) runs over every candidate's
  induced arcs; enumeration gains a braid-aware bias so the candidate
  list spans the score range instead of clustering near the
  lexicographic corner; the chooser prompt states the phase doctrine
  and shows each candidate's scores; the choice stays the LLM's. The
  chosen order's scores land in the GROW report — **B12**, the braid
  report — with warn lines for busted caps.
- **Moment 2 — POLISH entry.** B12 re-runs on the realized graph (the
  weave scored candidates pre-tensor; new linear stretches from bridges
  exist now). The repair primitive exists: a `swap_linear_beats`
  mutation in `graph/mutations.py` — pin checks enforced at the
  mutation layer, re-contextualization of affected beats mandatory, a
  violating construction (a swap across a pin) unrepresentable, backed
  by a numbered invariant in design doc 01 §8 with its `validate.py`
  check and test. Repair is operator/engine-invoked and targeted; no
  automatic repair loop (§7).
- **Moment 3 — during POLISH.** The additive machinery respects the
  braid it inherited: passage collapse prefers boundaries at thread
  switches (a preference in the collapse assessment, not a constraint —
  the intersections precedent); the fork loop's site selection prefers
  interruption at thread switches over mid-block cuts; pacing-beat
  insertion places into the braid under §4's pins.

## 7. Deliberate exclusions (design decisions, not deferrals)

- **No cloning shared beats into soft diamonds.** Reason: word economy
  — cloning multiplies authored words per arc (heritage "The Cost of
  Branching"), and the braid gains placement freedom it can already
  express through commit distribution. Trigger to revisit: a live read
  where a diamond-heavy story's braid provably caps at the atomicity
  limit *and* the SEED-shape fix was tried and rejected.
- **No automatic late-repair loop at moment 2.** Reason: moment 1 is
  load-bearing (§3.3) and late moves are priced; an automatic loop
  would spend LLM re-contextualization calls repairing what a better
  weave choice gets free. Trigger: B12 shows per-arc lumps that were
  invisible at weave time recurring across runs — that pattern means
  the weave-time scorer's arc projection has a systematic blind spot,
  and the fix may then be repair automation *or* a scorer fix.
- **No head model at the weave.** Reason: annotate is the head
  authority (POV-sequences design); the entities-overlap tiebreaker
  carries the contiguity signal blocks need. Trigger: B11 × B12
  correlation shows annotate systematically splitting the blocks the
  weave built.
- **No LLM-invented orders.** Unchanged doctrine: the model chooses
  among engine-enumerated candidates, never writes an order. Not up
  for revisiting in this epic.

## 8. Slices

- **PR-1 — the braid decided (frontier).** Arc-order induction for
  candidates (queries), the §5 scorer, enumeration bias, chooser-prompt
  doctrine + scores, B12 at GROW. The doctrine docs land here too:
  AGENTS.md iron rule 4 and design doc 01's freeze invariant sharpened
  per §3.1 (author-ratified wording), design doc 02's GROW section
  gains the braiding contract. *Acceptance*: on the cc-struct-medium
  GROW checkpoint (unbilled rerun of the weave pass), the chosen
  candidate's worst-arc middle run ≤ K where the run-6 baseline scores
  6; offline suite green; golden untouched (its graph is hand-authored
  and already woven).
- **PR-2 — the repair primitive (mid-tier against this contract).**
  `swap_linear_beats` with pin checks, the new invariant + validate
  check + violating-construction tests, mandatory re-contextualization
  wiring, B12 at POLISH entry.
- **PR-3 — braid-respecting POLISH (mid-tier).** Collapse boundary
  preference, fork-loop site preference, insertion placement under the
  pins.
- **Validation**: rerun GROW-from-weave on the cc-struct-medium
  checkpoint (unbilled), B12 before/after, author read of one arc
  against the run-6 baseline arc.

## 9. Open questions

1. Metric defaults (N, K = 3, S = 2) are knobs from analysis —
   revisit against the validation read before calling them calibrated.
2. Late-twist representation: today the exception survives because
   nothing enforces; if warn noise on deliberate twists becomes a
   nuisance, a scaffold-level marker (SEED annotating a dilemma as
   late-intro) is the escalation — prompt-visible, engine-checked, not
   built now.
3. Whether moment-2 repair ever automates (trigger recorded in §7).
4. Degenerate scopes: micro/short stories with one or two dilemmas
   have little to braid — B12 should stay quiet rather than warn on
   structurally unavoidable runs; the scorer needs a floor beneath
   which phases don't apply.
