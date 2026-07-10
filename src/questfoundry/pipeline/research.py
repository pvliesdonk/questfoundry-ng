"""Craft-corpus retrieval core (design doc 02 §1 "Craft context", 03 §10;
mini-ADR A13).

Deterministic retrieval over a markdown vault: standing queries derived
from the vision, hybrid/keyword search via ``markdown-vault-mcp``, merged
and stably re-sorted (never trust library tie-breaking), rendered
into a byte-identical digest markdown. Search results feed prompt bytes,
so this module is a pure function of (config, corpus, queries) with no
non-deterministic content (no timestamps).

The pass layer lives here too: `research_pass(stage)` is the head pass
`with_research` prepends to every stage, its `apply` performing the
retrieval (mini-ADR A13: the model decides *what it needs*, the engine
fetches). This module must not import `pipeline.runner`,
`pipeline.stages`, or `pipeline.prompts`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from questfoundry.models.base import Stage
from questfoundry.models.concept import Vision
from questfoundry.models.craft import CraftConfig
from questfoundry.pipeline.types import ApplyError, PassSpec, StageImpl
from questfoundry.project.io import Project


class ResearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    reason: str = ""


class ResearchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queries: list[ResearchQuery]


def _is_placeholder(value: str) -> bool:
    return not value or value.upper().startswith("TODO")


def standing_queries(vision: Vision | None, stage: Stage) -> list[str]:
    """Deterministic queries built from the vision's open-vocabulary
    fields: one joining genre + subgenre, one for tone, one per theme.

    [] before a vision has real content — DREAM's head, where no vision
    exists yet (context there is premise + scope, design doc 02 §1's
    DREAM amendment) and DREAM itself, whose placeholder vision
    (`genre="TODO"`, `tone="TODO"`, see `project/io.py:scaffold_project`)
    would otherwise slip through. From BRAINSTORM on, this returns the
    same list regardless of stage — stage-specific needs are the
    research pass's librarian queries, not this function's job.
    """
    if vision is None or stage == Stage.DREAM:
        return []
    if _is_placeholder(vision.genre) or _is_placeholder(vision.tone):
        return []
    queries: list[str] = []
    genre_query = " ".join(part for part in (vision.genre, vision.subgenre) if part.strip())
    if genre_query:
        queries.append(genre_query)
    if vision.tone.strip():
        queries.append(vision.tone)
    for theme in vision.themes:
        if theme.strip() and not _is_placeholder(theme):
            queries.append(theme)
    return queries


def _eligible_files(cfg: CraftConfig, corpus_root: Path) -> list[tuple[str, str]]:
    """Sorted (posix relpath, sha256 hex) pairs for every ``*.md`` file
    under the configured folders (``cfg.folders == []`` means the whole
    corpus). A dict dedups files reachable through more than one
    configured folder."""
    roots = [corpus_root / folder for folder in cfg.folders] if cfg.folders else [corpus_root]
    files: dict[str, str] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            rel = path.relative_to(corpus_root).as_posix()
            files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return sorted(files.items())


def corpus_fingerprint(cfg: CraftConfig, corpus_root: Path) -> str:
    """sha256 hex over sorted (relpath, per-file sha256) of eligible
    files. Content only — no mtimes — so the fingerprint is stable
    across machines and clock skew and changes only when the material a
    run actually read changes."""
    digest = hashlib.sha256()
    for rel, file_hash in _eligible_files(cfg, corpus_root):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _embedding_provider(cfg: CraftConfig) -> Any:
    """Module-level seam so tests substitute a deterministic fake
    provider without a network call or the fastembed model download.
    Lazy import: a keyword-mode or corpus-less project never needs
    fastembed installed."""
    from markdown_vault_mcp.providers import FastEmbedProvider

    return FastEmbedProvider(model_name=cfg.embedding_model)


def _search_query(vault: Any, cfg: CraftConfig, query: str) -> list[tuple[str, str, str]]:
    """One query's ranked, word-budgeted ``(path, heading, content)``
    snippets: one search per eligible folder (``cfg.folders == []``
    searches the whole vault once), flattened `GroupedResult.sections`,
    merged, and stably re-sorted by ``(-score, path, heading or "")`` —
    the library's own ordering is not a contract we lean on."""
    folders: list[str | None] = list(cfg.folders) if cfg.folders else [None]
    ranked_keys: list[tuple[float, str, str]] = []
    contents: dict[tuple[str, str], str] = {}
    for folder in folders:
        for result in vault.reader.search(
            query, limit=cfg.top_k, mode=cfg.search_mode, folder=folder
        ):
            for section in result.sections:
                heading = section.heading or ""
                key = (result.path, heading)
                ranked_keys.append((-section.score, result.path, heading))
                contents[key] = section.content
    ranked_keys.sort()
    seen: set[tuple[str, str]] = set()
    top: list[tuple[str, str, str]] = []
    for _, path, heading in ranked_keys:
        key = (path, heading)
        if key in seen:
            continue
        seen.add(key)
        top.append((path, heading, contents[key]))
        if len(top) == cfg.top_k:
            break
    return _cap_words(top, cfg.words_per_query)


