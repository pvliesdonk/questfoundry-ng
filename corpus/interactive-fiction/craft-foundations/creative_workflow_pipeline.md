---
title: Creative Workflow and Production Pipeline
summary: Structured workflows for interactive fiction production—from initial planning through export, with stage gates and handoffs.
topics:
  - workflow
  - pipeline
  - production
  - stages
  - handoffs
  - exports
  - playbooks
  - quality-gates
cluster: craft-foundations
---

# Creative Workflow and Production Pipeline

Craft guidance for structuring IF production—stage separation, handoffs between roles, quality gates, and export configurations.

---

## The Core Pipeline

### Stage Overview

Interactive fiction production flows through distinct stages:

```
Vision → Structure → Prose → Validation → Canon → Export
```

| Stage | Focus | Output |
|-------|-------|--------|
| Vision | What story to tell | Concept, scope, themes |
| Structure | How it branches | Briefs, topology |
| Prose | What players read | Passages, dialogue |
| Validation | Quality assurance | Pass/fail, feedback |
| Canon | Committed truth | Approved artifacts |
| Export | Distribution format | Bundled deliverables |

### Why Stages Matter

- **Clear handoffs** — Each stage produces defined outputs
- **Quality gates** — Issues caught before they cascade
- **Parallel work** — Different aspects can progress independently
- **Iteration** — Problems fixed at the right level

---

## Stage 1: Vision

### What Happens

- Define story concept and themes
- Establish scope (number of passages, branches)
- Set genre, tone, audience
- Identify research needs

### Outputs

| Output | Content |
|--------|---------|
| Concept | What the story is about |
| Scope | Size and complexity targets |
| Style direction | Genre, tone, voice |
| Research agenda | What needs verification |

### Key Decisions

- How many passages?
- What branching complexity?
- Who is the audience?
- What makes this story worth telling?

---

## Stage 2: Structure

### What Happens

- Design story topology (hubs, branches, convergences)
- Create passage briefs for each planned passage
- Define choice points and their connections
- Plan state tracking (what to remember)

### The Brief Pipeline

```
Scope (N passages) → Topology Design → Passage Briefs (N briefs)
```

**Critical Rule:** Topology must be valid before creating briefs. Validate structure first.

### Outputs

| Output | Content |
|--------|---------|
| Topology map | How passages connect |
| Passage briefs | Intent, stakes, choices for each passage |
| State plan | What flags/variables to track |
| Gate conditions | What locks/unlocks content |

### Scope Budget

**N passages means at most N unique destinations.**

Each passage ID you reference costs one from your budget. Design patterns that fit:

| Passages | Pattern Options |
|----------|-----------------|
| 3 | Linear, or hub with 2 endings |
| 5 | Hub with 3-4 endings, or short branch-and-merge |
| 10+ | Complex branching, multiple hubs, longer arcs |

---

## Stage 3: Prose

### What Happens

- Write passage prose from briefs
- Develop dialogue and description
- Craft choice text
- Integrate story beats

### The Prose Pipeline

```
Passage Brief → Scene Draft → Style Review → Passage
```

**Rule:** Prose must have a brief to work from. No brief = no passage.

### Outputs

| Output | Content |
|--------|---------|
| Passages | Full prose for each brief |
| Choice text | Options players select |
| Integrated beats | Story moments woven in |

### Brief Fidelity

Prose honors brief intent:

- **Respect topology** — Don't add/remove connections
- **Honor stakes** — Keep what matters at risk
- **Deliver beats** — Include planned moments
- **Match constraints** — Avoid what brief prohibits

---

## Stage 4: Validation

### What Happens

- Check work against quality bars
- Provide actionable feedback
- Gate progression to canon

### Two Validation Modes

| Mode | When | Depth | Speed |
|------|------|-------|-------|
| Pre-gate | During creation | Quick checks | Fast |
| Full-gate | Before canon | All 8 bars | Thorough |

### Pre-Gate Validation

Quick checks during creation:

- Schema compliance
- Required fields present
- Obvious errors
- Basic structure

**Purpose:** Catch issues early, before more work builds on them.

### Full-Gate Validation

Comprehensive review before commitment:

- All 8 quality bars assessed
- Cross-references verified
- Canon alignment checked
- Spoiler hygiene confirmed

**Purpose:** Ensure work is ready for permanent record.

### Validation Outcomes

| Outcome | Meaning | Action |
|---------|---------|--------|
| Pass | All bars satisfied | Promote to next stage |
| Partial | Some issues found | Fix and revalidate |
| Fail | Critical problems | Significant rework needed |

---

## Stage 5: Canon

### What Happens

- Approved work committed to permanent record
- Becomes source of truth
- Immutable once committed

### Canon Commitment

```
Validated Artifact → Lifecycle Transition → Cold Store
```

**Critical Rule:** Never commit without validation. Never bypass quality gates.

### Hot vs Cold

| Store | Purpose | Mutability |
|-------|---------|------------|
| Hot (Workspace) | Work in progress | Mutable |
| Cold (Canon) | Committed truth | Immutable |

