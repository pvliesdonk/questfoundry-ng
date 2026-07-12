---
cluster: narrative-structure
summary: Non-chronological storytelling in interactive fiction — fragment assembly,
  environmental and database narrative, reconstruction of a fixed past, reverse chronology,
  interlocking routes, and the freedom-vs-comprehension problem.
title: Nonlinear and Alternative Structures
topics:
- nonlinear-narrative
- database-narrative
- environmental-storytelling
- fragment-assembly
- in-medias-res
- reverse-chronology
- frame-narrative
- interlocking-routes
- kishotenketsu
- jo-ha-kyu
- reader-orientation
---

# Nonlinear and Alternative Structures

Craft guidance for telling stories out of chronological order — where the sequence in which information reaches the reader is disrupted, fragmented, reversed, or placed under the player's control. This is distinct from *branching choice topology* (covered in [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — that note is about *what the player decides*; this one is about *the order in which the story arrives*). Two structurally specific patterns have their own notes: [[Narrative & Game Design/Interactive Fiction/narrative-structure/time_loop_patterns|Time Loop Patterns]] and [[Narrative & Game Design/Interactive Fiction/narrative-structure/rashomon_patterns|Rashomon Patterns]]. This note covers everything else under the nonlinear umbrella.

---

## The Central Tension: Freedom vs Comprehension

Linear narrative lets the author guarantee that setup A arrives before payoff B. The moment order is disrupted — and especially the moment the *player* controls it — that guarantee is gone. Every technique below is, at root, a solution to one problem: **how to disrupt chronology without losing the reader.**

The failure modes cluster into three:

- **Confusion** — no orientation scaffolding; the reader cannot tell what they know, what they don't, or what to pursue next.
- **Incompletion** — critical information sits in an optional space the reader never reaches, so they hit an ending without the context to understand it.
- **False freedom** — the nonlinearity is cosmetic; players eventually detect that order did not really matter, and the device collapses.

The classical vocabulary for departures from story-order is Gérard Genette's: *anachrony* (any mismatch between story time and narrative time), *analepsis* (flashback) and *prolepsis* (flash-forward). It is worth knowing because it names precisely what you are doing when you break chronology.

---

## Who Controls the Order?

The first design question. **Author-fixed** nonlinearity disrupts chronology but keeps the sequence in the author's hands (reverse chronology, in medias res, a frame). **Player-controlled** nonlinearity hands the order to the reader (environmental exploration, database search, geographic routing). The orientation and comprehension problems are far sharper in the player-controlled case.

---

## Author-Fixed Techniques

### In Medias Res

Begin mid-action; deliver the prior context afterward through dialogue, documents, or flashback. The opening creates a "why" gap the reader is motivated to close. Failure mode: insufficient anchoring — the reader does not yet care about the present situation enough to be curious about its causes. *Disco Elysium* (ZA/UM, 2019) opens inside a blackout and backfills an entire life through investigation.

### Reverse Chronology

Events presented backward; the *cause* arrives after its *effect*. Most powerful when the theme is inevitability, regret, or the inescapable past — the reader's recurring "now I understand why" becomes its own beat. *Braid* (Jonathan Blow, 2008) plays its final level entirely in reverse, retroactively reframing the whole game's apparent rescue as a pursuit. Without clear temporal markers, though, the reader cannot build the forward timeline and the causal reveal fails.

### Frame and Dual-Timeline Narrative

Two timelines run concurrently — typically a past investigation and a present consequence — and the reader moves between them. The engine is dramatic irony: knowing the past while living the present (or the reverse). *Norco* (Geography of Robots, 2022) alternates a present-day protagonist with a deceased mother's timeline, assembling what happened from both ends.

### Temporal Markers and Anchors

Whatever the technique, time jumps need signposting. Clear chapter labels ("Ten years earlier"), date stamps, and formatting cues (typography or italics for a past timeline) keep the reader oriented; **object anchors** link timelines without exposition (a character touching the same scar, or a photograph, in two eras). The mechanics of moving between scenes are covered further in [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_transitions|Scene Transitions]].

---

## Player-Controlled Techniques

### Fragment Assembly (Database Narrative)

The story exists as a fixed archive of fragments; the order of encounter is the player's, and meaning accumulates rather than arriving in a designed sequence. The defining craft principle, from Sam Barlow, is **narrative robustness**: each fragment must be *multi-valent* — it must carry weight wherever in the sequence it lands. A clip that only makes sense given a prior clip creates a hard dependency that breaks for every discovery order but one, and the work silently fails for most players. *Her Story* (Sam Barlow, 2015) is the canonical case: 271 video clips surfaced by free-text search, with a five-result cap per keyword that forces players to vary their queries rather than exhaust the archive at once. (Its *unreliable multiple-account* dimension is treated in [[Narrative & Game Design/Interactive Fiction/narrative-structure/rashomon_patterns|Rashomon Patterns]]; here the focus is its database *structure*.)

### Environmental and Epistolary Storytelling

