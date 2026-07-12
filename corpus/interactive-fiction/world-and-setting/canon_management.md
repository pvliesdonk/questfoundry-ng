---
title: Canon and Worldbuilding Management
summary: Building and maintaining world truth—cause chains, timeline anchoring, canon organization, and spoiler stratification.
topics:
  - canon
  - worldbuilding
  - lore
  - timeline
  - cause-chains
  - spoiler-levels
  - canon-packs
  - consistency
cluster: world-and-setting
---

# Canon and Worldbuilding Management

Craft guidance for building and maintaining world truth in interactive fiction—from documenting why facts are true to organizing lore into portable packs.

---

## The Nature of Canon

**Definition:** Canon is the authoritative truth of your story world. Not suggestions, not possibilities—facts that all other content must respect.

**Why Canon Matters:**

- Consistency creates believability
- Players notice contradictions
- Canon enables parallel creation (multiple authors/agents)
- World depth comes from coherent history

**Canon Is Not:**

- Draft ideas (those live in workspace)
- Player interpretation (that varies)
- Author's private notes (unless promoted)
- Everything written (most is discarded)

---

## Cause Chains

### The Core Rule

**Every fact needs a cause. "It just is" is not canon.**

Unjustified facts feel arbitrary. They break immersion because readers sense something missing. Cause chains provide depth and believability.

### Building a Cause Chain

**Structure:**

1. **Truth:** The fact you're establishing
2. **Immediate cause:** Why is this true?
3. **Deeper cause:** Why is that true?
4. **Open question:** Where the chain stops (for now)

**Example:**

| Level | Content |
|-------|---------|
| Truth | The Guild controls the waterfront |
| Immediate cause | After the Collapse, they were the only organization with intact logistics |
| Deeper cause | Their founder foresaw the crisis and stockpiled resources |
| Open question | How did the founder predict the Collapse? |

### When to Stop

Not every cause chain needs infinite depth. Stop when:

- You've reached a satisfying foundation
- Further depth doesn't serve the story
- The mystery itself is valuable
- Research can't provide more

Mark stopping points as **open questions** for potential future exploration.

### Cause Chain Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| "It just is" | Feels arbitrary | Ask "Why?" at least once |
| Circular reasoning | A because B because A | Find external anchor |
| Infinite regress | Never reaches foundation | Accept a stopping point |
| Hand-waving | "Magic did it" | Even magic has rules |

---

## Timeline Anchoring

### Why Timelines Matter

Without temporal positioning, events can contradict each other or violate causality. Timeline anchoring prevents impossible sequences.

### Anchor Types

| Type | Definition | Example |
|------|------------|---------|
| Absolute | Fixed date in story time | Year 347 of the New Era |
| Relative | Relationship to another event | Three years after the Collapse |
| Sequential | Order without specific duration | After the Last War but before the Guild's Rise |

### Anchoring Events

Every significant event needs a `timeline_position`:

- When did it happen?
- What came before?
- What came after?
- How long did it last?

**Cross-reference against existing anchors.** If a new event contradicts established chronology, one of them is wrong.

### Timeline Validation

Before finalizing events, check:

- [ ] Is the timeline position documented?
- [ ] Does it fit with known anchors?
- [ ] Do cause-and-effect relationships respect time?
- [ ] Are event durations plausible?

### Timeline Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Floating events | No temporal position | Add at least relative anchor |
| Impossible sequence | Effect before cause | Reorder or revise |
| Compressed history | Too much in too little time | Expand or simplify |
| Vague dates | "A long time ago" for everything | Establish relative order |

---

## Canon Organization

### Canon Packs

A **canon pack** is a portable, thematic container of related lore.

**Pack Types:**

| Type | Focus | Example |
|------|-------|---------|
| Era | Timeline-bounded period | Age of Founding pack |
| Faction | Group-focused lore | Guild of Artificers pack |
| Metaphysics | World rules | How Magic Works pack |
| Geography | Place-focused lore | The Eastern District pack |

### Pack Scope

| Scope | Meaning | Use Case |
|-------|---------|----------|
| Book | Story-specific lore | Unique to this narrative |
| World | Shareable lore | Could appear in other stories |

### Creating a Canon Pack

1. Choose pack type (Era, Faction, Metaphysics, Geography)
2. Set scope (book or world)
3. Gather related lore entries
4. Build cause chains for each entry
5. Establish timeline positions
6. Check internal consistency
7. Check external consistency (against other packs)
8. Classify spoiler levels
9. Document open questions

### Canon Pack Validation

**Internal consistency:**

- Do entries within the pack contradict each other?
- Are cause chains complete?
- Are timeline positions compatible?

**External consistency:**

- Does this pack contradict other packs?
- Do faction motivations still make sense?
- Are metaphysical rules consistent?

**Narrative feasibility:**

- Can the story use this lore as intended?
- Does this enable or block narrative possibilities?

