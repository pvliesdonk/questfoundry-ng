# Heritage — the original QuestFoundry source documents

Documents from the original QuestFoundry, carried here verbatim (plus
an import banner). The first two defined its story model; the third
its interface conventions:

- [`how-branching-stories-work.md`](how-branching-stories-work.md) —
  the narrative guide: what an author is trying to accomplish at each
  stage and why.
- [`story-graph-ontology.md`](story-graph-ontology.md) — the formal
  data model that translates the guide into graph terms.
- [`semantic-conventions.md`](semantic-conventions.md) — the semantic
  clarity conventions (typed id prefixes, axis separation in outcomes,
  purpose-named fields, directive prompt register, diegetic gate
  language). NG already embodies several (typed `kind:slug` ids per
  mini-ADR A11, enums for finite sets, actionable repair errors); the
  prompt-register conventions are reference input for the prose-quality
  effort (author-supplied 2026-07-11, see `docs/STATUS.md`).

## Status: reference, not authority

**NG's single source of truth is [`docs/design/`](../design/).** These
files carry their original status banners ("Authoritative",
"Canonical") — that status applied to the *original* project and does
not transfer. NG
deliberately departs from the original in recorded ways (see the
Departures sections in design docs 01/02 and the mini-ADR table in
03 §9); treating these files as binding would silently reopen those
decisions.

## Why they are in the repo at all

Because the alternative failed twice. The original project stranded
when hard-won conceptual understanding (notably the tensor-of-Y-graphs
weave model) lived in conversations and decayed across sessions; and an
NG session (2026-07-08, PR #9) reproduced the failure in miniature —
the NG design docs were silent on multi-hard topology, the session
free-derived a wrong conclusion ("structurally impossible"), and it
took the author re-supplying these documents to converge back to the
settled model. See the decision log in [`docs/STATUS.md`](../STATUS.md).

**The rule:** when the NG design docs are silent on a story-model
question, consult these documents *before* deriving from first
principles. If they answer it, bring the answer into the NG design docs
(that's what makes it durable). If they conflict with the NG docs, the
NG docs win — and the conflict is worth surfacing in a PR, because it
is either a deliberate departure that should be recorded or a bug in
the NG docs.
