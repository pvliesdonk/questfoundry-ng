---
title: Player Analytics and Metrics for Interactive Fiction
summary: Tracking player behavior, choice analytics, engagement metrics, and using data to improve interactive narratives.
topics:
  - analytics
  - metrics
  - player-behavior
  - choice-tracking
  - engagement
  - data-driven
  - playtesting
  - user-research
cluster: craft-foundations
---

# Player Analytics and Metrics for Interactive Fiction

Craft guidance for tracking and analyzing player behavior in IF—choice analytics, engagement metrics, and data-driven narrative improvement.

---

## Why Analytics for IF

### Unique Opportunities

Interactive fiction generates rich behavioral data:

- **Every choice** recorded
- **Reading pace** measurable
- **Path selection** trackable
- **Replay patterns** visible
- **Abandonment points** identifiable

### What Analytics Can Answer

| Question | Data Needed |
|----------|-------------|
| Which choices are hard? | Decision time, hover patterns |
| Where do players quit? | Abandonment by passage |
| Which content is skipped? | Reading time, scroll depth |
| Do choices feel meaningful? | Replay rates, path diversity |
| What paths are popular? | Choice distribution |
| Is pacing working? | Session duration, completion rate |

---

## Key Metrics Categories

### Engagement Metrics

**Session metrics:**

- Session duration
- Sessions per player
- Time between sessions
- Completion rate

**Progress metrics:**

- Passages read per session
- Branches explored
- Replay frequency
- Drop-off points

### Choice Metrics

**Distribution:**

- % selecting each option
- Variation across player segments
- Comparison to intended distribution

**Decision process:**

- Time spent on choice
- Hover/focus patterns
- Back-button usage before choice

**Outcome perception:**

- Replay to try other options
- Player feedback/reactions
- "Would choose differently" surveys

### Narrative Quality Indicators

Research has identified user-log indicators for automatic IF evaluation:

| Indicator | What It Measures |
|-----------|------------------|
| Length | Total content consumed |
| Duration | Time spent in experience |
| Diversity | Variety of paths explored |
| Renewal | Replay behavior |
| Choice range | Options explored across sessions |
| Choice frequency | Decisions per time unit |
| Choice variety | Different choices across replays |

---

## Data Collection Approaches

### Event Logging

Track discrete events:

```
{passage_viewed: "forest_path", timestamp: "2024-01-15T14:32:00"}
{choice_made: "help_stranger", from: "forest_path", timestamp: "2024-01-15T14:33:15"}
{session_end: "natural", last_passage: "village_gate", duration: 847}
```

### State Snapshots

Periodic captures of game state:

```
{checkpoint: "chapter_2_start",
 relationship_sarah: 3,
 inventory: ["key", "letter"],
 flags: ["met_stranger", "helped_merchant"]}
```

### Aggregation Strategies

**Real-time:** Dashboard updates immediately
**Batch:** Process daily/weekly for trends
**Cohort:** Compare player groups over time

### Privacy Considerations

- **Anonymization:** No personally identifiable data
- **Consent:** Clear data collection disclosure
- **Minimization:** Collect only what's needed
- **Security:** Protect collected data
- **Deletion:** Honor removal requests

---

## Implementation Options

### For Twine/Web-Based IF

**Simple approach:** Google Analytics events

```javascript
gtag('event', 'choice_made', {
  'passage': 'forest_path',
  'choice': 'help_stranger'
});
```

**Dedicated tools:**

- **PlayFab-Twine** — Free analytics integration
- **Custom backends** — Full control, more work

### For Ink/Game Engine IF

**Unity Analytics:**

- Built-in event tracking
- Dashboard visualizations
- Cohort analysis

**Third-party:**

- GameAnalytics
- Amplitude
- Mixpanel

### For ChoiceScript

Limited built-in analytics; Choice of Games may share aggregate data with published authors.

---

## Telltale-Style Statistics

### Showing Choices to Players

> A notable approach involves showing "Telltale style metrics" to users, where after completing the game, players can see "for this major choice, X% of players made the same choice as you."

**Benefits:**

- Validates player decisions
- Creates social experience
- Encourages replay
- Generates discussion

**Implementation:**