The story is embedded in a space — objects, documents, audio logs, visible damage — and the player traverses narrative by exploring. Henry Jenkins' term is **embedded narrative**: the static plot lives in the mise-en-scène and the player's path assembles it. The epistolary sub-variant embeds *communications* (letters, logs, calls), which adds a narrator layer and an implied reader. *Gone Home* (Fullbright, 2013) is the touchstone, and it models the key discipline — **tiering**: the core story sits on the mandatory path (audio journals you cannot miss), while enrichment lives in optional spaces. *Tacoma* (Fullbright, 2017) extends this with scrub-able AR recordings the player rewinds and replays to follow different characters through one event. *Analogue: A Hate Story* (Christine Love, 2012) gates its logs through an AI mediator that withholds and releases clusters.

### Hub-and-Spoke Reconstruction of a Fixed Past

The story-world is fully determined — nothing the player does changes what happened — and the player navigates that fixed past non-chronologically, reconstructing it from fragments. A spatial **hub** (a ship, a house, a station) provides orientation in the absence of a timeline: the player's knowledge of the *space* substitutes for knowledge of the *sequence*, like a memory palace. *Return of the Obra Dinn* (Lucas Pope, 2018) is the exemplar — the ship itself is the reference frame.

### Deductive Reconstruction

A sharper relative of fragment assembly: the player's task is not to *discover* information but to *conclude* from it, and the game validates the conclusions. The load-bearing element is the validation mechanism. *Obra Dinn*'s rule-of-three — no fate is confirmed until three are correctly deduced at once — prevents guessing and forces genuine cross-referential inference. Too loose and players guess; too strict and they stall. This shades into detective-genre craft; see [[Narrative & Game Design/Interactive Fiction/genre-conventions/mystery_conventions|Mystery Conventions]] for fair-play cluing.

### Geographic and Modular Nonlinearity

Space structures the narrative: regions hold different fragments, the player picks the route, and no single correct order exists. Each module must be self-contained enough to work wherever it falls yet gain meaning from its neighbours — Alexis Kennedy and Jon Ingold's "modular storytelling." Geography doubles as orientation (you always know roughly *where* you are even if not *when*). *80 Days* (inkle, 2014) routes 150-plus cities this way; its content is linear *within* a city but nonlinear in *which* cities and in what order.

### Interlocking Routes

Multiple characters' storylines reference the same events, and progress in one route gates or recolours another. *Resident Evil 2* (Capcom, 1998) coined the "zapping system": choices in Scenario A (items taken, enemies killed) alter Scenario B. *13 Sentinels: Aegis Rim* (Vanillaware, 2019) builds an entire game from thirteen interlocking nonlinear perspectives, where the protagonist of one chapter is a background figure or antagonist in another, and chapters lock until prerequisite events occur elsewhere. The craft cousin of this is hub-and-spoke convergence; see [[Narrative & Game Design/Interactive Fiction/narrative-structure/ensemble_convergence_patterns|Ensemble Convergence Patterns]].

---

## Keeping the Reader Oriented

Every player-controlled technique needs orientation scaffolding. The proven solutions:

- **Spatial anchoring** — a physical hub stands in for chronological position (the ship, the house, the station).
- **A reference document** — an in-world artefact that records progress: *Obra Dinn*'s logbook, *Her Story*'s session tags, *Outer Wilds*' ship computer. This is also diegetic design (see [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]]).
- **Geographic progression** — a reliable heuristic (e.g. further east = later/harder) that substitutes for a timeline.
- **A discovery log / evidence board** — an explicit running record of what is known.
- **Redundancy** — deliver load-bearing information through multiple independent paths so no single missed fragment breaks comprehension (the design ethos of *Outer Wilds*, whose clues systematically point at adjacent clues).
- **Soft gates and tiering** — put information that is meaningless without context behind a *soft* prerequisite (visit X before Y becomes legible) rather than a hard progression lock, and keep critical beats on the mandatory path.

The craft judgement is always: which information is load-bearing enough to protect with a gate, and which can be trusted to the player's curiosity?

---

## Parallel Narratives

When two storylines run in tandem, **write them interleaved, not separately then woven** — separate drafting produces a "silo" feel that is hard to dissolve later. Common arrangements: **alternating chapters** (a steady A/B rhythm), **braided** (switching within chapters for tighter integration), and **thematic parallel** (unrelated plots echoing one motif). Interleaving is what lets each thread comment on the other.

---

## Alternative Dramatic Structures

Not all alternatives to three-act structure are about *order* — some are different shapes of dramatic build. Two East Asian frameworks recur in IF craft:

### Kishōtenketsu

A four-act structure descended from classical Chinese *jueju* poetry: **Ki** (introduction), **Shō** (development), **Ten** (a twist — a surprising, often unrelated element that recontextualizes rather than a conflict), **Ketsu** (conclusion that reconciles the twist with the first two acts). Its engine is **juxtaposition and harmony** rather than the conflict-and-resolution of the Western three-act. It suits slice-of-life, surreal, and horror IF (where the "Ten" recontextualizes safety into danger).

