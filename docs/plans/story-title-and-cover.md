# Story title & a real cover (build spec)

> Status: **BUILT** (2026-07-24, one PR, TDD). Brainstormed with the author
> 2026-07-23/24. A generated story title, a portrait titled cover. See the
> decision-log entry 2026-07-24.

## The problem

The reader-facing title on every export — HTML `<title>`/header, the print
title page, Twee `StoryTitle`, and the new cover — is `project.name`
(`export/runtime_json.py:69`, `meta.title`). `project.name` is an
**administrative label**, not a story title: `examples/closed-circle-oss`
is named `Closed Circle (gpt-oss)`, so `(gpt-oss)` leaks onto the front
cover. The golden only looks right by luck (its project happens to be named
"The Keeper's Bargain"). There is no story-title field anywhere.

Two more problems the first cover surfaced:

- **The cover illustration carries no title.** The `#117` layout draws the
  title *over* the art in HTML/print, so the raw `cover.png` — the actual
  cover artifact — has no title on it.
- **Wrong aspect ratio.** The cover rendered at the passage-art default
  `3:2` (landscape, 1264×848). A book cover is **portrait**.

## Design

Three parts, one PR.

### Part 1 — a generated story title

- **Model:** `Vision.title: str = ""` (new field, optional so existing
  `vision.yaml` load unchanged).
- **DREAM generates it, author-overridable** (the `pov_hint` / A17 pattern:
  DREAM produces it, an authored value is honored). `DreamProposal` gains
  `title: str`; `dream.j2` instructs a concise, evocative title (no genre
  label, no subtitle bloat) and, when a title is already given, to return it
  unchanged. `_apply` sets `vision.title = project.vision.title or
  proposal.title` — an authored title wins; otherwise the generated one.
  `_context` passes the authored title so the prompt can echo it.
- **Exports use it:** `runtime_json` sets `meta.title = project.vision.title
  or project.name` (fallback keeps pre-title projects and any un-titled
  example working). Every other export reads `meta.title` already
  (`twee.py:28`, `html.py`, `gamebook.py`), so this is the single source.
  `project.name` returns to being a pure admin label.

### Part 2 — portrait cover aspect ratio

- `COVER_ASPECT_RATIO = "2:3"` in `illustrate.py` (standard trade book).
- The cover render overrides `aspect_ratio` to this; passage briefs keep the
  configured/`DEFAULT_ASPECT_RATIO` `3:2`. One localized branch in the
  render loop keyed on the cover.

### Part 3 — the title on the cover image (backend-aware)

The title text is `project.vision.title or project.name` (same as
`meta.title`). Decided at *illustrate* time, where the provider is known:

- **Text-capable backends — `{"openai", "gemini"}`:** append a title
  instruction to the cover prompt so the model renders the title into the
  art (modern Gemini/OpenAI set text cleanly). Example suffix: *"Across the
  open space at the top, render the book's title in large, clean lettering
  that fits the art's style: «TITLE»."*
- **Everything else (`placeholder`, future diffusion):** do not ask the
  model for text — **composite the title with PIL** into the reserved space
  after the image is written (`ImageFont.load_default(size=…)`, Pillow ≥ 10;
  a legibility band behind the text). No font is bundled.

Either path leaves `cover.png` **titled**. Because the title now lives in
the image, the export layouts stop drawing their own cover title: the HTML
cover screen shows just the image + Begin; the print cover page shows just
the full-page image. (The interior title page, browser tab, and Twee
`StoryTitle` still use `meta.title` — those are correct.)

DRESS's `dress_cover.j2` is unchanged: it still writes the atmospheric,
spoiler-safe base prompt that *reserves* space for a title. Whether that
space is filled by the model or by PIL is an illustrate-time decision, so
DRESS stays provider-agnostic.

## Where each change lands

- `models/concept.py` — `Vision.title`.
- `pipeline/stages/dream.py` + `prompts/dream.j2` — generate/preserve the
  title.
- `export/runtime_json.py` — `meta.title = vision.title or project.name`.
- `export/html.py`, `export/gamebook.py` — drop the cover-only title
  overlay (the image carries it now).
- `illustrate.py` — `COVER_ASPECT_RATIO`, `TEXT_CAPABLE_PROVIDERS`, the
  cover render branches (aspect override; title-into-prompt for text-capable;
  PIL composite otherwise). A `_composite_title(path, title)` helper.
- `tests/fixtures/keeper/calls/000.json` — the envision fixture gains
  `title`.
- Examples backfill: `examples/keepers-bargain/vision.yaml` (title "The
  Keeper's Bargain") and `examples/closed-circle-oss/vision.yaml` (title
  "Closed Circle"); the others fall back to `project.name`. Re-render the
  `closed-circle-oss` cover portrait + titled (1 billed Gemini call) and
  refresh `art/images/cover.png`.

## Testing

- `Vision.title` round-trips; absent → `""`.
- DREAM: envision generates a title; an authored `vision.title` is preserved
  through `_apply`; `dream.j2` renders the "return it unchanged" clause when
  a title is given.
- `runtime_json`: `meta.title` is `vision.title` when set, else
  `project.name`.
- illustrate: the cover render uses `2:3`; a text-capable provider gets the
  title appended to the cover prompt; a non-text provider triggers the PIL
  composite (assert `cover.png` was post-processed — dimensions/portrait and
  that the composite ran; text-in-pixels is not asserted). Passage briefs
  keep `3:2` and are never composited.
- exports: HTML cover screen and print cover page no longer render a second
  title over the cover; interior title/tab still use `meta.title`.
- golden e2e stays green through DRESS with the new envision field.

## Docs

- 01 §2 Concept layer (Vision gains a title) + the concept model.
- 02 DREAM (envision now yields a title).
- 04 §2/§4 (the cover image carries the title; exports don't double it).
- Decision-log entry.

## Out of scope

- Backfilling `vision.title` on every example (fallback covers them).
- A subtitle/author-line on the cover (title only, per the brainstorm).
- Re-rendering every example's art (only `closed-circle-oss`'s cover, which
  this changes).
