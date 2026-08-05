# 04 — Export & Play

SHIP is deterministic compilation from the passage graph to four formats.
The **canonical runtime JSON** is primary; every other format is derived
from it, and the play engine (`qf play`, the HTML player) executes it.
This section defines the runtime model and the per-format specifics.

## 1. Canonical runtime JSON

The exported subset of the graph — the persistent boundary. Working data
(dilemmas, paths, beats, hints, feasibility notes) never ships.

```jsonc
{
  "format": "questfoundry-runtime",
  "version": 1,
  "meta": { "title": "...", "author": "...", "scope": "micro" },  // title = vision.title, else project.name
  "start": "p-001",
  "passages": {
    "p-017": {
      "prose": "…markdown…",
      "choices": [
        { "label": "Tell him everything", "to": "p-018",
          "requires": [], "grants": ["cartographer_knows"] }
      ],
      "ending": null            // or { "id": "e-2", "title": "The Long Watch" }
    }
  },
  "flags": { "cartographer_knows": { "codeword": "CONFESSED" } },  // codeword only if projected
  "entities": { "character:keeper": { "base": {…}, "overlays": [ { "when": [...], "details": {…} } ] } },
  "codex":  [ { "entity": "character:keeper", "title": "…", "body": "…md…" } ],
  "art":    [ { "passage": "p-017", "image": "images/017.png", "caption": "…",
                "alt": "…", "ratio": "3:2" } ],
  "cover":  { "image": "art/images/cover.png", "alt": "…", "ratio": "2:3" }
                                        // present only once the cover image is rendered
}
```

Every image entry carries two pieces of metadata besides its caption, and
both are load-bearing rather than decorative (§7):

- **`alt`** — what a reader who cannot see the picture is told *instead of*
  it. The caption sits beside the picture and every reader gets it; the alt
  text stands in for it, so it never repeats the caption. It is mandatory:
  a PDF/UA-1 build cannot be produced without it, and `validate_runtime`
  refuses an entry that has none.
- **`ratio`** — the frame's shape, from the fixed menu `2:3 | 3:2 | 1:1`
  (§7). A cover's ratio is stated rather than chosen: a cover is portrait.

Runtime semantics (all players implement exactly this):

1. State is a set of active flags, initially empty.
2. At a passage, render prose (+ illustration), then the choices whose
   `requires` ⊆ active flags. Unavailable choices are *hidden*, never
   shown disabled — the player must not see the machinery.
3. Taking a choice adds its `grants` and moves to `to`.
4. A passage with `ending` set terminates the playthrough.

Variant passages need no special runtime support: variants are ordinary
passages whose *incoming* choices carry disjoint `requires` — gating was
resolved into the graph by POLISH. Entities/overlays ship for codex
display and future runtimes; the prose already reflects them.

SHIP's exit gate re-imports the JSON and re-validates reachability, gate
satisfiability, and ending reachability (I10/I13 at the export boundary).

## 2. Standalone HTML

One self-contained file: embedded runtime JSON + a small dependency-free
JS player + inlined (base64) images. Works from `file://`, no network, no
build step. Features: a **title screen** (§7, style `screen`) setting the
cover as an inset object — the image carries its own title — beside
begin / continue / how-to-read and a reading-mode control; passage
rendering, choice handling, a codex panel, an optional "journey so far"
recap (list of passages visited), and a save/restore slot in
`localStorage`. Deliberately minimal — anyone wanting more should consume
the JSON or the Twee export.

## 3. Twee 3

Twee 3 / SugarCube 2 (the broadest Twine ecosystem target):

- Passage per Twee passage; choices become links; `grants` become
  `<<set $flags.x true>>` on entry via a small header macro; `requires`
  become `<<if>>` guards around links.
- `StoryData` carries IFID (generated once, stored in `project.yaml`) and
  start passage.
