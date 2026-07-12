---
title: Quality Standards for Interactive Fiction
summary: Quality bars for interactive fiction—integrity, reachability, comprehension, style, safety, accessibility, canon, spoiler hygiene, and research posture.
topics:
  - quality-bars
  - validation
  - integrity
  - reachability
  - comprehension
  - style-consistency
  - safety
  - accessibility
  - canon-compliance
  - spoiler-hygiene
  - research-posture
cluster: craft-foundations
---

# Quality Standards for Interactive Fiction

Craft guidance for evaluating and maintaining quality in interactive fiction through validation bars covering structure, clarity, safety, and coherence.

---

## Overview

Quality assurance in interactive fiction differs from linear narrative because of branching paths, state dependencies, and player agency. These bars adapt industry QA practices to IF-specific concerns.

**Industry grounding:**

- **Technical QA:** Structural validation (ChoiceScript's quicktest, Twine link checking)
- **Content QA:** Narrative consistency, beta-testing feedback
- **Accessibility QA:** WCAG compliance, inclusive design
- **Domain-specific:** Some bars (Canon, Research Posture) apply particularly to fact-based or world-rich fiction

### Bar Categories

| Category | Bars | Focus |
|----------|------|-------|
| Technical | Integrity, Reachability | Does it work? |
| Clarity | Comprehension, Style | Is it understandable? |
| Content | Safety, Accessibility | Is it responsible? |
| Consistency | Canon, Spoiler | Does it cohere? |
| Research | Research Posture | Is it grounded? |

---

## Bar 1: Integrity

**Definition:** Structural completeness—all pieces fit together correctly.

### What Integrity Checks

- **References resolve:** Every link points to existing content
- **Fields present:** Required data exists and is valid
- **Schema compliance:** Artifacts match their type definitions
- **No orphans:** All content connects to the structure

### Common Integrity Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Dangling reference | Choice leads to nonexistent passage | Create missing passage or redirect |
| Missing required field | Passage without title | Add required content |
| Type mismatch | String where number expected | Correct data type |
| Circular dependency | A requires B requires A | Restructure dependencies |

### Automated Validation

Integrity can be largely automated:

- Schema validation catches type/field errors
- Graph traversal finds dangling references
- ChoiceScript's quicktest detects missing labels and syntax errors
- Twine validates link targets

---

## Bar 2: Reachability

**Definition:** Player access—all content can be reached through valid play.

### What Reachability Checks

- **Forward reachability:** Can players reach every passage from the start?
- **Gate obtainability:** Can every gated path be unlocked?
- **No dead ends:** Do all paths eventually lead somewhere meaningful?
- **Recovery possible:** Can players recover from mistakes?

### Common Reachability Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Unreachable passage | No path leads to lighthouse scene | Add route or remove passage |
| Unobtainable gate | Need item that doesn't exist | Create obtainment path |
| Dead end | Choice leads nowhere | Add continuation |
| Permanent lock-in | Early choice blocks critical content | Add alternate paths |

### Testing Reachability

- **Automated:** Graph traversal, randomtest (ChoiceScript runs random playthroughs)
- **Manual:** Systematic branch coverage during playtesting
- **Hybrid:** Automated detection, human verification of edge cases

---

## Bar 3: Comprehension

**Definition:** Player understanding—readers grasp what's happening and what choices mean.

### What Comprehension Checks

- **Plot clarity:** Can players summarize what happened?
- **Choice distinction:** Are options meaningfully different?
- **Motivation clarity:** Do players understand why things happen?
- **Spatial/temporal logic:** Is setting and timeline clear?

### Common Comprehension Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Unclear stakes | Players don't know what's at risk | Establish consequences |
| Synonym choices | "Go left" / "Head left" / "Turn left" | Differentiate intent |
| Missing context | Action assumes knowledge player lacks | Provide setup |
| Confusion cascade | One unclear element creates more | Clarify root cause |

### Detecting Comprehension Issues

Comprehension requires human testing:

- **Post-play summary:** "What was the story about?"
- **Choice explanation:** "Why did you pick that option?"
- **Confusion moments:** Watch for re-reading, hesitation
- **Unexpected outcomes:** "I thought that would..."

See [[Narrative & Game Design/Interactive Fiction/craft-foundations/testing_interactive_fiction|Testing Interactive Fiction]] for methodology.

---

## Bar 4: Style

**Definition:** Voice consistency—the work reads as if one author wrote it.

### What Style Checks

- **Register stability:** Does formality stay consistent?
- **Vocabulary coherence:** Are word choices appropriate throughout?
- **Tone maintenance:** Does mood match across scenes?
- **Period accuracy:** Historical settings avoid anachronisms?

### Common Style Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Register shift | "My liege" then "What's up" | Maintain appropriate register |
| Anachronism | Modern slang in Victorian setting | Use period-appropriate language |
| Tone break | Comedic scene in tragedy without purpose | Align with overall tone |
| Voice drift | Character sounds different across scenes | Review for consistency |

### Style Validation

A consistent B+ voice beats inconsistent A+ fragments. Readers notice jarring shifts even if individual passages are excellent.

See [[Narrative & Game Design/Interactive Fiction/prose-and-language/voice_register_consistency|Voice Register Consistency]] for detailed guidance.

---

## Bar 5: Safety

**Definition:** Harm prevention—sensitive content handled responsibly.

### What Safety Checks

- **Content warnings present:** Sensitive material flagged appropriately
- **No gratuitous content:** Dark material serves story purpose
- **Harmful stereotypes avoided:** Representations are thoughtful
- **Age-appropriate:** Content matches target audience

### Common Safety Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Missing warning | Violence without content note | Add specific warning |
| Gratuitous darkness | Shock value without narrative purpose | Remove or justify |
| Harmful trope | Stereotyped character treatment | Revise representation |
| Audience mismatch | Adult content in middle-grade work | Adjust content or audience |

### Safety Review

- Check content warnings against actual content
- Evaluate purpose of sensitive material
- Consider diverse reader perspectives
- Consult sensitivity readers for relevant topics

---

## Bar 6: Accessibility

**Definition:** Inclusive access—players with disabilities can engage with the work.

### What Accessibility Checks

- **Screen reader compatibility:** Text is properly structured
- **Keyboard navigation:** All interactions work without mouse
- **Color independence:** Meaning not conveyed by color alone
- **Reading level:** Prose matches target audience capability
- **Timing flexibility:** No time-limited interactions without options

### Common Accessibility Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Image-only content | Critical info in untagged image | Add alt text or text equivalent |
| Low contrast | Light gray text on white | Increase contrast ratio |
| Color-coded choices | Red=danger, green=safe with no other indicator | Add text/icon indicators |
| Rapid timing | Must click within 3 seconds | Allow timing adjustments |

### Accessibility Standards

WCAG 2.1 provides baseline guidance:

- **Perceivable:** Content available to all senses
- **Operable:** Interface works with various inputs
- **Understandable:** Content and operation are clear
- **Robust:** Works with assistive technologies

See [[Narrative & Game Design/Interactive Fiction/audience-and-access/accessibility_guidelines|Accessibility Guidelines]] for detailed standards.

---

## Bar 7: Canon

**Definition:** World consistency—content matches established truth.

### What Canon Checks

- **Fact alignment:** Does content match the world bible?
- **Character consistency:** Do characters behave as established?
- **Timeline coherence:** Do events fit the chronology?
- **Rule compliance:** Does content follow world rules?

### Common Canon Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Contradictory fact | Character dies in chapter 3, appears in chapter 5 | Align with canon |
| Timeline error | Event happens before its cause | Reorder or clarify |
| Character break | Peaceful character initiates violence without reason | Justify or revise |
| Rule violation | Magic works differently than established | Follow world rules |

### Canon Validation

- Cross-reference against world bible
- Check timeline positioning
- Verify character behavior against profiles
- Track state dependencies across branches

---

## Bar 8: Spoiler Hygiene

**Definition:** Player experience—discovery is preserved, secrets stay hidden.

### What Spoiler Checks

- **No early reveals:** Plot twists not exposed before their time
- **Reference safety:** Codex/glossary doesn't spoil story
- **Gate text safety:** Locked content hints don't reveal too much
- **Surface separation:** Player-facing content is clean

### Spoiler Classification

| Level | Definition | Treatment |
|-------|------------|-----------|
| Minor | Background flavor | May appear with careful phrasing |
| Major | Affects understanding/strategy | Must be omitted or heavily obscured |
| Critical | Would ruin experience | Never appears, no exceptions |

### Common Spoiler Failures

| Issue | Example | Fix |
|-------|---------|-----|
| Codex spoiler | Entry reveals villain's identity | Remove from codex |
| Gate hint | Lock text reveals what's behind door | Obscure hint |
| Early foreshadowing | Too-obvious setup spoils twist | Increase subtlety or remove |
| Meta-knowledge | Player knows what character shouldn't | Separate knowledge layers |

---

## Bar 9: Research Posture

**Definition:** Factual grounding—claims about real-world facts are appropriately supported.

**Note:** This bar applies primarily to fiction engaging with real history, science, or current events. Pure fantasy may have minimal research requirements beyond internal consistency.

### Posture Levels

| Posture | Meaning | Surface Treatment |
|---------|---------|-------------------|
| Corroborated | Multiple reliable sources agree | State directly |
| Plausible | Reasonable based on evidence | Soft hedge ("believed to be") |
| Disputed | Sources actively conflict | Present as in-world disagreement |
| Uncorroborated | No sources found | Neutral phrasing, assess risk |

### Risk Assessment for Uncorroborated Claims

| Risk | Impact | Example |
|------|--------|---------|
| Low | Flavor detail | Color of tavern sign |
| Medium | Affects plot | How organization made decisions |
| High | Central premise | Medical procedure critical to plot |

### Research Application

- Every real-world claim should have assessed posture
- High-risk uncorroborated claims need attention before publication
- Surface treatment (hedging language) matches posture level
- See [[Narrative & Game Design/Interactive Fiction/genre-conventions/historical_fiction|Historical Fiction]] for detailed methodology

---

## Validation Approaches

### Pre-Gate (Quick Check)

Fast validation for work-in-progress:

- Schema compliance
- Required fields present
- Link/reference validation
- Basic structural integrity

**When to use:** Before passing work to next stage, during active creation.

### Full-Gate (Comprehensive)

Thorough validation before commitment:

- All bars assessed
- Cross-references verified
- Human review for non-automatable aspects
- Complete quality review

**When to use:** Before promoting to canon, before publication.

### What Can Be Automated

| Bar | Automation Level |
|-----|------------------|
| Integrity | High — schema validation, link checking |
| Reachability | High — graph traversal, randomtest |
| Comprehension | Low — requires human testing |
| Style | Low — requires human judgment |
| Safety | Medium — keyword flagging, human review |
| Accessibility | Medium — automated checks + manual testing |
| Canon | Medium — cross-reference, human verification |
| Spoiler | Low — requires content understanding |
| Research | Low — requires source evaluation |

---

## Actionable Feedback

Quality feedback must be actionable. Vague criticism wastes time.

### Bad Feedback

- "The prose needs work."
- "Something feels off about this scene."
- "Style issues throughout."

### Good Feedback

- "Paragraph 3, sentence 2: 'okay' is anachronistic for 1850s setting. Replace with period-appropriate acknowledgment."
- "Choice 2 and Choice 3 are near-synonyms—both involve 'investigating.' Differentiate the action or target."
- "Canon conflict: Chapter 2 states the Guild was founded in Year 350, but this passage says Year 347. Verify and align."

### Feedback Structure

1. **Location:** Where exactly is the issue?
2. **Problem:** What specifically is wrong?
3. **Standard:** Which quality bar is violated?
4. **Fix:** What specific change resolves it?

---

## Bar Priority

When bars conflict, prioritize:

1. **Safety** — Never compromise on harm prevention
2. **Accessibility** — Inclusive access is non-negotiable
3. **Integrity** — Must be structurally sound
4. **Canon** — World consistency matters for coherence
5. **Comprehension** — Players must understand
6. **Other bars** — Balance based on context

---

## Design Goals vs Quality Bars

Some aspects of IF quality are **design goals**, not validation bars:

**Nonlinearity/Choice Meaningfulness:**

Whether branches lead to meaningfully different experiences is a design decision. Linear IF and highly branching IF can both be high quality. Evaluating whether "choices matter" depends on authorial intent and genre expectations, not a universal standard.

**Emotional Impact:**

Whether the story moves readers emotionally cannot be validated—only tested through reader response.

**Pacing Effectiveness:**

Whether rhythm and flow work requires human judgment about subjective experience.

These aspects require playtesting and reader feedback, not validation bars.

---

## Quick Reference

| Bar | Focus | Key Question | Automation |
|-----|-------|--------------|------------|
| Integrity | Structure | Does it hold together? | High |
| Reachability | Access | Can players get there? | High |
| Comprehension | Clarity | Do players understand? | Low |
| Style | Voice | Does it sound unified? | Low |
| Safety | Harm | Is content responsible? | Medium |
| Accessibility | Inclusion | Can everyone engage? | Medium |
| Canon | Truth | Does it match the world? | Medium |
| Spoiler | Discovery | Are secrets preserved? | Low |
| Research | Facts | Are claims supported? | Low |

---

## Research Basis

Key sources informing IF quality standards:

| Concept | Source |
|---------|--------|
| ChoiceScript quicktest/randomtest | Choice of Games documentation |
| Content vs Technical QA | BioWare narrative QA practices |
| Playtest methodology | Emily Short, IF craft essays |
| Accessibility standards | WCAG 2.1 (W3C) |
| Comprehension testing | Usability research (Nielsen, Lewis) |

ChoiceScript's automated testing tools (quicktest for syntax/structure, randomtest for reachability through random playthroughs) represent industry-standard IF validation. BioWare's distinction between Content QA (narrative consistency, character voice) and Technical QA (scripting, triggers, flags) informed the bar categorization.

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/craft-foundations/testing_interactive_fiction|Testing Interactive Fiction]] — Playtest methodology
- [[Narrative & Game Design/Interactive Fiction/audience-and-access/accessibility_guidelines|Accessibility Guidelines]] — Detailed accessibility standards
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/voice_register_consistency|Voice Register Consistency]] — Style consistency guidance
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/worldbuilding_patterns|Worldbuilding Patterns]] — Canon consistency
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/historical_fiction|Historical Fiction]] — Research methodology
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] — Player-facing content standards
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/research_and_verification|Research and Verification]] -- methodology for Bar 9 (research posture): certainty levels and uncorroborated-claim handling
