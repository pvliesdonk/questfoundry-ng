# Vendored craft corpus

A curated subset of the author's interactive-fiction craft corpus,
embedded in the repo (author call, 2026-07-12; STATUS decision log) so
corpus-grounded runs and retrieval tests are reproducible without
access to the author's vault. Runs 7 and 8 each had to re-stage this
material by hand from out-of-repo exports; this copy ends that.

## Contents

`interactive-fiction/` carries the **eight non-exemplar clusters**
(55 notes): `audience-and-access`, `craft-foundations`,
`emotional-design`, `genre-conventions`, `narrative-structure`,
`prose-and-language`, `scope-and-planning`, `world-and-setting`.
Each note is frontmattered markdown with a `cluster` field matching
its folder.

The vault's ninth cluster, `style-exemplars`, is **deliberately
absent**: unscoped retrieval fills early-stage digests wall-to-wall
with style exemplars (the 02 §1 bias vector, hit live in run 7), and
exemplars enter through M9's reserved exemplar mechanism, not general
retrieval (design doc 03 §10).

## Using it

Point a project's `craft:` block here — `craft.corpus` is absolute or
project-relative (`pipeline/research.py:corpus_root`):

```yaml
craft:
  corpus: ../../corpus/interactive-fiction   # from examples/<project>/
  folders:
    - audience-and-access
    - craft-foundations
    - emotional-design
    - genre-conventions
    - narrative-structure
    - prose-and-language
    - scope-and-planning
    - world-and-setting
```

With every cluster listed (or `folders: []`), scoping is redundant for
*this* corpus — the exemplars are already excluded — but keeping the
explicit list matches the recorded runs and stays correct if exemplar
material is ever vendored alongside.

## Provenance and stability

The notes are the author's own (© Peter van Liesdonk), shared under
the repository's terms. Treat the content as **fingerprinted input**:
the corpus hash joins research-digest freshness and the A16 stage
fingerprint (design doc 03 §9, A16/A17), so editing a note here
invalidates in-flight ledgers and digest freshness for projects
pointing at it — which is exactly the contract. Curation (adding,
trimming, rewording) remains the author's pass.
