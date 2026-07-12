---
title: "Scene and Sequel in Interactive Fiction"
summary: "Applying Swain's Scene/Sequel pattern to branching narratives — mapping Reaction-Dilemma-Decision onto the player choice mechanic."
topics:
  - scene-sequel
  - swain-structure
  - pacing
  - player-choice
  - reaction-beats
  - dilemma-mapping
  - branching-pacing
  - sequel-as-choice
cluster: narrative-structure
---

# Scene and Sequel in Interactive Fiction

Craft guidance for applying Dwight Swain's Scene/Sequel model directly to interactive fiction design — treating the Sequel not as a passive transition but as the structural home of player choice, and using Scene/Sequel ratios as a deliberate pacing instrument across branches.

---

## The Scene/Sequel Model

The Scene/Sequel framework, introduced by Swain and expanded by Bickham, divides narrative into two complementary unit types. [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] covers this at an overview level; here we go deeper into mechanics and IF-specific application.

### Scene: The Unit of Conflict

A **Scene** (in the Swain sense, distinct from a visual scene or passage) is a micro-arc of conflict built from three beats:

| Beat | Function | Question It Answers |
|------|----------|---------------------|
| **Goal** | What the POV character wants right now | What am I trying to do? |
| **Conflict** | The opposition they encounter | What stops me? |
| **Disaster** | The setback that ends the unit | What went wrong? |

The Disaster is the engine of the entire model. Without it, there is nothing to react to, nothing to decide, and no reason for the next Scene to exist.

**Types of Disaster:**

- **Outright failure** — The character does not get what they want. The door is locked, the NPC refuses, the plan collapses.
- **Yes-but** — The character gets what they want, but at an unexpected cost. They find the key, but an alarm triggers. They convince the NPC, but must make a promise they cannot keep.
- **Unexpected complication** — Something unrelated intervenes before the conflict resolves. A new threat, a revelation, a ticking clock that changes priorities.

The critical rule: **Disaster must be a logical consequence**, not a random event. If the character picks a lock and the building collapses, the reader (or player) feels cheated unless the collapse was foreshadowed. If the character picks a lock and the alarm sounds, the consequence follows from the action. Logical Disasters earn the Sequel that follows.

### Sequel: The Unit of Transition

A **Sequel** bridges one Scene to the next through three beats:

| Beat | Function | Question It Answers |
|------|----------|---------------------|
| **Reaction** | Emotional and physical response to Disaster | How do I feel about what just happened? |
| **Dilemma** | Assessment of available options | What can I do now? |
| **Decision** | Commitment to a new course of action | What will I do? |

The Sequel translates Disaster into a new Goal, which launches the next Scene. Without Sequels, stories become disconnected events — things happen, but the character (and reader) never processes them, never weighs options, and never commits to a direction. The result feels mechanical, like a sequence of action set pieces with no connecting tissue.

### The Alternation Principle

The classical model presents strict Scene-Sequel alternation: every Scene is followed by a Sequel, every Sequel launches a Scene. This is a **teaching model**, not a rigid rule.

In practice, writers use several variations:

- **Compressed Sequels** — Bickham's term for Sequels reduced to a single sentence or even a phrase. "She gritted her teeth and turned for the back door." Reaction, Dilemma, and Decision collapsed into one beat. Used in fast-paced sequences where lingering would kill momentum.
- **Half-Scenes** — A Scene interrupted by a new complication before the Disaster lands. The character is pursuing Goal A when complication B forces an immediate pivot. The interrupted Scene's Disaster is deferred, creating suspense.
- **Stacked Sequels** — Multiple Disasters accumulate before the character has time to process any of them. The Sequel that follows must address several setbacks at once, deepening the Dilemma.
- **Embedded Sequels** — Sequel beats woven into ongoing action rather than presented as standalone units. The character reacts while running, weighs options while fighting, decides while the clock ticks.

