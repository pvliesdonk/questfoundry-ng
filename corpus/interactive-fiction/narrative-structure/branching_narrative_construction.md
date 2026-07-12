---
title: Branching Narrative Construction
summary: Methodologies for building branching narratives—structural patterns, construction processes, small-scale choice architecture.
topics:
  - branching-narrative
  - construction-methodology
  - structural-patterns
  - choice-architecture
  - topology-design
  - state-tracking
  - scope-management
  - decomposition
cluster: narrative-structure
---

# Branching Narrative Construction

Methodologies for building branching narratives from the ground up—structural patterns, construction processes, and the interplay between large-scale architecture and small-scale choice design.

This document complements `branching_narrative_craft.md` (what makes choices meaningful) by focusing on **how to construct** branching structures.

---

## Structural Patterns

Different patterns suit different narrative goals. Most successful interactive fiction combines multiple patterns.

### Time Cave

Pure branching with minimal re-merging. Each choice leads to more choices.

**Structure:**

- All choices roughly equal significance
- No rejoining or reusing content
- Many unique endings

**Characteristics:**

- Content grows exponentially (3 binary choices = 8 endings)
- Broad rather than long
- Players miss most content per playthrough

**Best for:** Short experimental IF, replay-focused works, high-stakes consequences.

**Tradeoff:** Unsustainable at scale. A 10-choice time cave needs 1,024 endings.

### Gauntlet

Linear central thread with pruned side branches that quickly rejoin or terminate.

**Structure:**

- One primary story path
- Side branches via failure, backtracking, or quick rejoining
- Minimal state-tracking needed

**Characteristics:**

- Creates atmosphere of constraint or hazard
- Most players see core content
- Easy to author

**Best for:** Horror, survival, constrained protagonist situations.

**Tradeoff:** Limited player agency. May feel restrictive despite branching appearance.

### Branch and Bottleneck

Branches diverge then reconverge at key story beats.

**Structure:**

- Paths fan out from bottleneck points
- Heavy state-tracking accumulates differences
- Convergence at narrative milestones

**Characteristics:**

- Sustainable at any length
- Divergence accumulates over time
- Different journeys, shared destinations

**Best for:** Character growth narratives, commercial IF, long-form stories.

**Tradeoff:** Early playthroughs feel similar. Requires substantial content.

### Quest / Modular Clusters

Distinct modular branches organized by geography or topic rather than time.

**Structure:**

- Tightly-grouped node clusters
- Many approaches to single situations
- Episodic rather than linear

**Characteristics:**

- Suited for exploration narratives
- Consistent world, variable paths
- Can be assembled non-linearly

**Best for:** Open-world narratives, investigation stories.

**Tradeoff:** Large minimum scope. Less overall narrative direction.

### Sorting Hat

Heavy early branching determines major late-game branch. Later sections often linear.

**Structure:**

- Early choices set player on track
- Tracks diverge significantly
- Within each track: linear or light branching

**Characteristics:**

- Compromise between breadth and depth
- Multiple complete arcs
- Signals player influence upfront

**Best for:** Games with classes, factions, or major identity choices.

**Tradeoff:** Authors effectively write multiple games. Players may notice funneling.

### Loop and Grow

Central thread loops repeatedly. State-tracking unlocks new options each cycle.

**Structure:**

- Core loop structure (location, routine, time period)
- State changes unlock new content on return
- Progressive revelation through repetition

**Variant (Hub and Spoke):** Central hub with branches that return.

**Characteristics:**

- Emphasizes regularity while maintaining momentum
- Exploration across cycles
- Natural fit for time-loop or trapped narratives

**Best for:** Groundhog Day stories, workplace/routine settings, mystery investigation.

**Tradeoff:** Requires narrative justification for repetition.

---

## Beyond Branching

Pure branching isn't the only option. Alternative architectures avoid exponential content multiplication.

### Quality-Based Narrative (QBN)

Content unlocks based on accumulated stats rather than predetermined paths.

**How it works:**

- Storylets (atomic story pieces) tagged with unlock conditions
- Player stats (skills, relationships, items) determine availability
- System surfaces relevant storylets based on current state

