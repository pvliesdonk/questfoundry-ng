---
cluster: genre-conventions
summary: Genre craft for children's and YA interactive fiction — age-band distinctions,
  the archetypes (Chosen One, Found Family, the Absent Adult), coming-of-age structure,
  children's-IF design, and the gamebook lineage.
title: Children and YA Genre Conventions
topics:
- children-fiction
- young-adult
- middle-grade
- age-bands
- tropes
- coming-of-age
- school-setting
- found-family
- chosen-one
- gamebooks
- agency
- content-ratings
---

# Children and YA Genre Conventions

Genre craft for writing interactive fiction aimed at children and teenagers — the archetypes and structures the genres run on, how the conventions shift across age bands, and what the interactive medium adds. This note is the *genre* companion to [[Narrative & Game Design/Interactive Fiction/audience-and-access/audience_targeting|Audience Targeting]], which holds the mechanical craft (reading level, vocabulary, sentence length, choice complexity, fail-state policy by age). Read that note for the dials; read this one for the conventions those dials serve.

---

## The Age Bands

Children's publishing divides into bands that are not marketing buckets but reflect real differences in reading level, cognitive development, and a protagonist's relationship to home and the wider world. The craft distinctions that matter for genre:

| Band | Reader ages | Protagonist ages | Romance | Violence | Darkness & endings | Voice |
|------|-------------|------------------|---------|----------|--------------------|-------|
| **Early / chapter** | 5–9 | 5–9 | None | Slapstick only | Mild fear that resolves; hope required | Earnest, concrete |
| **Middle grade** | 8–12 | 10–13 | Crushes only | Action, no graphic detail | Death possible if handled with hope; order restored | Observant, earnest |
| **Lower YA** | 12–15 | 14–16 | Love, intensity; physical implied | Visceral, not gratuitous | Meaningful death, mental health, injustice; bittersweet | Introspective, first-person-leaning |
| **Upper YA** | 15–18 | 16–18 | Sexuality present, not explicit | Graphic where earned | Full range bar erotica; world may change for good | Introspective, sometimes cynical |

> [!tip] The two orientations
> The cleanest organizing principle for the MG/YA divide: **middle-grade protagonists discover who they are in relation to home and community; YA protagonists leave home — literally or figuratively — to discover who they are in relation to the wider world.** Almost every other difference (stakes, romance, darkness, ending tone) follows from this one.

For the per-band vocabulary, sentence-length, reading-level (Flesch-Kincaid), choice-count, consequence-delay, and fail-state tables, see [[Narrative & Game Design/Interactive Fiction/audience-and-access/audience_targeting|Audience Targeting]]. This note does not repeat them.

---

## Core Principles

### Write at Full Quality

The cardinal rule of YA, from editors of the genre: **never simplify the language, story, or craft.** Writing for teens is not writing *down*. The vocabulary ceiling is absent; the register is contemporary and character-appropriate. What changes between adult and YA fiction is *perspective and subject*, not *quality*. The same holds for middle grade: simpler sentences, never simpler thinking.

### Don't Condescend, Don't Moralize

Teens detect condescension and moralizing instantly, and both break the fictional dream. Never set a protagonist up for a fall purely to teach a lesson; never mark the "right" choice with moral framing. The story demonstrates; it does not lecture. In IF this is sharper than in prose, because a choice with a visibly "correct" answer is not a choice — it is a quiz. Meaning should emerge from consequence, not from narration.

### The In-the-Moment Voice

YA delivers the protagonist's experience *as they live it*, not filtered through an adult's retrospective wisdom. The reader is inside the character with full emotional access — first person and second person both achieve this; third-person omniscient rarely fits the genre's intimacy. For IF, second-person present tense ("You shoulder the door open") is a natural servant of this convention, but only if the choice text keeps the teen's immediacy rather than lapsing into neutral-observer voice.

### Agency as Empowerment

The medium's strongest feature with young audiences is genuine agency: the felt sense that the reader's choice matters. For children especially this is not a stylistic flourish but the value proposition — *you are not watching the hero, you are the hero.* This is why the children's gamebook tradition is overwhelmingly second-person, and why the cardinal sin is letting an adult character make the consequential choice the player should own.

---

## Key Archetypes

### The Chosen One (Reimagined)

A classic fantasy trope, but in MG/YA it specifically dramatizes **adolescent empowerment**.

- **MG version:** wonder and wish-fulfilment. "I am special." The discovery that the world is bigger and you matter in it.
- **YA version:** burden and responsibility. "Why me? I didn't ask for this." The discovery that mattering carries cost.