- Prose markdown is converted to SugarCube markup (a bounded, lossy
  mapping — the lint step flags constructs that don't survive).

The Twee export is the "escape hatch": authors who want to keep working
in Twine take this and leave QuestFoundry behind, by design.

## 4. Print gamebook (PDF)

The most format-specific pipeline, in five deterministic steps:

1. **Codeword projection.** Decide which flags the *reader* must track:
   exactly the flags some choice gate tests. Soft-dilemma routing flags
   qualify (readers cross a convergence where pages rejoin, so state must
   survive on paper); hard-dilemma flags never do (the page structure
   keeps those readers on disjoint pages); cosmetic flags qualify only if
   a later passage actually tests them. A "**Write down the codeword
   CONFESSED**" line is hoisted into a section when *every* choice
   arriving there grants the flag (commit passages — the common case);
   a grant not shared by all arrivals stays inline on its choice line.
   Grants of unprojected flags render nowhere. Every projected codeword
   is a single memorable word drawn from the story's diction —
   LLM-suggested at DRESS time (mini-ADR A12; POLISH predates voice and
   prose, so the diction doesn't exist there), stored on the flag,
   deterministic here. A flag reaching print without a stored codeword
   gets one derived from its slug, with a warning to run DRESS.
2. **Residue-variant lowering.** Digital runtimes hide unavailable
   choices; paper cannot. Where variant passages exist, the *incoming*
   reference becomes a codeword test ("If you have CONFESSED turn to 83,
   otherwise turn to 84"). POLISH's I10 guarantee (gates always
   satisfiable per arc) is what makes these instructions always
   resolvable.
3. **Numbering & shuffling.** Passages are assigned section numbers in a
   seeded pseudo-random order with craft constraints: the start is
   section 1; structurally adjacent passages get non-adjacent numbers
   (prevents accidental spoiling by peripheral vision); variants of one
   moment are separated; endings are scattered. The seed is stored in
   `project.yaml` on first export (`print_seed`, overridable with
   `--seed`), so re-export is stable unless the graph changed. At tiny
   passage counts the constraints may be unsatisfiable; the best
   assignment is kept and the compromises reported as warnings.
4. **Layout.** A Typst template chosen from the print styles in §7 (default
   `paperback`): an optional full-page **cover** (the cover image — it
   already carries its own title, drawn by the image backend or composited
   at illustrate time) when a `cover` is present, then front matter (title
   page, how-to-play, codeword log page), numbered sections with
   illustrations, choice lines in a consistent typographic form, codex as
   an appendix ("The Keeper's Almanac"), and an ending index by ending id
   (unnumbered-title only, to stay spoiler-safe). The PDF is compiled with
   `pdf_standards="ua-1"`, so the compiler refuses a document missing
   alt text or a title.
5. **Lint.** Every "turn to N" resolves; every codeword is granted before
   any test of it on every arc; section count matches passage count; no
   passage orphaned by the shuffle; every placed illustration has alt text.
   The last of those duplicates a check the compiler also makes, on
   purpose: Typst's message names neither the section nor the brief to fix.

## 5. Play & QA tooling

- **`qf play`** — terminal player on the runtime JSON: renders prose,
  tracks flags, offers choices; `--show-state` reveals flags and current
  passage id for debugging. Works pre-FILL too, rendering beat summaries
  instead of prose — this makes the *structure* playable at the end of
  POLISH, before a single passage is written (cheap structural
  playtesting is the point of the frozen topology).
- **`qf simulate`** — non-interactive walkers: `--all-arcs` (exhaustive
  dilemma-combination coverage), `--random N` (false-branch and detour
  coverage), each verifying completeness, gate satisfiability, and
  ending reachability, and emitting a coverage report (passages never
  visited by any walk = export-blocking bug).
- **LLM playtester (later milestone)** — an automated reader that plays
  arcs and files subjective reports (pacing, choice ambiguity, residue
  visibility) as advisory review input.

## 6. Illustrations (`qf illustrate`)

Renders the DRESS illustration briefs into `art/images/<passage-slug>.png`
(M7; mini-ADR A18 in [03 §9](03-architecture.md)). A **command beside
`qf export`, never a pipeline stage**: cloud image generation exposes no
seeds, so its bytes cannot join checkpoint byte-stability or A16 replay.
Idempotence is by file presence — an existing image skips its brief,
re-running the command costs zero API calls, and `--force` re-renders.

- **Provider seam**: `image-generation-mcp` as a Python library
  (`ImageService` + `register_provider`; the markdown-vault-mcp
  precedent). Providers: `openai` (gpt-image-2 lineup), `gemini`
  (`gemini-3.1-flash-image`), and the deterministic zero-network
  `placeholder` — CI's hermetic path. Configured by a project.yaml
  `images:` block (`provider`, optional `model` / `aspect_ratio` /
  `quality`) or `--provider`; keys come from `OPENAI_API_KEY` /
  `GEMINI_API_KEY`.
- **Prompt assembly is engine-side and deterministic**: art direction
  (style, palette, influences, notes) first, then the visual-profile
  fragment of every entity the brief depicts (the heritage consistency
  device), then the brief's scene. A brief citing an unprofiled entity
  fails loud.
- **Cost controls**: sample-first gate (first render pauses for
  confirmation; `--yes` for batch), `--budget N` render cap,
  `--priority N` floor, one ledger entry per paid call (`kind: image`
  in `reports/ledger.jsonl`). Generation errors are never retried
  automatically; a typed content-policy refusal gets exactly one
  LLM-reformulated attempt (utility role), then is reported and the
  batch continues.
- **Bytes are normalized to PNG at the single write site** — providers
  return what they like (Gemini hands back JPEG) while everything
  downstream keys on the `.png` contract.
- **Consumers**: the runtime JSON `art` entries key on file presence
  (§1); the HTML player inlines rendered images as data URIs (the
  player stays one self-contained file) above the passage prose; the
  print gamebook fills its illustration slots via typst-root-anchored
  paths (`/art/images/…` — typst resolves leading-slash paths from its
  compilation root, not the OS root).

Style-reference conditioning (feeding a rendered image back as a
reference for the rest of the batch — the library's edit path supports
it on both cloud providers) is the documented escalation if sample
images show character drift; not built until a live run demands it.

**Ratio** is per-image data, not a global setting: each brief carries one
(§7's menu), and `qf illustrate` renders at it. An `images.aspect_ratio`
in `project.yaml` pins one shape for the whole book — an author override
of DRESS's per-scene choice. The cover is always portrait, whatever else
is configured.

## 7. Export styles and the accessibility contract

The exports are **styled**, and the styles are selectable: `qf export pdf
--style <name>` and `qf export html --style <name>`, with `--large-print`
as a modifier over either. The style layer is
[`export/style.py`](../../src/questfoundry/export/style.py); the furniture
each style needs lives with its medium (`gamebook.py`, `html.py`),
because what print and screen genuinely share is the contract below, not
running heads and title screens. The directions come from the author's
layout design project, imported as
[`plans/gamebook-layouts.md`](../plans/gamebook-layouts.md).

| Style | Medium | Direction |
|---|---|---|
| `paperback` | print | 1a — A5, sections flow continuously, running heads carry the spread's section range, instructions hang-indent with the turn-to number bold at the right margin |
| `bound` | print | 1b — a wide outer margin carries the section numerals and their codewords; instructions are indented italic blocks with the number inline at full size. The narrower measure is what costs it its extra pages |
| `compendium` | print | 1c — the cover cropped to a top-anchored band with display type beneath it; heavy type carries the front matter |
| `screen` | HTML | 1d — the cover as an object on a shelf: a title screen with the cover inset, begin/continue/how-to-read, a reading-mode control |
| `table` | HTML | 1e — the cover as the room: filled to the viewport, the type set over a scrim |

Asking for a style that does not exist names the ones that do.

A style is a **record plus its medium's furniture**, never a template of
its own. `PrintStyle` carries geometry, type, its ramp, and four furniture
axes — where the section numeral sits (`inline` / `margin`), how an
instruction is set (`hanging` / `italic-block`), how the cover is placed
(`full-bleed` / `band`), and what the front matter is (`plain` / `heavy`);
`ScreenStyle` carries one (`shelf` / `room`). Each axis exists because the
built styles actually differ on it. Two consequences worth stating:

- **A marginal column is checked like a ramp.** `check_geometry` fails the
  build when the column plus its gutter does not fit the outer margin —
  otherwise it overprints the page edge, which no colour check sees and no
  reader of the generated Typst notices.
- **The how-to-play page describes the edition in hand.** An edition that
  prints its numbers in the margin must not tell the reader to look at the
  right-hand margin of a line, so that page varies with the furniture.

### The contract every style obeys

- **A contrast-checked colour ramp.** Five roles — `page`, `ink`, `muted`,
  `accent`, `rule` — each measured against that style's own page colour
  and each carrying the WCAG floor its use demands: body ink ≥ 7:1 (a whole
  book is read at that size), text roles ≥ 4.5:1 (1.4.3), non-text
  roles — borders, dividers, the focus ring — ≥ 3:1 (1.4.11). A ramp that
  misses a floor **fails the build**, with the measured ratio, the floor,
  and the direction to move. Light and dark screen modes are two ramps,
  both checked.
- **Never colour alone** (1.4.1). No role carries meaning: colour makes a
  page legible, a word or a glyph carries the information. On paper, gates
  are written into the sentence ("If you have RAVEN…") and codewords are
  named, never merely tinted. *The contract's "locked choices stay visible
  with the reason" clause is a print concern only:* paper cannot hide a
  choice, so residue-variant lowering (§4 step 2) spells the gate out. A
  digital runtime **hides** an unavailable choice (§1 rule 2) — the reader
  must not see the machinery — so there is no locked state to label.
- **A role is checked against the page it belongs to.** Where a style sets
  type over something that is not its page colour — 1e's scrimmed cover —
  the roles are re-measured there rather than carried across. `--accent` in
  light mode is a dark ink-blue: right on paper-on-screen, unreadable on a
  near-black scrim. That is also why 1e scrims at all: the exporter has
  never seen the cover art, so the scrim is what makes the floor hold
  whatever the image turns out to be.
- **Semantics and motion (HTML).** Choices are `<button>`s inside a
  `<nav aria-label="Choices">`; the passage is an `<article>` named by its
  heading that takes focus on every turn; status changes announce through
  a polite live region rather than stealing focus; the turn's 180ms
  cross-fade collapses to 0 under `prefers-reduced-motion`; the measure is
  in `ch`, so it reflows to 320px and survives 200% zoom without a
  horizontal scrollbar.
- **PDF/UA-1 (print).** Compiled with `pdf_standards="ua-1"`, so the
  compiler refuses a build with a missing alt text or document title.
  Section numbers are real headings, so the PDF outline is the book's own
  numbering and a screen reader can move section to section.
- **Large print is a modifier, not a style** (author, 2026-07-30): type
  scale, leading and measure over the style's own palette and furniture,
  combinable with any of them. The measure narrows as the type grows, so
  characters-per-line — the thing that actually governs readability —
  stays near where the style set it. It writes its own edition
  (`<slug>-<style>-large-print`) rather than overwriting the plain one.

### Art geometry

The ratio menu is `2:3` (portrait) | `3:2` (landscape) | `1:1` (square) —
the **provider-portable** intersection, narrowed to what a page or a
screen places well (author ratification, 2026-07-30: provider capability
is the binding constraint). DRESS chooses one per scene; a new ratio is a
menu change gated on provider support, never a free string. The cover is
fixed at 2:3.

Each style declares the width its placement gives each ratio, as a
fraction of the text measure. A landscape plate sits at the measure; a
portrait plate is capped so a tall frame leaves prose on the page with it.
**Height always follows from the ratio** — letterboxing distorts, and a
distorted plate is a bug. A ratio outside the menu (a hand-edited brief)
is placed as landscape and reported as a warning; the page still builds.

A **full-bleed** cover needs 1750×2625px (300dpi at A5 trim plus bleed).
Below that floor the export places the same art **inset** and says so,
rather than handing the printer an upscale to soften: the honest fallback.
