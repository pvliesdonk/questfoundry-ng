---
title: "Beat Taxonomies from Craft Literature"
summary: "Named beat types and their functions from Save the Cat, Story Grid, and other craft frameworks — a vocabulary for what beats do at each story position."
topics:
  - beat-taxonomy
  - save-the-cat
  - story-grid
  - beat-function
  - beat-sheet
  - story-beats
  - structural-beats
  - beat-naming
cluster: narrative-structure
---

# Beat Taxonomies from Craft Literature

Craft guidance for understanding the named beat types that appear across major storytelling frameworks —Save the Cat, Story Grid, the Hero's Journey, and others —and how their function labels serve as diagnostic and generative tools for interactive fiction.

---

## What Is a Beat Taxonomy?

### Three Levels of "Beat"

The word "beat" means different things depending on who uses it. Craft literature operates at three distinct levels, and confusing them causes real problems in planning and discussion.

| Level | What It Describes | Example | Covered In |
|-------|-------------------|---------|------------|
| Prose beat | Smallest unit of prose —one action, line of dialogue, or sensory detail | "She set down the glass." | [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] |
| Structural beat | Named story event with a specific dramatic function | Catalyst, Midpoint, All Is Lost | This article |
| Emotional beat | A moment designed to produce a specific feeling in the reader | Catharsis, dread, triumph | [[Narrative & Game Design/Interactive Fiction/emotional-design/emotional_beats|Emotional Beats]] |

These are not competing definitions. They operate at different scales. A single moment in a story is simultaneously all three: a prose beat (two sentences of dialogue), a structural beat (the Catalyst), and an emotional beat (shock that reframes everything). Recognizing which level you are discussing prevents the most common planning confusion —arguing about "beats" when two people mean different things.

> **Example of all three levels at once:**
> A character opens a letter revealing her father is alive. At the prose level, this is an action beat followed by an emotion beat. At the structural level, this is the Catalyst —it disrupts the status quo and launches the story. At the emotional level, this is a shock-and-wonder beat designed to produce astonishment in the reader. All three descriptions are correct. They describe different aspects of the same moment.

### Why Function Names Matter

Consider two descriptions of the same story moment:

- "The hero learns the village is threatened" —this is **content**
- "Catalyst" —this is **function**

Content tells you what happens. Function tells you what the moment **does for the story**. A Catalyst disrupts the status quo and forces the protagonist into a new situation. That function is the same whether the content involves a threatened village, a mysterious letter, or a job offer in another city.

Function names are diagnostic tools. When a story feels flat at the midpoint, the diagnosis "your Midpoint lacks a stakes reversal" is more actionable than "the middle is boring." The name carries the fix.

Function names are also **communication tools**. When collaborators share a vocabulary of beat functions, structural discussions become precise. "Move the Catalyst earlier" is unambiguous. "Make the beginning more exciting" is not. A shared taxonomy reduces misunderstanding and wasted iteration.

---

## Save the Cat Beat Sheet

Blake Snyder developed his 15-beat framework for screenwriting in *Save the Cat!* (2005). Jessica Brody adapted it for novels in *Save the Cat! Writes a Novel* (2018). The framework remains one of the most widely used structural tools because it names both the function and the approximate position of each beat.

### The 15 Beats

