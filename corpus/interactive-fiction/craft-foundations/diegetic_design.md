---
title: Diegetic Design for Interactive Fiction
summary: Show the world, hide the gears—keeping mechanics invisible while presenting everything through the fiction.
topics:
  - diegetic-design
  - immersion
  - gate-design
  - choice-design
  - player-facing-content
  - meta-avoidance
  - codex-voice
cluster: craft-foundations
---

# Diegetic Design for Interactive Fiction

Craft guidance for maintaining immersion by expressing all mechanics through the fiction—gates as in-world obstacles, choices as character actions, and surfaces that never reveal the machinery behind them.

---

## Core Principle: Show the World, Hide the Gears

**Definition:** Diegetic design means everything the player sees exists within the story world. No game mechanics, schema names, or authorial intrusions appear on player-facing surfaces.

**Why It Matters:**

- Immersion depends on consistency
- Meta-references break the fictional contract
- Players should feel they're in the story, not playing a game
- Coherent worlds feel more real

**The Test:** Would an in-world character understand this text? If it requires knowledge of the game's structure, it's not diegetic.

---

## Gates and Locks

### What Makes a Gate Diegetic

A diegetic gate presents its condition as an in-world obstacle, not a game mechanic.

**Good Gate:**
> The foreman's seal is required to enter the restricted level.

**Bad Gate:**
> This option is locked until you obtain the foreman_seal codeword.

### Gate Design Checklist

| Element | Diegetic | Non-Diegetic |
|---------|----------|--------------|
| Condition | "The guards demand proof of membership" | "Requires: union_member flag" |
| Reason | "Only those bearing the seal may pass" | "Locked until later chapter" |
| Solution hint | "Perhaps the foreman could be convinced..." | "Complete quest A first" |
| Failure | "The guard turns you away" | "Insufficient progress" |

### Expressing Gates Naturally

**Name the obstacle specifically:**

- What blocks entry? (guards, locked doors, missing knowledge)
- What does the world call the requirement? (seal, token, reputation)

**Imply the solution:**

- Where might one find what's needed?
- Who would know how to proceed?

**Match the register:**

- A fantasy tavern uses different language than a noir detective's office
- Gates should feel native to the story's voice

---

## Choice Text

### Contrastive Choices

Choices must differ in both verb and intent, not just phrasing.

**Good Choices:**
>
> - Confront the foreman directly
> - Search his office after hours
> - Report to the union steward

**Bad Choices (Near-Synonyms):**
>
> - Investigate further
> - Continue investigating
> - Keep looking into it

**Bad Choices (Same Verb):**
>
> - Talk to the guard politely
> - Talk to the guard firmly
> - Talk to the guard casually

### Choice Text Guidelines

**Never Include:**

| Pattern | Example | Problem |
|---------|---------|---------|
| Meta instructions | "Click here to continue" | Reveals UI layer |
| Outcomes | "This will anger the foreman" | Removes suspense |
| Game awareness | "Choose wisely" | Acknowledges it's a game |
| Directions | "Proceed to the next scene" | Breaks fiction |

**Always Include:**

- Action verbs (confront, search, flee, persuade)
- Specific objects or targets (the foreman, the office, the exit)
- Implied stakes (distinct consequences readers can anticipate)

### The Prediction Test

Players should be able to predict different consequences from different choices. If two choices seem equivalent, they're not contrastive enough.

---

## Player-Facing Surfaces

### What Counts as Player-Facing

- Passage prose (what players read)
- Choice text (what players select)
- Codex entries (reference material)
- Export bundles (final deliverables)
- Art plan descriptions (when rendered)

### What Must Never Appear

| Category | Examples |
|----------|----------|
| Schema internals | `codeword:`, `pid:`, `flag_id:` |
| Anchor names | `anchor:lighthouse_secret` |
| Artifact IDs | `passage_abc123` |
| Agent names | "The Lorekeeper decided..." |
| Model references | "According to GPT..." |
| Research citations | "Wikipedia states..." |

### The Surface Test

Read all player-facing text and ask:

1. Does this assume knowledge outside the story world?
2. Would a character in this world understand every term?
3. Is anything here "about" the story rather than "in" the story?

If any answer is yes, rewrite.

---

## Codex and Reference Material

### The In-World Scholar

Codex entries should read as if written by a scholar within the fiction.

**Good Codex Entry:**
> The Guild of Artificers controls much of the waterfront trade. Founded in the years following the Collapse, they rose to prominence through unmatched logistics and a reputation for reliability.

