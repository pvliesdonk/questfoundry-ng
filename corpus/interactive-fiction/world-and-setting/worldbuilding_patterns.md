---
title: Worldbuilding Patterns for Interactive Fiction
summary: Creating consistent fictional worlds with internal logic, timeline management, causality chains, and implied depth.
topics:
  - worldbuilding
  - world-consistency
  - internal-logic
  - timeline-management
  - causality-chains
  - implied-depth
  - rules-establishment
cluster: world-and-setting
---

# Worldbuilding Patterns for Interactive Fiction

Craft guidance for creating consistent, believable fictional worlds—internal logic, timeline management, causality, and the art of implying depth.

---

## World Consistency

### The Internal Logic Principle

Every fictional world operates by rules. Fantasy worlds have magic systems. Sci-fi worlds have technology limits. The rules themselves matter less than consistent application. Readers accept any premise—they reject inconsistency.

### Establishing Rules Early

Introduce world rules before you need them. A magic system that conveniently solves a climactic problem feels like cheating. The same system established in chapter one feels like clever foreshadowing.

Bad:
> "I never mentioned this, but I can actually teleport when I'm really scared." (convenient new ability)

Good:
> Earlier: She practiced the blink-step, managing three feet before exhaustion hit.
> Later: Terror surged through her. The blink-step carried her twenty feet—farther than ever before.

### The Consistency Checklist

For any world element, track:

- **What it can do** (capabilities)
- **What it can't do** (limitations)
- **What it costs** (consequences, resources, effort)
- **Who has access** (rarity, training requirements)

### Common Consistency Errors

- Magic/technology that works differently scene to scene
- Characters forgetting abilities they demonstrated earlier
- Rules that apply to some characters but not others without explanation
- Scale inconsistencies (travel time, population, economics)

---

## Timeline Mapping

### Why Timelines Matter

Readers track time unconsciously. When a character mentions "last week's meeting" but three chapters ago you wrote "yesterday's meeting," trust erodes. In interactive fiction with branching paths, timeline errors multiply.

### The Timeline Document

Maintain a separate timeline tracking:

- **Story events** in chronological order (not narrative order)
- **Character ages** at key moments
- **Seasonal markers** (weather, holidays, academic years)
- **Travel time** between locations
- **Duration** of key events

### Relative vs Absolute Time

Use relative time references carefully:

Bad:
> "Three days ago" (but how many scenes ago? When was "now"?)

Better:
> "The morning after the storm" (anchored to memorable event)

Best:
> Track both internally, use memorable anchors in prose.

### Interactive Fiction Considerations

With branching narratives:

- Time may pass differently on different paths
- Characters age consistently regardless of path taken
- Events referenced across branches must align
- "Three days later" on one branch can't conflict with simultaneous events on another

---

## Causality Chains

### Every Action Has Consequences

Believable worlds demonstrate cause and effect. When characters make choices, the world responds. When events occur, ripples spread outward.

### Building Causal Chains

**First-Order Effects:** Direct, immediate consequences
> The dam breaks → the valley floods.

**Second-Order Effects:** Consequences of consequences
> The valley floods → crops destroyed → food shortage → migration.

**Third-Order Effects:** Ripples reaching unexpected places
> Migration → overcrowding in cities → political tension → new laws.

### Tracking Causality

For major story events, ask:

1. What happens immediately?
2. Who else is affected?
3. What changes in a week? A month? A year?
4. What wouldn't happen if this event didn't occur?

### Common Causality Errors

- Major events with no aftermath
- Characters who should know about events remaining ignorant
- Economic impacts ignored (wars cost money, disasters destroy infrastructure)
- Political implications unexplored
- "Reset button" storytelling where consequences disappear

### Interactive Causality

In branching narratives, player choices must have visible effects. The world should feel responsive:

- NPCs remember and reference past decisions
- Environmental changes persist
- Reputation systems reflect accumulated choices
- Closed-off paths result from earlier decisions

---

## The Codex Pattern

### Separating World from Story

A codex (or "bible") is a reference document containing world facts independent of any particular story. The story reveals portions of the codex; the codex ensures consistency across revelations.

### What Goes in a Codex

- **Geography:** Maps, distances, climate, resources
- **History:** Major events, eras, conflicts, rulers
- **Culture:** Customs, religions, social structures, taboos
- **Technology/Magic:** Systems, limitations, practitioners
- **Characters:** Backstories, relationships, motivations
- **Languages:** Naming conventions, phrases, linguistic patterns

### Codex vs Exposition

The codex is for the author. The story reveals only what serves the narrative. Having detailed history doesn't mean explaining it all.

Bad:
> "The Kingdom of Valdris was founded in the Third Age by King Aldric the Conqueror, who united the seven warring tribes..."

Good:
> The ancient crown still bore notches from seven different blades—one for each tribe that had knelt.

### Living Documents

Codices evolve as stories progress. New details emerge; contradictions require resolution. The key is updating the codex immediately when story decisions alter established facts.

---

## Iceberg Theory

### Show the Tip, Imply the Depth

Hemingway's iceberg theory (from *Death in the Afternoon*, 1932): "The dignity of movement of an iceberg is due to only one-eighth of it being above water." Worldbuilding works the same way. Readers should sense vast depth without seeing it all.

### Techniques for Implying Depth

