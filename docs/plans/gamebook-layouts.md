# Gamebook layouts — styled print & HTML export (Design Input)

> Status: **CURRENT EPIC (author call, 2026-07-30) — decisions
> ratified, build not started.** The layout directions come from the
> author's Claude Design project ("Questfoundry gamebook layout
> directions", project `5147ccb0-3922-4b92-84c4-a55032396ad0`),
> authored over four design turns and imported into the repo
> administration 2026-07-30 at the author's direction. The *mockups
> and their rationale are the design project's*; the code-grounding
> notes are this session's (agent). The open decisions were **answered
> by the author in-session 2026-07-30** — see "Ratified decisions"
> below.

The design project drafts **three print directions and two HTML player
directions**, all set with real output from *The Letter and the
Frontier* (same four sections, same codewords, like-for-like), plus a
shared accessibility contract and art-geometry rules. Its final turn is
a hand-over: four open decisions the templates cannot make alone —
they need answers from the generator side before the Typst and
`html.py` templates are written.

## What the design delivers

**Print directions (mocked at A5, 148×210mm):**

- **1a — The Paperback** (single column): sections flow continuously
  (~90 pages for a 148-passage book instead of one per page);
  hanging-indent instruction list with the turn-to number bold at the
  right margin; running heads carry the spread's section range;
  genre-neutral mass-market look.
- **1b — The Bound Edition** (marginal numbers): section numerals and
  codewords live in a wide outer margin; instructions as indented
  italic blocks with bold full-size numbers; in-world Codex as a
  spoiler-safe appendix. ~15% more pages than 1a; "looks designed, not
  generated".
- **1c — The Compendium** (band cover, type-driven): the cover art
  cropped to a top-anchored band; heavy type carries the front matter.

**HTML player directions:**

- **1d — cover as an object on a shelf**: title screen with the 2:3
  cover as an inset object, begin/continue/how-to-read actions, a
  reading-mode control.
- **1e — cover as the room**: cover filled to the viewport, subject
  centred, type over it.

**The shared accessibility contract (every style obeys):**

- A **contrast-checked colour ramp** per style (measured roles: body
  ink 13.9:1, muted ≥4.5:1, accent/codeword ≥4.5:1, choice borders and
  focus ring ≥3:1). DRESS may pick hue freely; a relative-luminance
  validator in the exporter fails the build when the accent lands
  outside the ramp.
- **Never colour alone** (WCAG 1.4.1): gates written into the sentence
  ("Because you have RAVEN…") plus a glyph; locked choices stay
  visible with the reason; held-codeword counts as a sentence.
- **Semantics & motion**: choices are `<button>`s in a
  `<nav aria-label="Choices">`; the section is an `<article>` with an
  `<h2>` and focus moves to it on turn; codeword gains announce via a
  polite live region; 180ms cross-fade → 0 under
  `prefers-reduced-motion`; ch-based measure that reflows to 320px and
  survives 200% zoom.
- **Print/PDF**: compile with **PDF/UA-1** so the compiler itself
  refuses a PDF with missing alt text or title; a **large-print**
  variant (proposed as a modifier, not a sixth style).
- **CI**: axe-core over exported HTML for a handful of sections per
  style.

**Art geometry:** cover fixed at **2:3**, plates at **3:2**; per-style
crop rules at A5 (full-bleed centre-crop loses ~8% with bleed — DRESS
must compose with safe margins; inset never crops and is the honest
fallback below the ~1750×2625 px floor for 300dpi full-bleed); plates
set to the text measure, height follows, letterbox never distort; cap
one plate per spread.

## Code grounding (current exporter state, 2026-07-30)