def _cap_words(
    snippets: list[tuple[str, str, str]], words_per_query: int
) -> list[tuple[str, str, str]]:
    """Truncate a query's total snippet text to `words_per_query` words
    across all its included sections, cutting inside the section that
    would overflow the budget and dropping any sections after it."""
    capped: list[tuple[str, str, str]] = []
    budget = words_per_query
    for path, heading, content in snippets:
        if budget <= 0:
            break
        words = content.split()[:budget]
        capped.append((path, heading, " ".join(words)))
        budget -= len(words)
    return capped


def _render_section(query: str, snippets: list[tuple[str, str, str]]) -> str:
    lines = [f"## {query}", ""]
    if not snippets:
        lines.append("(no matches)")
    else:
        for i, (path, heading, content) in enumerate(snippets):
            label = f"{path}#{heading}" if heading else path
            if i:
                lines.append("")
            lines.append(f"### {label}")
            lines.append("")
            lines.append(content)
    return "\n".join(lines)


def _render_digest(meta: dict, sections: list[tuple[str, list[tuple[str, str, str]]]]) -> str:
    # sort_keys=False: `meta`'s insertion order is the frontmatter's byte
    # layout, so callers control it deterministically instead of relying
    # on an alphabetical re-sort.
    header = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=88)
    body = "\n\n".join(_render_section(query, snippets) for query, snippets in sections)
    return f"---\n{header}---\n\n{body.rstrip()}\n"


def retrieve(
    cfg: CraftConfig,
    corpus_root: Path,
    cache_dir: Path,
    stage: Stage,
    queries: list[tuple[str, str]],
) -> str:
    """Run every ``(kind, query)`` pair — ``kind`` is ``"standing"`` or
    ``"librarian"`` — against the corpus and return the digest markdown
    persisted at ``research/<stage>.md``.

    Lazy-imports `markdown_vault_mcp` inside the function: the
    corpus-less `skip_if` path (the common case — CI and the golden
    story never configure `craft:`) must not need the library installed.
    Two calls with the same inputs return byte-identical strings: no
    timestamps, no non-deterministic ordering — the digest enters the
    next stage's content fingerprint.
    """
    from markdown_vault_mcp import Vault

    cache_dir.mkdir(parents=True, exist_ok=True)
    provider = _embedding_provider(cfg) if cfg.search_mode == "hybrid" else None
    vault = Vault(
        source_dir=corpus_root,
        index_path=cache_dir / "index.db",
        embeddings_path=cache_dir / "embeddings.db",
        embedding_provider=provider,
        read_only=True,
        # Keep the change-tracker state out of corpus_root (often a
        # read-only, sometimes version-controlled, checkout) — it lives
        # beside the other retrieval cache artifacts instead.
        state_path=cache_dir / "state.json",
    )
    try:
        vault.index.build_index()
        if cfg.search_mode == "hybrid":
            vault.index.build_embeddings()
        sections = [(query, _search_query(vault, cfg, query)) for _kind, query in queries]
    finally:
        vault.close()

    sources = sorted({path for _, snippets in sections for path, _, _ in snippets})
    meta = {
        "stage": stage.value,
        "corpus_fingerprint": corpus_fingerprint(cfg, corpus_root),
        "standing_queries": [q for kind, q in queries if kind == "standing"],
        "librarian_queries": [q for kind, q in queries if kind == "librarian"],
        "top_k": cfg.top_k,
        "sources": sources,
    }
    return _render_digest(meta, sections)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("research digest needs YAML frontmatter (---)")
    try:
        header, body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("unterminated research digest frontmatter") from exc
    return header, body


def digest_body(text: str) -> str:
    """The digest markdown after its YAML frontmatter block (the blank
    separator line right after the closing `---` is not part of it)."""
    _, body = _split_frontmatter(text)
    return body.lstrip("\n")


def digest_meta(text: str) -> dict:
    """Parse a digest's YAML frontmatter into a dict."""
    header, _ = _split_frontmatter(text)
    meta = yaml.safe_load(header)
    return meta if isinstance(meta, dict) else {}


# One line per stage on what the librarian is researching *for* — the only
# stage-varying ingredient of the research prompt (standing queries are
# story-identity, not stage-specific).
STAGE_FOCUS: dict[Stage, str] = {
    Stage.DREAM: "expanding a bare premise into the creative contract — "
    "genre, tone, themes, audience, content boundaries.",
    Stage.BRAINSTORM: "inventing the cast and the dramatic dilemmas; "
    "every entity must anchor a dilemma.",
    Stage.SEED: "triaging dilemmas (branched or locked) and scaffolding "
    "each into its paths, beats, and endings.",
    Stage.GROW: "weaving the dilemma scaffolds into one story DAG — "
    "interleaving, intersections, bridge beats.",
    Stage.POLISH: "compiling frozen beats into passages and choices — "
    "residue, variants, pacing diamonds, ending titles.",
    Stage.FILL: "locking the story's voice, then writing every passage's "
    "prose.",
    Stage.DRESS: "art direction, illustration briefs, the diegetic codex, "
    "and codewords.",
}


