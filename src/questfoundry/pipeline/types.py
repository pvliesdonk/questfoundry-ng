"""Contracts for the uniform stage loop (design doc 02 §1, 03 §4).

A stage is declarative: one or more LLM passes plus a gate. The runner
(`pipeline/runner.py`) owns the loop — context → render → complete →
apply (with repair) → gate → checkpoint — so stage modules contain no
orchestration code, only schemas, context builders, apply functions,
and prompts.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

from questfoundry.graph.validate import Issue, Severity
from questfoundry.models.base import Stage
from questfoundry.project.io import Project

ModelRole = Literal["architect", "writer", "utility"]


class ApplyError(Exception):
    """A proposal could not be applied. The message is human/model-readable
    and is fed back to the model verbatim for a repair attempt."""


def resolve_entity_ref(g: Any, ref: str) -> str:
    """The id contract (mini-ADR A11) at the apply layer: every entity
    reference in a proposal is the exact `kind:slug` id, or the provably
    unambiguous bare slug (prefix restoration is parsing, not
    prediction). Display names are rejected with the expected set —
    every apply that stores entity refs on a beat must resolve through
    here, or junk sails through the gates until something collides with
    it (validation run, 2026-07-09: a diamond arm carrying 'Wren').
    """
    from questfoundry.models.world import Entity

    if isinstance(g.get(ref), Entity):
        return ref
    entities = [e for e in g.nodes_of(Entity) if e.retained]
    matches = {e.id for e in entities if e.id.split(":", 1)[1] == ref}
    if len(matches) == 1:
        return matches.pop()
    raise ApplyError(
        f"{ref!r} is not an entity id; use one of: {sorted(e.id for e in entities)}"
    )


@dataclass(frozen=True)
class PassSpec:
    """One LLM call within a stage.

    - `template`: Jinja2 filename under `pipeline/prompts/`.
    - `build_context(project)`: dict rendered into the template. The
      runner adds `notes` (author steering) and, on repair rounds,
      `repair_errors` (list[str]).
    - `apply(proposal, project)`: mutate the project through
      `graph/mutations.py` (or set `project.vision`); return
      human-readable summary lines of what was applied. Raise
      `ApplyError` (or let `MutationError` escape) to trigger repair —
      the runner snapshots and restores the mutable project state
      (graph, vision, voice, enrichment, research) around failed
      applies. Apply must be deterministic: kept-pass replay, ledger
      resume, and the research pass's engine-side retrieval all rely
      on re-applying a recorded proposal reproducing the same bytes.
    - `skip_if(project)`: optional; return a reason string to skip the
      pass (no LLM call, recorded on the report with attempts=0), or
      None to run it. For passes whose engine-determined work list can
      be empty (e.g. GROW's bridge pass with no gaps).
    - `review(proposal, project, adapter)`: optional post-apply LLM
      judgment (FILL's automated prose review). Return issue strings;
      any issue restores the graph and re-enters the repair loop with
      them, so "≤2 revision rounds, then halt" (design doc 02, FILL)
      is the ordinary repair contract, not bespoke machinery.
    """

    name: str
    role: ModelRole
    template: str
    schema: type[BaseModel]
    build_context: Callable[[Project], dict]
    apply: Callable[[BaseModel, Project], list[str]]
    skip_if: Callable[[Project], str | None] | None = None
    review: Callable[[BaseModel, Project, Any], list[str]] | None = None


@dataclass(frozen=True)
class StageImpl:
    """A pipeline stage: ordered passes sharing one exit gate.

    `passes` may be a callable computing the pass list from the project
    at stage start — FILL's per-passage work queue depends on the story.

    `gate(project)` returns validation issues; the stage succeeds iff
    none are errors. Most stages use `graph.validate.run_checks` at
    their own Stage level.
    """

    stage: Stage
    passes: tuple[PassSpec, ...] | Callable[[Project], tuple[PassSpec, ...]]
    gate: Callable[[Project], list[Issue]]


@dataclass
class PassReport:
    name: str
    attempts: int = 1
    applied: list[str] = field(default_factory=list)
    # The accepted proposal (JSON mode), persisted at checkpoint so
    # `qf rerun --keep` can re-apply it without an LLM call.
    proposal: dict | None = None


@dataclass
class StageReport:
    stage: Stage
    passes: list[PassReport] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    error: str | None = None  # runner-level failure (repairs exhausted, ...)

    @property
    def success(self) -> bool:
        return self.error is None and not any(
            i.severity == Severity.ERROR for i in self.issues
        )
