# Decision log

The dated, chronological record of notable decisions and efforts, session by
session — a **provenance archive**: search it for *why* something changed, don't
read it end-to-end.

> Written and maintained by coding agents for hand-off (AGENTS.md
> §"Documentation contract"). An entry is an agent's account of a decision, not
> author-ratified ground truth, unless it cites an explicit author instruction.
> **This is not the source of any rule** — durable rules live in the design docs
> (01–04, including their Departures sections) and the mini-ADR table (03 §9),
> which are what an agent reads by area. This file is the "how we got here" trail.

Older narrative that once lived in STATUS.md ("Where we are") is preserved in git
history; the decisions it recorded are captured below and in the design docs.

---

- **2026-07-18 (I13 reachability walk — a powerset blowup on cosmetic
  keyword grants, ~62 GiB):** The comprehensive medium run's POLISH gate
  ran for minutes at 100% CPU and **~62 GiB RSS** before the host OOM'd (it
  took the Claude Code terminal with it — compounded by an agent mistake:
  polling with repeated full-replay `qf status` calls while the gate ran).
  Root-caused by reproducing the gate under a hard `RLIMIT_AS` cap +
  `faulthandler.dump_traceback_later` (a safe stand-in for the debugger the
  process was already dead for): the sampler pinned it to
  `check_i13_passage_graph`. Its per-arc BFS keyed the visited-set on
  `(passage, accumulated-flag-set)` and accumulated **every** choice grant.
  Pre-cosmetic-forks that was a handful of dilemma routing flags; the PR-4/5
  grant model now mints a `flag:cw-*` per rendering, almost all unconsumed
  (the PR-6 finding), so the state became a powerset over grants —
  `2**(#grants)` states, ~62 GiB here. Fix: project the accumulated flags to
  the **gate-relevant** set (flags some choice actually `requires`) before
  using them as the visited-set key — a grant nothing tests cannot change
  which choices are takeable, so this never changes what I13 decides; it
  restores the pre-cosmetic-forks bound. Violating-construction test (24
  unconsumed-cosmetic diamonds → 2**24 states pre-fix, `MemoryError` under a
  4 GiB cap; linear and instant post-fix). End-to-end: the real POLISH gate
  now completes and checkpoints (stage → polish, 159 passages) under a 30 GiB
  cap, 0 errors. Doctrine, again: it was the plumbing (an algorithmic bug in
  a gate walk), not the model. Process note: never poll a large in-flight run
  with repeated `qf status` (each is a full ledger replay into memory); grep
  the log instead.

