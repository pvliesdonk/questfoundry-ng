"""Canonical runtime JSON (design doc 04 §1) — the persistent boundary.

Every other export format is derived from this one, and every player
implements exactly its semantics. `validate_runtime` is the round-trip
check: it re-walks the exported document alone (no graph access), so a
bug that only exists in the export cannot hide behind the graph's own
validators (I10/I13 at the export boundary).
"""

from __future__ import annotations

from collections import deque

from questfoundry.graph import queries
from questfoundry.models.base import EdgeKind
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import StateFlag
from questfoundry.models.world import Entity
from questfoundry.project.io import Project

FORMAT = "questfoundry-runtime"
VERSION = 1


def _slug(node_id: str) -> str:
    return node_id.split(":", 1)[1]


def build_runtime(project: Project) -> dict:
    g = project.graph
    starts = queries.start_passages(g)
    if len(starts) != 1:
        raise ValueError(f"expected exactly one start passage, found {starts}")

    passages = {}
    for p in sorted(g.nodes_of(Passage), key=lambda p: p.id):
        choices = [
            {
                "label": e.payload.get("label", ""),
                "to": _slug(e.dst),
                "requires": sorted(e.payload.get("requires", [])),
                "grants": sorted(e.payload.get("grants", [])),
            }
            for e in g.out_edges(p.id, EdgeKind.CHOICE)
        ]
        passages[_slug(p.id)] = {
            "prose": p.prose,
            "choices": choices,
            "ending": {"id": p.ending.id, "title": p.ending.title} if p.ending else None,
        }

    flags = {
        f.id: {"description": f.description, "codeword": f.codeword}
        for f in sorted(g.nodes_of(StateFlag), key=lambda f: f.id)
    }
    entities = {
        e.id: {
            "name": e.name,
            "concept": e.concept,
            "base": e.base,
            "overlays": [o.model_dump() for o in e.overlays],
        }
        for e in sorted(g.nodes_of(Entity), key=lambda e: e.id)
        if e.retained
    }
    return {
        "format": FORMAT,
        "version": VERSION,
        "meta": {"title": project.name, "scope": project.vision.scope},
        "start": _slug(starts[0]),
        "passages": passages,
        "flags": flags,
        "entities": entities,
        "codex": _codex(project),
        "art": _art(project),
    }


def _codex(project: Project) -> list[dict]:
    return [
        {"entity": c.entity, "title": c.title, "body": c.body}
        for c in sorted(project.enrichment.codex, key=lambda c: c.entity)
    ]


def _art(project: Project) -> list[dict]:
    """One entry per illustration brief whose image has actually been
    generated/commissioned (`art/images/<passage-slug>.png`); briefs
    without an image file yet simply don't ship (design doc 04 §1)."""
    entries = []
    for brief in sorted(project.enrichment.briefs, key=lambda b: b.priority):
        slug = _slug(brief.passage)
        if not (project.root / "art" / "images" / f"{slug}.png").exists():
            continue
        entries.append(
            {"passage": slug, "image": f"art/images/{slug}.png", "caption": brief.caption}
        )
    return entries


def validate_runtime(data: dict) -> list[str]:
    """Re-validate the exported document on its own terms: structure,
    reachability under flag semantics, gate satisfiability, endings."""
    problems: list[str] = []
    if data.get("format") != FORMAT or data.get("version") != VERSION:
        problems.append("format/version header mismatch")
        return problems
    passages: dict = data["passages"]
    start = data["start"]
    if start not in passages:
        problems.append(f"start passage {start!r} missing")
        return problems

    known_flags = set(data.get("flags", {}))
    for pid, p in passages.items():
        if not p["prose"].strip():
            problems.append(f"passage {pid} has no prose")
        if p["ending"] and p["choices"]:
            problems.append(f"ending passage {pid} has choices")
        if not p["ending"] and not p["choices"]:
            problems.append(f"non-ending passage {pid} has no choices")
        for c in p["choices"]:
            if c["to"] not in passages:
                problems.append(f"choice in {pid} targets unknown passage {c['to']!r}")
            for flag in [*c["requires"], *c["grants"]]:
                if flag not in known_flags:
                    problems.append(f"choice in {pid} references unknown flag {flag!r}")

    known_entities = set(data.get("entities", {}))
    for entry in data.get("codex", []):
        if entry["entity"] not in known_entities:
            problems.append(f"codex entry references unknown entity {entry['entity']!r}")
    for entry in data.get("art", []):
        if entry["passage"] not in passages:
            problems.append(f"art entry references unknown passage {entry['passage']!r}")

    # walk with flag state, as every player will
    visited: set[str] = set()
    endings_reached: set[str] = set()
    seen: set[tuple[str, frozenset[str]]] = set()
    frontier: deque[tuple[str, frozenset[str]]] = deque([(start, frozenset())])
    while frontier:
        pid, flags = frontier.popleft()
        if (pid, flags) in seen or pid not in passages:
            continue
        seen.add((pid, flags))
        visited.add(pid)
        p = passages[pid]
        if p["ending"]:
            endings_reached.add(p["ending"]["id"])
            continue
        for c in p["choices"]:
            if set(c["requires"]) <= flags:
                frontier.append((c["to"], flags | set(c["grants"])))
    for pid in passages:
        if pid not in visited:
            problems.append(f"passage {pid} is unreachable in the exported runtime")
    if not endings_reached:
        problems.append("no ending is reachable in the exported runtime")
    return problems