Variations: the **Unchosen One** (the overlooked sidekick who must step up — resonant for teens who feel passed over); the **Chosen Who Chooses Differently** (accepts the power, rejects the scripted path); the **Reluctant Inheritor** (legacy and inherited expectation reframed as fantasy); the **Anti-Chosen** (discovers they are the prophesied villain). For IF, let players define what "chosen" means through choices — accept destiny, rewrite it, or reject it. The explicitly *unchosen* path can be the most compelling interactive storyline.

### The Absent Adult

Young protagonists need agency, so adults are removed or neutralized. The **Orphan** (freedom through loss); the **Clueless Parent** (loving but ignorant of the stakes, generating the guilt of secrecy); the **Antagonistic Authority** (adults as oppressive system, the engine of dystopian YA); the **Failing Adult** (overwhelmed, sees the danger but cannot shield the child — more realistic than incompetence); the **Absent-by-Choice** (abandonment as the wound driving the need to prove oneself). In IF, adult absence is what *creates the space* for player agency. An adult who returns mid-story forces a real choice: accept authority again, or hold onto independence.

### The Found Family

The core emotional anchor of YA: belonging discovered not in blood but in a ragtag group. Variations: the **Reluctant Assembly** (circumstance forces them together; bonds form through shared ordeal); the **Fractured Family** (breaks mid-story; reassembly is earned, not guaranteed); the **Toxic Found Family** (belonging that is also entrapment — the protagonist must tell the difference); the **Expanding Circle** (grows by accumulation, each member shifting the dynamic). For IF, found-family members should hold *individual* relationships with the player, not just group membership — and betrayal hits hardest when the player chose to trust.

### The Rival