**Casual References:**
> "Pass the saltrice—no, the blue kind, not that southern stuff."

Two words imply trade routes, regional agriculture, and cultural preferences.

**Assumed Knowledge:**
> "Everyone knew what happened to oath-breakers."

The absence of explanation suggests this is common knowledge in the world.

**Visible Consequences:**
> The old quarter had wider streets—built for horse carts before the rails came.

History visible in architecture, no exposition needed.

**Partial Information:**
> "The War of Whispers? We don't speak of that. Not since the Silence Decree."

Mystery implies depth. Not everything needs explaining.

### The "What's for Breakfast" Test

Can your characters eat breakfast without you inventing their food on the spot? Do they have currency, calendars, curse words? These small details, known but rarely shown, create the iceberg's mass.

### Avoiding Over-Revelation

Bad:
> "This sword was forged by the Dwarves of Mount Keld using the seven-fold technique passed down from Master Thrain who learned it from the Fire Spirits during the Second Compact after the War of Flames which occurred in the year 847 of the Third Age..."

Good:
> The blade held an edge that never dulled. Dwarf-forged, clearly. Nothing else kept its bite like that.

---

## Worldbuilding in Interactive Fiction

### Player-Discovered Lore

In IF, players discover world details through exploration:

**Environmental lore:**

- Objects in rooms reveal history
- Architecture implies culture
- Decay shows passage of time
- Repairs show what matters

**Optional discovery:**

- Codex entries for curious players
- Overheard conversations
- Found documents
- NPC dialogue options

**Design principle:** Core story works without optional lore. Lore enriches for those who seek it.

### Worldbuilding Through Choices

Choices themselves can reveal world rules:

**Choice implies capability:**

> "Use the guild seal to demand entry"

This choice implies: guilds exist, they have seals, and seals have authority.

**Choice implies constraint:**

> "You can't go that way—the Barrier holds."

This implies: magic exists, it can create barriers, and players can't bypass them.

**Choice implies culture:**

> "Bow to the Elder as custom requires"
> "Nod, as outsiders do"

Two options reveal cultural norms and player's relationship to them.

### Branching and World State

Different branches may reveal contradictory information:

**The fog of war approach:**

Player only knows what they've learned on their path. Other characters may know different "truths."

**The consistent world approach:**

All paths reveal the same underlying reality, just from different angles.

**The unreliable narrator approach:**

Different sources contradict. Player must evaluate credibility.

**Choose one and maintain it.** Mixed approaches confuse players.

### Interactive Codices

IF can provide reference material:

**Player-facing codex:**

- Unlocks as player discovers information
- Never spoils future content
- Reflects character knowledge, not author knowledge
- Written in-world where possible

**Design traps:**

- Codex entry spoils twist ("The Guild—secretly evil")
- Entry appears before relevant content
- Technical info breaks immersion
- Too much reading; too little playing

See [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] for player-safe reference guidelines.

---

## Common Mistakes

### The Infodump Trap

Stopping the story to explain the world. Readers came for story, not encyclopedia entries. Weave worldbuilding into action and dialogue.

### Inconsistent Scale

A kingdom that takes "weeks to cross" but armies arrive in days. Cities of "millions" with the political intrigue of small towns. Economics that don't add up.

### Convenient Worldbuilding

Rules that bend when the plot needs them to. Magic that works perfectly when heroes use it, fails when villains try. Technology that exists only when convenient.

### Style Guide Neglect

Names that don't follow consistent patterns. One elf named "Aelindor" and another named "Bob." Cultures with mismatched naming conventions break immersion.

---

## Quick Reference

| Goal | Technique |
|------|-----------|
| Consistency | Track rules, limits, costs, access |
| Timeline | Maintain chronological document |
| Causality | Map ripple effects from events |
| Depth | Codex for authors, icebergs for readers |
| Integration | Weave world into action and dialogue |
| Scale | Verify distances, populations, economics |
| Naming | Consistent patterns per culture |

---

## Research Basis

Key sources informing worldbuilding craft:

| Concept | Source |
|---------|--------|
| Iceberg theory | Ernest Hemingway, *Death in the Afternoon* (1932) |
| Magic system design | Brandon Sanderson, "Sanderson's Laws of Magic" (blog essays, 2007-2012) |
| Worldbuilding as craft | Orson Scott Card, *How to Write Science Fiction and Fantasy* (1990) |
| Consistency principles | N.K. Jemisin, craft essays on systematic worldbuilding |

Sanderson's First Law: "An author's ability to solve conflict with magic is directly proportional to how well the reader understands said magic." This principle applies beyond fantasy—any world system (technology, social structure, economy) that solves problems must be established before it's needed.

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/world-and-setting/canon_management|Canon Management]] — Cause chains, timeline anchoring, consistency
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/setting_as_character|Setting as Character]] — Making settings dynamic participants
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/exposition_techniques|Exposition Techniques]] — Revealing world through action
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/historical_fiction|Historical Fiction]] — Research and period authenticity
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/fantasy_conventions|Fantasy Conventions]] — Fantasy-specific worldbuilding
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/character_naming_by_culture|Character Naming by Culture]] -- naming conventions as the first worldbuilding readers encounter
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/location_naming_patterns|Location Naming Patterns]] -- toponymy as worldbuilding texture and cultural-layer signal