The alternation principle is better understood as: **every significant setback deserves a response, and every response should lead to action.** How compressed or expanded that cycle is depends on pacing needs.

---

## The Sequel as Player Choice

Here is the central argument of this document: **in interactive fiction, the Sequel IS the choice point.** The three beats of the Sequel — Reaction, Dilemma, Decision — map directly onto the mechanics of presenting a choice to the player.

### Mapping Sequel Beats to IF Mechanics

| Sequel Beat | IF Implementation | Example |
|-------------|-------------------|---------|
| **Reaction** | Aftermath prose shown to the player | "The bridge collapses behind you. Dust chokes the air. Your hands are shaking." |
| **Dilemma** | Choice presentation — the options and their implied trade-offs | "You could press deeper into the ruins, or double back through the river canyon." |
| **Decision** | The player's click — selecting an option | Player selects "Press deeper into the ruins" |

This mapping is not metaphorical. When an IF passage ends a Scene with a Disaster and then presents the player with options, the passage is *literally* executing a Sequel. The Reaction is the prose the player reads. The Dilemma is the set of choices. The Decision is the player's selection. Each Decision launches a new Scene — a new Goal-Conflict-Disaster cycle.

### The Sequel-as-Node Pattern

The most naturally paced IF emerges when each passage is structured as a complete Sequel:

1. **Open with Reaction** — Show the consequences of the previous choice. Ground the player emotionally. This is the aftermath prose, the first thing the player reads.
2. **Present the Dilemma** — Transition from emotional response to assessment. What are the options? What are the trade-offs? The prose should make the stakes of the upcoming choice legible.
3. **End with Decision links** — The choice options themselves, each of which launches the player into a new Scene.

> The explosion rocks the warehouse floor. Smoke billows from the shattered crates, and through the haze you can see Marta slumped against the far wall, not moving. The exit is behind you — clear, safe, thirty seconds to the street.
>
> But Marta has the ledger. Without it, everything you've done tonight means nothing.
>
> - **Rush to Marta** — she might still be alive, and the ledger might still be intact
> - **Get out now** — you can't help her if you're dead, and the building is coming down
> - **Search the crates** — the ledger might have been thrown clear in the blast

