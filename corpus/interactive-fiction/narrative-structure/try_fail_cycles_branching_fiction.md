---
title: "Try-Fail Cycles in Branching Fiction"
summary: "Using escalating failure sequences as natural choice points in interactive fiction — each failed attempt as a branch, compounding failures across paths."
topics:
  - try-fail-cycle
  - escalation
  - failure-as-choice
  - branching-escalation
  - rule-of-three
  - compounding-failure
  - choice-points
  - stakes-ladder
  - yes-but-no-and
cluster: narrative-structure
---

# Try-Fail Cycles in Branching Fiction

Craft guidance for building stories where the protagonist's repeated attempts to solve a problem generate the story's branching structure — each failure raising the stakes, revealing information, and presenting the player with a natural question: how do you try again?

---

## The Try-Fail Cycle

### Structure and Purpose

The try-fail cycle is one of the oldest narrative engines: a character attempts something, fails, and must try again under worse conditions. The basic pattern runs Attempt, Failure, Escalation, repeated until the final attempt produces resolution — success, transformed success, or earned defeat.

The pattern works because each failure does three things simultaneously:

1. **Raises the stakes** — resources are spent, allies are alienated, time runs out
2. **Reveals information** — the failure teaches something about the problem, the world, or the character
3. **Increases investment** — the reader (or player) has watched the struggle and wants resolution more intensely

**The Rule of Three** is the most common implementation. Audiences expect three attempts: the first establishes the difficulty, the second deepens it, and the third resolves it. Two attempts feel thin. Four or more risk exhausting patience unless each attempt is substantially different.

The escalation requirement is non-negotiable. Each attempt must be harder, costlier, or more desperate than the last. A cycle where the character simply "tries again" with no meaningful change feels like padding, not storytelling. The escalation can be external (the guard is now alert), internal (the character is now wounded), or both — but something must be different.

### The Yes-But / No-And Vocabulary

Traditional craft treats attempt outcomes as binary: success or failure. Improv and modern writing craft offer a richer vocabulary with four outcome types that produce different escalation effects.

| Outcome Type | Description | Escalation Effect | When to Use |
|--------------|-------------|-------------------|-------------|
| **Yes-And** | Full success plus unexpected benefit | Ends the cycle with momentum | Final attempt; rare mid-cycle |
| **Yes-But** | Success with a catch or new complication | Solves one problem, creates another | Mid-cycle pivot; bittersweet resolution |
| **No-But** | Failure with a silver lining or new clue | Maintains hope; reveals information | Early and mid-cycle; sustains engagement |
| **No-And** | Full failure plus new complication | Maximum escalation; darkest outcome | Raising stakes dramatically; forcing desperation |

These four outcomes give writers far more control than pass/fail. A mid-cycle **No-But** ("the lock doesn't open, but you notice the hinges are rusted") keeps the player engaged and learning. A **No-And** ("the lock doesn't open, and the alarm triggers") forces genuine desperation. The final attempt might produce a **Yes-But** ("you escape, but your ally doesn't") rather than a clean triumph — and the story is richer for it.

### What Changes Between Attempts

Each attempt in a try-fail cycle must differ from the previous one in at least one meaningful dimension:

**Approach** — a different method, tool, or strategy. Picking the lock fails; now try breaking the door down.

**Stakes** — what is risked has changed. First attempt risked time; second risks discovery; third risks a relationship.

**Information** — what the character now knows. The first failure revealed the guard's schedule; the second revealed the alarm system. The third attempt uses both.

**Desperation** — the character's emotional state has shifted. Calm analysis gave way to improvisation, which gave way to recklessness.

If attempts differ only in "trying harder," the cycle feels mechanical. The character who picks the lock, then picks it harder, then picks it really hard has not earned resolution — they have repeated themselves. The character who picks the lock, then tries the window, then bribes the guard has demonstrated resourcefulness and exhausted their options, making whatever comes next feel earned.

---

