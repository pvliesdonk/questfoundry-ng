# Decision log (ADRs)

One **Architecture Decision Record** per file, `NNNN-title.md`, append-only. The
log is spread across small files on purpose: a decision log in one document grows
without bound (the old STATUS "Decision log" reached ~1,900 lines) — one file per
decision keeps each piece small and lets you open only what you need.

> **All of this is written by coding agents for hand-off** (AGENTS.md
> §"Documentation contract"). A record is an *agent's* account of a decision, not
> author-ratified ground truth, unless it cites an explicit author instruction.
> When in doubt, `git log` and the PR thread are the ground truth; a record that
> reads as "the author decided X" without a reference is an agent's framing —
> distrust it. (Real provenance arrives when work moves to GitHub issues.)

## How to add one

Copy [`0000-template.md`](0000-template.md) to the next number, fill it in, link
it from the PR. Keep it short — Context / Decision / Consequences, a few
paragraphs. Supersede rather than rewrite: a later ADR that changes an earlier
one sets the old one's status to `Superseded by NNNN` and explains why (the
old file stays as history).

## Index

_(none migrated yet)_

## Legacy: the mini-ADR table

Design doc [`03-architecture.md` §9](../design/03-architecture.md) carries a
compact **mini-ADR table (A1–A21)** — the pre-ADR decision record, still
authoritative for those entries. Migrating it into per-file ADRs here is a
follow-up; until then, cite `A<n>` for those and add new decisions as ADR files.