- Aggregate on server
- Display at episode/game end
- Highlight meaningful choices only

### Design Considerations

**What to show:**

- Major story choices
- Character-defining moments
- Surprising distributions

**What to hide:**

- Trivial choices
- Spoiler-heavy statistics
- Embarrassingly lopsided choices

---

## Using Data to Improve IF

### Identifying Problems

| Data Pattern | Possible Problem |
|--------------|------------------|
| High abandonment at X | Pacing, confusion, difficulty |
| Choice split 99/1 | One option seems wrong |
| Long decision time | Unclear choices |
| No replays | Choices feel meaningless |
| Skipped passages | Content too slow |

### Common Findings

**From research on narrative games:**

> Understanding player behaviors helps craft narratives that resonate more deeply, including tracking choice patterns across branching storylines to refine underutilized quests or dialogue branches.

**Typical discoveries:**

- Players skip long exposition
- Moral choices split evenly; optimal choices don't
- Replays drop sharply after first playthrough
- Abandonment clusters at specific points

### Iterative Improvement

1. **Baseline:** Measure before changes
2. **Hypothesize:** What might improve metrics?
3. **Change:** Implement modification
4. **Measure:** Compare to baseline
5. **Learn:** Adopt or revert based on data

---

## Player Modeling

### Beyond Aggregate Data

Individual player modeling enables:

- **Personalized content** based on play style
- **Difficulty adjustment** for struggle detection
- **Recommendation** of paths/content
- **Prediction** of likely choices

### Research Approaches

Academic research has explored:

> Drama managers can learn models of player storytelling preferences and automatically recommend narrative experiences predicted to optimize the player's experience.

**Techniques:**

- Collaborative filtering
- Personality modeling
- Behavior clustering
- Preference learning

### Practical Applications

| Model | Application |
|-------|-------------|
| Pacing preference | Adjust text length dynamically |
| Risk tolerance | Offer appropriate challenges |
| Exploration style | Surface or hide optional content |
| Narrative preference | Emphasize character or plot |

---

## Limitations and Caveats

### What Analytics Can't Tell You

- **Why** players made choices
- **Emotional** response to content
- **Quality** of writing
- **Meaning** derived from experience

### Metric Pitfalls

**Goodhart's Law:** When a measure becomes a target, it ceases to be a good measure.

Optimizing for completion rate might make IF shorter, not better.

**Survivorship bias:** Only see data from players who stayed.

High engagement among completers doesn't show why others left.

**Correlation vs causation:** A precedes B doesn't mean A caused B.

Long passages correlate with abandonment, but cutting them might not help.

### Complementary Methods

Analytics work best alongside:

- **Playtesting:** Qualitative observation
- **Surveys:** Direct player feedback
- **Interviews:** Deep understanding of experience

---

## Quick Reference

| Goal | Metric | Tool |
|------|--------|------|
| Engagement | Session duration, completion | Event logging |
| Choice balance | Distribution % | Choice tracking |
| Pacing | Reading time per passage | Timestamp analysis |
| Problems | Abandonment clusters | Funnel analysis |
| Replay value | Return sessions, path diversity | Cohort tracking |
| Player satisfaction | Survey responses | Post-play feedback |

---

## Research Basis

Key sources on game analytics and IF metrics:

| Concept | Source |
|---------|--------|
| Game analytics foundations | Magy Seif El-Nasr et al., *Game Analytics* (2013) |
| IF user-log indicators | Sali et al., "Measuring the User Experience in Narrative-Rich Games" |
| Player modeling | Yannakakis & Togelius, *Artificial Intelligence and Games* (2018) |
| Drama manager recommendation | Mark Riedl et al., research on automated storytelling |

Professor Magy Seif El-Nasr's work establishing game analytics as a field includes "developing evidence-based methodologies to measure game environment effectiveness through novel behavior mining and visual analytics tools."

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/craft-foundations/testing_interactive_fiction|Testing Interactive Fiction]] — Qualitative testing methods
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/episodic_serialized_if|Episodic Serialized IF]] — Using statistics between episodes
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — Structure affecting metrics
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/quality_standards_if|Quality Standards IF]] — Quality beyond metrics
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/if_platform_tools|IF Platform Tools]] — Platform analytics capabilities
