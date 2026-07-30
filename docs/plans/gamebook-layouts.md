# Gamebook layouts — styled print & HTML export (Design Input)

> Status: **DESIGN INPUT — not yet scoped as an epic.** The layout
> directions come from the author's Claude Design project
> ("Questfoundry gamebook layout directions", project
> `5147ccb0-3922-4b92-84c4-a55032396ad0`), authored over four design
> turns and imported into the repo administration 2026-07-30 at the
> author's direction. The *mockups and their rationale are the design
> project's*; the code-grounding notes and recommendations below are
> **this session's (agent) framing** for author ratification — per the
> AGENTS.md documentation contract, nothing here is author-ratified
> until the open decisions get explicit answers.

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

## The open decisions (need author answers)

1. **Per-image aspect ratio as data.** Let runtime JSON carry the
   ratio per image (and DRESS choose it per scene: portrait for a
   character, landscape for a vista); each style declares which ratios
   it can place (inline / full-width / full-bleed / margin). A new
   ratio becomes data, not a template rewrite. *Touches:*
   `runtime_json.py`, `illustrate.py`, DRESS brief schema.
2. **Passage-text metadata.** The higher-leverage ask: tags for
   passage kind (opening / beat / hub / ending), codeword spans,
   in-world documents (a letter set as a letter), dialogue-heavy
   no-justify. One annotation pass serves both layout and PDF/UA
   semantics. Guard: add a tag only when ≥2 styles render it
   differently. **Alt text first regardless — it is mandatory for
   UA-1** and the DRESS brief already writes the scene description
   that can seed it.
3. **Style naming & pairing.** Proposed `--style
   paperback|bound|compendium` (print) and `screen|table` (HTML);
   large-print as a *modifier* combinable with any style; whether a
   style bundles a print+HTML pair or stays per-medium.
4. **Section numbering.** Shuffled (current, seeded, anti-spoiler) vs
   sequential — decides whether running heads and "turn to" ranges are
   real navigation. Recommend keeping the shuffle and adding the 1a
   running heads (they make the shuffle navigable).

## Imported artifacts

The design canvas (`Gamebook Layouts.dc.html` + runtime) is in the
session scratchpad, not the repo (it is a working input, ~120KB of
mockup HTML; the durable content is this contract). Re-import any time
via the Claude Design project id above; the project's `github.md`
carries the screen→repo-file map.
