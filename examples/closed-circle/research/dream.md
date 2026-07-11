---
stage: dream
corpus_fingerprint: 7bc17145775f5a8ca857717a34126a93073be2984a36df82246ff97cc8683a9f
standing_queries: []
librarian_queries:
- closed circle genre blending escalation
- intersecting subplots consequence compounding
- long payoff fair play clue distribution
- tone management dark comedy violence boundaries
- state tracking closed circle attrition
top_k: 4
sources:
- audience-and-access/accessibility_guidelines.md
- audience-and-access/audience_targeting.md
- audience-and-access/localization_considerations.md
- craft-foundations/audio_visual_integration.md
- craft-foundations/player_analytics_metrics.md
- craft-foundations/testing_interactive_fiction.md
- emotional-design/conflict_patterns.md
- emotional-design/emotional_beats.md
premise_sha: 8b63d487cbbd0f4a
---

## closed circle genre blending escalation

### audience-and-access/audience_targeting.md#Audience Targeting for Interactive Fiction

Craft guidance for writing interactive fiction for different age groups—vocabulary, themes, complexity, and content appropriateness. ---

### craft-foundations/audio_visual_integration.md#Audio-Visual Integration in Interactive Fiction

Craft guidance for integrating audio and visual elements into interactive narratives—sound design principles, dynamic music, and multimedia storytelling. ---

### emotional-design/conflict_patterns.md#Escalation Arcs

### The Stakes Ladder Conflicts must escalate. Each confrontation should raise stakes higher than the last. Without escalation, stories plateau and readers disengage. **Escalation dimensions:** - **Scope:** Personal → local → global - **Consequences:** Inconvenience → loss → death - **Difficulty:** Easy choices → impossible choices - **Investment:** Strangers at risk → loved ones at risk → self at risk ### The Try-Fail Cycle Characters should fail before they succeed. Each failure raises stakes and reveals new information. 1. Character tries obvious solution → fails 2. Character tries harder/smarter solution → fails, but learns something 3. Character tries unconventional solution → fails, but gets closer 4. Character synthesizes learning into final approach → succeeds (or fails meaningfully) ### Avoiding Plateau Signs your conflict has plateaued: - Same type of challenge repeating - Stakes haven't increased in several scenes - Antagonist isn't responding to protagonist's actions - Resolution seems equally possible now as three chapters ago ### False Victories and True Setbacks Escalation includes reversals: -

## intersecting subplots consequence compounding

### audience-and-access/audience_targeting.md#Choice Complexity by Age

### Branching Depth | Audience | Max Meaningful Branches | |----------|------------------------| | Early Readers | 2–3 | | Middle Grade | 3–5 | | Young Adult | 5–8 | | Adult | No limit | ### Consequence Delay | Audience | How Far Ahead? | |----------|----------------| | Early Readers | Immediate | | Middle Grade | 1–3 passages | | Young Adult | Full story | | Adult | Full story | ### Failure States | Audience | Approach | |----------|----------| | Early Readers | Avoid; redirect to success | | Middle Grade | Limited; learning opportunity | | Young Adult | Acceptable; meaningful | | Adult | As story requires | ---

### craft-foundations/testing_interactive_fiction.md#Branch Coverage Testing

### The Coverage Problem A 10-passage story with 2 choices per passage has 512 possible paths. No single playtest reveals all content. ### Systematic Coverage Approaches **Breadth-first testing:** Test all branches at first decision, then all at second, etc. | Pro | Con | |-----|-----| | Catches first-branch bugs quickly | Misses deep-path issues | **Depth-first testing:** Complete one full path before trying alternatives. | Pro | Con | |-----|-----| | Tests full narrative arcs | May miss early-branch issues | **Priority-based testing:** Focus on main paths

## long payoff fair play clue distribution

### audience-and-access/localization_considerations.md#Text Design for Translation

