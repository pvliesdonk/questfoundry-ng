---
title: Interactive Fiction Platform Tools
summary: Overview of major IF authoring platforms including Twine, Ink, ChoiceScript, Inform, and others with comparison and selection guidance.
topics:
  - platforms
  - tools
  - twine
  - ink
  - choicescript
  - inform
  - authoring
  - game-engines
cluster: craft-foundations
---

# Interactive Fiction Platform Tools

Craft guidance for selecting and understanding IF authoring platforms—Twine, Ink, ChoiceScript, Inform, and alternatives with trade-off analysis.

---

## Platform Landscape

### Categories of IF Tools

| Category | Examples | Best For |
|----------|----------|----------|
| Visual/Node-based | Twine, Yarn Spinner | Writers, rapid prototyping |
| Scripting languages | Ink, ChoiceScript | Game integration, complex state |
| Parser-based | Inform, TADS | Traditional IF, puzzles |
| Game engine plugins | Ink+Unity, Yarn+Godot | Commercial games |
| Hybrid platforms | Ren'Py, Fungus | Visual novels |

### Selection Criteria

Key questions for platform selection:

1. **Technical skill level** — How much coding is acceptable?
2. **Target platform** — Web, mobile, game engine, standalone?
3. **Complexity needs** — Simple branching or complex state?
4. **Publishing path** — Self-publish or through platform?
5. **Customization** — Default styling or full control?
6. **Collaboration** — Solo or team workflow?

---

## Twine

### Overview

Twine is an open-source tool for creating interactive, nonlinear stories without coding requirements. It uses a visual node-based editor where passages appear as connected boxes.

**Current version:** 2.x (as of 2025)

### Strengths

- **No code required** for basic stories
- **Visual flowchart** shows structure at a glance
- **Publishes to HTML** — works anywhere
- **Multiple story formats** (Harlowe, SugarCube, Snowman)
- **Extensible** with CSS, JavaScript
- **Free and open-source**

### Limitations

- **Self-publishing only** — no built-in distribution
- **Scaling challenges** with very large projects
- **Format fragmentation** — different formats have different syntax
- **Limited collaboration** support natively

### Story Formats

| Format | Approach | Best For |
|--------|----------|----------|
| Harlowe | Beginner-friendly, macro-based | New authors, simple projects |
| SugarCube | Feature-rich, JavaScript-compatible | Complex projects, customization |
| Snowman | Minimal, JavaScript-first | Developers, total control |
| Chapbook | Clean, readable syntax | Narrative focus |

### Basic Syntax (Harlowe)

```
:: Start
You stand at a crossroads.

[[Go north->North Path]]
[[Go south->South Path]]

:: North Path
The path leads to a forest.

(set: $visited_forest to true)
[[Continue->Forest]]
```

### When to Choose Twine

- Learning IF authoring
- Rapid prototyping
- Web-first distribution
- Writers with minimal coding background
- Projects where visual structure helps

---

## Ink

### Overview