This passage opens with Reaction (the explosion's aftermath, the emotional weight of seeing Marta down), moves through Dilemma (escape vs. rescue vs. search, with competing priorities made explicit), and terminates with Decision links. Each option launches a new Scene with a different Goal.

### Embedded Sequels

Not every Sequel needs to be a standalone passage. **Embedded Sequels** weave Sequel beats into ongoing action:

> You duck behind the counter as another shot splinters the wood above your head. Marta's gone — through the kitchen door, if the blood trail means anything. **You could follow her blood trail** or **hold position and wait for the shooter to reload.**

Here the Reaction (ducking, registering Marta's absence) and Dilemma (follow or hold) are embedded within a Scene that is still in progress. The Disaster has not fully resolved — conflict is ongoing — but a Decision point has emerged.

**When to use embedded vs. standalone Sequels:**

| Approach | Best For | Effect on Pacing |
|----------|----------|------------------|
| Standalone Sequel | Major turning points, emotionally significant choices | Slower, more reflective, signals importance |
| Embedded Sequel | Tactical decisions, mid-action pivots | Faster, more urgent, maintains momentum |

---

## Pacing Control Across Branches

### The Scene/Sequel Ratio

The ratio of Scene to Sequel length is a primary pacing lever. This is a **design parameter, not a quality metric** — no ratio is inherently better.

| Ratio (Scene:Sequel) | Pacing Feel | Genre Fit |
|-----------------------|-------------|-----------|
| **3:1** (high Scene) | Fast, breathless, relentless | Thriller, horror, action |
| **2:1** | Brisk with room to breathe | Adventure, mystery |
| **1:1** (balanced) | Measured, character-driven | Drama, literary IF |
| **1:2** | Contemplative, choice-heavy | Relationship, political intrigue |
| **1:3** (high Sequel) | Slow, philosophical, introspective | Slice of life, meditation |

A thriller branch might run 300 words of conflict followed by 100 words of Sequel. A relationship branch might run 150 words of conflict followed by 450 words of processing, deliberation, and emotionally weighted choices.

### Per-Branch Pacing Design

Different branches within the same IF work can and should run at different Scene/Sequel ratios:

| Branch Type | Typical Ratio | Sequel Emphasis | Example |
|-------------|---------------|-----------------|---------|
| Action/chase | 3:1 | Compressed — one-sentence Reactions, immediate Decisions | Fleeing through the market; each choice is a split-second direction |
| Investigation | 2:1 | Balanced — moderate Reaction, focused Dilemma | Interrogating suspects; each answer raises new questions |
| Social/political | 1:1 | Extended Dilemma — multiple considerations per choice | Negotiating between factions; every option has visible trade-offs |
| Relationship | 1:2 | Deep Reaction — emotional processing before Dilemma | Processing a betrayal; the character (and player) must sit with what happened |
| Contemplative | 1:3 | Full Sequel — Reaction, Dilemma, and Decision all explored at length | Choosing whether to leave the settlement; memories, obligations, fears examined |

### Maintaining Coherence Across Paths

When different branches run at different ratios, the emotional experience can diverge sharply. A player who took the action branch arrives at Act 3 wired and breathless; a player who took the relationship branch arrives thoughtful and invested. Both should feel that the story has been building toward this moment.

**Techniques for coherence:**

- **Similar emotional intensity curves** — Even if one branch is fast and another slow, both should hit similar intensity levels at similar structural points. The action branch achieves intensity through rapid Scene succession; the relationship branch achieves it through deep Sequel weight.
- **Bottleneck points that reset pacing** — Where branches converge, use a transitional passage that re-establishes a shared pacing baseline. A brief Sequel after the action branch, a brief Scene after the contemplative branch. This transitional node serves as a pacing airlock between different rhythmic environments.
- **Map intensity curves across branches** — Plot emotional intensity for each major branch. If one branch peaks at node 5 and another peaks at node 12, the player experience will feel incoherent when branches merge. Align the peaks, even if the mechanisms differ.
- **Consistent Disaster severity at merge points** — The Disaster that feeds into a convergence node should carry roughly equivalent emotional weight regardless of which branch delivered the player there. If the action branch ends on a life-threatening Disaster but the relationship branch ends on a minor social awkwardness, the shared Sequel that follows cannot serve both players.

---

## Scene/Sequel Antipatterns in IF

### The All-Scene Branch

A branch that is nothing but Goal-Conflict-Disaster-Goal-Conflict-Disaster without any Sequel beats. The player clicks from crisis to crisis without processing. Choices feel arbitrary because there is no Dilemma — just reaction under pressure with no time to weigh anything.

**Symptoms:** Players report feeling exhausted. Choices feel meaningless. The player cannot articulate why they chose what they chose.

**Fix:** Insert compressed Sequels even in fast-paced branches. A single sentence of Reaction between Scenes is enough to create the sense of a thinking character. "Your heart is hammering. Two options, no good ones." Even minimal Sequel prose makes the next choice feel deliberate rather than random.

**Test:** After writing an action branch, read it aloud. If you cannot identify a single moment where the character (not just the player) pauses to consider, the branch needs Sequel material.

### The All-Sequel Branch

A branch that is nothing but Reaction-Dilemma-Decision without genuine Scenes. The player reads reflection after reflection, weighs option after option, but nothing actually happens. No conflict, no opposition, no Disaster to make the next Sequel necessary.

**Symptoms:** Players report feeling bored. Choices feel academic — interesting in theory but disconnected from events. The story stagnates.

**Fix:** Ensure every Sequel leads into a Scene with real conflict. If the player Decides to confront someone, the next passage must contain opposition — not another round of contemplation. Sequels that lead to more Sequels create a contemplation loop that drains momentum.

**Test:** Trace each Decision link to its destination. If the destination passage opens with more Reaction rather than a new Goal and Conflict, you have stacked Sequels. Restructure so that every Decision leads to action.

### Sequel Depth Mismatch

Branch A gives the player a rich, emotionally layered Sequel with 400 words of processing. Branch B gives the player a two-sentence transition and immediately throws them into the next Scene. When these branches merge, the tonal whiplash is jarring. The player from Branch A has been treated to deep character work; the player from Branch B has been sprinting. The merged path cannot satisfy both without a transitional buffer.

**Fix:** Establish a minimum Sequel depth per branch type. Even action branches should dedicate at least two to three sentences to each Sequel. Even contemplative branches should cap Sequel length to prevent stagnation. Set a floor and a ceiling, and design within that range.

### The Missing Disaster

Scenes that end without a genuine setback — the character achieves their Goal without meaningful opposition, or the Scene simply stops without resolution. When there is no Disaster, the Sequel that follows has nothing to react to. The Dilemma feels manufactured because there is no genuine pressure.

**Fix:** Every Scene needs a Disaster of some kind — outright failure, a yes-but cost, or an unexpected complication. If the character succeeds cleanly, the Scene should either escalate stakes (the success reveals a worse problem) or be cut entirely. A Scene without a Disaster is a Scene that has not earned its Sequel.

**In IF specifically,** the Missing Disaster often occurs when writers want to reward the player for a "correct" choice. Resist this. Even when the player chooses well, the Scene that follows should introduce a new complication. Reward good choices with *better problems*, not with the absence of problems.

---

## Interactive Fiction: Sequel-Driven Choice Architecture

### Designing Choice Points as Sequels

A step-by-step process for building choice points from the Sequel model:

1. **Write the Disaster** — What just went wrong? What is the setback the player must respond to? Be specific. "The plan failed" is weak; "The guard recognized your forged pass and now the alarm is sounding" is actionable.
2. **Write the Reaction prose** — Show the character's immediate emotional and physical response. This grounds the player before asking them to think strategically. Two to four sentences.
3. **Design the Dilemma as 2-4 options** — Each option must represent a genuinely different approach, not variations on the same action. "Fight the guard" and "Attack the guard" are not meaningfully different. "Bluff your way past," "Run for the side exit," and "Surrender and work from inside" are.
4. **Ensure each Decision launches a new Scene** — Every option should lead to a passage with a new Goal, new Conflict, and new Disaster. If an option leads to another Sequel without an intervening Scene, the pacing will stall.

**The options must represent genuinely different approaches.** If two choices lead to functionally identical Scenes with cosmetically different prose, the player will feel the illusion collapse. Each Decision should produce a meaningfully different Goal-Conflict-Disaster chain.

### Sequel Depth as Emotional Weight Signal

Players learn, usually unconsciously, to read Sequel depth as a signal of choice importance:

- **Long Sequel** (200+ words of Reaction and Dilemma) — This is a big decision. Take your time. The story is telling you this matters.
- **Medium Sequel** (50-150 words) — A meaningful but not pivotal choice. The story is moving but wants you to think.
- **Short Sequel** (one to two sentences) — A tactical decision. Act on instinct. The story is not slowing down for you.

Use this signal **intentionally**. If a choice is genuinely pivotal — if it determines the ending or defines the character — give it a long Sequel with deep Reaction. If a choice is tactical — which door to open, which route to take — give it a compressed Sequel that maintains momentum.

The danger is accidental mismatch: a trivial choice preceded by a deep Sequel (the player agonizes over nothing) or a pivotal choice preceded by a compressed Sequel (the player clicks past the most important moment in the story without realizing it).

### The Recursive Pattern

Each branch in an IF work is itself a Scene-Sequel chain. And each Scene within that chain may contain its own compressed Scene-Sequel cycles. The pattern is fractal:

- **Act level** — The act is a macro-Scene with a macro-Disaster. The transition between acts is a macro-Sequel.
- **Chapter level** — Each chapter is a Scene-Sequel chain of three to seven nodes.
- **Node level** — Each passage contains a Scene (the narrative content) and a Sequel (the choice point).
- **Beat level** — Within a single passage, compressed Scene-Sequel cycles may occur in prose.

This recursive structure means that Scene/Sequel is not just a passage-level tool — it is an architectural principle that operates at every scale of the work. Designing at the act level first (what are the macro-Disasters and macro-Decisions?) and then drilling down to the passage level produces more coherent pacing than building bottom-up.

**Practical application:** When outlining an IF project, start by identifying three to five macro-Disasters (act-level setbacks) and the macro-Sequels between them (the major choice points). Then fill in the chapter-level Scene-Sequel chains within each act. Finally, write passage-level Scenes and Sequels. This top-down approach ensures that local pacing decisions serve the global arc.

## Quick Reference

| Goal | Technique |
|------|-----------|
| Create meaningful choice points | Structure each choice as a complete Sequel: Reaction, Dilemma, Decision |
| Signal choice importance | Use Sequel depth — longer Sequels for pivotal decisions, shorter for tactical ones |
| Maintain pace in action branches | Use compressed Sequels — one to two sentences of Reaction before options |
| Deepen contemplative branches | Extend Sequel Reaction and Dilemma beats; slow the ratio toward 1:2 or 1:3 |
| Prevent exhausting pacing | Never run more than three consecutive Scenes without a Sequel pause |
| Prevent stagnant pacing | Ensure every Sequel Decision leads to a Scene with real conflict |
| Achieve cross-branch coherence | Align emotional intensity curves; use bottleneck points to reset pacing |

---

## Research Basis

The techniques in this document draw from established narrative craft literature and interactive fiction design practice:

| Concept | Source |
|---------|--------|
| Scene/Sequel model (Goal-Conflict-Disaster / Reaction-Dilemma-Decision) | Dwight V. Swain, *Techniques of the Selling Writer* (1965) |
| Compressed Sequels, Scene construction methodology | Jack M. Bickham, *Scene and Structure* (1993) |
| Pacing ratios and Scene/Sequel proportion | Randy Ingermanson, building on Swain's framework for practical application |
| IF node structure and passage design | Emily Short, writings on choice-based narrative structure and node architecture |
| Player choice as reflective pause | Jon Ingold / inkle, design philosophy behind *80 Days* and *Sorcery!* — choices as moments of deliberation |
| Fractal narrative structure | Marie-Laure Ryan, *Narrative as Virtual Reality* (2001) — recursive story structures |

Swain's original model was designed for linear fiction, but its strength — the insight that stories alternate between action and reflection, between setback and response — translates directly to interactive fiction. The Sequel, which in linear fiction is written by the author, becomes in IF the structural moment where control passes to the player. This is not a metaphor; it is a mechanical correspondence.

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] — Overview of beat structures and Scene/Sequel fundamentals
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_structure_and_beats|Scene Structure and Beats]] — Three-paragraph cadence and beat integration
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — Construction methodology for branching structures
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/moral_dilemma_chains|Moral Dilemma Chains]] — Dilemma design connects to Sequel Dilemma beats
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/cascading_disaster_patterns|Cascading Disaster Patterns]] — Scene Disasters connect to cascading failure escalation
- [[Narrative & Game Design/Interactive Fiction/emotional-design/emotional_beats|Emotional Beats]] — Emotional dimension of Sequel Reaction beats
- [[Narrative & Game Design/Interactive Fiction/emotional-design/conflict_patterns|Conflict Patterns]] — Conflict within Scenes; opposition design
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/beat_taxonomies_craft_literature|Beat Taxonomies from Craft Literature]] -- Coyne Five Commandments map directly onto the Scene Goal-Conflict-Disaster spine