### String Externalization **Principle:** All player-facing text should be separate from code. **Good:** ``` dialogue.meeting_stranger = "Hello, I don't believe we've met." ``` **Bad:** ``` print("Hello, I don't believe we've met.") ``` ### Avoiding Concatenation **The Problem:** Different languages have different word orders. Concatenated strings break. **Bad:** ``` "You have " + count + " apples." ``` In German: "Sie haben 5 Äpfel." (works) In Polish: "Masz 5 jabłek." (word order differs) **Good:** ``` "You have {count} apples." // Translators can reorder: "{count} jabłek masz." ``` ### Placeholder Guidelines - Use named placeholders, not positional - Allow translators to reorder - Document what each placeholder contains - Provide context for all strings ### Text Expansion Translations often expand or contract text: | Language | Expansion vs English | |----------|---------------------| | German | +30% | | French | +15-20% | | Spanish | +20-25% | | Japanese | -10-50% | | Chinese | -30-50% | **Implications:** - UI must accommodate longer text - Buttons need flexible sizing - Text areas should scroll or wrap - Test with expanded text ### Pluralization **The Problem:** Languages have different plural rules. **English:** 1 apple, 2 apples (singular, plural) **Polish:** 1 jabłko, 2 jabłka, 5…

## tone management dark comedy violence boundaries

### audience-and-access/accessibility_guidelines.md#See Also

- [[Narrative & Game Design/Interactive Fiction/audience-and-access/audience_targeting|Audience Targeting]] — Age and audience considerations - [[Narrative & Game Design/Interactive Fiction/genre-conventions/horror_conventions|Horror Conventions]] — Content warnings for dark content - [[Narrative & Game Design/Interactive Fiction/genre-conventions/historical_fiction|Historical Fiction]] — Sensitive historical content - [[Narrative & Game Design/Interactive Fiction/audience-and-access/localization_considerations|Localization Considerations]] — Cultural accessibility - [[Narrative & Game Design/Interactive Fiction/craft-foundations/quality_standards_if|Quality Standards]] -- Bar 6 (Accessibility) validation checks and WCAG mapping - [[Narrative & Game Design/Live Game Design/corpus/immersive-and-live-action/puzzle-accessibility|Puzzle Accessibility]] -- sibling framework from live-game design (physical, sensory, cognitive, linguistic accessibility)

### craft-foundations/audio_visual_integration.md#Common Mistakes

### Audio Overload Constant sound fatigues listeners. Use silence, vary intensity. ### Mood Mismatch Upbeat music during tragedy, peaceful ambience during horror—jarring. ### Poor Loop Points Obvious audio loops break immersion. Test transitions extensively. ### Inaccessible Design Required audio for critical info excludes deaf/hard-of-hearing players. ### Production Value Gap High-quality prose with low-quality audio feels worse than text-only. ### Ignoring Player Agency Cutscene-style audio during interactive moments feels disconnected. ---

### emotional-design/emotional_beats.md#Quick Reference

| Element | Guideline | |---------|-----------| | Setup | Investment before impact | | Restraint | Understatement over melodrama | | Concrete | Specific details over abstract feelings | | Space | Let beats breathe | | Contrast | Joy after sorrow, relief after terror | | Earning |

## state tracking closed circle attrition

### audience-and-access/accessibility_guidelines.md#Motor Accessibility

### Input Methods **Support Multiple Input Types:** - Mouse/touch - Keyboard only - Voice commands (where available) - Switch devices - Eye tracking (specialized) ### Keyboard Navigation **Requirements:** - All functions accessible via keyboard - Visible focus indicators - Logical tab order - Keyboard shortcuts for common actions - No keyboard traps **Best Practices:** - Arrow keys for menu navigation - Enter/Space for selection - Escape to close/back - Tab for focus movement ### Timing Considerations **Challenges:** - Timed choices create pressure - Quick reactions required - Holding buttons difficult **Solutions:** - Avoid mandatory time limits - Adjustable timer speeds - Option to disable timers - No penalties for slow response ### Click/Tap Targets **Requirements:** - Minimum 44x44 pixels (touch) - Adequate spacing between targets - No precision clicking required - Clear visual boundaries ---

### craft-foundations/player_analytics_metrics.md#Quick Reference

| Goal | Metric | Tool | |------|--------|------| | Engagement | Session duration, completion | Event logging | | Choice balance | Distribution % | Choice tracking | | Pacing | Reading time per passage | Timestamp analysis | | Problems | Abandonment clusters | Funnel analysis | | Replay value | Return sessions, path diversity | Cohort tracking | | Player satisfaction | Survey