- `export/gamebook.py` emits **one hard-coded restrained style** as an
  assembled Typst string: page **130×200mm — not the A5 the mockups
  assume**; one section per page (`#pagebreak()` after every section,
  vs 1a's continuous flow); centred `--- N ---` section heads; no
  running heads; full-bleed cover page already shipped (#117/#120).
- Numbering is already a **seeded shuffle with anti-spoiler adjacency
  constraints** (`_assign_numbers`), answering half of the design's
  "shuffled or sequential?" question — sequential would be a new mode,
  not the default.
- `export/html.py` is a ~185-line standalone player; no title screen,
  no reading-mode controls, no aria live regions yet.
- Runtime JSON art entries carry `{passage, image, caption}` — **no
  `alt` field**; `IllustrationBrief` has no alt either. The design's
  "alt text is the mandatory first metadata" finding is a real gap:
  a UA-1 build cannot pass without it.
- The bundled `typst` Python package (0.15.0) already accepts
  `pdf_standards` in `compile()` — UA-1 enforcement is one argument,
  plus the alt-text plumbing it will then demand.
- **Tooling decision (recommend): stay on bare Typst.** The exporter
  generates its own markup; Quarto's Markdown→Typst layer would add a
  round-trip for no benefit. Everything the mockups need — running
  heads reading the current section range, marginal numerals, per-style
  set/show rules, recto/verso-aware margins, full-bleed pages — is
  plain Typst (set/show rules, `context`/`counter`/`query`, `place`,
  page margins per style). The style presets become Typst template
  modules the generator selects, not Quarto formats.

## Ratified decisions (author, in-session 2026-07-30)

1. **Art ratios: provider capability is the binding constraint**
   (author's framing — the deciding axis is what the image providers
   can actually produce, not what the templates would like).
   Measured against `image-generation-mcp`:
   - OpenAI (gpt-image): exactly `1:1, 3:2, 2:3, 16:9, 9:16`, max
     edge **1536px**. Gemini: 14 ratios (adds 3:4, 4:3, 21:9…), up
     to 2K. **Portable intersection: `1:1, 3:2, 2:3, 16:9, 9:16`.**
   - Therefore: per-image ratio becomes runtime-JSON data, but the
     menu is the provider-portable, book-shaped subset — **2:3
     (portrait), 3:2 (landscape), 1:1 (square)** — and DRESS may pick
     per scene from that menu only. Each style declares which ratios
     it places (inline / full-width / full-bleed / margin). A new
     ratio is a menu change, gated on provider support.
   - Resolution (**author correction, 2026-07-30**): the providers DO
     reach the ~1750×2625px floor for 300dpi full-bleed A5 — Gemini's
     image API takes `image_size` up to **4K** on current image
     models, and OpenAI's **gpt-image-2** accepts arbitrary `size`
     (beyond 2560×1440 total pixels is documented as experimental);
     only the older gpt-image-1.x is fixed at 1536px. The 1536/2K
     ceiling is the **installed `image-generation-mcp` adapter
     surface** (Gemini adapter exposes 1K/2K via its `hd` flag; the
     OpenAI adapter pins gpt-image-1.5's size table) — so the epic
     includes an **adapter task**: request high resolution for covers
     and full-bleed plates (filed as
     [image-generation-mcp#337](https://github.com/pvliesdonk/image-generation-mcp/issues/337);
     the 2K cap dates to its #162 quality wiring, which knew of the 4K
     tier but recorded no reason for stopping at 2K).
     Full-bleed at 300dpi is a supported target; **inset is the
     fallback** when a rendered file falls short of its placement's
     floor, checked at export time. *Touches:* `runtime_json.py`,
     `illustrate.py`, DRESS brief schema, the image-generation-mcp
     seam.
2. **Passage metadata: alt text + passage kind + in-world documents**
   (author, 2026-07-30). Alt text on every image (mandatory for
   UA-1 — the DRESS brief's scene description seeds it), passage kind
   (opening / beat / hub / ending), and in-world document marking (a
   letter set as a letter). Codeword spans, dialogue-heavy no-justify,
   and tone wait for demonstrated need (the two-styles rule).
3. **Large print is a modifier** (author, 2026-07-30): combinable
   with any print style — type scale, leading, and measure over the
   style's own palette and furniture.
4. **First build: 1a (Paperback) + 1d (Shelf)** (author, 2026-07-30).
   The shared token/template layer is proven on the simplest print
   furniture and the calmer title screen; 1b/1c/1e follow as
   variations.

Adopted without objection (agent proposal, presented 2026-07-30):
style names `--style paperback|bound|compendium` (print, mapping
1a/1b/1c in that order) and `screen|table` (HTML, mapping **1d Shelf →
`screen`**, **1e Room → `table`** — the calmer object-on-a-shelf title
screen is the conventional screen player; the cover-as-the-room
direction is the immersive at-the-table one); **numbering stays
shuffled** (the seeded
anti-spoiler shuffle is deliberate; sequential would reintroduce
adjacency spoilers) with 1a's running heads making the shuffle
navigable. Print/HTML pairing stays per-medium for now; a bundled
preset is CLI ergonomics the build can add if it earns its place.

## Imported artifacts

The design canvas (`Gamebook Layouts.dc.html` + runtime) is in the
session scratchpad, not the repo (it is a working input, ~120KB of
mockup HTML; the durable content is this contract). Re-import any time
via the Claude Design project id above; the project's `github.md`
carries the screen→repo-file map.
