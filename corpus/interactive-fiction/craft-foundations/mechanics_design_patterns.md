---
cluster: craft-foundations
summary: Designing game mechanics for interactive fiction at two registers — systems
  that work (stats, skill checks, economy, inventory) and mechanics that mean (procedural
  rhetoric, mechanic-as-metaphor, ludonarrative harmony).
title: Mechanics Design Patterns
topics:
- game-design
- mechanics
- procedural-rhetoric
- ludonarrative-dissonance
- stats
- skill-checks
- economy
- inventory
- diegetic-ui
- mechanic-as-metaphor
---

# Mechanics Design Patterns

Craft guidance for designing game mechanics in interactive fiction. Mechanics operate at two registers, and this note covers both: the **systems register** — making a stat system, skill check, or economy actually *work* — and the **expressive register** — making a mechanic *mean something*, so the rules themselves carry the story's argument. In text IF the "mechanics" are choice architecture, stats, inventory, time, and relationship meters; everything here translates to those surfaces.

---

## The Expressive Power of Mechanics

A mechanic is not just plumbing. It can be the primary carrier of a work's meaning — sometimes more so than its prose. Four ideas ground this:

- **Procedural rhetoric** (Ian Bogost, *Persuasive Games*, 2007): because games are rule-based and participatory, they make arguments by *encoding claims into their rules*. A game about bureaucratic dehumanization does not describe it — it makes you *enact* it. Every rule about what the player can and cannot do is an argument about the world.
- **MDA — Mechanics, Dynamics, Aesthetics** (Hunicke, LeBlanc & Zubek, 2004): designers build mechanics, which produce run-time dynamics, which produce aesthetic (emotional) experiences; players meet them in the reverse order. The craft lesson: design a mechanic by asking *what emotion it should produce*, not just whether it functions. A mechanic with no intended aesthetic is coherent but inert.
- **Ludonarrative dissonance** (Clint Hocking, 2007, on *BioShock*): the failure that occurs when what the mechanics *reward* contradicts what the story *endorses*. The concept is the negative space that defines the goal — alignment.
- **The mechanic is the message** (Brenda Romero, *Train*, 2009): meaning lives in the act of playing. In *Train*, players optimize rail logistics, then discover the boxcars' destinations are Nazi camps — the procedural complicity *is* the argument. Jason Rohrer's *Passage* (2007) makes the same point gently: a narrowing viewport and a single, ungameable death convey the whole emotional truth of mortality with no text at all.

---

## Mechanics as Meaning: The Patterns

Seven patterns for making a mechanic do narrative work, each with its text-IF translation.

### 1. Mechanic as Metaphor

The rule *is* the theme, not an illustration of it. In text IF, **the shape of a choice is itself an argument**: three options with one obviously right answer argues the situation has a right answer; a slate of only-bad options argues tragedy; choices with opaque consequences argue action under uncertainty. Decide the number, framing, and clarity of choices by what the scene is *arguing*, not by what feels interactive.

### 2. Resource Systems as Theme

What you make scarce is what the work is about. *This War of Mine* (11 bit studios, 2014) rations food and sanity, so it is about moral erosion under survival pressure; *Papers, Please* (Lucas Pope, 2013) rations time, so it is about a system's indifference to the person behind each document. In IF, a relationship meter that *decays*, or trust that never fully recovers once lost, turns a progress bar into a moral weight. What the player must ration tells them what the story values.

### 3. Stats and Skills as Characterization

Stats need not be competency scores; they can be *personality*. *Disco Elysium* (ZA/UM, 2019) makes its 24 skills internal voices that argue with the protagonist, and its Thought Cabinet makes ideologies equippable. In IF, opposed-pair stats (Stoic/Emotional, Ruthless/Merciful) track *who the character is*, not what they can do. The test: a stat that is never reflected back in prose or dialogue is a widget; a stat that changes how the character *speaks* is characterization.

### 4. Diegetic UI in Text

