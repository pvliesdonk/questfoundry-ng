# Thaw Between — auto-generated exit-run example

An **LLM-generated** story project: the first complete weak-tier run the
pipeline carried end to end (DREAM → … → FILL → **DRESS**). Preserved as an
artifact of what the compiler produces, not as a hand-authored fixture.

- **Model:** `gpt-oss:120b-cloud` (Ollama), all three roles.
- **Premise:** a lighthouse keeper (Elara Wren) discovers the light is the only
  thing keeping something in the sea asleep; a visiting cartographer offers her
  a way off the rock (`vision.yaml`).
- **Scope:** `micro`. **Reached stage:** `dress` (validates 0 errors,
  1 advisory warning; `uv run qf validate examples/thaw-between`).

## What it is / isn't

- **Not a CI gate.** The hand-authored [`keepers-bargain`](../keepers-bargain)
  is the golden story that must always pass; *this* is a generated sample and
  is deliberately kept out of the golden gate — its prose and structure are a
  weak model's output, warts included.
- **Provenance:** it exists because a chain of review/rework fixes finally let a
  weak tier complete (see `docs/STATUS.md`, decision log 2026-07-12): structured
  review contract → `approved`/`needs_work` verdict → micro-detail redesign →
  rework convergence (rejected-draft + per-finding accounting) → word budget as
  a graded finding.

## Regenerating exports

Exports are not committed (regenerate on demand):

```
uv run qf export html -C examples/thaw-between
uv run qf export pdf  -C examples/thaw-between
```

## Known rough edge

The prose skews to high reading complexity — good as artistry, less so for a
gamebook's navigability. Tracked as a follow-up (accessibility / readability
steering); see `docs/STATUS.md`.