def corpus_root(cfg: CraftConfig, project_root: Path) -> Path:
    """`craft.corpus` is absolute or project-relative."""
    root = Path(cfg.corpus)
    return root if root.is_absolute() else project_root / root


def _require_library() -> None:
    """Fail loud, before any LLM spend, when a corpus is configured but
    the retrieval library is missing — the corpus-less path never gets
    here (skip_if fires first), so base installs stay dependency-free."""
    try:
        import markdown_vault_mcp  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "a craft corpus is configured but markdown-vault-mcp is not "
            "installed — install the 'craft' extra (questfoundry[craft])"
        ) from exc


def digest_fresh(text: str, project: Project) -> bool:
    """A17 freshness: the digest was retrieved from the current corpus
    with the current standing queries. Either drifting means the world
    the digest described is gone — re-retrieve. Malformed metadata is
    stale, never fatal (the tolerant half of the A16 staleness contract).
    """
    cfg = project.craft
    if cfg is None:
        return False
    try:
        meta = digest_meta(text)
        stage = Stage(meta.get("stage", ""))
    except ValueError:
        return False
    root = corpus_root(cfg, project.root)
    return meta.get("corpus_fingerprint") == corpus_fingerprint(cfg, root) and meta.get(
        "standing_queries", []
    ) == standing_queries(project.vision, stage)


def research_pass(stage: Stage) -> PassSpec:
    """The head pass of every stage when a corpus is configured: the
    librarian proposes queries, apply retrieves and sets the digest.
    Note the runner dispatches `skip_if` before keep/resume replay
    (`runner.run_stage`), which is what makes the freshness skip
    (mini-ADR A17) take precedence over a stale ledger entry.
    """

    def _skip(project: Project) -> str | None:
        if project.craft is None:
            return "no craft corpus configured"
        existing = project.research.get(stage.value)
        if existing is not None and digest_fresh(existing, project):
            return f"digest is fresh (delete research/{stage.value}.md to re-retrieve)"
        return None

    def _context(project: Project) -> dict:
        _require_library()
        cfg = project.craft
        root = corpus_root(cfg, project.root)
        if not root.is_dir():
            raise RuntimeError(f"craft corpus not found at {root} (craft.corpus in project.yaml)")
        standing = standing_queries(project.vision, stage)
        return {
            "stage": stage.value,
            "stage_focus": STAGE_FOCUS[stage],
            # A placeholder vision (DREAM's head) yields no standing
            # queries; the prompt then grounds on the premise instead.
            "vision": project.vision if standing else None,
            "premise": project.vision.premise,
            "standing": standing,
            "max_queries": cfg.max_queries,
        }

    def _apply(proposal: ResearchProposal, project: Project) -> list[str]:
        cfg = project.craft
        if len(proposal.queries) > cfg.max_queries:
            raise ApplyError(
                f"{len(proposal.queries)} queries exceed the cap of "
                f"{cfg.max_queries}; keep only the sharpest"
            )
        standing = standing_queries(project.vision, stage)
        taken = {q.casefold() for q in standing}
        librarian: list[str] = []
        dropped = 0
        for q in proposal.queries:
            text = q.query.strip()
            if not text or text.casefold() in taken:
                dropped += 1
                continue
            taken.add(text.casefold())
            librarian.append(text)
        root = corpus_root(cfg, project.root)
        queries = [("standing", q) for q in standing] + [("librarian", q) for q in librarian]
        digest = retrieve(cfg, root, project.root / "cache" / "research", stage, queries)
        project.research[stage.value] = digest
        meta = digest_meta(digest)
        lines = [
            f"corpus {meta['corpus_fingerprint'][:12]}: "
            f"{len(standing)} standing + {len(librarian)} librarian queries, "
            f"{len(meta['sources'])} source note(s)"
        ]
        if dropped:
            lines.append(f"{dropped} duplicate/empty librarian query(ies) dropped")
        return lines

    return PassSpec(
        name="research",
        role="architect",
        template="research.j2",
        schema=ResearchProposal,
        build_context=_context,
        apply=_apply,
        skip_if=_skip,
    )


def with_research(impl: StageImpl) -> StageImpl:
    """Prepend the research pass. Callable pass lists stay callable and
    are resolved per run — DRESS builds per-run review closures and FILL
    its per-project queue inside theirs; resolving eagerly here would
    freeze that state across runs."""
    head = research_pass(impl.stage)
    if callable(impl.passes):
        original = impl.passes

        def passes(project: Project) -> tuple[PassSpec, ...]:
            return (head, *original(project))

    else:
        passes = (head, *impl.passes)
    return StageImpl(stage=impl.stage, passes=passes, gate=impl.gate)