**Advantages:**

- Modular content addition without cascading obligations
- Players create unintended narrative chains
- Scales without exponential growth

**Challenges:**

- Significant bookkeeping for authors
- Narrative spine less visible during authoring
- Requires robust state management

**Examples:** Fallen London, many roguelikes.

### Salience-Based Narrative

System selects most contextually relevant content from a pool.

**How it works:**

- Dialogue/scenes tagged with applicability conditions
- Engine matches current world state to available content
- Most relevant option surfaces automatically

**Advantages:**

- Reactive feel without explicit choice points
- Easy to add specialized variants gradually
- Doesn't require comprehensive coverage

**Best for:** Environmental dialogue, NPC reactions, layered commentary.

**Examples:** Firewatch, Left 4 Dead's dynamic dialogue.

### Waypoint Narrative

System pathfinds toward authored beats while player redirects.

**How it works:**

- Key story beats defined as waypoints
- System constantly navigates toward next waypoint
- Player choices detour but system "heals" back to spine

**Advantages:**

- Reduces combinatorial explosion
- Maintains narrative direction
- Player agency in journey, author control of destination

**Challenges:**

- Can feel like fighting the system
- Requires sophisticated dialogue management

---

## Construction Process

### Phase 1: Concept and Scope

**Define the container:**

- Genre, tone, target length
- Core theme or question
- Target structure pattern (or hybrid)

**Set scope constraints:**

- Number of major branches
- Target passage count
- State variables to track

**Key question:** What kind of story is this? A character growth story (branch-and-bottleneck), an exploration (quest), a transformation (sorting hat)?

### Phase 2: Spine First

Before branching, establish the core arc.

**Identify:**

- Beginning state (character, world)
- Ending state (or ending states)
- Key transformation beats

**The spine is:**

- What every player experiences in some form
- The narrative through-line
- Not necessarily the "main path"—may be the emotional arc underlying all branches

**Why spine first:**

- Prevents meandering branches that lose narrative purpose
- Ensures every path serves the same thematic goal
- Provides anchor points for convergence

### Phase 3: Anchor Points

Declare structural anchors before designing branches.

**Anchors include:**

- **Hubs:** Where player choice fans out
- **Bottlenecks:** Where paths reconverge
- **Gates:** Where progression requires conditions
- **Endings:** Terminal states

**Place anchors on spine:**

- Where do players return?
- What must happen regardless of path?
- Where does meaningful divergence occur?

**Key insight:** Anchors are structural, declared early. They constrain branching rather than emerging from it.

### Phase 4: Fracture Points

Identify where the spine can meaningfully diverge.

**Good fracture points:**

- Character decisions with genuine stakes
- Points where different approaches lead to different content
- Moments where player values can express

**Bad fracture points:**

- Cosmetic choices masquerading as meaningful
- Points where all options lead to same outcome
- Random selection without player investment

**For each fracture, define:**

- What distinguishes the options
- How long before convergence (or termination)
- What state changes result

### Phase 5: Branch Expansion

Expand one branch at a time, not simultaneously.

**Process:**

1. Select highest-priority fracture
2. Design the branch content
3. Validate connection to anchors
4. Repeat for next fracture

**Why sequential:**

- Prevents disconnected parallel narratives
- Each branch can reference established content
- Scope stays visible and controlled

### Phase 6: Connection and Validation

Verify the topology before writing prose.

**Check:**

- All passages reachable from start
- All branches connect to anchors or endings
- Gates have obtainable conditions
- No orphaned content

**Balance check:**

- No branch dramatically shorter than others (unless intentional)
- All paths satisfying
- Consequences proportional to choices

---

## Small-Scale Choice Patterns

Within any structure, local choice patterns create texture.

### Confirmation-Required Choice

Escalating prompts before risky decisions.

> "Are you sure?"
> "This cannot be undone. Proceed?"

**Effect:** Player opts in multiple times. Consequence feels earned.

### Track-Switching Choice

Multiple beats to change direction before commitment.

**Effect:** Mirrors genuine protagonist conflict. Allows mid-narrative reversals.

### Scored Choice

Repeated decisions in one direction accumulate points.