**Work flows:** Hot → Validation → Cold

---

## Stage 6: Export

### What Happens

- Build distribution bundles from canon
- Format for target platforms
- Include appropriate assets

### Export Configurations

| Configuration | Purpose | Contents |
|---------------|---------|----------|
| Playtest | Internal review | MD, HTML only, no assets |
| Milestone | Stakeholder review | + EPUB, art/audio plans |
| Production | Player distribution | All formats, full assets |
| Translation | Localization QA | Source + target languages |

### Playtest Build

Quick build for internal review:

- Formats: Markdown, HTML
- Languages: Primary only
- Assets: None
- Speed: Fast

**Use for:** Narrative flow testing, early feedback.

### Milestone Build

Stakeholder-ready package:

- Formats: Markdown, HTML, EPUB
- Languages: Primary only
- Assets: Plans included (not renders)
- Speed: Moderate

**Use for:** Progress reviews, editorial feedback.

### Production Build

Release-ready bundle:

- Formats: All (MD, HTML, EPUB, PDF)
- Languages: All supported
- Assets: Full renders and audio
- Speed: Comprehensive

**Use for:** Player distribution.

### Export Rules

- **Never export from Hot** — Only canon
- **Snapshot first** — Tag version before export
- **Match configuration to purpose** — Don't over-build for playtests

---

## Handoffs Between Stages

### Vision → Structure

| From | To | Handoff |
|------|----|---------|
| Concept owner | Architect | Scope, themes, constraints |

**Clear handoff includes:**

- Number of passages
- Branching complexity target
- Key themes and tone
- Any structural requirements

### Structure → Prose

| From | To | Handoff |
|------|----|---------|
| Architect | Writer | Passage briefs |

**Clear handoff includes:**

- Complete brief for each passage
- Topology showing connections
- State/flag requirements
- Style guide reference

### Prose → Validation

| From | To | Handoff |
|------|----|---------|
| Writer | Validator | Completed passages |

**Clear handoff includes:**

- Passage artifacts with brief references
- Declaration of completion
- Any known issues flagged

### Validation → Canon

| From | To | Handoff |
|------|----|---------|
| Validator | Archivist | Approved artifacts |

**Clear handoff includes:**

- Validation report (all bars pass)
- Lifecycle transition request
- Artifacts ready for cold store

---

## Iteration and Rework

### When Validation Fails

```
Fail → Feedback → Rework → Revalidate
```

**Feedback must be actionable:**

- Specific location
- Clear problem
- Which bar violated
- Suggested fix

### Scope Changes

If scope needs to change mid-production:

1. **Stop current work** — Don't continue on invalid assumptions
2. **Reassess structure** — Does topology still work?
3. **Update briefs** — Reflect new scope
4. **Communicate change** — All affected parties

### When to Escalate

| Situation | Action |
|-----------|--------|
| Scope insufficient for story | Escalate to vision owner |
| Brief conflicts with style | Escalate to style owner |
| Canon conflict discovered | Escalate to lore owner |
| Quality bar keeps failing | Escalate to project lead |

---

## Pipeline Anti-Patterns

### Skipping Structure

**Problem:** Going directly from vision to prose.

**Result:** Inconsistent topology, structural rework late in process.

**Fix:** Always create briefs before prose.

### Bypassing Validation

**Problem:** Committing work without quality checks.

**Result:** Errors propagate, compound over time.

**Fix:** Mandatory validation before canon.

### Premature Export

**Problem:** Building distribution bundles from work-in-progress.

**Result:** Incomplete or inconsistent deliverables.

**Fix:** Export only from validated canon snapshots.

### Scope Creep in Structure

**Problem:** Adding passages beyond budget during structure phase.

**Result:** Incomplete story, orphaned passages.

**Fix:** Respect scope budget; escalate if insufficient.

---

## Quick Reference

| Stage | Input | Output | Gate |
|-------|-------|--------|------|
| Vision | Idea | Concept, scope | Scope approval |
| Structure | Scope | Briefs, topology | Topology validation |
| Prose | Briefs | Passages | Pre-gate |
| Validation | Passages | Pass/fail | Full-gate |
| Canon | Approved | Committed | Lifecycle transition |
| Export | Canon | Bundles | Configuration match |

| Export Type | Formats | Assets | Languages |
|-------------|---------|--------|-----------|
| Playtest | MD, HTML | None | Primary |
| Milestone | + EPUB | Plans | Primary |
| Production | + PDF | Full | All |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — Structure design
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_structure_and_beats|Scene Structure and Beats]] — Brief to prose
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/quality_standards_if|Quality Standards]] — Validation bars
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/canon_management|Canon Management]] — Cold store principles
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/idea_capture_and_hooks|Idea Capture and Hooks]] -- deferral discipline that runs alongside the pipeline; what to defer vs handle now
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/collaborative_if_writing|Collaborative IF Writing]] -- team adaptations of the pipeline: handoffs, voice consistency, story bible