## Try-Fail as Branching Architecture

The central argument: try-fail cycles are natural branch generators for interactive fiction. Where standard branching imposes choice from outside ("go left or right"), try-fail branching emerges from story logic ("that didn't work — what do you try next?").

### Each Failure as a Choice Point

After a failed attempt, the player faces a natural question: how to approach the problem differently. This produces organic branching — not because the author inserted a fork in the road, but because the situation demands a decision.

Consider the difference:

> **Author-imposed branching:** "You reach a fork in the corridor. Do you go left or right?"
>
> **Try-fail branching:** "The door is locked. The guard returns in ten minutes. You can pick the lock, find another entrance, or try to bluff your way past the guard when he returns."

The second version branches because the problem demands it. Each option represents a genuine approach with its own logic, difficulty, and failure mode. The player is not choosing a path — they are choosing a strategy. This distinction matters: strategy choices feel meaningful in ways that directional choices do not.

### Hub-and-Spoke Try-Fail

The player returns to a central problem after each failed attempt, choosing which approach to try next.

The structure:

> Hub (the problem) --> Spoke 1 (attempt, fails) --> Hub --> Spoke 2 (attempt, fails) --> Hub --> Spoke 3 (attempt, succeeds or transforms the problem)

The player controls the ordering. Each spoke may reveal information useful in other spokes. The hub itself may change as consequences accumulate — the guard is now suspicious, the window is now boarded up, the bribe contact has left.

**Best for:** investigation sequences, puzzle-solving, negotiation, gaining access to a guarded location.

