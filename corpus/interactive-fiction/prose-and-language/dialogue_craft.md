---
title: Dialogue Craft for Interactive Fiction
summary: Writing compelling dialogue with character voice, subtext, natural exposition, and effective tagging techniques.
topics:
  - dialogue
  - character-voice
  - subtext
  - exposition
  - dialogue-tags
  - verbal-tics
  - speech-patterns
cluster: prose-and-language
---

# Dialogue Craft for Interactive Fiction

Craft guidance for writing compelling dialogue—character voice, subtext, natural exposition, and effective tagging.

---

## Character Voice

### Making Each Character Sound Distinct

Every character needs their own unique way of speaking that instantly identifies them. A gruff ex-military type won't speak the same way as a bubbly teen, and a professor won't phrase things like a street performer.

### The Voice Profile

Before writing dialogue, consider each character's:

- **Vocabulary range** (complex or simple?)
- **Sentence length** (clipped or elaborate?)
- **Formality level** (formal or casual?)
- **Use of contractions** (won't vs will not)
- **Verbal tics** (repeated words, filler sounds)
- **Metaphorical vs literal** speech

### Speech Pattern Framework

Map characters along these axes:

1. **Simple vs Complex** vocabulary
2. **Succinct vs Colorful** expression
3. **Slang vs Conventional** grammar
4. **Straightforward vs Clever** delivery

Example contrast:
> Anxious character: "I don't know. Maybe. Could be dangerous."
>
> Confident character: "I've analyzed the situation thoroughly. This is clearly the optimal approach."

### Verbal Tics and Catchphrases

Repetitive phrases can become character trademarks. Gatsby's "old sport" appears over 40 times in *The Great Gatsby*, revealing both his charm and his constructed identity—a borrowed affectation that hints at the facade.

Use sparingly to avoid reader irritation. One or two defining tics per character is enough.

### The No-Tag Test

Read a dialogue scene aloud without any tags. Can you tell who's speaking based solely on their voice? If not, the voices need more distinction.

---

## Subtext

### What Characters Mean vs What They Say

Subtext is the unspoken message beneath words—the gap between what people say and what they're thinking. In real life, we rarely say exactly what we mean. Fiction should reflect this.

### Why Subtext Matters

While audiences connect with characters based on what they say, subtext allows deeper connection. When readers decode the unspoken, they become active participants rather than passive observers.

### Creating Subtext

**Through Body Language:**
> "I'm fine." She wouldn't meet his eyes, arms crossed tight against her chest.

The words say "fine." Everything else screams the opposite.

**Through Silence:**
> "Will you help me?"
>
> A long pause. The clock ticked. Finally: "I'll think about it."

The pause says more than the words.

**Through Conflicting Desires:**
One character wants something the other won't give. The unspoken desire drives tension.

### Good vs Bad Examples

Bad (On-the-Nose):
> "I'm so angry at you right now! You betrayed me and I'll never trust you again!"

Good (With Subtext):
> "That's interesting." She turned away, adjusting curtains that didn't need adjusting. "I suppose everyone has their own definition of loyalty."

Bad (Melodramatic):
> "I love you."
> "No, not as much as I love you."

Good (With Tension):
> "You should probably go."
> "Is that what you want?"
> "It's late."

---

## Exposition Through Dialogue

### The "As You Know, Bob" Trap

The cardinal sin: characters telling each other things they already know for the reader's benefit.

Bad:
> "As you know, Sarah, we've been working together at the hospital for five years, ever since we both graduated from medical school."

This is an info dump disguised as dialogue, and it doesn't fool anyone.

### The Golden Rule

Dialogue is always from one character to another. It can't sound like you're manipulating it for the reader, even though you are. It must be what a character would naturally say.

### Natural Exposition Techniques

**Use a Newcomer:**
A character new to the situation can naturally ask questions. Harry Potter learns about the magical world alongside the reader.

**Use Conflict:**
Characters in disagreement naturally explain their positions.

Bad (Info Dump):
> "The Artifact was created three centuries ago by the Mage Council to prevent the Dark War. It has three powers..."

Good (Through Conflict):
> "You're not actually going to give it to him?"
> "What choice do I have? You saw what he did to the village."
> "But if he learns to manipulate time—"
> "I know what it can do. I've spent three years studying it."

**Use Discovery:**
Characters learn information in real-time. Reader discovers alongside them.

### Warning Signs of Info Dumps

- Characters using each other's names constantly
- Overly detailed explanations of shared knowledge
- Formal, speech-like delivery ("As I'm sure you're aware...")
- Long monologues without interruption
- "As you know..." or "Remember when..."

---

## Dialogue Tags and Beats

### The Case for "Said"

"Said" functions as an invisible word—a principle championed by Elmore Leonard ("Never use a verb other than 'said' to carry dialogue") and widely taught in craft workshops. Because of its ubiquity, it disappears into the prose while fancier alternatives draw attention to themselves.

**Rule of thumb:** 80% of your dialogue tags should use "said."

### Said-Bookisms to Avoid

Fancy dialogue tags result in purple prose:

Bad:
> "I can't believe it!" she ejaculated.
> "Consider the evidence," he pontificated.
> "You're wrong," she hissed. (Can't hiss words without sibilants)

Use alternatives sparingly and only when they add essential information:

- "Whispered" (volume)
- "Shouted" (volume)
- "Asked" (with questions)
- "Muttered" (delivery)

### Action Beats: The Superior Alternative

Action beats often work better than creative tags because they show rather than tell.

Instead of:
> "Get out of my office," he said angrily.

Better:
> He slammed his fists on the desk. "Get out of my office."

### Punctuation Rules

**With Dialogue Tags (speech verbs):**
> "I don't know," she said.

Comma before closing quote. Don't capitalize after.

**With Action Beats (no speech verb):**
> "I don't know." She turned away.

Period to finish dialogue. Capitalize after—it's a new sentence.

### Using Tags for Pacing

**Fast-Paced (minimal tags):**
> "Where is it?"
> "I don't know."
> "Don't lie to me."
> "I'm not."

**Slow-Paced (beats add reflection):**
> "Where is it?" He leaned against the doorframe, studying her face.
>
> She looked down at her hands. "I don't know."
>
> He waited, letting silence stretch between them. "Don't lie to me."

### Action Beats as Emotional Indicators

> "I'm fine." She twisted her wedding ring around her finger. (anxiety)
>
> "Nothing happened." He wouldn't meet her eyes. (deception)
>
> She crossed her arms. "I'm not backing down." (confidence)

---

## Dialogue in Interactive Fiction

### Conversation Branching

IF dialogue often branches based on player choice. Design for:

**The hub pattern:**

Player returns to central dialogue node after exploring topics.

```
NPC: "What would you like to know?"
├── "Tell me about the village" → [info] → return to hub
├── "What happened last night?" → [info] → return to hub
└── "Never mind" → exit conversation
```

**The track pattern:**

Choices advance conversation forward, no return.

```
NPC: "Are you with the resistance?"
├── "Yes" → [committed to resistance track]
├── "No" → [suspected as enemy]
└── "That depends" → [more questions, then choice again]
```

**The variable pattern:**

Dialogue changes based on accumulated state.

```
[if relationship >= 5]: "It's good to see you again, friend."
[if relationship < 5]: "What do you want?"
```

### Dialogue in Choice Text

When choices ARE dialogue (player speaking):

**Write as the character would speak:**

Good:
> "I don't think that's a good idea."
> "Let's do this."
> "Tell me more about the artifact."

Bad:
> Ask about the artifact
> Express doubt about the plan
> Agree enthusiastically

The bad examples are instructions; the good examples are speech.

**Exception:** Very long spoken choices may need summarization:

> [Tell her about your encounter with the stranger]

This works when the actual dialogue would be too long for choice text.

### NPC Dialogue Consistency

NPCs must speak consistently across all branches:

**Track what NPCs know:**

- What has player told them?
- What have they witnessed?
- What have other NPCs told them?

**Common errors:**

- NPC asks question player already answered
- NPC references event that didn't happen on this path
- NPC's mood doesn't match player's last interaction

**Solution:** State-based dialogue with clear conditions.

### Revealing Character Through Choice Structure

How dialogue is structured reveals character:

**Terse character:**

> "Yes."
> "No."
> "Maybe."

**Elaborate character:**

> "Well, I suppose if we consider all the factors, one might conclude..."
> "Absolutely not, and I'll tell you why—"
> "It's complicated. Let me explain."

Match choice text length to character voice.

---

## Common Mistakes

### All Characters Sound the Same

If you could pull a line from anywhere and not know which character said it, the voices are too similar. Each character needs identifiable patterns.

### Overusing Names

Real people don't use each other's names constantly in conversation. Only use names when getting attention or emphasizing a point.

### Dialogue Without Purpose

Every line should advance plot, develop character, or both. Phone calls and dinners that don't contribute to the story don't belong in fiction.

### The Read-Aloud Test

Read dialogue aloud. If it sounds awkward, it is awkward. Real speech has rhythm and flow that's easy to hear but hard to see on the page.

---

## Quick Reference

| Goal | Technique |
|------|-----------|
| Distinct voices | Speech profile per character |
| Subtext | Gap between said and meant |
| Natural exposition | Conflict, discovery, newcomer |
| Attribution | "Said" + action beats |
| Fast pace | Minimal tags |
| Slow pace | Beats between lines |
| Emotional reveals | Actions contradict words |

---

## Research Basis

Key sources on dialogue craft:

| Concept | Source |
|---------|--------|
| "Said" as invisible | Elmore Leonard, "10 Rules of Writing" (2001); Stephen King, *On Writing* (2000) |
| Subtext in dialogue | Robert McKee, *Dialogue* (2016) |
| "As You Know, Bob" trap | Turkey City Lexicon (1988), science fiction workshop critique vocabulary |
| Action beats | Sol Stein, *Stein on Writing* (1995) |

The "said is invisible" principle has empirical support: readers process common dialogue tags faster than unusual ones, maintaining immersion. Leonard's dictum is intentionally extreme—occasional variation serves purpose, but "said" should dominate.

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/prose-and-language/prose_patterns|Prose Patterns]] — Sentence-level craft and rhythm around dialogue
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] — Player-facing content standards
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/character_voice|Character Voice]] — Distinctive voices for each character
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/subtext_and_implication|Subtext and Implication]] — What's said beneath the surface
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/pacing_and_tension|Pacing and Tension]] — Using dialogue for pacing control
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/exposition_techniques|Exposition Techniques]] — Revealing information through dialogue
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/voice_register_consistency|Voice and Register Consistency]] -- register management within and between speakers
- [[Narrative & Game Design/Interactive Fiction/prose-and-language/narrative_point_of_view|Narrative Point of View]] -- whose perspective frames the dialogue and what they can perceive
