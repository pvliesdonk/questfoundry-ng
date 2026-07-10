# QuestFoundry NG

**QuestFoundry NG turns a one-paragraph premise into a complete, playable
interactive-fiction gamebook** — branching prose, meaningful choices,
illustrations briefs, and exports to Twine, HTML, JSON, and a print-ready
"turn to page 47" PDF.

It is a *pipeline*, not a chatbot. The story is built in staged passes —
each pass produced by an LLM under strict structural control, validated by
a deterministic engine, and reviewable by a human author before the next
pass begins. The result is a story where every playthrough is complete and
coherent, and every choice leaves a mark.

```
 premise ──▶ DREAM ──▶ BRAINSTORM ──▶ SEED ──▶ GROW ──▶ POLISH ──▶ FILL ──▶ DRESS ──▶ SHIP ──▶ playable gamebook
             vision     cast &         paths    beat     passage    prose    art &      twee/html/
                        dilemmas       & beats  DAG      graph               codex      json/pdf
```

## Why this is hard, and how we solve it

Ten binary choices means a thousand possible journeys. Naïve branching
explodes; naïve merging makes choices meaningless. QuestFoundry NG controls
the explosion *structurally*: stories branch on **dilemmas** (binary
dramatic questions), the backbone dilemmas commit late (keeping most
content shared), the subplot dilemmas reconverge (bounding their cost), and
**residue** — flags, entity overlays, mood beats, variant passages — keeps
every choice alive in the prose without multiplying the whole book.

LLMs are creative but structurally unreliable, so the division of labor is
strict: **LLMs propose, the engine disposes.** Every model output is a
typed proposal validated against graph invariants before it can mutate the
story. A broken structure is rejected at the gate where it is cheapest to
fix, never discovered mid-prose.

## Status

✅ **M5 — DRESS, print, and finish (complete).** All eight stages run:
`qf run --to dress` takes a one-paragraph premise through prose to
art direction, illustration briefs, a spoiler-safe in-world codex, and
print codewords — and `qf export pdf` compiles a real gamebook: numbered
sections in seeded anti-spoiler order, "*Write down the codeword
CONFESSED*" / "*If you have CONFESSED, turn to 5*" play, a codeword log
page, the codex as an appendix, and an ending index. `qf rerun <stage>
--keep <pass>` regenerates a stage from its predecessor's checkpoint
while re-applying kept passes for free. Under it sit M4 (FILL, HTML/
Twee/JSON exports), M3 (passage compilation, `qf play`), M2 (the weave),
M1 (stage runner, LLM adapter), and the M0 foundation. Multi-hard
weaving landed and ran live: hard forks nest, every beat after the first
fork is instantiated per world, and endings multiply (2 hard → 4
endings). The first `medium`-scope story — ["The Bubblegum
Alibi"](examples/bubblegum-alibi/), a closed-circle murder mystery in a
bubblegum high school — generated end-to-end for ~$3.25: 46 beats in
two worlds, 20 passages, 16 arcs, 4 endings, full enrichment, every
export round-trip clean. Since then the structural-depth effort landed:
**locked dilemmas** (a triaged dilemma may explore one answer as a
fork-less storyline woven through every playthrough — BRAINSTORM
overgenerates, triage locks the surplus; in a mystery, the red
herrings) and **richer residue** (every soft convergence gets a
flag-gated residue arm per path — the story visibly remembers — and an
arm may be a 2-beat chain that reads as one passage). Next: M6,
craft-corpus research.
The golden story ["The Keeper's Bargain"](examples/keepers-bargain/)
carries hand-authored enrichment — now including a locked dilemma (what
ended the previous keeper's watch) and the residue diamond — and prints
end-to-end:

```console
$ uv sync --group dev
$ uv run qf validate examples/keepers-bargain
[B3] scope 'micro' targets 10-20 passages, found 8 (advisory)

The Keeper's Bargain @ dress: 0 error(s), 1 warning(s)
all gates pass
$ uv run qf export pdf --dir examples/keepers-bargain
exported examples/keepers-bargain/exports/the-keepers-bargain.typ and …/the-keepers-bargain.pdf
$ uv run qf export html --dir examples/keepers-bargain    # browser player + codex panel
$ uv run qf play examples/keepers-bargain     # or play it in the terminal
$ uv run qf export twee --dir examples/keepers-bargain   # take it to Twine
```

Live progress, milestone state, and the decision log are tracked in
[`docs/STATUS.md`](docs/STATUS.md). Working instructions for contributors
— human or AI agent — live in [`AGENTS.md`](AGENTS.md) (imported by
`CLAUDE.md`); automated-review norms in [`REVIEW.md`](REVIEW.md).

The design lives in [`docs/design/`](docs/design/):

| Document | Contents |
|---|---|
| [00 — Vision](docs/design/00-vision.md) | Problem, product vision, goals and non-goals, guiding principles |
| [01 — Story Model](docs/design/01-story-model.md) | The domain model: entities, dilemmas, paths, beats, passages, flags — and the invariants that bind them |
| [02 — Pipeline](docs/design/02-pipeline.md) | The eight stages: contracts, LLM vs. engine responsibilities, validation gates, human review |
| [03 — Architecture](docs/design/03-architecture.md) | Technical design: stack, package layout, graph engine, LLM adapter, project-on-disk format, CLI, testing |
| [04 — Export & Play](docs/design/04-export-and-play.md) | Runtime JSON, HTML player, Twee, and the print gamebook algorithm |
| [05 — Roadmap](docs/design/05-roadmap.md) | Milestones, exit criteria, risks |

## Heritage

This is a ground-up redesign informed by the original QuestFoundry's story
model — in particular its narrative guide (*How Branching Stories Work*)
and graph ontology. Those documents are inspiration, not specification;
where NG diverges, the design docs say so and why.
