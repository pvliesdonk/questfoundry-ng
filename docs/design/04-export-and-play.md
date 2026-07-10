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
  "meta": { "title": "...", "author": "...", "scope": "micro" },
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
  "art":    [ { "passage": "p-017", "image": "images/017.png", "caption": "…" } ]
}
```

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
build step. Features: passage rendering, choice handling, a codex panel,
an optional "journey so far" recap (list of passages visited), and a
save/restore slot in `localStorage`. Deliberately minimal — anyone
wanting more should consume the JSON or the Twee export.

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
4. **Layout.** Typst template: front matter (title, how-to-play, codeword
   log page), numbered sections with illustrations, choice lines in a
   consistent typographic form, codex as an appendix ("The Keeper's
   Almanac"), and an ending index by ending id (unnumbered-title only, to
   stay spoiler-safe).
5. **Lint.** Every "turn to N" resolves; every codeword is granted before
   any test of it on every arc; section count matches passage count; no
   passage orphaned by the shuffle.

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