| Beat Name | Position | Function | What It Accomplishes |
|-----------|----------|----------|----------------------|
| Opening Image | 1% | Snapshot of "before" | Establishes tone, mood, and protagonist's starting state |
| Theme Stated | 5% | Thematic question posed | Someone states the theme (often to the protagonist, who doesn't yet understand it) |
| Setup | 1-10% | World and character establishment | Shows protagonist's flawed world, introduces key characters, plants seeds |
| Catalyst | 10-12% | Disruption of status quo | An event that makes the old world unsustainable —the story's inciting incident |
| Debate | 12-25% | Protagonist resists the call | Internal or external deliberation about whether to act —raises stakes of saying yes |
| Break into Two | 25% | Commitment to action | Protagonist makes an active choice to enter the new world or situation |
| B-Story | 22-30% | Secondary relationship introduced | Often a love interest or mentor —carries the thematic argument |
| Fun and Games | 25-50% | Promise of the premise | The "trailer moments" —what the audience came for. The concept in action |
| Midpoint | 50% | Stakes shift | Either a false victory (things seem great but aren't) or a false defeat. Raises stakes permanently |
| Bad Guys Close In | 50-75% | Increasing pressure | External forces tighten, internal flaws resurface, the team fractures |
| All Is Lost | 75% | Lowest point | The protagonist's plan fails. Often involves a "whiff of death" —something or someone is lost |
| Dark Night of the Soul | 75-80% | Emotional processing | Protagonist confronts despair, reflects on failure, reaches for deeper truth |
| Break into Three | 80% | Synthesis and new plan | A-Story and B-Story merge. Protagonist finds a new approach using lessons learned |
| Finale | 80-99% | Final confrontation and resolution | Protagonist enacts the new plan, defeats opposition, proves transformation |
| Final Image | 99-100% | Snapshot of "after" | Mirrors Opening Image to show how far the protagonist has come |

### Beat Functions vs Beat Positions

The beat sheet prescribes both function and position. Snyder was precise: Catalyst at 12%, Midpoint at 50%, All Is Lost at 75%. These percentages come from screenplay structure, where a 110-page script has rigid timing expectations.

For interactive fiction, **positions are guidelines, not rules**. A branch might reach its Catalyst at 5% or 20%. What matters is that the function is present and correctly ordered. A story where All Is Lost comes before Midpoint has a structural problem regardless of position.

The ordering constraint is more important than the positional constraint:

1. Setup before Catalyst
2. Catalyst before Break into Two
3. Fun and Games before Midpoint
4. Bad Guys Close In before All Is Lost
5. Dark Night before Finale

**Practical implication for IF:** When scaffolding a branching story, check that every path through the graph respects this ordering. A branch that jumps from Catalyst directly to Finale skips the middle —it may be short, but it still needs escalation and a low point to feel complete.

### Adaptation from Screenwriting to Prose

Snyder wrote for 110-page screenplays. Jessica Brody's adaptation for novels identified key differences:

**Longer Setup.** Novels have room for deeper character establishment. The Setup expands from a few pages to multiple chapters, allowing subplots, world-building, and character relationships that film compresses.

**More complex B-Stories.** Film B-Stories are often a single relationship. Novel B-Stories can involve multiple secondary characters and subplots, each carrying a facet of the thematic argument.

**Expanded Dark Night of the Soul.** In screenwriting, this might be a single scene. In novels, it can be an entire chapter of reflection, flashback, and emotional reckoning. Brody argues this is where the novel form most surpasses film —internal experience rendered in full.

**Fun and Games as a larger territory.** The promise of the premise occupies a quarter of the story. In novels, this section builds the world and relationships that make the second half's losses devastating.

**Interactive fiction adds a further adaptation.** The Debate beat —where the protagonist resists the call —often becomes the first major choice point. The reader decides whether to accept the call, and that decision creates the first meaningful branch. Similarly, Break into Two is frequently the mechanism through which the story's central branching structure activates: the reader's commitment to a path IS the break into Act II.

The B-Story also transforms in IF. Rather than a single secondary relationship carrying the thematic argument, interactive fiction can offer different B-Story characters on different branches —each embodying a different facet of the theme. A branch where the reader allies with a mentor explores the theme through wisdom and tradition. A branch where the reader allies with a rival explores it through competition and self-reliance. The B-Story becomes branch-variable content, and its variation is one of the primary ways branches feel meaningfully different.

---

## Story Grid Beat Hierarchy

Shawn Coyne's Story Grid methodology (*The Story Grid*, 2015) takes a different approach. Rather than prescribing a fixed sequence of named beats, Coyne defines a hierarchy of structural units, each containing the ones below it.

### The Hierarchy: Beat, Scene, Sequence, Act, Story

| Level | Contains | Turns On | Example |
|-------|----------|----------|---------|
| Beat | Single action or exchange | Behavior shift | Character's expression changes from confident to uncertain |
| Scene | Multiple beats | Value shift (positive to negative or reverse) | "Safe" turns to "in danger" |
| Sequence | 2-5 scenes | Larger value shift compounding scene turns | A series of discoveries escalates "curious" to "terrified" |
| Act | Multiple sequences | Major value reversal | Act I ends with the protagonist's world upended |
| Story | All acts | Global value transformation | Character moves from "cowardly" to "courageous" (or the reverse) |

The key insight is that **every level turns on a value shift**. A beat without a shift is dead weight. A scene without a value change is a candidate for cutting. This fractal property —the same structure at every scale —makes Story Grid a powerful analytical tool.

For interactive fiction, this hierarchy maps naturally to the generation pipeline. The global story defines the overarching value transformation. Acts correspond to major story phases. Sequences map to clusters of related passages. Individual passages are scenes. And the prose beats within each passage are the smallest units. Each level can be planned, generated, and validated independently using the same value-shift criterion.

### Story Beats vs Emotional Beats

Coyne distinguishes between external (story) beats and internal (emotional) beats:

**External beats:** Goal pursuit, obstacle encountered, crisis point, action taken. These move the plot.

**Internal beats:** Emotional reaction, subtext processing, value questioning, worldview shift. These move the character.

Coyne's central insight: **every scene needs both or it fails.** A scene with only external beats feels mechanical —things happen but nobody processes them. A scene with only internal beats feels static —characters feel things but nothing happens.

This maps directly to Swain's Scene-Sequel model:

| Coyne's Term | Swain's Equivalent | Function |
|--------------|-------------------|----------|
| External beats | Scene (Goal-Conflict-Disaster) | Move the plot forward through action |
| Internal beats | Sequel (Reaction-Dilemma-Decision) | Move the character forward through processing |

The vocabulary differs, but the structural requirement is identical: action followed by processing, then new action. A story that neglects either half —all plot with no reflection, or all feeling with no events —fails at the scene level regardless of how strong its macro structure may be.

### The Five Commandments of Storytelling

Coyne identifies five elements required in every scene:

1. **Inciting Incident** —An event that upsets the balance and launches the scene
2. **Turning Point Progressive Complication** —A complication that forces a crisis (not just any complication —the one that makes the situation impossible to ignore)
3. **Crisis** —A dilemma requiring choice, typically "best bad choice" or "irreconcilable goods"
4. **Climax** —The character's action in response to the crisis
5. **Resolution** —The new state after the action, setting up the next scene

These five commandments apply at every level of the hierarchy. An act has its own inciting incident, turning point, crisis, climax, and resolution. So does the global story. This fractal structure means the same diagnostic vocabulary works at any scale: "Your scene lacks a clear crisis" uses the same framework as "Your story lacks a clear crisis."

**The crisis question is particularly valuable for interactive fiction.** Coyne defines two types of crisis: the **best bad choice** (all options have costs) and **irreconcilable goods** (two desirable outcomes that cannot both be achieved). These map directly to meaningful choice design —the best IF choices are exactly these crisis types. A choice where one option is obviously correct is not a crisis and will not engage the reader.

---

## Comparative Taxonomy

### Mapping Across Frameworks

Different frameworks emphasize different aspects of the same underlying story movements. This table maps approximate equivalences across five major systems:

| Story Position | Swain | Save the Cat | Story Grid | Hero's Journey | Three-Act |
|----------------|-------|--------------|------------|----------------|-----------|
| Opening state | Setup | Opening Image + Setup | Beginning Hook (setup) | Ordinary World | Act I opening |
| Inciting event | Goal introduced | Catalyst | Inciting Incident (global) | Call to Adventure | Act I turning point |
| Commitment | Decision | Break into Two | End of Beginning Hook | Crossing the Threshold | Act II begins |
| Midpoint shift | Mid-scene disaster | Midpoint | Middle Build turning point | Ordeal / Innermost Cave | Act II midpoint |
| Low point | Disaster (major) | All Is Lost | All Is Lost moment | Death and Rebirth | Act II turning point |
| Climax | New goal enacted | Finale | Climax (global) | Return with Elixir | Act III climax |

**These mappings are approximate.** The Hero's Journey's "Ordeal" is not exactly the Save the Cat "Midpoint" —Campbell emphasizes mythological death-and-rebirth where Snyder emphasizes a false victory or false defeat. But they occupy the same structural territory and serve related dramatic functions.

Notice what the table reveals: every framework has a name for the inciting disruption and the climactic resolution. The frameworks diverge most in how they describe the middle —the long stretch between commitment and crisis. Save the Cat fills this with "Fun and Games" and "Bad Guys Close In." Story Grid fills it with progressive complications. The Hero's Journey fills it with "Tests, Allies, and Enemies." These are different lenses on the same structural territory, and each highlights something the others miss.

### Where the Frameworks Disagree

**Scale of focus.** Swain operates at the micro level —scene and sequel, beat by beat. Save the Cat operates at the macro level —whole-story architecture. Story Grid bridges both, defining fractal structure from beat to story. No single framework covers all scales equally well.

**What drives structure.** Save the Cat is prescriptive: these beats, in this order, at these positions. Story Grid is diagnostic: these elements must be present, but the framework adapts to genre conventions. The Hero's Journey is mythological: structure reflects universal human experience rather than dramatic engineering.

**The role of the protagonist.** Save the Cat assumes a single protagonist with a clear arc. Story Grid accommodates ensemble casts through multiple value shifts. The Hero's Journey assumes a mythic hero pattern that not all stories follow.

**Genre sensitivity.** Story Grid is explicitly genre-aware —a thriller has different obligatory scenes than a romance. Save the Cat is more genre-neutral, applying the same 15 beats regardless. The Hero's Journey applies best to adventure, fantasy, and coming-of-age; it strains when applied to intimate domestic stories.

**Treatment of the middle.** This is the most revealing disagreement. Save the Cat splits the middle into distinct phases (Fun and Games, then Bad Guys Close In) with a clear Midpoint dividing them. Story Grid treats the middle as a series of progressive complications building toward a crisis. The Hero's Journey sees it as a sequence of trials. Syd Field originally called it "the problem with Act II" —the middle is where stories sag, and each framework's attempt to structure it reveals its priorities. For interactive fiction, the Save the Cat vocabulary is most immediately useful because it names the emotional trajectory (playful exploration giving way to tightening pressure) rather than just the mechanical structure.

No single framework is complete. The richest vocabulary for structural analysis comes from combining them: Save the Cat for macro architecture, Story Grid for scene-level diagnosis, Swain for prose-level beat construction, and the Hero's Journey for mythological resonance.

**Practical recommendation:** Use Save the Cat beat names when planning overall story shape. Switch to Story Grid vocabulary when diagnosing individual scenes. Use Swain's Scene-Sequel language when writing or reviewing prose. This layered approach gives you precision at every scale without forcing one framework to cover territory it was not designed for.

---

## Interactive Fiction: Beat Functions in Branching Stories

### Mandatory vs Branch-Variable Beats

In a linear story, every reader encounters every beat. In branching fiction, some beats must appear on all paths while others can be branch-specific.

| Beat | Mandatory / Variable | Why |
|------|----------------------|-----|
| Catalyst | Mandatory | Without it, no path has a reason to begin. Every branch needs its inciting disruption |
| Break into Two | Mandatory | The choice point that launches the branch IS the break. Often the branching mechanism itself |
| Midpoint equivalent | Mandatory | Every path needs a stakes shift or it sags in the middle |
| All Is Lost equivalent | Variable per branch | Different paths can have different low points —this is where branches feel most distinct |
| Dark Night of the Soul | Variable per branch | The nature of reflection depends on what was lost, which differs by path |
| Climax equivalent | Mandatory | Every path must resolve. A branch without a climax is an abandoned thread |
| Final Image | Mandatory | Every ending needs closure, though the image differs by path |

The principle: **every path through the story should contain a complete emotional arc.** A reader who takes any single route should experience disruption, escalation, low point, and resolution. Paths that skip the low point feel hollow. Paths that skip the climax feel abandoned.

Note that "mandatory" does not mean "identical across branches." The Catalyst can be shared (all branches begin from the same disruption) or branch-specific (each path has its own triggering event). What matters is presence, not identity.

### The Branch as Beat Sheet

Each major branch can be analyzed as its own mini beat sheet. This does not mean every branch needs all 15 Save the Cat beats —that would be impractical. But every branch needs a minimum set:

- **Catalyst** —why this path exists, what launched the reader down it
- **Fun and Games** —the content unique to this branch, the reason to take this path
- **Crisis / All Is Lost** —the hardest moment on this path, where things feel most desperate
- **Resolution** —how this path concludes, what transformation it reveals

Branches that lack a crisis or low point feel like tourism —pleasant but dramatically inert. The reader visits interesting locations without ever being challenged. Branches that lack unique Fun and Games content feel like cosmetic variations of the same story.

**Test each branch independently.** Read through a single path from start to finish. Does it feel like a complete story? Does tension rise and fall? Is there a moment of genuine difficulty? If a branch reads as flat, check which beat functions are missing.

> **Example of a hollow branch:** The reader chooses to investigate the abandoned mine. The branch describes the mine's history, shows some interesting geological features, introduces a minor character, and concludes with the reader emerging safely. Nothing went wrong. No stakes were raised. No crisis was faced. The branch has Fun and Games content but no All Is Lost, no Crisis, no transformation. It reads as a side tour, not a story path.
>
> **The same branch with beat functions:** The reader enters the mine (Catalyst —the entrance collapses behind them). They discover evidence of an old crime (Fun and Games —unique branch content). Their light source fails and they hear movement deeper in the tunnels (Bad Guys Close In). They realize the minor character they trusted is the one who caused the collapse (All Is Lost). They must decide whether to confront the character or find another way out (Crisis). The branch now has structural shape.

### Scaffolding with Beat Functions

During initial scaffolding, assign beat functions to the story skeleton before writing any prose. This creates a structural map that serves as both generation guide and validation tool.

**The process:**

1. Outline the story's passages and branching structure
2. Assign a beat function to each passage (Catalyst, Fun and Games, Midpoint, etc.)
3. Walk each branch path and verify it contains the minimum function set
4. Identify gaps —if no passage on a branch is labeled "All Is Lost," that branch likely lacks a genuine low point
5. Adjust structure before writing prose —adding, moving, or reframing passages to fill structural gaps

**Beat function map as validation.** After scaffolding, check:

- Does every branch have a Catalyst, Midpoint equivalent, and Climax?
- Is there at least one All Is Lost or Crisis beat per branch?
- Do Fun and Games beats deliver content unique to their branch?
- Does the ordering make structural sense (no Finale before Midpoint)?

This validation catches structural problems early, before prose has been written and rewriting becomes expensive. A missing function label is far easier to fix than a missing chapter.

**Example beat function map for a three-branch story:**

| Passage | Branch A (Confront) | Branch B (Investigate) | Branch C (Flee) |
|---------|---------------------|------------------------|-----------------|
| P1-P3 | Setup / Catalyst (shared) | Setup / Catalyst (shared) | Setup / Catalyst (shared) |
| P4 | Fun and Games | Fun and Games | Fun and Games |
| P5 | Bad Guys Close In | Midpoint | Bad Guys Close In |
| P6 | Midpoint | Bad Guys Close In | All Is Lost |
| P7 | All Is Lost | All Is Lost | Dark Night of the Soul |
| P8 | Dark Night of the Soul | Dark Night of the Soul | Finale |
| P9 | Finale | Finale | Final Image |
| P10 | Final Image | Final Image | —|

Reading down each column, you can verify that every branch contains the minimum function set. If Branch C lacked an All Is Lost passage, the map would reveal that gap immediately. The map also reveals pacing differences: Branch C reaches its low point earlier (P6) and resolves faster, creating a shorter, more intense experience. Branch B delays its Midpoint to P5 but front-loads investigation content. These are design choices, visible and adjustable before any prose is written.

---

## Quick Reference

| Framework | Key Contribution | Best Used For |
|-----------|-----------------|---------------|
| Save the Cat | 15 named beats with positions and functions | Macro story architecture, planning overall shape |
| Story Grid | Fractal hierarchy with Five Commandments per level | Scene-level diagnosis, genre-aware analysis |
| Swain (Scene-Sequel) | Micro-level beat construction and pacing | Prose-level rhythm, action-reaction patterns |
| Hero's Journey | Mythological resonance and archetypal structure | Fantasy, adventure, coming-of-age stories |

| Beat Function | What It Does | IF Application |
|---------------|-------------|----------------|
| Catalyst | Disrupts status quo, launches the story | Must appear on every branch —often IS the branch point |
| Midpoint | Shifts stakes via false victory or false defeat | Prevents middle sag; every path needs a stakes reversal |
| All Is Lost | Delivers the lowest emotional point | Branch-variable —different paths have different darkest moments |
| Dark Night of the Soul | Processes loss, reaches for deeper truth | Where character voice emerges most strongly in prose |
| Finale | Applies transformation to resolve the story | Each branch ending must feel earned through its own arc |

---

## Research Basis

The taxonomies in this article draw from established craft literature spanning screenwriting, novel writing, and story analysis:

| Concept | Source |
|---------|--------|
| 15-beat story structure for screenwriting | Blake Snyder, *Save the Cat!* (2005) |
| Beat sheet adaptation for novels | Jessica Brody, *Save the Cat! Writes a Novel* (2018) |
| Story Grid hierarchy and Five Commandments | Shawn Coyne, *The Story Grid* (2015) |
| Scene-Sequel structure and prose beats | Dwight V. Swain, *Techniques of the Selling Writer* (1965) |
| The Hero's Journey (monomyth) | Joseph Campbell, *The Hero with a Thousand Faces* (1949); Christopher Vogler, *The Writer's Journey* (1992) |
| Three-act structure and paradigm | Syd Field, *Screenplay: The Foundations of Screenwriting* (1979) |
| Story structure and value shifts | Robert McKee, *Story: Substance, Structure, Style, and the Principles of Screenwriting* (1997) |

Snyder's beat sheet and Coyne's Story Grid represent different philosophies —prescriptive vs diagnostic —but both provide named vocabulary for structural functions. Swain's Scene-Sequel model operates at a different scale entirely, addressing the prose-level rhythm that fills these larger structural containers. The combination of all three scales —macro (Save the Cat), meso (Story Grid), and micro (Swain) —provides the most complete structural vocabulary available.

McKee's contribution is the emphasis on value shifts as the engine of story: every scene must turn on a value (safe/endangered, loved/unloved, free/trapped), and the story's global arc is a sequence of these turns. This value-based thinking complements the beat-naming approach —once you know a beat's function (Catalyst) and its value shift (safe to endangered), you have both the structural role and the emotional content defined before writing a word of prose.

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_sequel_in_interactive_fiction|Scene and Sequel in Interactive Fiction]] —Swain's micro-level complements this macro-level taxonomy
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] —Prose-level beat types that operate below structural beats
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_structure_and_beats|Scene Structure and Beats]] —Beat integration into prose
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/try_fail_cycles_branching_fiction|Try-Fail Cycles in Branching Fiction]] —Try-fail maps to Bad Guys Close In
- [[Narrative & Game Design/Interactive Fiction/emotional-design/emotional_beats|Emotional Beats]] —Emotional peak types complement structural functions
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] —Construction methodology where beat labels guide scaffolding
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/endings_patterns|Endings Patterns]] —Final Image and resolution beats
