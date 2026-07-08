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

🏗️ **M2 — GROW.** DREAM → BRAINSTORM → SEED → GROW run end-to-end:
`qf run --to grow` turns a one-paragraph premise into a woven, **frozen**
beat DAG — dilemma scaffolds interleaved on engine-enumerated candidate
orders (the LLM only picks among them), intersections merging scenes
across storylines, state flags derived from consequences — passing gates
G0–G3, against a live Anthropic provider or fully offline via recorded
fixtures. Under it sit M1 (stage runner, LLM adapter, front-of-pipeline
stages) and the M0 foundation: the typed story graph, the invariant
validators (I1–I13), the project-on-disk format, and the `qf` CLI. The
hand-authored golden story
["The Keeper's Bargain"](examples/keepers-bargain/) loads, passes every
gate, and walks all four of its arcs to their endings:

```console
$ uv sync --group dev
$ uv run qf validate examples/keepers-bargain
[B3] scope 'micro' targets 15-25 passages, found 7 (advisory)

The Keeper's Bargain @ polish: 0 error(s), 1 warning(s)
all gates pass
$ uv run qf simulate examples/keepers-bargain --all-arcs
...
The bargain holds + The truth shared  (path:keep + path:tell)
  beat:storm-glass
  ...
  beat:tell-commit  (commit, +flag:elias-knows)
  ...
  beat:keep-ending  (ending)

4 arc(s): all complete
$ uv run qf graph examples/keepers-bargain --layer beats      # Mermaid to stdout
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
