"""DRESS — art and codex (design doc 02, 01 §7).

Four passes sharing gate G6. DRESS reads the finished story; it never
changes it — the one exception is print codewords, presentation metadata
stored on flags via `mutations.set_flag_codeword`, not a structural edit.

1. *direction* — one art-direction record plus one visual profile per
   retained entity, both singleton/total: reruns keep the author-approved
   direction (`skip_if`), so an author who hand-edits `art/direction.yaml`
   is never overwritten by a re-run.
2. *briefs* — a fixed-size, prioritized list of illustration requests
   (`max(3, min(20, passages // 5))`), each grounded in the direction and
   an established passage.
3. *codex* — one diegetic entry per entity that anchors >=1 dilemma,
   reviewed for spoiler safety through `PassSpec.review` (FILL's pattern):
   the review sees conditional material (overlays, consequences) the
   codex must never state as fact.
4. *codewords* — one memorable print codeword per flag the print export
   will need to gate on (`queries.projected_flags`); skipped once every
   projected flag already has one, including the zero-flags case.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from questfoundry.graph import mutations, queries
from questfoundry.graph.validate import run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import Consequence, Dilemma
from questfoundry.models.enrichment import (
    ArtDirection,
    CodexEntry,
    CoverBrief,
    IllustrationBrief,
    VisualProfile,
)
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import StateFlag
from questfoundry.models.world import Entity
from questfoundry.pipeline.refpin import pin, retained_entity_ids
from questfoundry.pipeline.review import build_verdict_schema, evaluate_review, render_finding
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl
from questfoundry.project.io import Project

REVIEW_SYSTEM = (
    "You are the reviewer for QuestFoundry, a compiler that turns a premise into a "
    "branching interactive-fiction gamebook. Judge strictly against the given spoiler "
    "rules and respond only in the requested JSON format."
)

# The codex review's clause set (docs/plans/review-contract.md): spoiler
# safety has exactly these three defects. Shared envelope, this review's rules.
CODEX_REVIEW_RULES = (
    "conditional_stated_as_fact",
    "machinery_leakage",
    "ending_title_named",
)
CODEX_REVIEW_SCHEMA = build_verdict_schema("CodexReview", CODEX_REVIEW_RULES)


# -- pass 1: direction ---------------------------------------------------------


class ProfileItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    appearance: str
    iconography: list[str] = []


class DirectionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: str
    palette: str
    influences: list[str] = []
    notes: str = ""
    profiles: list[ProfileItem]


def _direction_skip(project: Project) -> str | None:
    return "art direction already set" if project.enrichment.direction is not None else None


def _direction_context(project: Project) -> dict:
    g = project.graph
    entities = sorted((e for e in g.nodes_of(Entity) if e.retained), key=lambda e: e.id)
    return {
        "vision": project.vision,
        "entities": entities,
        "passage_count": len(g.nodes_of(Passage)),
    }


def _direction_apply(proposal: DirectionProposal, project: Project) -> list[str]:
    g = project.graph
    retained = {e.id for e in g.nodes_of(Entity) if e.retained}
    seen: dict[str, ProfileItem] = {}
    for item in proposal.profiles:
        if item.entity not in retained:
            raise ApplyError(
                f"profile entity {item.entity!r} is not a retained entity; "
                f"expected one of {sorted(retained)}"
            )
        if item.entity in seen:
            raise ApplyError(
                f"entity {item.entity} has more than one profile — "
                "keep exactly one; drop the extras"
            )
        seen[item.entity] = item
    missing = retained - set(seen)
    if missing:
        raise ApplyError(
            f"every retained entity needs exactly one profile; missing {sorted(missing)}"
        )
    if not proposal.style.strip() or not proposal.palette.strip():
        raise ApplyError("art direction needs a non-empty style and palette")

    project.enrichment.direction = ArtDirection(
        style=proposal.style,
        palette=proposal.palette,
        influences=proposal.influences,
        notes=proposal.notes,
    )
    project.enrichment.profiles = sorted(
        (
            VisualProfile(
                entity=item.entity, appearance=item.appearance, iconography=item.iconography
            )
            for item in proposal.profiles
        ),
        key=lambda p: p.entity,
    )
    return [f"direction: {proposal.style}"] + [
        f"profile: {p.entity}" for p in project.enrichment.profiles
    ]


# -- cover ---------------------------------------------------------------------


class CoverProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str


def _cover_skip(project: Project) -> str | None:
    if project.enrichment.cover is not None:
        return "cover already set"
    if project.enrichment.direction is None:
        return "no art direction to base a cover on"
    return None


def _cover_context(project: Project) -> dict:
    return {"vision": project.vision, "direction": project.enrichment.direction}


def _cover_apply(proposal: CoverProposal, project: Project) -> list[str]:
    if not proposal.prompt.strip():
        raise ApplyError("the cover prompt is empty; describe an atmospheric, spoiler-safe cover")
    project.enrichment.cover = CoverBrief(prompt=proposal.prompt)
    return ["cover set"]


# -- pass 2: briefs -------------------------------------------------------------


class BriefItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage: str
    priority: int
    caption: str
    prompt: str
    entities: list[str] = []


class BriefsProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    briefs: list[BriefItem]


def _target_brief_count(project: Project) -> int:
    return max(3, min(20, len(project.graph.nodes_of(Passage)) // 5))


def _briefs_context(project: Project) -> dict:
    g = project.graph
    rendered = []
    for p in sorted(g.nodes_of(Passage), key=lambda p: p.id):
        excerpt = " ".join(p.prose.split()[:50])
        rendered.append({"passage": p, "is_ending": p.ending is not None, "excerpt": excerpt})
    return {
        "vision": project.vision,
        "direction": project.enrichment.direction,
        "profiles": project.enrichment.profiles,
        "passages": rendered,
        "target": _target_brief_count(project),
    }


def _briefs_apply(proposal: BriefsProposal, project: Project) -> list[str]:
    g = project.graph
    target = _target_brief_count(project)
    if len(proposal.briefs) != target:
        raise ApplyError(
            f"need exactly {target} briefs, got {len(proposal.briefs)} — add or drop "
            f"briefs to hit {target}, keeping the most illustratable scenes; at most "
            "one brief per passage"
        )
    passages = {p.id: p for p in g.nodes_of(Passage)}
    seen_passages: set[str] = set()
    priorities = []
    for item in proposal.briefs:
        passage = passages.get(item.passage)
        if passage is None:
            raise ApplyError(
                f"{item.passage!r} is not a passage id; use one of {sorted(passages)}"
            )
        if item.passage in seen_passages:
            raise ApplyError(
                f"passage {item.passage} has more than one brief — "
                "keep exactly one; drop the extras"
            )
        seen_passages.add(item.passage)
        priorities.append(item.priority)
        stray = set(item.entities) - set(passage.entities)
        if stray:
            raise ApplyError(
                f"brief for {item.passage}: entities {sorted(stray)} are not among that "
                f"passage's entities {passage.entities}"
            )
        if not item.caption.strip() or not item.prompt.strip():
            raise ApplyError(f"brief for {item.passage} needs a non-empty caption and prompt")
    if sorted(priorities) != list(range(1, target + 1)):
        raise ApplyError(
            f"priorities must be exactly 1..{target}, dense and unique; got {sorted(priorities)}"
        )

    project.enrichment.briefs = sorted(
        (
            IllustrationBrief(
                passage=item.passage,
                priority=item.priority,
                caption=item.caption,
                prompt=item.prompt,
                entities=item.entities,
            )
            for item in proposal.briefs
        ),
        key=lambda b: b.priority,
    )
    return [f"brief {b.priority}: {b.passage}" for b in project.enrichment.briefs]


# -- pass 3: codex ---------------------------------------------------------------


class CodexItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    title: str
    body: str


class CodexProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[CodexItem]


def _anchoring_entities(g) -> set[str]:
    # a reserved dilemma is unwoven feedstock — its anchors earn no codex
    reserved = {d.id for d in g.nodes_of(Dilemma) if d.reserved}
    anchored = {
        e.dst for e in g.edges if e.kind == EdgeKind.ANCHORED_TO and e.src not in reserved
    }
    return {e.id for e in g.nodes_of(Entity) if e.retained and e.id in anchored}


def _entity_conditionals(g, entity_id: str) -> tuple[list, list[str]]:
    """Overlays and consequences for one entity: material the codex context
    surfaces so the model (and the reviewer) can see what NOT to reveal."""
    entity = g.node(entity_id)
    assert isinstance(entity, Entity)
    consequences: list[str] = []
    for d in g.nodes_of(Dilemma):
        if entity_id not in g.out_ids(d.id, EdgeKind.ANCHORED_TO):
            continue
        for path_id in queries.explored_paths(g, d.id):
            for cid in g.out_ids(path_id, EdgeKind.HAS_CONSEQUENCE):
                consequence = g.node(cid)
                assert isinstance(consequence, Consequence)
                consequences.append(consequence.text)
    return entity.overlays, consequences


def _ending_titles(g) -> list[str]:
    return sorted(p.ending.title for p in g.nodes_of(Passage) if p.ending)


def _codex_entities_context(project: Project) -> list[dict]:
    g = project.graph
    rendered = []
    for entity_id in sorted(_anchoring_entities(g)):
        overlays, consequences = _entity_conditionals(g, entity_id)
        rendered.append(
            {"entity": g.node(entity_id), "overlays": overlays, "consequences": consequences}
        )
    return rendered


def _codex_context(project: Project) -> dict:
    return {
        "vision": project.vision,
        "voice": project.voice,
        "entities": _codex_entities_context(project),
    }


def _codex_apply(proposal: CodexProposal, project: Project) -> list[str]:
    g = project.graph
    required = _anchoring_entities(g)
    seen: dict[str, CodexItem] = {}
    for item in proposal.entries:
        if item.entity not in required:
            raise ApplyError(
                f"{item.entity!r} is not a dilemma-anchoring retained entity; "
                f"the codex covers exactly {sorted(required)}"
            )
        if item.entity in seen:
            raise ApplyError(
                f"entity {item.entity} has more than one codex entry — "
                "keep exactly one; drop the extras"
            )
        seen[item.entity] = item
        if not item.title.strip():
            raise ApplyError(f"codex entry for {item.entity} needs a non-empty title")
        word_count = len(item.body.split())
        if not 60 <= word_count <= 200:
            raise ApplyError(
                f"codex entry for {item.entity} is {word_count} words; body must be 60-200 words"
            )
    missing = required - set(seen)
    if missing:
        raise ApplyError(
            f"the codex must cover exactly {sorted(required)}; missing {sorted(missing)}"
        )

    project.enrichment.codex = sorted(
        (
            CodexEntry(entity=item.entity, title=item.title, body=item.body)
            for item in seen.values()
        ),
        key=lambda c: c.entity,
    )
    return [f"codex: {c.entity} — {c.title}" for c in project.enrichment.codex]


def _codex_review_for():
    # anchored + arbitrated like FILL's review (see the 2026-07-09
    # validation-run decision log): persistence is signal, and a second
    # failure is architect-arbitrated before it may halt the stage
    prior: list[str] = []

    def review(proposal: CodexProposal, project: Project, adapter: Any) -> list[str]:
        from questfoundry.pipeline import runner

        env = runner._environment()
        context = _codex_context(project)

        def rendered(arbitration: list[str] | None) -> str:
            return env.get_template("dress_codex_review.j2").render(
                **context,
                entries=proposal.entries,
                ending_titles=_ending_titles(project.graph),
                prior_issues=list(prior),
                arbitration=arbitration,
            )

        verdict = adapter.complete(
            system=REVIEW_SYSTEM, prompt=rendered(None), schema=CODEX_REVIEW_SCHEMA, role="utility"
        )
        # approved auto-accepts; a needs_work verdict gates on confident
        # objective defects only (review-contract) — a warn or low-confidence
        # finding never halts the stage.
        issues = evaluate_review(verdict)
        if not issues:
            return []
        if prior:
            final = adapter.complete(
                system=REVIEW_SYSTEM,
                prompt=rendered([render_finding(f) for f in verdict.findings]),
                schema=CODEX_REVIEW_SCHEMA,
                role="architect",
            )
            final_issues = evaluate_review(final)
            if not final_issues:
                return []
            issues = final_issues
        prior.extend(issues)
        return issues

    return review


# -- pass 4: codewords ------------------------------------------------------------


class CodewordItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag: str
    codeword: str


class CodewordsProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codewords: list[CodewordItem]


def _pending_codewords(g) -> set[str]:
    return {f for f in queries.projected_flags(g) if g.node(f).codeword is None}  # type: ignore[union-attr]


def _codewords_skip(project: Project) -> str | None:
    return (
        "every projected flag already has a codeword"
        if not _pending_codewords(project.graph)
        else None
    )


def _codewords_context(project: Project) -> dict:
    # Uniqueness is global (mutations.set_flag_codeword rejects reuse), so
    # on a rerun the model must see the codewords already spoken for —
    # "distinct from every other codeword" is unfollowable blind.
    g = project.graph
    flags = [g.node(f) for f in sorted(_pending_codewords(g))]
    taken = sorted(f.codeword for f in g.nodes_of(StateFlag) if f.codeword)
    return {"vision": project.vision, "voice": project.voice, "flags": flags, "taken": taken}


def _codewords_apply(proposal: CodewordsProposal, project: Project) -> list[str]:
    g = project.graph
    pending = _pending_codewords(g)
    seen: set[str] = set()
    for item in proposal.codewords:
        if item.flag not in pending:
            raise ApplyError(
                f"{item.flag!r} does not need a codeword; expected exactly {sorted(pending)}"
            )
        if item.flag in seen:
            raise ApplyError(
                f"flag {item.flag} given more than one codeword — "
                "keep exactly one; drop the extras"
            )
        seen.add(item.flag)
    missing = pending - seen
    if missing:
        raise ApplyError(
            f"codewords must cover exactly {sorted(pending)}; missing {sorted(missing)}"
        )

    lines = []
    for item in proposal.codewords:
        mutations.set_flag_codeword(g, item.flag, item.codeword)
        lines.append(f"{item.flag}: {item.codeword}")
    return lines or ["no projected flags need a codeword"]


def _passes(project: Project) -> tuple[PassSpec, ...]:
    # Every DRESS reference set exists at stage start (after FILL) and no
    # pass changes another's, so pin each here (exact ids — these fields
    # are all exact-membership, not resolve_entity_ref; pipeline/refpin.py).
    g = project.graph
    passages = sorted(p.id for p in g.nodes_of(Passage))
    passage_entities = list(dict.fromkeys(e for p in g.nodes_of(Passage) for e in p.entities))
    direction_schema = pin(
        DirectionProposal, "DirectionProposal", {("ProfileItem", "entity"): retained_entity_ids(g)}
    )
    briefs_schema = pin(
        BriefsProposal,
        "BriefsProposal",
        {("BriefItem", "passage"): passages, ("BriefItem", "entities"): passage_entities},
    )
    codex_schema = pin(
        CodexProposal, "CodexProposal", {("CodexItem", "entity"): sorted(_anchoring_entities(g))}
    )
    codewords_schema = pin(
        CodewordsProposal,
        "CodewordsProposal",
        {("CodewordItem", "flag"): sorted(_pending_codewords(g))},
    )
    return (
        PassSpec(
            name="direction",
            role="architect",
            template="dress_direction.j2",
            schema=direction_schema,
            build_context=_direction_context,
            apply=_direction_apply,
            skip_if=_direction_skip,
        ),
        PassSpec(
            name="briefs",
            role="writer",
            template="dress_briefs.j2",
            schema=briefs_schema,
            build_context=_briefs_context,
            apply=_briefs_apply,
        ),
        PassSpec(
            name="codex",
            role="writer",
            template="dress_codex.j2",
            schema=codex_schema,
            build_context=_codex_context,
            apply=_codex_apply,
            review=_codex_review_for(),
        ),
        PassSpec(
            name="codewords",
            role="utility",
            template="dress_codewords.j2",
            schema=codewords_schema,
            build_context=_codewords_context,
            apply=_codewords_apply,
            skip_if=_codewords_skip,
        ),
        # Cover last: it depends only on `direction` (first), so ordering it
        # here keeps its generation independent of the passes between and lets
        # its recorded fixture append without renumbering the others.
        PassSpec(
            name="cover",
            role="architect",
            template="dress_cover.j2",
            schema=CoverProposal,
            build_context=_cover_context,
            apply=_cover_apply,
            skip_if=_cover_skip,
        ),
    )


DRESS_STAGE = StageImpl(
    stage=Stage.DRESS,
    passes=_passes,
    gate=lambda p: run_checks(p.graph, p.vision, Stage.DRESS, enrichment=p.enrichment),
)