**Effect:** Outcome determined by statistical weight, not single final selection.

### Re-enterable Node

Classic conversation tree—explore sub-topics before progression.

**Effect:** Combats exposition dumps through interactive discovery.

### Floating Choice

Choice available across multiple passages until used.

**Effect:** Player timing matters. Creates strategic layer.

### Delayed Consequence

Choice in early passage affects later passage.

**Effect:** Reward for attentive players. Must signpost connection when consequence arrives.

---

## Scope Management

Branching multiplies content. Managing scope is essential.

### The Exponential Problem

- 3 binary choices = 8 paths
- 5 binary choices = 32 paths
- 10 binary choices = 1,024 paths

**Mitigation strategies:**

- Branch and bottleneck (converge regularly)
- State-based variation (same nodes, different text)
- Delayed branching (choices affect later, not immediately)

### Content Efficiency

**High efficiency:** State-based variations, QBN, salience systems.

**Medium efficiency:** Branch-and-bottleneck, hub-and-spoke.

**Low efficiency:** Time cave, full parallel tracks.

### The Vignette Method

From Choice of Games methodology:

1. Brainstorm 15-20 vignette ideas
2. Identify key variables (honor, cleverness, relationships)
3. Refine to 8-12 scenes with cohesive structure
4. Prototype to test balance
5. Iterate based on playtest

---

## Common Mistakes

### Branching Too Early

Divergence in chapter 1 creates parallel games.

**Fix:** Use early choices for state, not structure. Branch later.

### Converging Too Abruptly

"All roads lead to Rome" destroys agency.

**Fix:** Let differences persist. Converge at natural milestones.

### Forgetting the Spine

Branches meander without narrative purpose.

**Fix:** Every branch should serve the same thematic goal.

### State Without Consequence

Tracking variables that never affect anything.

**Fix:** Every tracked variable should pay off visibly.

### Undeclared Gates

Players hit walls without understanding why.

**Fix:** Foreshadow gate conditions. Make requirements clear.

### Symmetric Branches

All branches equal length, equal weight, interchangeable.

**Fix:** Asymmetry creates interest. Some paths should be harder, shorter, more rewarding.
## Quick Reference

| Construction Phase | Output | Key Question |
|--------------------|--------|--------------|
| Concept & Scope | Pattern choice, constraints | What kind of story? |
| Spine First | Core arc, transformation | What happens regardless of choices? |
| Anchor Points | Hubs, bottlenecks, gates | Where do players return/converge? |
| Fracture Points | Meaningful divergences | Where can this go differently? |
| Branch Expansion | Content for each path | What happens on this branch? |
| Connection | Validated topology | Does everything connect properly? |

| Pattern | Scope Efficiency | Narrative Depth | Player Agency |
|---------|------------------|-----------------|---------------|
| Time Cave | Low | Low (broad) | High |
| Gauntlet | High | High | Low |
| Branch & Bottleneck | Medium | Medium-High | Medium |
| Quest/Modular | Medium | Medium | High |
| Sorting Hat | Low-Medium | High (per track) | Medium |
| Loop and Grow | High | Medium | Medium |
| QBN/Salience | High | Variable | High |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_craft|Branching Narrative Craft]] — What makes choices meaningful
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] — Gates as in-world obstacles, contrastive choices
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/nonlinear_structure|Nonlinear Structure]] — Time manipulation and parallel narratives
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] — Emotional rhythm for arcs
- [[Narrative & Game Design/Interactive Fiction/scope-and-planning/scope_and_length|Scope and Length]] — Managing branching scope
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_sequel_in_interactive_fiction|Scene and Sequel in Interactive Fiction]] — Pacing branches with Swain's Scene/Sequel pattern
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/beat_taxonomies_craft_literature|Beat Taxonomies from Craft Literature]] — Beat function labels for scaffolding and structural validation
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/try_fail_cycles_branching_fiction|Try-Fail Cycles in Branching Fiction]] — Hub-and-spoke and linear try-fail as branching architecture
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/endings_patterns|Endings Patterns]] -- branch-and-bottleneck and key-node convergence as the endpoint design problem