### Jo-ha-kyū

A pacing concept — 序破急, roughly "beginning, break, rapid" — originating in gagaku court music and developed by the Noh playwright Zeami into a near-universal rhythm across Japanese traditional drama: begin slowly and gather potential (*jo*), accelerate and complicate (*ha*), resolve swiftly (*kyū*). It applies at any scale — a whole work, an act, or a single scene or encounter.

---

## Related Patterns

Two nonlinear forms have dedicated notes; reach for them rather than duplicating here:

- **Time loops** — diegetic repetition where the player accumulates knowledge across resets: [[Narrative & Game Design/Interactive Fiction/narrative-structure/time_loop_patterns|Time Loop Patterns]].
- **Rashomon / multiple contradictory accounts** — the same event told from conflicting perspectives, truth synthesized by the reader: [[Narrative & Game Design/Interactive Fiction/narrative-structure/rashomon_patterns|Rashomon Patterns]].

---

## Quick Reference

| Structure | Order controlled by | Orientation device | Best for |
|-----------|--------------------|--------------------|----------|
| In medias res | Author | The "why" gap | Hooks; thrillers |
| Reverse chronology | Author | Temporal markers | Inevitability, regret |
| Dual-timeline / frame | Author | Labelled threads | Dramatic irony |
| Fragment assembly / database | Player | Reference doc; robust fragments | Investigation, memory |
| Environmental / epistolary | Player | Tiered space; mandatory path | Discovery, intimacy |
| Hub-and-spoke reconstruction | Player | Spatial anchor | Fixed-past mystery |
| Geographic / modular | Player | Geography as progression | Journeys, breadth |
| Interlocking routes | Player (across routes) | Cross-route state | Ensembles, replay |
| Kishōtenketsu | Author | — | Slice-of-life, surreal, horror |

---

## Research Basis

| Concept | Source |
|---------|--------|
| Anachrony / analepsis / prolepsis (the vocabulary of non-chronological order) | Gérard Genette, *Narrative Discourse* (1980) |
| Embedded narrative; environmental storytelling | Henry Jenkins, "Game Design as Narrative Architecture" (2004) |
| Encyclopedic affordance underpinning database narrative | Janet Murray, *Hamlet on the Holodeck* (1997) |
| Narrative robustness; multi-valent fragments; the five-clip cap | Sam Barlow on *Her Story* — "Powerful Stories Require Ambiguity" (2015); *Her Story* (2015) |
| Hub-and-spoke reconstruction of a fixed past; deductive validation (rule-of-three) | Lucas Pope, *Return of the Obra Dinn* (2018) |
| Environmental/epistolary tiering (critical on the mandatory path) | Fullbright, *Gone Home* (2013); *Tacoma* (2017) |
| AI-gated epistolary release | Christine Love, *Analogue: A Hate Story* (2012) |
| Geographic / modular storytelling | inkle, *80 Days* (2014); Kennedy & Ingold, "modular storytelling" (2015) |
| Reverse chronology recontextualizing prior play | Jonathan Blow, *Braid* (2008) |
| Dual-timeline frame narrative | Geography of Robots, *Norco* (2022) |
| Redundancy as comprehension insurance | Mobius Digital, *Outer Wilds* (2019) — see [[Narrative & Game Design/Interactive Fiction/narrative-structure/time_loop_patterns|Time Loop Patterns]] |
| Interlocking routes ("zapping"); interlocking nonlinear perspectives | Capcom, *Resident Evil 2* (1998); Vanillaware, *13 Sentinels: Aegis Rim* (2019) |
| Fragment assembly in parser IF; early hypertext nonlinearity | Adam Cadre, *Photopia* (1998); Michael Joyce, *afternoon, a story* (1987) |
| Kishōtenketsu (four-act, juxtaposition over conflict) | Classical Chinese *jueju* poetic structure, adopted across East Asian narrative |
| Jo-ha-kyū (slow / break / rapid pacing) | Gagaku court music; developed by Zeami for Noh theatre |

---

## See Also

- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_construction|Branching Narrative Construction]] — choice topology (what the player decides) vs information order (this note)
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/branching_narrative_craft|Branching Narrative Craft]] — meaningful choice and state tracking
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/time_loop_patterns|Time Loop Patterns]] — diegetic repetition with knowledge accumulation
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/rashomon_patterns|Rashomon Patterns]] — contradictory multiple accounts of one event
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/scene_transitions|Scene Transitions]] — the mechanics of moving between scenes and timelines
- [[Narrative & Game Design/Interactive Fiction/genre-conventions/mystery_conventions|Mystery Conventions]] — fair-play cluing for deductive reconstruction
- [[Narrative & Game Design/Interactive Fiction/craft-foundations/diegetic_design|Diegetic Design]] — in-world reference documents as orientation
- [[Narrative & Game Design/Interactive Fiction/narrative-structure/ensemble_convergence_patterns|Ensemble Convergence Patterns]] — hub-and-spoke and parallel-thread convergence