Ink is a narrative scripting language developed by Inkle Studios (creators of *80 Days*, *Heaven's Vault*). Designed for game engine integration, especially Unity.

### Strengths

- **Game engine integration** — built for Unity, Unreal plugins exist
- **Clean, readable syntax** — text-first approach
- **Powerful conditionals** — complex logic without clutter
- **Professional pedigree** — proven in commercial titles
- **Inky editor** — dedicated authoring environment
- **Free and open-source**

### Limitations

- **Requires integration** — doesn't publish standalone easily
- **Steeper learning curve** than Twine
- **Less visual** — no node graph view
- **External presentation** — you build the UI separately

### Basic Syntax

```ink
=== intro ===
You stand at a crossroads.

* [Go north]
    -> north_path
* [Go south]
    -> south_path

=== north_path ===
The path leads to a forest.
~ visited_forest = true
-> forest

=== forest ===
{visited_forest: The familiar trees welcome you back.|You enter the unknown woods.}
```

### Key Features

**Weaves:** Inline content flow without explicit jumps
**Knots and stitches:** Hierarchical content organization
**Conditional text:** `{condition: text if true|text if false}`
**Tunnels:** Reusable content chunks
**Variables and logic:** Full programming capabilities

### When to Choose Ink

- Building a game with narrative elements
- Unity or Unreal as target platform
- Need complex state management
- Professional/commercial projects
- Programmers comfortable with scripting

---

## ChoiceScript

### Overview

ChoiceScript is Choice of Games' proprietary scripting language for choice-based interactive fiction. Simple syntax focused on branching narratives.

### Strengths

- **Extremely accessible** — minimal coding knowledge required
- **Built-in publishing** — Hosted Games/Choice of Games stores
- **Proven market** — established audience
- **Testing tools** — quicktest, randomtest for validation
- **Consistent UI** — readers know the format

### Limitations

- **Publishing requirement** — must go through CoG/Hosted Games
- **Limited customization** — standardized presentation
- **Revenue sharing** — platform takes percentage
- **Content guidelines** — must follow CoG standards

### Basic Syntax

```
*label start
You stand at a crossroads.

*choice
    #Go north.
        *goto north_path
    #Go south.
        *goto south_path

*label north_path
The path leads to a forest.
*set visited_forest true
*goto forest
```

### Testing Tools

**quicktest:** Syntax validation, missing label detection
**randomtest:** Plays through randomized paths to find reachability issues

```bash
# Run quicktest
java -jar quicktest.jar mygame/

# Run randomtest (1000 iterations)
java -jar randomtest.jar mygame/ 1000
```

### When to Choose ChoiceScript

- Want established distribution channel
- Comfortable with revenue sharing
- Writing text-heavy, choice-focused IF
- Prefer minimal technical overhead
- Content fits CoG guidelines

---

## Inform

### Overview

Inform is a design system for interactive fiction based on natural language. Inform 7 uses English-like syntax; Inform 6 is more traditional.

### Strengths

- **Natural language** — reads almost like prose
- **Parser-based IF** — traditional "type commands" interaction
- **Powerful world modeling** — objects, rooms, relationships
- **Mature ecosystem** — decades of development
- **IFComp standard** — traditional IF competition platform

### Limitations

- **Steep learning curve** — natural language has quirks
- **Parser baggage** — players must learn commands
- **Different audience** — parser IF is niche
- **Compilation complexity** — debugging can be difficult

### Basic Syntax (Inform 7)

```inform7
"My First Game" by Author Name

The Crossroads is a room. "You stand at a crossroads.
Paths lead north and south."

North of the Crossroads is the Forest.
South of the Crossroads is the Village.

The Forest is a room. "Tall trees surround you."

visited_forest is a truth state that varies.

After going to the Forest:
    now visited_forest is true;
    continue the action.
```

### When to Choose Inform

- Creating parser-based interactive fiction
- World-modeling is central to gameplay
- Traditional IF audience (IFComp, etc.)
- Complex object/puzzle interactions
- Appreciate natural language programming

---

## Other Notable Platforms

### Ren'Py

**Type:** Visual novel engine
**Language:** Python-based
**Best for:** Visual novels, anime-style games
**Note:** Strong on visuals, character sprites, scene management

### TADS

**Type:** Parser IF system
**Best for:** Traditional IF with complex world models
**Note:** More programming-oriented than Inform

### Yarn Spinner

**Type:** Dialogue system
**Best for:** Unity games needing branching dialogue
**Note:** Lighter than Ink, focused specifically on dialogue

### Fungus

**Type:** Unity visual scripting
**Best for:** Unity developers wanting visual flowcharts
**Note:** Node-based, no coding required

### Quest

**Type:** Parser/choice hybrid
**Best for:** Beginners wanting parser IF
**Note:** Both desktop app and web versions

---

## Platform Comparison

### Technical Complexity

| Platform | Coding Required | Learning Curve |
|----------|-----------------|----------------|
| Twine (Harlowe) | None | Low |
| ChoiceScript | Minimal | Low |
| Twine (SugarCube) | Some | Medium |
| Ink | Moderate | Medium |
| Inform 7 | Moderate | Medium-High |
| Ren'Py | Python knowledge | Medium |

### Publishing Options

| Platform | Self-Publish | Platform Store | Game Engine |
|----------|--------------|----------------|-------------|
| Twine | ✓ HTML | itch.io | — |
| Ink | Via engine | Via engine | Unity, Unreal |
| ChoiceScript | — | CoG/Hosted | — |
| Inform | ✓ z-machine | IFDB | — |
| Ren'Py | ✓ standalone | Steam, itch.io | — |

### Feature Strengths

| Feature | Best Platform |
|---------|---------------|
| Quick prototyping | Twine |
| Game engine integration | Ink |
| Established distribution | ChoiceScript |
| Parser puzzles | Inform |
| Visual novels | Ren'Py |
| Complex state | Ink, SugarCube |
| Accessibility | Twine, ChoiceScript |

---

## Migration Considerations

### Between Platforms

Migration is generally difficult:

- **Syntax incompatible** — no direct translation
- **Features differ** — may lose capabilities
- **Presentation changes** — look/feel shifts

### Strategies

1. **Start with outline** — platform-agnostic story structure
2. **Prototype in Twine** — validate concept
3. **Production in final platform** — rebuild for target
4. **Export narrative** — keep text, rebuild logic

### Avoiding Lock-in

- Keep story content in separate documents
- Document state/variable systems
- Maintain non-technical story bible
- Consider future scaling needs before starting

---

## Quick Reference

| Need | Recommended Platform |
|------|---------------------|
| First IF project | Twine (Harlowe) |
| Commercial game | Ink + Unity |
| Text-heavy, published | ChoiceScript |
| Parser IF | Inform 7 |
| Visual novel | Ren'Py |
| Rapid prototype | Twine |
| Complex branching | Ink or SugarCube |

---

## Research Basis

Platform documentation and analysis sources:

| Platform | Source |
|---------|--------|
| Twine | twinery.org official documentation |
| Ink | Inkle Studios, github.com/inkle/ink |
| ChoiceScript | Choice of Games, choiceofgames.com |
| Inform | Inform 7 documentation, inform7.com |
| Comparison | Emily Short's Interactive Storytelling blog |

Emily Short's craft essays, particularly "Choice-Based Narrative Tools" series, provide extensive platform analysis from a practitioner perspective.

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — Structure techniques
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/testing_interactive_fiction|Testing Interactive Fiction]] — QA for IF
- [[Narrative & Game Design/Interactive Fiction/scope-and-planning/scope_and_length|Scope and Length]] — Platform affects scope
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/quality_standards_if|Quality Standards IF]] — Validation criteria
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/player_analytics_metrics|Player Analytics Metrics]] — Platform analytics options
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/audio_visual_integration|Audio-Visual Integration]] -- per-platform AV capabilities (Twine HTML5 audio vs Ink+Unity middleware)