- **2026-07-18 (labels pass — the single-exit double-label, a
  constraint-completeness fix):** The first comprehensive medium run on
  current `main` (unbilled `gpt-oss:120b-cloud`, fresh scaffold — NOT a
  resume of an abandoned run) survived a transient empty-response drop at
  `labels:111` (cleared free on re-invoke; the M10 auto-resume gap, one
  data point) but then hit a deterministic halt at `labels:34`: "group 34:
  destination group 36 labeled twice." Diagnosis (author suspected a prompt
  nudge, confirmed): group 34 has exactly one exit, but its beats *narrate*
  two distinct actions ("she stays above ground, ignoring the passage… she
  scours the woods"), and the model reliably emitted one label per described
  action — both onto the single destination. Two faces of one gap: the
  prompt (`polish_labels.j2`) invited an action→label reading by showing the
  passage beats immediately above "CHOICES LEAVING IT" with an unconditional
  plural "labels must differ from one another," and the schema (`dst: int`,
  free list) could not forbid the malformed shape, so no repair round
  recovered. Fix, both faces (per the constraint-completeness doctrine — the
  same lesson as PR-C's interlude commit-guard: stated-and-trusted lost, only
  the mechanical check converged): a per-pass `_labels_schema(a)` pins `to`
  to the real out-destinations and fixes the list length to the exit count,
  so a single-exit passage is structurally incapable of two labels; the
  prompt marks the beats as CONTEXT (not choices), states the exact label
  count, and drops the plural "must differ" line for a single exit. The
  apply-layer checks stay the joint-constraint guard for the multi-exit
  duplicate an independent enum cannot forbid (refpin.py division of labor).
  Five violating-construction/render tests; `enum_type` broadened to
  `Sequence[object]` (it always supported int Literal members; the labels
  `to` is the first int caller). One instance of the `polish_labels` line in
  the standing prompt-template audit (BACKLOG). Run resumes against the fixed
  code from its ledger (labels 0–33 stay valid; 34 re-runs fresh).

- **2026-07-17, late (PR-6 scoped and closed without building — mint is
  not a reader-facing event):** Session-recovery investigation after a
  host crash found two unbilled validation runs abandoned (worktree
  pinned to a now-merged commit; see the entry below) and, with a live
  run free, used the gap to scope cosmetic-forks' one remaining BACKLOG
  item: PR-6, §4 consumption form 3, "If you noted PINE: …" print
  acknowledgment paragraphs. Investigation of `gamebook.py` and
  `queries.projected_flags` found form 1 (keyword-gated rendering, the
  diamond's extra arm) already delivers real print consumption
  end-to-end with zero new code: the gate is a genuine `requires` on a
  choice, so DRESS names it a codeword and print both hoists "write down
  X" and prints "if you have X, turn to Y." An initial scoping pass
  proposed a cheap fallback — a back-matter acknowledgment line for every
  minted-but-unconsumed cosmetic keyword, reusing the flag's stored
  `description` — but the author corrected the framing: **a cosmetic
  flag's mint is not itself a reader-facing event.** The agency a
  cosmetic fork delivers comes from the rendering's prose — genuinely
  different content, given unconditionally the moment the reader takes
  that arm — not from the flag underneath it, which is bookkeeping for a
  *possible* later reference. An unconsumed flag has no later reference,
  so nothing was withheld from the reader; printing a "write this down"
  instruction for it would be pure friction, asking the reader to track
  state that never resolves. Checked against current behavior:
  `projected_flags` already gates print's write-down instruction on a
  real downstream test, so an unconsumed keyword already gets zero print
  footprint today — the system was already correct, no gap to fill. A
  genuine inline-paragraph consumer (content that actually differs for
  holders, wired to a real site) would need new engine-side
  consumption-site selection plus a new authoring pass, comparable in
  size to form 1 itself, not an export-only PR — parked as a future
  option, not built. PR-6 closed (deleted from BACKLOG; plan doc §4 and
  the PR-slicing table marked closed-not-built; roadmap's cosmetic-forks
  entry now reads "no residual"). The cosmetic-forks epic is complete.

- **2026-07-17, evening (the interlude register fires — a three-probe
  doctrine exhibit):** The register had never fired live (three runs, two
  tiers, zero `interlude` marks). PR-C closed it with a probe series on
  the sequence-A/B graph (one unbilled annotate call each, roster/carrier
  replayed): **probe 0** (PR-B's stated expectation) — 0 marks; **probe 1**
  (moment-based rebalance: "a moment WORTH an entry — no summary reads as
  a journal entry") — 8 marks, all on COMMIT beats (the model re-framed
  the drama's peaks); **probe 2** (+ "the turn itself stays in scene …
  never the commit beat" stated verbatim) — 7 marks, 5 still on commits;
  **probe 3** (the rule ENFORCED: a repairable ApplyError with the
  corrective "move the mark to the reflective beat AFTER this turn") —
  **14 marks, all sequels, all post-turn, zero on commits, one repair
  round**. Stated-and-trusted was ignored twice; only the mechanical
  check converged — the enum-pin doctrine with receipts. Also in PR-C:
  B11's switch signal skips interlude beats (their page-turn is the
  register's known cost, reported by its own line; 8 interludes would
  otherwise drown genuine hops in ~16 switch warnings).

- **2026-07-17, later still (two epics shipped — author call; roadmap
  reconciled):** The author called **structural depth** and **cosmetic
  forks** shipped ("should have shipped already") — both epics' machinery
  is merged and live-validated (texture-trial through DRESS;
  run-6 author-read "a much better shape"; consumption 8/8 on the probe).
  Moved to the roadmap Shipped section; PR-6 (print acknowledgments) is
  cosmetic forks' one residual, now a BACKLOG item. The roadmap "Now"
  gains **POV sequences** (the run-unit annotate redesign, design agreed
  same day — the *sequence* term ratified by the author over "scene",
  which Swain's `scene_type` already owns) and "Next" gains **weave
  linearization — drama-layer braiding** (capsule interleaving +
  head-aware reordering; design constraint recorded: linearization is
  weave-side, pre-contextualize, because contextualize chains summaries
  narratively — reordering after it would force re-contextualization,
  before it reorder is a pure engine step; on today's capsule-shaped
  weave output there is little to reorder, so the primitive builds with
  that epic, not with POV sequences). Head-roster decisions ratified same
  session: resolve `pov_hint` → an explicit roster before annotate and
  pin the viewpoint enum to it (closes the ungated off-scheme-head
  BACKLOG item structurally — the kimi victim-head class becomes
  unrepresentable); `Voice` reads the roster at FILL; a
  no-roster-head sequence resolves by justified split or justified
  wide-cutaway (wide stays doctrinally a coda register, never an
  automatic fallback — if the valve fires often that is a weave/roster
  defect to fix upstream); B11 advisory reports mid-sequence splits,
  non-coda wides, and per-head share (a one-passage head is visible
  taste, not a hard rule).

- **2026-07-17, later (the beat/passage collapse read — two findings under
  one graph):** Reading the run-6 passage graph beside its beat graph, the
  author observed (a) a dilemma "very quickly playing out" in a straight
  line and (b) linear no-choice beat runs shattering into many thin
  no-choice passages. Session analysis on the run-6 graph confirmed both
  and separated three layers. **Boundary census (172 passages):** 37 end in
  a real choice, 36 are fork rejoins, **76 are pure POV splits** (no
  choice, no gate — I14 refusing to merge across a head switch), ~17 are
  `passage_beats_max=3` cap splits, 6 gates. **Head-hop rate:** 58% of
  consecutive annotated linear beat pairs switch heads
  (e.g. `call-out-farmers` lead-1..resolution runs gord,gord,HARPER,gord);
  `grow_annotate.j2` says "PREFER RUNS … rotate at a real shift of
  dramatic center, never beat-by-beat" — stated and trusted, i.e. a prompt
  defect by the repo's own doctrine. Texture arms inherit trunk heads via
  `mirrors`, so the fragmentation duplicates into every arm.
  **Counterfactual (repo's own `collapse_groups`):** heads held per run →
  159→114 passages (−28%), singletons 59→18, avg beats/passage 1.79→2.49;
  the raw choice topology is 78 runs (longest 9 beats). **Interaction:**
  the choice-stretch metric counts passages, so POV fragmentation inflates
  the deserts the fork loop then spends words interrupting — part of the
  +14% break surplus buys interruption of an artifact — and B3's 172>160
  is largely the same artifact. **Separately (drama layer):** the
  `call-out-farmers` capsule — 6 consecutive beats, no other thread
  interleaved — is a GROW weave gap, recorded as a roadmap "Later" epic
  (drama-layer braiding). **Author direction: fix the annotate layer
  first, by restructuring the task rather than adding prose rules — the
  run, not the beat, becomes the unit of viewpoint assignment; author
  sketches: stateful "we are at PoV X, keep unless impossible", or
  cluster-level "cover this stretch with minimal PoV change".** Design to
  be ratified before building; BACKLOG item carries the numbers.

- **2026-07-17 (run-6 read and ratified; the zero-consumption finding):**
  The stretch-capped loop's live run (run-6, rerun POLISH on the
  cc-struct-medium GROW checkpoint, `gpt-oss:120b`, unbilled) was read by
  the author and #102 merged on it: gate-clean, 0 errors + B10 ×1 (the
  seam-less 5-stretch), worst stretch 14 → 5, walks 2,324–3,241 →
  1,531–1,660 words/choice, ~25 sites / 3 rounds, 35 keywords minted,
  zero repair rounds, 62.8k words (+14% — the ratified break surplus).
  The run's one open finding: **zero keywords consumed live** — rounds
  2–3 offered round-1 keywords at every edge site (~18 offers) and the
  model omitted the optional `gated` rendering every time (confirmed
  against the run's LLM cache: no fork response contains a `gated`
  entry). Prompt-first diagnosis (this session's agent, reading
  `polish_fork.j2`): the KEYWORDS section is structurally tilted toward
  declining — it opens "(optional)"; its only vivid sentence is the
  failure-mode warning ("an arm richer than its siblings turns a
  declinable detour into a loss"); it names no positive criterion for
  when a keyword *does* echo or what a good gated arm delivers; and its
  final sentence is the decline instruction ("when no keyword genuinely
  echoes here, leave `gated` out"). Under that asymmetry — adding risks
  breaking a stated rule, omitting breaks nothing — the modal sample on
  any tier is to decline, 18/18. The fix is rebalancing the existing
  section (state the positive purpose and an echo criterion, keep the
  size-parity rule, move the decline case to a subordinate clause), not
  adding rules; consumption stays optional-never-assigned (§4).

- **2026-07-16, evening (stretch cap — the author metric lands; first
  loop-built graph read):** The first live loop-built medium graph
  (rerun POLISH on the cc-struct-medium GROW checkpoint, `gpt-oss:120b`,
  unbilled) validated the PR-5 prompts outright — residue + all 7 fork
  sites + 400 passage/audit passes, zero repair rounds in the loop — but
  the words ceiling starved interruption: 1 productive round, walks at
  ~2,700 words/choice, a 14-passage no-choice desert on every walk.
  **Author direction (verbatim intent): the long stretches must be
  interrupted, braided like the ending; the metric is the number of
  passages with no choice and the length of a no-choice stretch; words
  calibration comes later.** Implemented same day
  (`cosmetic-forks-stretch-cap`): `ScopePreset.choice_stretch_max`
  (default 4, the region the author judged reasonable), the DAG-wide
  conservative stretch metric (`projected_stretches`/`_stretch_chains` —
  walk-based measurement is blind to the desert inside the rendering a
  walk didn't take; a keyword-gated choice breaks no stretch for readers
  without the key), advisory **B10**, and `fork_plan` re-phased: depth
  first (words-gated, probe-measured exact pricing — the analytic
  marginal undercharged fork-boundary re-chunking, which is how the
  first run overshot the ceiling it enforced), then mandatory breaks
  (words-EXEMPT; same-round segment interiors deferred to the next
  round's recursion — a dry-run against the live GROW graph caught the
  apply-order collision), then B6 fine-tuning. Dry-run on the live
  graph: worst stretch 14 → 5 (the 5 has no free seam; B10 reports it),
  walks ~2,700 → ~1,600 w/d, 22 sites over 2 rounds, words +14% over
  target (the ratified trade). B6 stays advisory; the stretch cap is the
  primary structural criterion (sim exit criteria updated accordingly).

- **2026-07-16, later (cosmetic forks PR-5 built whole — the finalize
  loop; the order question mooted):** The 5a/5b/5c order decision the
  same-day hand-off left open resolved itself: one session built all three
  sub-slices together as draft PR #101 (the recorded coupling held —
  retiring mirrored cadence was inseparable from recursion + budget
  parity). Built plan §6 end to end on one branch: `finalize:0`
  keeps residue (obligations before decoration); engine-only planner rounds
  `finalize:<n>` recompute `fork_plan` on the current graph and expand into
  per-site `fork:<n>:<k>` writer passes; per-site schemas pin rendering
  count, beat counts, entities, and the offered-keyword enum; the apply
  splices through `insert_cosmetic_fork`, persists premises (rendering 0's
  onto frozen trunk heads), and mints `flag:cw-*` per non-empty rendering;
  a keyword-gated extra rendering is v1 consumption (edge-scale only —
  build decision, plan doc). I15 restated composition-closed (un-mirrored
  FALSE_BRANCH decoration contracted before projection; mirror chains
  ground out; structural choice-topology parity retired for per-walk
  budget parity) with legacy exemplar structures pinned valid; I16
  (cosmetic-gate locality) landed with check + violating constructions.
  Retired and deleted: `texture_sites`/`texture_plan`/`cadence_plan`/
  `insert_cadence_*`/`_texture_and_cadence`/`_twin_chain`/`_arm_pairs`;
  the scale sim now drives `fill_fork_budget` (the loop to its fixed
  point). Planner calls the sim forced: target the WORST projected walk
  (budget parity), degrade a cycled shape to a sidetrack at the words
  boundary, order tiers by marginal story-words per decision (scenes
  capped, edges, smalls last). Recalibration flagged, not retuned: honest
  words pricing means the band-top sim lands ~3% over B6's 800 (fixed
  point asserted instead), and arc-VIEW beat counts inflate with
  renderings (B3/B4 post-modulation, BACKLOG). Open questions 4 and 5
  answered (resume determinism pinned by test; B6 over-holding fixed —
  cosmetic holds are walk-accumulated in both walkers). **Drive-by fix:**
  the offline loop fixture exposed `_audit_one_context` comparing the
  Passage NODE to the passage id (always False), so every per-passage
  `audit:<pid>` prompt rendered with an EMPTY passage list — a severe
  prompt defect; the live run survived it only because the schema pins
  the passage enum (the medium run's halt itself was the giant-call,
  already fixed by #95's decomposition — this is that fix's remaining
  prompt half). Fixed and pinned by the fixture's audit passes. (The PR's
  earlier commit message calls this "the audit halt's root cause" — an
  overclaim written before #100's hand-off was visible; this entry is the
  corrected record.)
- **2026-07-16 (cosmetic forks PR-2 → PR-4 shipped; PR-5 sub-sliced, order
  left open):** Landed the epic's engine core across three merged PRs: **PR-2**
  (#97) the one splice primitive `insert_cosmetic_fork` behind the three shapes
  + premise per rendering incl. rendering 0 (guard relaxed, a frozen-beat-safe
  `set_beat_texture_premise` mutation — the freeze clarification — FILL/entry-
  labels reading it, 01 §6); **PR-3** (#98) engine-assigned cadence shape mix
  (`ScopePreset.cadence_arm_cycle`, front-loaded) + 3-arm diamonds — takes shape
  out of the model's hands, resolving the 44/44-sidetracks finding; **PR-4**
  (#99) the cosmetic grant model (`Beat.grants_flags`, `grant_beats`/
  `choice_grants`/I10 now cover `path=None` flags, the B6 held-note). Each PR's
  automated review found no correctness issues; small review suggestions
  (degenerate-marker guard, 3-arm apply-summary, doc-table consistency) were
  taken. **PR-5 (the loop) is sub-sliced (5a loop mechanism / 5b minting + I16 /
  5c recursion + retire mirrored cadence + budget parity + I15 restatement)**
  after reading the code surfaced a coupling — mirrored-cadence retirement is
  inseparable from recursion + budget parity, so it moves out of 5a into 5c
  (recorded in the plan's PR table). A second finding: the loop's headline
  value (decompose finalize to avoid ~60-site exhaustion) is speculative — the
  medium validation run produced the whole finalize proposal in one shot, no
  exhaustion — whereas minting + I16 is independent of the loop and builds on
  PR-4. The agent recommended flipping to **minting + I16 first**; the author
  paused to decide the order in a fresh session. Provenance for the validation
  exemplar and the audit/entity-roster fixes: entries below and the BACKLOG.


- **2026-07-15 (structural-depth medium validation run — machinery
  measured, four findings, two prompt defects):** Ran DREAM→POLISH at
  medium on `gpt-oss:120b-cloud` (unbilled, via the LAN daemon's cloud
  proxy), band-top `--words-target 55000`, the *Closed Circle* premise (the
  flat baseline's premise, for an apples-to-apples read). Purpose: measure
  the texture/cadence/finalize machinery as shipped before PR-2+, per the
  plan's sequencing. GROW froze 186 beats / 12 dilemmas / 64 arcs; finalize
  grew it to 312 and produced its **whole proposal in one shot** — 3
  scene-scale texture worlds (~12/18/29 beats, 76 arm beats mirroring 76
  trunk beats), 44 cadence forks, 6 residue arms — **no ~60-site
  exhaustion** (the plan's top finalize risk, retired for this run). The
  passage layer built clean (203 passages, 276 choices; 399 summary/labels
  passes). Scorecard (recovered by replaying the cached POLISH proposals
  onto the GROW graph): B6 **971 words/choice** (band 250–800, above),
  B7 **76,160 words** (target 55,000, **+38%**); B4×64 / B8×18 / B3×1 are
  the known advisory bands (I12×71 is an artifact of the halted audit, not
  a defect). Four findings recorded in BACKLOG:
  1. **Finalize entity-roster halt — FIXED** (PR #92): the finalize schema
     pins `entities` to the retained cast's ids but the prompt showed only
     beat summaries, so the writer coined `character:finch` for the sheriff
     whose id is `character:marshal`. Fix: pass the cast, list
     `name (id): concept`. Live-validated (resume cleared finalize).
  2. **Cadence prompt bias → 44/44 sidetracks, 0 diamonds.** NOT model
     discretion (44 samples, zero variance = the prompt steering): the
     `polish_finalize.j2` FALSE BRANCHES section undersells the diamond (no
     hook, no "use it when", "look left / look right" booby-prize) and
     oversells the sidetrack (evocative + near-universal "use it where
     lingering is plausible" trigger). Confirms plan **PR-3** (engine-
     assigned mandatory shape) is necessary — shape can't be left to the
     prompt. (Corrects the earlier framing of this as "the run surfaces
     weak-tier halts" and "model discretion", per the author 2026-07-15 —
     both are the blame-the-tier reflex AGENTS.md forbids; the axis is the
     prompt.)
  3. **PR-0 residue-paragraph regression:** the exit-label paragraph PR-0
     added to FALSE BRANCHES is written in sidetrack-only vocabulary ("the
     detour", "declined", "rejoins the same road"), wrong for a diamond arm.
  4. **Texture worlds overshoot the words budget** (B7 +38%, B6 above band):
     3 max-size worlds written twice inflate past `words_target` and crowd
     out choices — data for open-question 1 (mix ratio) and a possible
     `texture_plan` admission bug.
  The run **halted at the `polish_audit` pass** (undiagnosed: the audit is
  a single call enumerating ~70 ambiguous-state passages, several near-
  identical texture renderings, and produced duplicate entries; per AGENTS.md
  the audit prompt clarity and the "audited twice" message actionability are
  the first suspects, then the A21 giant-call decomposition). Resumable free
  (399 passes journaled). **Process note (author, 2026-07-15): this repo does
  NOT track work via GitHub issues** — the docs administration is the
  backlog; issues opened this session (#86/#89/#91/#93) were the agent's
  global-habit error, left as-is, no new ones.

- **2026-07-15 (cosmetic forks PR-1 built — one-mechanism framing,
  current-state truth only):** Rewrote 01 §6's false-branch and
  texture-world entries into a single unified presentation — cosmetic forks
  are **k ≥ 2 renderings of a trunk segment**, the shapes (sidetrack,
  diamond, texture world) differing only in parameters (segment length,
  rendering count, empty/segment/fresh content) — and introduced the
  *segment* / *rendering* vocabulary later PRs' code will use. Held strictly
  to the doc-truth rule the reshape settled (below): every added sentence is
  true of today's code. The three splice entry points are named as current;
  the unified primitive, the fourth *small two-worlds* parameterization, the
  per-rendering premise (rendering 0 included), and the retirement of
  mirrored-cadence twinning are marked as the epic's target with A24/plan
  pointers — today's premise asymmetry (fresh arms only) and structural
  choice-parity read as current behavior. Deliberately excluded (each rides
  the PR whose code makes it true): **no** I15 restatement, **no** I16,
  **no** freeze clarification, and no §8 invariant text touched. A "fence"
  paragraph names the two look-alikes that are not renderings (residue arms
  are routed/obligated, dilemma forks carry consequence). Docs-only.
- **2026-07-15 (cosmetic-forks PR-1 reshaped — no target-state in the
  authoritative docs):** The session building the epic's PR-1 flagged
  that the slice as specced wrote an engine that doesn't exist into 01
  (I15 restated before PR-5 retires the twinning; I16 stated without its
  check, against iron rule 6; premise-per-rendering before PR-2 relaxes
  the guard). Agent ruling (the slicing's author, question forwarded via
  the author), applying existing rules rather than making a new call:
  01/02 carry current-state truth only; each restatement rides the PR
  whose code makes it true (freeze clarification + premise rule → PR-2;
  I15 restatement + I16, with checks and violating tests → PR-5); PR-1
  shrinks to the one-mechanism framing and vocabulary that is true of
  today's code. Plans and mini-ADRs remain the forward-looking record —
  a decision is a fact once made; a system description is not. The rule
  now heads the plan's PR-slicing section.

- **2026-07-15 (cosmetic forks PR-0 — exit-label residue built):**
  Implemented §5 of [`plans/cosmetic-forks.md`](plans/cosmetic-forks.md),
  the standalone exit-label fix that ships ahead of the engine rework. The
  confirmed defect: a cosmetic rendering's rejoin label re-offers the
  onward step the reader already declined, because the label pass words it
  from the arm's beats alone while the only shared anchor (the destination
  summary) is identical across the parallel calls — independent samples
  converge. Three layers, no validator (the fix is context, not a fence —
  a label-similarity check would be the pedantic reviewer AGENTS.md warns
  against): (1) **finalize prompt** (`polish_finalize.j2`, FALSE BRANCHES)
  now requires each arm's beat summaries to state the *mark* the detour
  leaves — the mood/image/knowing the reader carries on with, textural
  memory never consequence — so the exit has residue to voice; (2) the
  **labels pass** orders cosmetic-fork renderings after their parallel
  trunk/sibling edges (`_polish_expand` two-key sort keyed on
  `pc.cosmetic_rejoin_sources`) and surfaces the sibling labels already
  worded onto the shared rejoin (`_labels_context` → `_sibling_labels`,
  reading applied CHOICE-edge labels), with a "carry this rendering's
  residue; never re-offer that action" instruction gated on `is_rendering`
  so ordinary passes stay byte-identical; (3) **generalized** past
  sidetracks — the rejoin detector is *source group carries a
  false-branch/texture-world beat AND its destination has ≥2 incoming
  group edges*, which covers diamond sibling arms and texture-world tails
  and excludes a capped arm's internal chunk seams (single-incoming, so
  nothing to differ from). Tests: helper flags the arm not the trunk (and
  both diamond arms), the expansion orders renderings last, the arm's
  context sees the trunk's onward label while a trunk pass sees none. Full
  suite + golden green.
- **2026-07-15 (cosmetic forks unified — the branching ideas thought
  through, shape ratified):** A design session took the day's three
  branching threads (residue keywords, the cadence-vocabulary follow-ons,
  the sidetrack exit-label convergence) from ideas to a contract, with two
  author corrections steering it: **"diamonds, sidetracks and texture
  worlds are all intrinsically the exact same mechanism"** (one construct:
  k ≥ 2 renderings of a trunk segment; the code already whispered it —
  `insert_texture_world` makes the trunk "conditionally traversed like a
  diamond arm"), and **"one arm should not have a different treatment than
  the other"** (the shipped texture world privileges the trunk: premise on
  arm beats only, so W4 grounds half the readers — the harmful asymmetry).
  Recursion reframed per the author as **running the same phase in a
  loop** (iterative finalize; a segment inside a rendering is just a
  segment next round) rather than mirror-of-mirror machinery. The agent's
  analysis also surfaced: the missing cosmetic **grant model**
  (`grant_beats()` returns `[]` for `path=None`, so the first
  keyword-gated consumer would fail I10 — fix: `Beat.grants_flags`,
  beat-layer like commit grants), the **I16 locality** enforcement of the
  obligation boundary, the consumption ranking (gated rendering first;
  keyword variants need gate-precedence semantics — deferred), and that
  the exit-label bug generalizes to diamond sibling arms and texture
  tails. Author ratified the whole shape ("I'm happy with this shape"),
  explicitly including three flagged leans: **budget parity over
  structural parity** (each rendering grows its own forks until its walks
  hit B6 — amends I15, retires mirrored-cadence twinning), **rendering-0
  premises may sharpen** a vague backdrop, and **the empty rendering stays
  unmarked**. Recorded: mini-ADR **A24**, roadmap "Next" epic, contract in
  `docs/plans/cosmetic-forks.md`; the three BACKLOG items folded in.
  Sequencing: PR-0 (exit-label residue) ships ahead; the structural-depth
  medium validation runs before the engine rework.

- **2026-07-15 (the texture-trial: COMPLETE — the first project through
  DRESS, structural depth validated at short scope):** "The Letter and
  the Frontier" (short, `gpt-oss:120b` unbilled) ran DREAM→DRESS
  gate-clean: **0 errors, 41 advisories** — 32× B4 (arc beat-band) + 1×
  B3 (93 passages vs the 24–64 short band): the known post-modulation
  band recalibration (BACKLOG), the same drift the kimi A/B showed; 8×
  B8 pacing; **B6, B7, B9 all silent** (words-per-choice in band, total
  words in band, bridge share under the tripwire). The milestone's
  levers all fired live: W1 — 1 hard + 4 soft from the coupled budget;
  W2 — 2 dilemmas reserved at triage and used as texture feedstock; W3 —
  finalize planted 3 texture worlds (34 arm beats, tw0–tw2) in ONE
  proposal plus mirrored cadence (19 false-branch/sidetrack splices, 8
  residue arms); W4 — arm prose grounds its premise (the tw0 twins:
  plains/dust trunk vs pines/moonlight arm, same events, no lifts).
  Structure: 155 beats / 93 passages / 32 arcs (all complete) / 20
  flags / 2 endings / ~18.1k prose words. Spend: 784 calls, 2.55M in /
  1.02M out, all unbilled. Operator record: seven halts, every one a
  real defect fixed at root (the stall journal is the session record;
  the fixes are PR #81's commits — I12's unit + split_on, batched
  echoes, the twice-corrected rework diagnosis ending in loosened
  review margins, the write-pass repair budget, legible bans). The last
  ~60 passages wrote with zero halts. Open for the milestone exit: the
  author's read, and the medium run with a band-top words target.

- **2026-07-15 (the write prompt gets legible bans; the exhaustion message
  gets honest channel counts — agent decision on the live run):** The
  texture-trial's seventh halt (`write:p-border-approach`) reported
  "failed review 4 times" but the cache showed 2 legitimate
  banned-dialogue-tag review rejections plus 2 echo apply repairs — the
  shared budget's channels were conflated in the message. The standing
  no-more-rules check found a clarity asymmetry, not a rule gap: the
  review prompt explains the tag ban in a paragraph while the write
  prompt handed the writer the bans as one semicolon-joined line.
  `fill_write.j2` now renders each existing ban as its own bullet (no new
  rules), and the runner's exhaustion message reports review and apply
  rejections separately so the operator reads true counts.

- **2026-07-15 (tier is the fluency knob, not the structure knob — author
  hypotheses on the kimi A/B):** Reading `examples/closed-circle-k2` against
  the gpt-oss baseline, the author's read (verbatim intent): a weaker model
  can be made to do anything *structurally* correct — write the *correct*
  prose — but the sheer creativity and quality of prose (fluency) cannot
  (easily) be mitigated; and (hypothesis 2) a very large exemplar of the
  specific style wanted might let a small model do better by copying.
  Hypothesis 2 is a BACKLOG experiment (Validation & experiments) — it sits
  in deliberate tension with the M6 exemplar rule and needs design first.
  This refines, not contradicts, the prompt doctrine: enforcement makes
  structure tier-independent; fluency is the residual axis where tier
  legitimately buys quality.

- **2026-07-15 (the kimi-k2.5 A/B: COMPLETE — gate-clean FILL, structure
  in band, and the tier-confound made concrete):** the parallel *Closed
  Circle* medium (same premise, same pinned rotating `pov_hint`, kimi-k2.5
  on ollama.com, pre-enforcement prompts throughout for comparability)
  finished FILL gate-clean: **0 errors, 41 advisory warnings** (32× B4 —
  every arc 151–161 beats vs the 80–150 band, the ~40% larger structure;
  6× B5 near-band; 3× B8 pacing; **no B6** — words-per-choice landed IN
  the 250–800 band). Side by side (gpt-oss:120b baseline → kimi-k2.5):
  beats 239→222 (bridge 89→27, false-branch 0→**63** — kimi filled the
  then-advisory cadence budget voluntarily), passages 112→159, prose
  words 30.6k→47.9k, branch points 10→**54**, endings 4→4, dilemmas 8→8;
  heads: both rotated 4 declared heads per passage (I14 clean), kimi
  additionally headed 4 passages with the *victim* (Bernard Croft — not
  in the declared voice rotation; scheme-conformance is ungated, noted in
  BACKLOG) and left 72 texture/coda passages headless (its 63 grafted
  diamonds are unannotated wildcards); **interludes 0 on both tiers** —
  the annotate gap is tier-independent, not a weak-model artifact.
  Operator load: 7 journaled stalls (5 echo-guard lifts, 2 honest 2-round
  review non-convergences with high-quality quoted findings) — all
  cleared by re-rolls, **zero prompt defects surfaced** (the baseline's
  ~15 stalls surfaced five); 4 transport drops auto-resumed by the
  bounded-retry operator loop; 2 container restarts resumed free from
  the ledger. Spend: 969 calls, 3.00M in / 3.98M out (vs 844 / 2.77M /
  1.04M — kimi's 4× output is its long-form generation), unbilled. Net
  reading: the same prompts produced a flat book on gpt-oss and a
  played-in-band structure on kimi purely through the advisory budgets —
  the strongest single piece of evidence for the enforcement doctrine
  (counts a prompt merely states are tier knobs) and for the B4-style
  band drift the structural-depth milestone's coupled budget addresses.

- **2026-07-14 (I12's unit is the dilemma, and the audit gains split_on —
  author-directed on the live run):** The texture-trial's second halt

- **2026-07-15 (FILL rework rounds are edit-based, engine-merged — agent
  decision on the texture-trial live run):** The run's fifth halt
  (`write:p-vara-laugh`, "failed review 2 times") traced to wholesale
  rewriting under a prompt-stated "REVISE, DON'T REWRITE": the cached
  drafts prove the writer fixed exactly the quoted findings each round,
  rewrote everything else, and regressed a grounded referent ("Vara's
  mask" → "the mask") that no finding touched — a fresh sample per round
  keeps the violation probability constant and the loop never converges.
  Stated-and-trusted became structurally enforced: the rework round's
  schema requires `edits: [{find, replace}]` and forbids `prose`
  (max_length=0); `_merge_edits` applies them engine-side (unique-match,
  all failures batched), and the apply fills `prose`/clears `edits` before
  recording so replay artifacts stay self-contained. Durable rule in
  design doc 02 (FILL, rework-convergence levers). Same session, earlier
  halts: the echo check batched all lifts into one error (design doc 02
  repair model gained the batch-all-violations rule), and the review's
  ending+split_on refusal was reworded to the honest reason (frozen
  ending set) with the I12 exception documented.

- **2026-07-15 (rework convergence is a prompting concern — author-corrected):**
  The texture-trial's fifth halt (`write:p-vara-laugh`, "failed review 2
  times") was wholesale rewriting under REVISE-DON'T-REWRITE: the cached
  drafts prove the writer fixed exactly the quoted findings each round,
  rewrote everything else, and regressed a grounded possessive ("Vara's
  mask" → "the mask") no finding touched. The agent first shipped an
  engine-side fix — rework rounds schema-forced to `edits: [{find,
  replace}]`, engine-merged — and the author rejected it the same day:
  *"this is a prompting issue … not something you must micromanage from
  the engine"* (573c318, reverted in full). The prompt-level fix that
  stands: the rework block ends with an explicit self-check (diff your
  revision against the shown draft sentence by sentence; restore any
  sentence no finding required changing, watching small anchors like
  possessives). Same halt cluster, earlier fixes that DID stand: the echo
  check batches every lift into one error, and the ending+split_on
  refusal gives the honest frozen-ending-set reason (I12 exception
  documented).

- **2026-07-15 (write passes get a repair budget of 4 — agent decision):**
  The texture-trial's sixth halt (`write:p-ambiguous-tweak`, "exhausted
  repairs") had a different shape from the fifth: the cache trace shows
  every round fixed exactly what it was shown (an echo, then two grounding
  findings), each fix added fresh text that tripped the next independent
  check, and the pipeline-default budget of 2 exhausted the moment a
  second echo surfaced — the writer never got a round to fix it. Nothing
  structural, no non-compliance: ordinary convergence across serial
  independent checks, one round short. `PassSpec.max_repairs` (per-pass
  override, None inherits the default) and FILL's write passes set 4.
  The default stays 2 everywhere else; arbitration still gates repeat
  review rejections.

- **2026-07-15 (over-strict review, not writer compliance — twice
  author-corrected):** The texture-trial's fifth halt (`write:p-vara-laugh`,
  "failed review 2 times" on choice_grounding) drew two wrong fixes in a
  row, both reverted the same day. The agent first read the cache trace as
  a writer defect (a rework regressed "Vara's mask" → "the mask" while
  fixing other findings) and shipped an engine-side edit-merge (rework
  rounds schema-forced to `edits`, 573c318); the author: *"this is a
  prompting issue … not something you must micromanage from the engine"*
  (reverted, ac9284e). The agent then added a writer-prompt self-check
  step (ab76fa9); the author again: *"you still sound like you are feeling
  you should micromanage a weak model in the prompts … the problems come
  from being too strict in your prompts"* (removed). The standing fix
  loosens the REVIEW where the halt was actually manufactured: the
  reviewer had re-rejected a hedged inference ("as if weighing") that the
  voice_pov rule's own carve-out permits, and demanded an explicit
  possessive for a gesture context already attributed — each pedantic
  rejection forced another rewrite, and rewrites churn new nits.
  choice_grounding now counts a context-identifiable referent as grounded;
  voice_pov names explicit observed inference as the narrator's own mind.
  Durable rule (author's words, refined 2026-07-15; design doc 02 FILL +
  AGENTS.md prompt-quality): when the rework loop fails, do NOT add more
  rules — first check the existing write prompt for clarity, then the
  existing review prompt for being overly strict. Same halt cluster,
  earlier fixes that DID stand: the echo check batches every lift into one
  error, and the ending+split_on refusal gives the honest
  frozen-ending-set reason (I12 exception documented).

- **2026-07-14 (I12's unit is the dilemma, and the audit gains split_on —
  author-directed on the live run):** The texture-trial's second halt
  (five spymaster passages "over the I12 cap") unwound into two author
  corrections. (1) The session's cap-enforcement-at-apply was wrong in
  spirit: a hard irrelevance budget pressures the model to mark
  load-bearing states irrelevant — the model was *right* to keep the
  letter-state flags relevant at a scene about surrendering the letter.
  (2) The count was a unit error: the "7 ambiguous states" were per-path
  flags of TWO dilemmas (a path derives one flag per consequence; any of
  them identifies the path), i.e. two binary uncertainties. I12 now
  counts **ambiguous dilemma states** (`ambiguous_dilemma_groups`), and
  passage-level gates condition arrivals (`passage_gate_flags`, the
  intersection of in-choice requires — incidentally fixing a latent
  heavy-residue variant over-count). And because a genuine >cap overlap
  is the *expected* regime at medium/long (author: "this is going to
  happen... so let's immediately address"), the escape valve named in
  I12's own message since M3 ships: the audit's **`split_on`** keys a
  passage on up to 2 dilemmas and `mutations.split_passage` re-presents
  the wired moment as flag-gated variants — arrivals hold a known side,
  the state honestly stops counting. Audit violations batch into one
  repairable error (the run's third halt was whack-a-mole: one violation
  surfaced per repair round). 01 §8 and 02 carry the durable rules.

- **2026-07-14 (texture worlds: contamination caught and the definition
  widened — author corrections on the live run):** Two corrections from
  the author reading the texture-trial's first finalize output. (1)
  **Prompt contamination**: `polish_finalize.j2` quoted the doctrine's
  forest/mountains example verbatim and the model echoed it as 2 of 3
  premises (the third, un-anchored premise grounded correctly in the
  story's own brainstormed material — the mechanism works when not
  anchored). The example and the place-named id example are gone. The
  session's first replacement — a "never take a setting from these
  instructions" fence — was itself rejected (author, same exchange):
  self-referential negation with no visible referent is bad prompt
  engineering; what shipped instead is the positive, structural
  constraint — the premise must anchor in a story element the beats,
  cast, or reserved material already carry, *and name it*. (2) **The
  definition was read too narrowly**: the session had equated texture
  with *setting*; the author's intent is *same events against another
  backdrop* on ANY consequence-free axis — place (forest/mountains),
  means (bus/train), company, or the small facts of things and people
  (a car blue/yellow, an innkeeper's son/daughter). Recorded in 01 §6;
  prompts (`polish_finalize.j2`, `fill_write.j2`), the premise field's
  comment, and the splice docstring now carry the wide reading. The
  running trial keeps its prompt-tinted forest/mountain premises; the
  fix is validated by the next run's premises.

- **2026-07-14 (structural depth PR-4: finalize plants texture worlds;
  FILL grounds them):** the milestone's pipeline wiring, completing
  W3/W4 (all four PRs now built; the live validation run is the open
  exit). `_texture_and_cadence` computes both fork budgets together —
  texture sites first (capped by the words budget: `texture_plan` admits
  a fork only while the projected story total fits `words_target` or the
  band top, closing PR-3's as-built note #3), then cadence sized on a
  scratch graph carrying probe arms, so the numbers the model sees are
  the numbers apply enforces; the schema, context, and apply all share
  it. The finalize proposal gains `texture_worlds` — site index, a
  one-line premise, one model-worded beat per trunk beat — with
  mandatory coverage checked before any splice (the cadence precedent)
  and the empty-list schema discipline when no sites are offered. Apply
  order: texture → false branches → residue, the cadence splices
  dispatching through the mirroring variants so a diamond inside a
  mirrored stretch lands in both worlds. The premise persists on arm
  beats (`Beat.texture_premise`, justified by the `Passage.variant_flag`
  persist-for-a-later-pass precedent, A21) and FILL's write prompt
  names it — the W4 context lever — with an explicit never-compare
  instruction (the parallel rendering must not leak into prose).
  Recorded fixtures stay green: their stories offer no texture sites,
  so the new mandatory check is vacuous there. Noted for the validation
  run: the texture entry is finalize's largest single proposal yet
  (~15 beats); weak-tier repair exhaustion there means decomposing the
  pass per-site (A21), never softening the requirement.

- **2026-07-14 (structural depth PR-3: the texture-worlds engine — I15,
  mirrored arms, mirrored cadence):** W3's engine half, built and probed
  on the structural simulation; A23 records the architecture decision.
  What shipped: `StructuralPurpose.TEXTURE_WORLD` + `Beat.mirrors`;
  `insert_texture_world` (parallel arm around a stretch, trunk edges
  untouched, twin's *effective* annotations engine-copied so both worlds
  read at the same band and head); `texture_sites` (cap-aligned
  consequence-free sub-stretches — whole runs never qualify, the medium
  sim's 60-beat trunk run always carries locked resolutions);
  `texture_plan` (longest-first sizing against the B6 projection, cap 3,
  budgeted before cadence); invariant **I15** (field checks + the
  edge-projection rule) at G4 with violating-construction tests; and
  `insert_cadence_diamond`/`insert_cadence_sidetrack`, which mirror a
  cadence splice into every arm paralleling its edge. The last one is
  the session's design turn: the plan's v1 reserved textured stretches
  from cadence, and the probe showed that starving a capacity-limited
  system (B6 780→1129 at medium-max — 3 fork decisions bought by ~14
  displaced diamonds); mirroring the diamonds into the arms — the
  author's "even containing branches", arrived early in cosmetic form —
  keeps B6 at 785 with 3 scene-scale worlds (21/15/6-beat stretches)
  planted. Measured cost: +10k story words at medium-max with flat walk
  words — the FILL/print price of writing stretches twice; PR-4 must
  fold that into the words-target arithmetic (plan W3 as-built note; the
  sim keeps `texture_worlds=False` default so W1's calibration constants
  stay true). Engine-only: nothing in the pipeline invokes texture
  worlds until PR-4 wires finalize, prompts, and the FILL context lever.

- **2026-07-14 (structural depth PR-2: the reserve disposition —
  brainstorm surplus as unwoven feedstock):** W2 of the milestone plan,
  built as designed with the seams the build surfaced. Triage gains the
  third disposition `reserve`: BRAINSTORM's requested total grows by a
  per-scope `reserve_dilemmas` allowance (1/2/3/4), and triage keeps the
  surplus in the graph with **no path** — never woven — as texture
  feedstock POLISH finalize surfaces (question, stakes, anchors) as
  advisory graft stock for false-branch arms: echo as texture, never
  advance or decide. Design note recorded in 01 §4: reserve is the one
  disposition that *needs* a stored marker (`Dilemma.reserved`, written
  only via `mutations.set_dilemma_disposition`) because its topology —
  zero explored paths — is also the pre-triage state; branched/locked
  stay topology-derived. Invisibility was a sweep of every
  `nodes_of(Dilemma)` consumer: `weave.shapes` skips reserved (else a
  zero-path dilemma is a WeaveError), SEED's scaffold/order contexts and
  the order schema's enum exclude them, FILL's voice context and shadows
  exclude them, I2 exempts them (feedstock anchors may be cut), and
  DRESS codex eligibility + G6 ignore their anchoring edges; the
  path-based machinery (I3/I6/I7, flags, arcs, freeze) ignores them by
  construction. B1 admits locked+reserve surplus pre-triage and counts
  reserved against the allowance post-triage; a reserved dilemma with a
  path is a gate error. Promotion needs no machinery: a rerun that
  raises `words_target` just re-triages the reserve. Recorded fixtures
  stay green (replay is order-based; the new proposal field is optional).

- **2026-07-14 (structural depth milestone started: the plan, the
  words-target coupling, B9):** The author-directed milestone (see the
  roadmap reframe entry below) moved from "Next" to "Now" the same day; a
  frontier session wrote the milestone contract
  (`docs/plans/structural-depth.md` — four workstreams, PR slicing, the
  texture-fork contract with its starred frontier seams) and built PR-1.
  The mechanics are the agent's, derived from the author's directions plus
  a new structural-simulation measurement: at the table budgets the
  projected story words reach only the *top* of each scope's words band
  (medium: 46–52k of 20–55k), so the lower band was reachable only by
  stretching — and one soft dilemma's marginal yield through the real
  weave/collapse/cadence machinery is ~9k story words at medium (~3.2k
  short, ~11k long). What shipped: `Vision.words_target` (author input,
  `qf new --words-target`, G0-checked against the band) couples the
  **soft** branched budget through `ScopePreset.budget_for` (hard counts
  and the locked allowance never move; clamp [1, table+2]; micro exempt;
  unset = the table exactly, so every existing project, fixture, and
  exemplar validates unchanged), B1/triage/prompts consume the derived
  budget with the derivation named in messages, and **B9** warns when
  bridges exceed 25% of beats — advisory *by design*: the count is
  engine-computed but not in-pass repairable (GROW must bridge every gap,
  I6), so the mandatory-at-apply treatment (the cadence precedent) is
  recorded in the plan as requiring engine-computed + exact + in-pass
  repairable, and bridge share fails the third test. The flat
  `closed-circle-medium` exemplar now trips B9 at 37% (its warning label;
  still 0 errors). Design docs 01 §2 / 02 updated; the BACKLOG
  tier-confound item shrank to the band-recalibration remainder.

- **2026-07-14 (the cadence budget becomes mandatory — the flat-book
  post-mortem):** Reading the checked-in `closed-circle-medium` exemplar, the
  author found it "essentially a flat story ... not interactive fiction" —
  heritage built false branching / passage collapse / soft dilemmas exactly
  against this. The numbers agree: 10 branch points over 112 passages (M8's
  `closed-circle`: 62 over 148), zero `false_branch`-purpose beats (M8: 70),
  words-per-choice 3352 vs the 250–800 B6 band. Root cause is architectural,
  not a model verdict (author, same session: even if kimi fills the budget
  where gpt-oss didn't, "it's still a prompting/architecture issue"): POLISH
  finalize's false-branch site counts are engine-computed (`cadence_plan`
  sizes them to bring words-per-choice into band — post-hoc it wants 63
  sites on this project) but were only *requested in prose*; the schema
  accepts `false_branches: []` and the apply validated only the placement
  of sites actually proposed. The live run's cache shows all four finalize
  rounds proposed zero sites, unchallenged — while the kimi-k2.5 A/B filled
  the same-shaped budget, confirming the heritage floor-count finding (a
  count a prompt merely states is a tier-dependent knob). Fix on the
  follow-up branch: `_finalize_apply` now rejects any proposal that leaves
  a run short of its site count (pre-splice, ApplyError naming run and both
  counts), the prompt says the counts are mandatory, design doc 02 records
  the contract, with a violating-construction test. The B6 gate itself stays
  advisory — the *budget* is the enforcement point because it is exact and
  actionable. The exemplar predates the fix and stays checked in as the
  cautionary baseline. The same author reading split the verdict cleanly:
  "the actual prose is good (for a 120b model)" (author, 2026-07-14) — the
  first author-ratified prose judgment on a weak-tier run, so the
  prose-quality engine half (echo guard, story-so-far, review contract,
  per-passage POV) held at FILL and the defect was purely structural, in
  POLISH's choice layer. (Same reading also surfaced a mechanical `qf graph`
  defect: per-world beat ids carry `--`, which Mermaid parses as an edge —
  ids are now sanitized, labels untouched.)

- **2026-07-14 (rotating-POV live validation: PASSED — first weak-tier medium
  FILL, gate-clean):** The fresh *Closed Circle* medium on `gpt-oss:120b`
  completed FILL with 0 gate errors (6 advisory warnings: 5× B5 near-band
  passages the graded contract accepted, 1× B6 words-per-choice high): 112
  passages / 239 beats / 8 dilemmas, the rotating scheme real at every level —
  voice "third-person limited, rotating among Jordan Blythe, Simon Kade, Marta
  Valen, Cole Duvall", 4 heads over 98 headed passages (60/14/12/12) + 14
  headless texture/coda passages, one head per passage (I14 passing), the
  reviewer observed live enforcing the per-passage head ("may only convey
  Jordan Blythe's internal state"). 844 calls, ~2.8M in / 1.0M out, unbilled.
  ~15 halts total, all diagnosed per the standing rule: five were pre-existing
  prompt/review defects fixed on the branch (finalize world-mismatch brief,
  dialogue-tag fabrication, restated-dialogue echo corrective, address-bans-
  in-dialogue, actor-identity matching), one a design gap backlogged (echo
  floor vs canonical utterances), the rest honest 2-round non-convergence
  cleared by fresh rolls (the operator loop's journal is the per-stall
  record). Zero failures attributable to the rotating-POV machinery. Not
  exercised: interludes (voice declared the register; annotate marked no
  beats) and DRESS. The kimi-k2.5 A/B of the same premise (structure ~40%
  larger; see the tier-confound backlog note) continues.

- **2026-07-14 (DREAM interprets the vision; it is not micromanaged — author
  decision):** After two live DREAM runs rewrote an authored rotating
  `pov_hint` into an invented single-head scheme, the session over-corrected
  twice — first an engine-keep of the authored wording (75de5a4), then a
  two-field authored/decided provenance split (c03b37a) — and the author
  rejected both: DREAM's task is to *translate* the author's vision into a
  creative contract, so its output is legitimately interpretive, and the
  rewrite-survival requirement was only ever this validation's *test* need,
  not pipeline semantics. What ships instead: **visibility only** — the
  authored `pov_hint` now renders in the dream prompt as vision input (both
  live rewrites happened because `_context` never passed it: interpretation
  without the input is not interpretation), `_apply` stores the model's
  translation exactly as before, and the sanctioned override when an author
  or a validation must pin the scheme is the existing A17 path: **edit the
  DREAM artifact after DREAM, before BRAINSTORM** (the live validation's
  operator loop automates the stop-and-check). `pov_hint_decided` and
  `effective_pov_hint` are reverted; `Vision` keeps its single field.

- **2026-07-14 (model strength is not the diagnosis axis — author correction to
  the standing rule):** During the *Closed Circle* live validation the session
  wrote off FILL stalls as "classic stochastic weak-tier behavior" — a red-flag
  phrase — and the author corrected the *frame itself*, twice: (1) an
  under-determined prompt makes **every** tier sample the gap; a strong model
  does not reconstruct intent, it fills the gap plausibly and confidently, so
  the same variance ships with more fluency; (2) strong-tier success on an
  unproven prompt is therefore not neutral luck but **the masking mechanism
  observed in action** — evidence the model papered over a defect that is
  still there, now invisible, waiting for a different sample, story, or tier.
  Codified in AGENTS.md §"Prompt and error-message quality" (direct author
  instruction, this session): only constraint completeness validates a prompt,
  "stochastic weak-tier behavior" joins the forbidden phrases, and the weak
  tier surfaces defects first only because it fails less persuasively. The
  correction immediately produced results: tracing the stall journal against
  the prompts (instead of writing "stochastic") found three real write-prompt
  under-determinations, fixed the same session (head pronouns in the viewpoint
  line; check-the-beats-off; REVISE, DON'T REWRITE).

- **2026-07-14 (repair-message audit — all 79 ApplyError sites, author-requested):**
  The *Closed Circle* live run exhausted finalize repairs on a residue
  world-mismatch whose message listed the valid set but not the corrective —
  despite earlier sessions having been asked to audit *all* prompts and repair
  messages. The author called it out ("what else was silently skipped"); no
  artifact existed to answer that, which is itself the finding: **an audit
  without a per-site record is a claim, not an audit.** This session enumerated
  every `raise ApplyError` in `src/questfoundry` (79 sites: polish 23+, dress 18,
  grow 15, seed 15, fill 5, brainstorm/research/types 1 each) and judged each
  against the AGENTS.md contract (reason + subject + recovery_action as an
  instruction). Verdicts (as corrected by PR #74 review): **64 already
  conformant** (imperative corrective or exact valid set present;
  `format_validation_error` and seed's aggregated scaffold-audit briefs
  verified conformant — and the false-branch/residue KeyError wraps, which
  this audit first mis-recorded as blunt: `add_beat` already converts the
  duplicate-id KeyError into an actionable MutationError, so the added
  `except KeyError` branches were dead code and would have mislabeled a
  GraphError; reverted, the combined catch's inner messages carry their own
  correctives), **6 blunt → fixed** (finalize world-mismatch — fixed earlier
  the same day; false-branch not-in-long-run, now pointing at the prompt's
  CADENCE runs; SEED unknown answer / unknown locked dilemma, now listing the
  valid ids; GROW intersection member, now listing the eligible beats; DRESS
  brief-count, now stating add/drop-to-target; POLISH needs-no-variants, now
  instructing `variants: []`), and **9 duplicate-entry sites sharpened** with the explicit
  "keep exactly one / drop the extras" imperative (dress profiles/briefs/
  codex/codewords, grow rewrite/annotate dups + intersection double-membership,
  polish audit/arcs dups). The **prompt-template half is NOT covered** by this
  audit — recorded as an explicit BACKLOG item listing all 28 templates so the
  next "audited?" question has a checkable answer either way.

- **2026-07-14 (rotating limited POV — author-answered design, built offline):**
  The five open questions in `docs/plans/rotating-pov.md` were put to the author
  directly (explicit per-question prompts, this session) and answered: viewpoint
  **per passage** (never switching inside one; `wide` codas still compose on
  top), assigned **per beat by GROW's annotate pass**, **no cadence engine
  constraint** in v1 (prompt guidance: prefer runs), **first-person interludes
  in scope**, golden coverage by **annotating keepers-bargain's constant head**
  plus the recorded e2e fixture (no second golden). Design in
  `docs/plans/rotating-pov-build.md`; built the same session: `Beat.viewpoint`/
  `Beat.interlude` + `set_beat_viewpoint` (settled at freeze), `passage_viewpoint`
  derivation (computed, never stored), **I14** (one head per passage, gate G4) +
  a G3 referential check, the annotate schema pin to retained character ids, the
  collapse `split_viewpoints` cut (passage-building only; raw cadence runs stay
  uncut), per-passage POV keying in `fill_write.j2`/`fill_review.j2` with window
  head-switch notes, and `Voice.interlude` (+ required `VoiceProposal.interlude`,
  cast-validated). Architecture row A22 (03 §9). Open: the live *Closed Circle*
  validation on the unbilled tier — a **fresh medium project** (author-directed,
  2026-07-14): the prior session's medium project died with its container (only
  the old M8 `examples/closed-circle` survives in git, a different, completed
  project), and the old POLISH checkpoint would have been headless anyway (heads
  are minted at GROW's annotate; `qf rerun grow` is the resume point when a
  project *does* survive). The fresh vision pins the same premise and the
  rotating+journal `pov_hint` verbatim.

- **2026-07-13 (don't blame the weak model — a standing agent rule + two POLISH
  prompt fixes it forced):** During the narration_scope live runs two POLISH passes
  crashed on the weak tier, and the session reflexively wrote them off as "known
  weak-tier difficulty" — exactly the misjudgment AGENTS.md §"Prompt and error-message
  quality" warns against (author correction). Codified as a new lead rule in that
  section: *the agent will feel the urge to blame a weak model and will almost always
  be wrong; red-flag phrases ("weak-tier", "the model isn't strong enough") may not be
  written until the prompt and the error message have been read and shown correct.*
  Applying it produced two real defects, not model limits: (1) **finalize
  residue-duplicate** — the model emitted a second residue arm for a path and
  repair-exhausted; the rule *was* in the prompt, but the ApplyError's recovery_action
  offered only `followup` (a longer arm), never `fork` (two textures) — so a model that
  duplicated because it wanted two flavors was told the wrong tool. **Fixed:** the
  message now names both recovery paths and "drop the duplicate", and the finalize
  prompt preempts ("never two entries for one path — use followup/fork"). (2) **passages
  `AdapterError` at medium** — the *passages* pass generates the **whole** passage layer
  in a single call (apply requires every group covered at once); at medium scale
  (90-160 passages) that output overruns `num_ctx 32768` and truncates into invalid
  JSON. A genuine **scale/output-structure limit** (fix: chunk the pass, or raise
  num_ctx), diagnosed — not dismissed as model weakness; a real fix is a follow-up. A
  **death-ending noir micro** was also launched (the premise structurally forces an
  out-of-horizon coda) to finally exercise `wide` live.

- **2026-07-13 (narration_scope live validation — micro clean, `wide` not yet exercised;
  unbilled `gpt-oss:120b-cloud`):** After PR #68 merged, a fresh **noir micro**
  ("Rain and Jade", the Maltese-Falcon premise — preserved as
  [`examples/rain-and-jade`](../examples/rain-and-jade)) ran DREAM→FILL on the weak
  tier. **Result: clean completion, no regression.** FILL finished with 0 gate errors
  and **no review-exhaustion halt** — every passage ≤ 2 attempts, and the endings (a
  3rd-person-limited voice, "Sam Rain Marlowe" — the exact shape the pre-fix "Black
  Bird" run died on) wrote clean limited-POV prose, no head-hopping. **But all 30 beats
  came out `limited`** and the `wide` coda license was *not* exercised — because SEED
  produced a story where every consequence reaches the POV character directly (he hands
  the jade over, hears the informant, is roared at), so no beat *deserved* `wide`.
  Verified by reading the ending beat summaries: `limited` is correct throughout, not
  over-suppressed. **Finding (author's instinct, confirmed):** the system is nudged
  toward `limited` at *two* layers — the annotate prompt's "when in doubt, limited"
  (appropriate; `wide` is the marked exception) and, more consequentially, the
  *upstream* steering (this run's `dream` steer "the fates that land after the case
  closes are a brief coda" + the SEED perceivable-consequence steer) which biases SEED
  toward writing perceivable endings so a `wide`-deserving beat is rarely generated. So
  to actually exercise `wide`, a run needs a story that *structurally* demands an
  out-of-horizon coda — a **death ending** (aftermath beyond the detective's horizon —
  the "posthumous reputation" case) or a **time-skip epilogue**. Two orthogonal notes:
  supernatural drift (the jade *pulses*; a binding "ritual") against the vision's
  `content_notes` (a DREAM/BRAINSTORM adherence issue), and B7 2381 vs the micro floor
  2400 (the expected modulation-shortens-sequels signal). Also observed: a transient
  `RemoteProtocolError` (cloud dropped a large SEED-scaffold response) is **not**
  retried by the Ollama provider — it crashes the stage; the A16 ledger re-run recovers
  it free, but a transport-level retry/backoff is a worthwhile robustness follow-up.
  **Follow-up (same session):** the `limited`-nudge finding drove a **softening of the
  SEED coda steer** (`seed_scaffold.j2`, commit in PR #69) — the #68 wording forbade a
  coda beat from existing at all; the softened wording *permits* a brief earned coda
  while still discouraging omniscient full scenes (plan doc §"SEED context gap" updated
  to match). Result across **three** runs — micro (30), medium (111), softened-micro
  (24) — is **still all `limited`, 0 `wide`**: softening *permits* a coda but cannot
  *manufacture* one, and this recover-the-figurine premise keeps the detective present
  at every ending, so there is genuinely no out-of-horizon beat. **Conclusion:**
  completion + no-regression + the case-A/psychic-distance clarity are validated live;
  the `wide` license itself is proven only by unit tests so far. Exercising `wide`
  live needs a premise that *structurally* demands a coda — a **death ending** or a
  **time-skip epilogue** (the original "posthumous reputation" shape).
  **`wide` is now proven live** (preserved as [`examples/greywater-docks`](../examples/greywater-docks)):
  a death-ending noir micro (dying PI, "the city goes on without him") ran clean
  through FILL. **SEED** (softened steer) generated a genuine out-of-horizon coda beat
  (`beat:city-continues` — "life in Greywater Docks rolls on, indifferent to the broken
  myth"); **GROW annotate** tagged it `wide` on its own (a *narrative* beat, not the
  fallback — 24 `limited`, 1 `wide`); **FILL** wrote the finale passage `p-finale` in one
  pass — the *exact* collapse shape that broke "Black Bird" (climax `scene` beats +
  world-coda in one limited-POV finale) — narrating Elliot's death in limited POV then
  stepping back to a detached `wide` coda beyond the dead detective, no POV break, first
  try, and the reviewer did not flag it. The full chain (softened SEED → coda beat →
  annotate picks `wide` → FILL writes limited-then-wide → reviewer accepts) is validated
  end-to-end. Cleaner than `rain-and-jade` too (no supernatural drift). **The
  narration_scope effort is now fully live-validated.**

- **2026-07-13 (epilogue/POV collapse-feasibility — design decided, author-directed):**
  The noir finale failure (STATUS "Next up" kickoff) was diagnosed and resolved into a
  build contract, [`docs/plans/pov-narration-scope.md`](plans/pov-narration-scope.md).
  **The reframe that unlocked it:** the corpus's own POV note distinguishes *psychic
  distance* (camera far↔close) from *POV person*, so the one failure was really two.
  **(A)** "the Falcon is auctioned… fueling Victor's armaments" is a world-scope fact a
  *limited* narrator can deliver by widening distance — **not** a POV break; the failure
  there was a **blunt prompt** (`fill_write.j2`'s "Only that narrator's thoughts may be
  stated… every other character reaches the reader only through what the narrator can
  observe" conflates *no other minds* with *close distance always*), exactly the
  AGENTS.md "prompt is the first suspect" class — the model correctly refused a
  miswritten rule. **(B)** "Mace becomes a cautionary ghost" (his posthumous reputation,
  after he exits) is genuinely beyond a Mace-tied limited POV and needs a sanctioned
  coda register. **Root cause:** POV is chosen at FILL (the `Voice` singleton, one POV
  string) but beat feasibility-under-POV is fixed at SEED, four stages earlier, with no
  POV awareness (the scaffold prompt never even renders `vision.pov_hint`); the acute
  failure was a *collapse* event — a live scene + world coda crushed into one passage.
  **Decisions (author):** (1.a) a narrow per-beat `narration_scope ∈ {limited, wide}`
  annotation folded into GROW's existing `annotate` pass, settled-at-freeze like
  `scene_type`, `epilogue`→`wide` fallback else `limited`; **not** a full per-beat
  viewpoint-character field (that invites the head-hopping the corpus warns against).
  (3.a) `wide` is the marked exception — epilogue default, deliberate opt-in elsewhere.
  (2, resolved **no split**) the author's narrative argument settled it: a passage may
  run one paragraph `wide` and the next `limited`, and a forced collapse boundary would
  insert a spurious single-option page-turn between a climax and its coda — so FILL
  modulates register *per beat within a passage* (the `scene_type` pattern) and **POLISH
  collapse is untouched**. Scope stays orthogonal to length (`scene_type`/`passage_intensity`
  keep the word band). The case-A prompt fix ships regardless (a correctness fix).
  **Built the same session** (plan → all six checkpoints, contract
  [`docs/plans/pov-narration-scope.md`](plans/pov-narration-scope.md) marked BUILT):
  model + mutation, the widened `annotate` pass (one call still, `scene_type` +
  `narration_scope`), the FILL two-rule POV rewrite + per-beat scope directive +
  scope-keyed reviewer, the SEED `pov_hint`/brief-coda steer, golden left all-`limited`
  (an intimate story with no coda — `wide` covered by unit + fallback tests), docs
  (01 §Beat annotations/§10.3, 02 GROW/FILL). Fixture note held exactly: FILL prompt
  changes needed no re-record (call-order replay), only the GROW `annotate` recorded
  call (007.json) widened with `narration_scope` per beat. 557 tests, ruff clean,
  golden 0/0. **Open follow-up:** live validation on `gpt-oss:120b` (the noir re-run +
  a real *medium* — guard against the `scope:`-line operator slip).

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