Non-diegetic state ("You have 3 Willpower") splits player from character; diegetic state ("Your hands won't stop shaking") collapses the gap. The text-IF form of diegetic UI is **prose that expresses mechanical state in in-world terms**: a sanity stat surfacing as increasingly fractured sentences, a relationship meter showing up in whether an NPC uses the player's name. This is the mechanical extension of [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]].

### 5. Mechanical Reinforcement vs Dissonance

Aim for alignment: if the story is about restraint, make unconstrained action costly; if it is about grief, do not end on a cheery score screen. *Spec Ops: The Line* (Yager, 2012) is the instructive exception — it uses dissonance *deliberately*, letting comfortable shooter mechanics become the indictment. The common IF version of the failure: a "Corruption" stat that unlocks the best content, so the incentive structure argues *for* corruption regardless of what the narrative says.

### 6. Mechanic as Irreversible Moral Act

Let the *structure of agency* carry moral memory. *Undertale* (Toby Fox, 2015) makes the save system a record of violence — a genocide run permanently marks later playthroughs. *Depression Quest* (Zoë Quinn & Patrick Lindsey, 2013) greys out unavailable choices to enact, not describe, the foreclosure of agency. In text IF this is underused: a tone that shifts permanently after a betrayal, a stat that can never return to baseline, a codex entry that updates to reflect what the player caused.

### 7. Investigation as Form

Let the player's curiosity shape the order of revelation. *Her Story* (Sam Barlow, 2015) replaces linear narrative with database search — the player co-authors the structure by deciding what to look for. The softer, more common IF version: a mystery investigable in any order, with the prose self-adjusting to feel motivated on every path. This connects directly to [[Narrative & Game Design/Interactive Fiction/narrative-structure/nonlinear_structure|Nonlinear and Alternative Structures]].

---

## The Role of Stats

### Why Have Stats?

Stats (Strength, relationships, money, personality axes) enable **gating** (access based on past choices), **expression** (defining who the character is), and **consequence** (accumulating small choices into large outcomes).

### Types of Stat System

- **Personality pairs (opposed):** Stoic vs Emotional; increasing one lowers the other. Enforces consistency; can punish nuance if players min-max.
- **Skills/attributes (accumulative):** start low, grow through use. Clear progression; risk of the "jack of all trades" failing every high check.
- **Hidden variables:** Trust, Suspicion, Corruption tracked silently. Produces surprising-but-logical consequences; risks feeling unfair if the player can never infer the cause.

### Quality-Based Narrative

A note on the Fallen London / *Sunless Sea* lineage (Failbetter Games): "quality-based narrative" treats accumulating stats as the primary driver of which story content unlocks — stats *are* the narrative state, not a side system. A powerful pattern when the story is about gradual transformation.

---

## Designing Skill Checks

### Threshold vs Probability

- **Threshold (deterministic):** `If Strength > 5: success.` Best for competency — you know kung fu or you don't. Risk: players save-scumming or feeling locked out.
- **Probability (random):** `Roll d20 + Strength vs DC 15.` Best for external chaos and tension. Risk: failing despite specializing feels bad.
- **Best practice for IF:** thresholds for *competency*, probability for *external chaos* (does the guard glance over?).

### Fail Forward

Never let a failed check halt the story. Success: you pick the lock silently. Failure: you pick it, but snap the pick or wake the guard. Dead end (avoid): "You can't. Try again." Failure should *redirect*, not *stop*.

---

## Economy Design

- **Scarcity vs abundance** sets tone: every bullet counting is survival horror; trivial money is power fantasy. (See *Resource systems as theme* above — scarcity is also an expressive choice.)
- **Faucets and sinks:** sources (loot, reward, salary) vs drains (gear, bribes, healing, upkeep). If faucets exceed sinks, currency goes meaningless.
- **The shopping-list problem:** shopping is dull in text. Fix by making items *narrative* ("your father's rusted blade," not "Sword +1") and by constraining inventory so choices matter.

---

## Inventory Management

- **The bag of holding:** infinite inventory invites brute-force "use everything on everything" puzzle-solving.
- **Constrained inventory** ("carry 3 items") forces strategy — the gun or the medkit?
- **Key items** unlock narrative paths; never let them be sold or dropped unless that loss is a deliberate, valid failure state.