---

## Conflict Resolution

### When Canon Conflicts

Sometimes new lore contradicts existing canon. This requires explicit resolution.

**Never silently overwrite.** Silent changes cause cascading errors and undermine canon authority.

### Resolution Process

1. **Document the conflict** — What are the competing versions?
2. **Identify implications** — What depends on each version?
3. **Decide which is canon** — Based on story needs and history
4. **Update all dependent lore** — Propagate the decision
5. **Archive the non-canon version** — For reference

### Conflict Documentation

| Field | Content |
|-------|---------|
| Conflict ID | Unique identifier |
| Versions | Both competing facts |
| Sources | Where each appears |
| Dependencies | What relies on each |
| Resolution | Which is canon and why |
| Updates needed | What must change |

---

## Spoiler Stratification

### Spoiler Levels

Not all lore is safe for players to see. Classify everything:

| Level | Definition | Player-Facing Treatment |
|-------|------------|------------------------|
| Minor | Background flavor | May appear with careful phrasing |
| Major | Affects understanding/strategy | Must be omitted or heavily obscured |
| Critical | Would ruin experience | Never appears, no exceptions |

### Examples by Level

**Minor Spoiler:**
> The Guild's founder was wealthy.

Adds depth but doesn't change the experience. Can include in codex with appropriate phrasing.

**Major Spoiler:**
> The Guild's founder foresaw the Collapse.

Affects how players interpret Guild actions. Should be omitted from codex or heavily obscured.

**Critical Spoiler:**
> The Guild's founder *caused* the Collapse.

Central twist that would ruin discovery. Never in codex under any circumstances.

### Spoiler-Safe Derivation

When deriving player-facing content from canon:

1. **Identify spoiler level** for each fact
2. **Minor:** Include with in-world phrasing
3. **Major:** Omit or obscure (e.g., "Some say the founder knew more than most...")
4. **Critical:** Completely exclude
5. **Document omissions** for validation

### The In-World Scholar Test

Ask: "What would an in-world scholar know and publish?"

Scholars don't know:

- Secret motivations
- Hidden identities
- Future events
- Information meant for discovery

---

## Consistency Dimensions

### Internal Consistency

Within a single piece of lore:

- Facts don't contradict
- Cause chains are complete
- Timeline is coherent
- Motivations make sense

### Cross-Reference Consistency

Between lore elements:

- Shared facts agree
- Timeline positions align
- Character behaviors match
- World rules apply uniformly

### Narrative Consistency

With the story:

- Lore enables intended scenes
- Player choices remain meaningful
- Discovery is possible
- Pacing isn't disrupted

---

## Working with Uncertain Facts

### When Canon Isn't Established

Sometimes you need facts that don't yet have canon backing.

**Options:**

1. **Request canon creation** — Ask for official lore
2. **Use placeholder** — Mark as provisional
3. **Imply without stating** — Let players assume
4. **Present as in-world uncertainty** — "No one knows for certain..."

### Provisional Canon

Mark uncertain facts clearly:

| Status | Meaning | Treatment |
|--------|---------|-----------|
| Canonical | Established truth | Use directly |
| Provisional | Assumed but not official | Mark and verify later |
| Proposed | Suggested for consideration | Don't rely on yet |
| Rejected | Explicitly not canon | Don't use |

---

## Common Mistakes

### Retroactive Changes Without Propagation

**Problem:** Changing canon but not updating dependent content.

**Fix:** Track dependencies. When canon changes, identify and update all affected content.

### Treating References as Canon

**Problem:** Using other fiction as authoritative source.

**Fix:** Fiction is inspiration, not evidence. Research primary sources.

### Over-Detailed Canon

**Problem:** Defining more than the story needs.

**Fix:** Canon should enable stories, not constrain them unnecessarily. Leave room for future development.

### Under-Documented Canon

**Problem:** Facts exist in author's head but not in records.

**Fix:** If it matters, write it down. Unwritten canon is unreliable.

---

## Quick Reference

| Concept | Key Principle |
|---------|---------------|
| Cause chains | Every fact needs a documented why |
| Timeline anchoring | Events need temporal positions |
| Canon packs | Organize by theme and scope |
| Conflicts | Never silently overwrite |
| Spoiler levels | Minor/Major/Critical stratification |
| Consistency | Internal, cross-reference, and narrative |
| Uncertainty | Mark provisional canon clearly |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/world-and-setting/worldbuilding_patterns|Worldbuilding Patterns]] — Building coherent worlds
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/historical_fiction|Historical Fiction]] — Research and accuracy
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] — Player-facing content
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/quality_standards_if|Quality Standards]] — Canon validation bar
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — Structure planning
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_craft|Branching Narrative Craft]] -- world-state and character consistency across divergent paths
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/collaborative_if_writing|Collaborative IF Writing]] -- canon as the shared truth that keeps multi-author teams aligned