Growth through competition and comparison. The **Academic Rival** (mirrors the protagonist's ambition); the **Social Rival** (emotional, not material stakes); the **Rival Who Becomes the Friend** (competition revealing mutual respect); the **Rival Who Was Right** (growth requires admitting the enemy held the correct position).

### The Mentor

Complicated in YA by adolescent suspicion of adult authority. The **Cool Teacher** (the adult who "gets it" — at risk of an idealization the story must eventually complicate); the **Older Student** (a peer only slightly ahead, relatable and fallible); the **Reluctant Guide** (whose refusal forces the protagonist to earn guidance); the **Mentor Who Betrays** (devastating, because it confirms the adolescent fear that adults cannot be trusted).

---

## Narrative Structures

### Coming of Age (Bildungsroman)

The journey from innocence to experience: status quo (childlike dependence) → inciting incident (separation from safety) → trials (skill, failure, growing understanding of complexity) → resolution (return as a more independent self). In IF, the protagonist's *choices* should visibly accumulate into the person they become — the structural cousin of the moral portrait in [[Narrative & Game Design/Interactive Fiction/narrative-structure/moral_dilemma_chains|Moral Dilemma Chains]].

### The School Setting

A microcosm of society. **Sortings / factions** define identity fast (houses, cliques). The **academic year** provides natural pacing (term start, holidays, finals as climax). The **dual life** — balancing homework with saving the world — is the engine of tension.

### The Masquerade

Common in urban-fantasy YA: a hidden world overlapping the mundane, and the strain of keeping the secret from parents and friends. The masquerade frequently works as metaphor for the *secret self* (queer identity, neurodivergence) finding community — which is why "the reveal" lands with such emotional force.

---

## Content Boundaries

Boundaries escalate by band (romance from crushes to implied intimacy; violence from bloodless to earned-and-visceral; darkness from "resolves with hope" to "world genuinely changes"). Two craft notes:

- **The safe scare.** Children's horror — the Goosebumps model — is frightening enough to thrill but never genuinely traumatic: bad outcomes are brief, sometimes comic, and free of death, drugs, or depravity. The scare is real; the harm is not.
- **Dark themes earn their place through truth, not shock.** Death, injustice, mental illness belong in YA when they are emotionally honest; they fail when they are edgy for its own sake. In IF, a dark consequence branch must read as the natural result of character and situation, not as punishment for a player's choice.

Ratings frameworks form the practical outer boundary: **ESRB** E10+ maps roughly to upper-MG and **T (Teen, 13+)** to lower-YA content; **PEGI** 7/12 are the corresponding European tiers; **COPPA** sets a hard line at under-13 for any product collecting data or offering accounts (why teen IF apps gate at 13+); and **Common Sense Media**'s recommended ages (usually 1–3 years above official ratings) are the benchmark school and library gatekeepers actually use. For the content-by-age detail, again see [[Narrative & Game Design/Interactive Fiction/audience-and-access/audience_targeting|Audience Targeting]].

---

## Designing Children's and YA Interactive Fiction

- **Second person as empowerment.** The gamebook tradition is built on "You open the door" because it puts the young reader inside the protagonist's body. Use it deliberately, not by default.
- **Calibrate fail states to the band.** None for early readers (all paths are valid exploration); gentle and framed as learning for chapter/MG (a bad outcome should be *narratively meaningful*, with a way back into the story); meaningful but not arbitrary for YA. Never an abrupt punitive stop for the youngest bands.
- **Keep consequences traceable.** Younger players cannot hold long causal chains; keep branches from diverging so far that a consequence loses its visible cause. (The per-band consequence-delay figures live in [[Narrative & Game Design/Interactive Fiction/audience-and-access/audience_targeting|Audience Targeting]].)
- **A stat layer can make agency perceptible.** *Fighting Fantasy* added Skill/Stamina/Luck to the gamebook; *Psy High* tracks interlocking systems (money, grades, relationships). Visible state helps young players feel their choices register — keep it simple for MG, richer for YA.
- **Solve the fixed-protagonist-vs-projection tension.** YA wants a specific, opinionated voice; choice-based IF tends toward a blank protagonist for player projection. *Birdland* resolves this with a dream/waking structure: low-stakes dream choices let the player experiment with identity without permanent consequence — a structurally elegant fit for adolescent self-definition.
- **Mind the rating-versus-reality gap.** Mass-market teen apps (*Episode*, *Choices*) show how nominal age ratings can drift from actual content, and how premium-choice monetization gates the "best" outcomes behind payment — a real ethical and craft constraint when the audience is young.

---

## Writing Dystopian YA

**Core convention: the personal is political.** The teen's rebellion against strict rules mirrors the internal rebellion against the constraints of childhood, so the external regime and the internal coming-of-age are the same arc. The genre's signature **love triangle** is rarely just romance — it externalizes a choice between two futures or ideologies (safe tradition vs. dangerous freedom). Make both options genuinely tempting and the romance does structural work.

---

## Quick Reference

| Convention | Purpose |
|------------|---------|
| The two orientations | MG discovers self at home; YA leaves home — derive other choices from this |
| The Sorting | Rapid identity definition (house, clique, faction) |
| The Absent Adult | Clears space for protagonist (player) agency |
| Found Family | The emotional anchor; give each member an individual bond |
| First love | High stakes; everything feels new and intense |
| The Rebellion | Externalizes the internal teen struggle for autonomy |
| Second person | Empowerment — the young reader *is* the hero |
| The safe scare | Thrill without trauma for younger bands |
| No didacticism | Demonstrate through consequence; never mark the "right" choice |

---

## Research Basis

| Concept | Source |
|---------|--------|
| Age-band norms (protagonist age, word count, MG-vs-YA craft) | Publishing guides — Reedsy, Writer's Digest, Book Riot, SCBWI categories |
| YA craft principles (full quality, in-the-moment voice, purposeful darkness, no didacticism) | Reedsy "Writing Young Adult" (editor Kate Angelella; agent Melissa Nasson) |
| Foundational second-person gamebook format; multiple endings | *Choose Your Own Adventure* — Edward Packard & R.A. Montgomery, Bantam Books (1979–1998) |
| Stat layer over the gamebook (Skill/Stamina/Luck) | *Fighting Fantasy* — Steve Jackson & Ian Livingstone, Puffin Books (1982–) |
| The "safe scare" — horror without trauma for ages 8–12 | *Give Yourself Goosebumps* — R.L. Stine, Scholastic (1995–2000) |
| Didactic balance: curriculum through choice consequence, not narration | *The Oregon Trail* — MECC (1971; classroom standard from mid-1980s) |
| YA ChoiceScript with interlocking consequence systems | *Psy High* — Rebecca Slitt, Choice of Games (2014) |
| Dream/waking structure for identity experimentation | *Birdland* — Brendan Patrick Hennessy, Twine (2015; multiple XYZZY Awards) |
| Tone aligned to demographic (originally T-rated, rewritten to E10+) | *Minecraft: Story Mode* — Telltale Games (2015) |
| Rating-versus-content gap; premium-choice monetization caution | *Episode* (Episode Interactive, 2016); *Choices: Stories You Play* (Pixelberry, 2017) |
| Content rating frameworks (outer boundary) | ESRB; PEGI; COPPA (US, under-13); Common Sense Media (gatekeeper benchmark) |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/audience-and-access/audience_targeting|Audience Targeting]] — the mechanical companion: reading level, vocabulary, choice complexity, fail-state policy by age (this note does not duplicate it)
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/fantasy_conventions|Fantasy Conventions]] — the genre MG/YA most often borrows (chosen one, quest, magic systems)
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/horror_conventions|Horror Conventions]] — the "safe scare" and age-appropriate dread
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/romance_and_relationships|Romance and Relationships]] — romance limits and handling by age band
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/moral_dilemma_chains|Moral Dilemma Chains]] — YA moral ambiguity and the accumulated-choice portrait
- [[Narrative & Game Design/Interactive Fiction/world-and-setting/worldbuilding_patterns|Worldbuilding Patterns]] — building the school, the masquerade, the dystopia