**Bad Codex Entry:**
> The Guild is a major faction in Chapter 2. Players who ally with them get better equipment options and access to the restricted docks.

### What an In-World Scholar Knows

**Can Include:**

- Public knowledge (commonly known facts)
- Historical events (that aren't hidden history)
- Cultural practices (widely observed)
- General descriptions (places, groups, customs)

**Cannot Include:**

- Secret motivations ("The foreman secretly plans...")
- Hidden identities ("The masked figure is actually...")
- Plot twists ("It will later be revealed...")
- Future events ("This will become important when...")

### Voice Checklist for Codex

Before finalizing any codex entry:

- [ ] No "the player" or "the reader"
- [ ] No "this chapter" or "Act 2"
- [ ] No game mechanics (unlocks, bonuses, access to)
- [ ] No future knowledge (will later, eventually, soon)
- [ ] Appropriate formality for in-world document
- [ ] Could reference in-world sources (archives, scholars)

---

## Handling Uncertainty and Information Gaps

### When Research Is Uncertain

Don't cite sources on player-facing surfaces. Instead:

**Corroborated fact (high certainty):**
> Electric street lamps hummed in the newer districts.

**Plausible fact (moderate certainty):**
> The occasional hum of electric lamps marked the wealthier streets.

**Disputed fact (sources conflict):**
> Some claimed the eastern district had always been abandoned. Others remembered it differently.

**Uncorroborated (no sources):**
> The old lighthouse had stood for as long as anyone could remember.

### The Neutral Phrasing Pattern

For uncertain information, use phrases that:

- Sound natural in the fiction
- Don't make definitive claims
- Leave room for the truth to be different

| Certainty | Pattern |
|-----------|---------|
| High | Direct statement |
| Medium | "It was said that..." |
| Low | "Rumor held..." |
| Unknown | "No one knew for certain..." |

---

## Common Mistakes and Fixes

### Information Dumps

**Problem:** Explaining world facts by having characters lecture.

**Fix:** Integrate information through action and observation. Show, don't tell through dialogue.

### Fourth Wall Breaks

**Problem:** Acknowledging the reader or the story structure.

**Fix:** Stay fully in character perspective. The story world is the only world.

### Inconsistent Register

**Problem:** Modern slang in historical settings, formal language in casual contexts.

**Fix:** Maintain voice consistency. Read aloud to catch jarring shifts.

### Mechanical Leakage

**Problem:** Internal terms (codewords, PIDs, flags) appearing in prose.

**Fix:** Automated checking for common patterns. Human review for subtle cases.

### Spoiler Contamination

**Problem:** Hints about future events or hidden truths in early content.

**Fix:** Ask "would an in-world observer know this?" for every statement.

---

## Implementation Checklist

### Before Writing

- [ ] Understand what in-world observers would know
- [ ] Plan how gates will be expressed diegetically
- [ ] Choose voice and register for this content

### During Writing

- [ ] No meta-references in prose
- [ ] Gates named as in-world obstacles
- [ ] Choices use distinct verbs and objects
- [ ] Uncertainty expressed through neutral phrasing

### After Writing

- [ ] Run surface test on all player-facing content
- [ ] Check for schema internals and anchor names
- [ ] Verify codex voice checklist
- [ ] Review choices for contrastive clarity

---

## Quick Reference

| Element | Diegetic Approach |
|---------|-------------------|
| Gates | In-world obstacles with implied solutions |
| Choices | Distinct verbs + objects, no meta |
| Codex | In-world scholar voice |
| Uncertainty | Neutral phrasing, no citations |
| Missing info | "No one knew for certain" |
| Locked content | Named requirements, not flags |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_craft|Branching Narrative Craft]] — Choice structure and gates
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/dialogue_craft|Dialogue Craft]] — Authentic character voice
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/worldbuilding_patterns|Worldbuilding Patterns]] — Consistent world presentation
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/subtext_and_implication|Subtext and Implication]] — Showing without telling
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/prose_patterns|Prose Patterns]] — Scene structure and flow
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/research_and_verification|Research and Verification]] -- source for the certainty-to-phrasing mapping diegetic prose uses for uncertain facts
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/quality_standards_if|Quality Standards]] -- surface-test and spoiler-hygiene bars that validate diegetic discipline
- [[Narrative & Game Design/Live Game Design/corpus/escape-room-design/theme-and-immersion|Theme and Immersion in Escape Rooms]] -- cross-corpus parallel: diegetic vs non-diegetic puzzle distinction in live rooms