---

## Harmonizing Mechanic and Story

The practical checklist for avoiding ludonarrative dissonance (pattern 5):

1. **Diegetic framing** — express state in-world (Willpower, Blood Loss, "your hands shake") rather than as bare numbers.
2. **Metaphorical mechanics** — let the system embody the theme (a Sanity meter in cosmic horror; a decaying Trust meter in a story about betrayal).
3. **Aligned incentives** — reward what the story endorses. If the narrative prizes stealth or mercy, do not grant the richest rewards only for combat or cruelty.

---

## Quick Reference

| Goal | Pattern / technique |
|------|--------------------|
| Make a mechanic mean something | Mechanic as metaphor; resource scarcity as theme |
| Make stats characterize | Opposed personality pairs; reflect state in prose, not just gates |
| Avoid ludonarrative dissonance | Align incentives; diegetic framing; metaphorical mechanics |
| Keep failure from stalling pacing | Fail forward — redirect, never dead-end |
| Choose a check type | Threshold for competency; probability for external chaos |
| Keep an economy meaningful | Balance faucets and sinks; narrativize items; constrain inventory |
| Give choices moral weight | Irreversible consequences; decaying or unrecoverable stats |
| Make state immersive | Diegetic UI — express the number as in-world prose |

---

## Research Basis

| Concept | Source |
|---------|--------|
| Procedural rhetoric — arguments encoded in rules | Ian Bogost, *Persuasive Games* (MIT Press, 2007) |
| MDA framework (Mechanics / Dynamics / Aesthetics; eight aesthetics) | Robin Hunicke, Marc LeBlanc & Robert Zubek, "MDA: A Formal Approach to Game Design" (2004) |
| Ludonarrative dissonance | Clint Hocking, "Ludonarrative Dissonance in BioShock" (2007; original blog defunct, widely archived) |
| The mechanic is the message; procedural complicity | Brenda Romero, *Train* (2009), from "The Mechanic Is the Message" series |
| Mechanic alone as emotional argument (memento mori) | Jason Rohrer, *Passage* (2007; MoMA collection) |
| Bureaucratic complicity through the gameplay loop | Lucas Pope, *Papers, Please* (2013) |
| Intentional dissonance as critique | Yager Development, *Spec Ops: The Line* (2012) |
| Stats/skills as psyche; equippable ideology | ZA/UM, *Disco Elysium* (2019) |
| Save system as moral memory; irreversible consequence | Toby Fox, *Undertale* (2015) |
| Unavailable choices as representation (depression) | Zoë Quinn & Patrick Lindsey, *Depression Quest* (2013) |
| Diegetic death loop (no dissonance — fiction absorbs the loop) | Supergiant Games, *Hades* (2020) |
| Binary choice as the mechanic of rule | Nerial, *Reigns* (2016) |
| Resource scarcity as moral erosion | 11 bit studios, *This War of Mine* (2014) |
| Control scheme as theme (dual-stick grief) | Starbreeze Studios, *Brothers: A Tale of Two Sons* (2013) |
| Database search as narrative form | Sam Barlow, *Her Story* (2015) — see [[Narrative & Game Design/Interactive Fiction/narrative-structure/nonlinear_structure|Nonlinear and Alternative Structures]] |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] — expressing mechanics through fiction; the diegetic-UI pattern
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — choice architecture as a mechanic
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/moral_dilemma_chains|Moral Dilemma Chains]] — the mechanic-as-irreversible-moral-act pattern at length
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/nonlinear_structure|Nonlinear and Alternative Structures]] — investigation/database as form
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/player_analytics_metrics|Player Analytics Metrics]] — measuring whether mechanics land as intended
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/if_platform_tools|IF Platform Tools]] -- what stat/inventory/skill-check mechanics each platform natively supports
- [[Narrative & Game Design/Live Game Design/corpus/puzzle-design/self-resolving-puzzles|Self-Resolving Puzzles]] -- live-game cousin of mechanic-as-judge: the mechanism itself adjudicates, no GM in the loop