> **Example:** The player needs to enter a noble's estate. Spokes: forge an invitation (fails — the seal is wrong, but you learn the guest list), climb the wall (fails — guards patrol, but you spot the servants' entrance), befriend a servant (fails — but you learn the noble's schedule). Each failure reveals something. The player synthesizes the information for a final approach.

Hub-and-spoke try-fail is one of the most sustainable branching architectures because all paths converge on the same problem. The branches are wide but contained, and each spoke can be developed independently.

### Linear Try-Fail

Each failure leads directly to the next attempt without returning to a hub. The momentum is forward; the player does not choose the ordering.

The structure:

> Attempt 1 (fails, consequence forces) --> Attempt 2 (fails, desperation drives) --> Attempt 3 (resolution)

The player may have less choice in ordering but more sense of momentum. Each failure's specific consequence determines what the next attempt must be.

**Best for:** chase sequences, combat encounters, time pressure situations, escape scenarios.

> **Example:** Escaping a collapsing building. The main stairway is blocked (Attempt 1 — No-And: the ceiling collapses behind you). You try the fire escape (Attempt 2 — No-But: it is jammed, but you see the loading dock below). You jump for the loading dock awning (Attempt 3 — Yes-But: you land hard and injure your ankle, but you are out).

Linear try-fail works well for high-momentum sequences where pausing to choose would break tension. The player's agency comes from within each attempt (how they handle it) rather than between attempts (which one to try).

### Information-Gathering Try-Fail

Each failure is designed to reveal a specific piece of information needed for the eventual solution. The player must synthesize clues gathered across multiple failures.

The structure:

> Attempt 1 (fails, reveals clue X) --> Attempt 2 (fails, reveals clue Y) --> Attempt 3 (uses X + Y to succeed)

The key design element is synthesis. The final attempt does not succeed because the character "tries harder" — it succeeds because the character now possesses knowledge assembled from previous failures. The player who paid attention recognizes the connection.

**Best for:** mystery and investigation, puzzle design, any scenario where understanding the problem IS the solution.

> **Example:** Breaking a magical ward. First attempt (direct force) reveals the ward responds to elemental magic. Second attempt (fire spell) reveals the ward absorbs single elements but cracks under combined elements. Third attempt (fire and ice simultaneously) succeeds — but only if the player connects what the first two failures taught.

---

## Compounding Failure Across Branches

### The Failure Ledger

In interactive fiction, failed attempts should leave persistent marks on the game state. Track consequences as flags that affect later encounters:

- **Failed bribe:** the guard is now suspicious of strangers
- **Failed break-in:** security has been heightened throughout the estate
- **Failed disguise:** the player's face is now known to the household
- **Failed charm:** the NPC is now hostile rather than neutral

The player's specific failure history produces a specific challenge set. A player who failed the bribe and the break-in faces a different final approach than a player who failed the disguise and the charm. This means the "same" problem has multiple solutions, each shaped by what went wrong before.

The failure ledger is also a storytelling tool. When an NPC says "You're the one who tried to break in last night," the player's failure becomes part of the narrative fabric rather than a discarded branch.

### Escalation Order Independence

In hub-and-spoke try-fail structures, the player controls the sequence. This creates a design challenge: how do you ensure escalation regardless of which spoke the player tries first?

**Solution 1: Compounding complications.** Each failure adds a complication that makes ALL remaining approaches harder. Failed bribe makes the guard alert, which affects the break-in attempt AND the disguise attempt. Order does not matter because every failure compounds.

**Solution 2: Weighted later attempts.** The third attempt is inherently harder because two failures have accumulated. The system does not need to track which failures — only how many. Two failures mean heightened security, regardless of what specifically went wrong.

**Solution 3: Parallel difficulty, different character.** All approaches are roughly equal in difficulty but test different player skills or values. The bribe tests resourcefulness, the break-in tests daring, the disguise tests social manipulation. Escalation comes not from increasing difficulty but from accumulating consequences.

The best designs combine these. Each failure adds a specific complication (Solution 1) while later attempts are generically harder due to accumulated suspicion (Solution 2), and the approaches themselves test different aspects of the character (Solution 3).

### The Diminishing Options Pattern

A powerful variant: each failure eliminates one approach entirely. The player starts with four or five possible strategies. Each failed attempt removes that strategy from the board. After three failures, only the desperate option remains.

This creates emergent narrative. The player who burned through the clever approaches — diplomacy, stealth, deception — is left with brute force. The story implicitly says: "You ran out of clever options." The desperation is not scripted; it is produced by the player's own sequence of failures.

Design considerations:

- Start with enough approaches (4-5) that the player has genuine choice even after failures
- The "desperate option" should always be available as a last resort
- Some approaches should be clearly riskier, creating tension between safe-early and dangerous-late
- The final approach should feel like a natural consequence of exhausting alternatives

---

## Distinguishing Try-Fail from Related Patterns

### Try-Fail vs Cascading Disaster

Try-fail and cascading disaster both involve escalating problems, but they operate on different logic.

| Dimension | Try-Fail Cycle | Cascading Disaster | Combined |
|-----------|---------------|-------------------|----------|
| Source of problems | External obstacle persists | Character's solutions create NEW problems | Solutions to the obstacle create new obstacles |
| Character role | Problem-solver | Problem-creator | Both simultaneously |
| Escalation driver | The obstacle is harder to overcome | The consequences are harder to contain | Each attempt makes the obstacle harder AND creates side effects |
| Emotional register | Determination, resourcefulness | Desperation, moral compromise | Grim determination eroding into desperation |
| Resolution | Earned success through learning | Collapse or narrow escape | Pyrrhic victory at best |

They combine naturally. A character trying to rescue a hostage (try-fail) whose first attempt alerts the kidnappers, whose second attempt injures a bystander, and whose third attempt requires lying to the police (cascading disaster layered onto try-fail).

### Try-Fail vs Dilemma Chain

Try-fail and dilemma chains address different questions about a problem.

In a try-fail cycle, the problem is fixed and the question is **how** to solve it. The locked door must be opened. The approaches differ, but the goal is constant.

In a dilemma chain, the problem requires sacrifice and the question is **what to sacrifice**. The situation cannot be solved without cost, and the player must choose which cost to pay.

They connect at the boundary: a try-fail cycle may culminate in a dilemma when all approaches have been exhausted. The player who has tried everything and failed faces a final choice that is no longer "how do I solve this?" but "what am I willing to give up to solve this?" This transition — from resourcefulness to sacrifice — is one of the most powerful moments in interactive fiction.

### Try-Fail vs Standard Branching

Standard branching creates divergence: the player chooses a path, and each path leads somewhere different. The story fans outward.

Try-fail branching creates approach variation: the player chooses how to tackle a fixed problem, and all approaches converge on the same goal. The story expands locally but contracts structurally.

| Dimension | Standard Branching | Try-Fail Branching |
|-----------|-------------------|-------------------|
| Path direction | Paths diverge toward different destinations | Paths circle back to the same problem |
| Scalability | Exponential growth; expensive to maintain | Contained growth; spokes share a hub |
| Player experience | "Where does this path lead?" | "How do I solve this?" |
| Authoring cost | Each branch needs unique content through resolution | Each attempt needs unique content; resolution is shared |
| Convergence | Requires bottleneck passages or state tracking | Naturally convergent — the problem IS the bottleneck |

This convergence property makes try-fail one of the most practical branching architectures for sustainable IF development. The branches are real and meaningful, but they all feed back into a shared narrative spine.

---

## Interactive Fiction: Designing Try-Fail for Player Satisfaction

### Making Failure Feel Fair

Nothing kills player engagement faster than feeling cheated by a failure they could not have anticipated or prevented. Every failed attempt must satisfy the player's sense of fairness.

**Explain why the approach failed.** Not with a dismissive "that doesn't work" but with specific information: "The lock is more complex than you expected — it requires a three-tumbler technique you don't know." The player understands the failure and gains knowledge.

**Foreshadow failure conditions.** If the break-in will fail because of guard patrols, hint at the patrols before the attempt. The player who chose the break-in anyway made an informed risk. The player who missed the hint learns to read the environment more carefully.

**Prefer No-But to No-And in early attempts.** Early failures should feel like setbacks with silver linings, not catastrophes. Save the No-And outcomes for later in the cycle when the player has invested enough to handle a harsh failure.

### Making Each Attempt Feel Meaningful

Even failed attempts must produce story value. The player should never feel they "wasted" a choice.

**Information value:** Every failure reveals something — about the problem, the world, or the characters involved. The failed bribe reveals the guard's loyalty. The failed break-in reveals the alarm system. Knowledge persists even when approaches fail.

**Character development:** Attempts reveal character. The player who tries diplomacy first is building a different character than the player who tries force first. NPCs should notice and respond to the player's approach pattern.

**Relationship changes:** Failed attempts affect relationships. The guard you tried to bribe is now wary of you. The servant you befriended may still be sympathetic even though the attempt failed. These relationship shifts carry forward.

**Unique content:** Each failed approach should unlock content the player would not otherwise see. The player who tried the bribe learns about the guard's backstory. The player who tried the wall learns about the estate's architecture. Failure branches should contain discoveries that reward exploration.

### The Final Attempt as Earned Climax

The resolution of a try-fail cycle should feel earned — not lucky, not arbitrary, but the logical result of everything the player learned through failure.

**Synthesis of failure knowledge.** The final approach works because it incorporates what earlier failures taught. The player recognizes that their earlier "wasted" attempts were actually reconnaissance.

**Player recognition.** The connection between past failures and current success should be visible. If the player picked the lock (learning it has three tumblers), tried the window (learning the guard schedule), and now enters through the servants' door at the shift change using a three-tumbler pick — they should see how each failure contributed.

**Variant: the earned refusal.** Allow the player to choose NOT to try again. After two or three failures, walking away should be a valid, acknowledged option. This choice can itself be powerful — the character who recognizes the cost is too high, who accepts a limitation, who changes their goal rather than their method.

### Scaling Try-Fail for Story Length

The try-fail cycle is fractal — it operates at multiple scales, and larger stories embed cycles within cycles.

**Short IF (20-50 passages):** One core try-fail cycle with three attempts. The entire story IS the cycle. Each attempt is a significant portion of the narrative.

**Medium IF (50-150 passages):** Two to three try-fail cycles at different scales. The main plot has its own cycle, and individual chapters may contain smaller ones. A negotiation scene might have its own mini-cycle within a larger quest cycle.

**Long IF (150+ passages):** Nested cycles at multiple levels. The overall arc is a try-fail cycle (three major attempts to achieve the goal). Each major attempt contains its own try-fail cycle. Individual scenes within those attempts may have their own micro-cycles.

**The fractal property:** a single "attempt" at one scale may itself be a complete try-fail cycle at a smaller scale. The player's second major attempt to infiltrate the castle (macro-cycle) involves trying three different approaches to get past the gate (micro-cycle within the macro attempt).

## Quick Reference

| Goal | Technique |
|------|-----------|
| Generate natural branching | Use each failure as a choice point — "what do you try next?" |
| Ensure escalation regardless of order | Compound complications from every failure; weight later attempts heavier |
| Make failure feel fair | Explain why it failed; foreshadow conditions; prefer No-But early |
| Make attempts meaningful | Each failure reveals information, develops character, or shifts relationships |
| Build earned resolution | Final attempt synthesizes knowledge from previous failures |
| Control cycle length | Rule of Three for most contexts; 4-5 approaches for diminishing options |
| Sustain long IF structure | Nest try-fail cycles fractally — micro-cycles within macro attempts |

---

## Research Basis

| Concept | Source |
|---------|--------|
| Rule of Three in dramatic structure | Syd Field, *Screenplay: The Foundations of Screenwriting* (1979) — three-act escalation |
| Try-fail cycle and Yes-But/No-And vocabulary | Mary Robinette Kowal et al., *Writing Excuses* podcast — systematic failure outcome taxonomy |
| Scene Disaster as story engine | Dwight V. Swain, *Techniques of the Selling Writer* (1965) — Goal-Conflict-Disaster framework |
| Hub-and-spoke puzzle design in IF | Emily Short, various essays on puzzle-based interactive fiction structure |
| Hub-and-spoke puzzle architecture | Steve Meretzky, design notes on *Planetfall* and *A Mind Forever Voyaging* (Infocom, 1983-1985) |
| "Failing forward" in interactive design | Jenova Chen, GDC talks on *Flow* theory and meaningful failure in games |
| Nested scene conflicts and sequel structure | Jack M. Bickham, *Scene and Structure* (1993) — layered conflict within scene units |
| Escalation through resourcefulness depletion | Brandon Sanderson, BYU lectures on try-fail cycles and reader satisfaction |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] — Rule of Three escalation and compounding consequences
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/cascading_disaster_patterns|Cascading Disaster Patterns]] — Related but distinct: solutions creating new problems vs approaches to a fixed problem
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_craft|Branching Narrative Craft]] — Choice architecture and consequence systems for IF
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — Hub-and-spoke structures and emotional arc scaffolding
- [[Narrative & Game Design/Interactive Fiction/emotional-design/conflict_patterns|Conflict Patterns]] — Try-fail cycle and stakes ladder as conflict engines
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/moral_dilemma_chains|Moral Dilemma Chains]] — When try-fail exhausts options and the final attempt requires moral compromise
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/endings_patterns|Endings Patterns]] — Earned resolution through accumulated failure and synthesis
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_structure_and_beats|Scene Structure and Beats]] — Each failure is a Scene Disaster triggering a Sequel
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_sequel_in_interactive_fiction|Scene and Sequel in Interactive Fiction]] -- each Attempt-Failure beat is a Scene whose Disaster launches the next Sequel
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/time_loop_patterns|Time Loop Patterns]] -- the loop as a diegetic, knowledge-accumulating try-fail engine
