"""Craft-corpus retrieval core (design doc 02 §1 "Craft context", 03 §10).

Determinism is the acceptance bar here: two `retrieve()` calls with the
same inputs must return byte-identical digest markdown, because those
bytes enter the next stage's content fingerprint (mini-ADR A13)."""

from __future__ import annotations

import re
import shutil

import pytest

from questfoundry.models.base import Stage
from questfoundry.models.concept import Vision
from questfoundry.models.craft import CraftConfig
from questfoundry.pipeline import research
from questfoundry.pipeline.research import ResearchProposal, ResearchQuery
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import scaffold_project
from tests.conftest import CORPUS, FakeEmbeddingProvider


def _vision(**overrides) -> Vision:
    defaults = dict(
        premise="A locksmith is asked to open a door she swore never to open again.",
        genre="gothic mystery",
        subgenre="locked-room",
        tone="tense, melancholy",
        themes=["trust", "the cost of secrets"],
        scope="micro",
    )
    defaults.update(overrides)
    return Vision(**defaults)


def _cfg(**overrides) -> CraftConfig:
    defaults = dict(corpus=str(CORPUS), top_k=4, words_per_query=200, search_mode="keyword")
    defaults.update(overrides)
    return CraftConfig(**defaults)


@pytest.fixture()
def fake_provider(monkeypatch):
    monkeypatch.setattr(research, "_embedding_provider", lambda cfg: FakeEmbeddingProvider())


# ---------------------------------------------------------------------------
# standing_queries
# ---------------------------------------------------------------------------


def test_standing_queries_none_vision_is_empty():
    assert research.standing_queries(None, Stage.BRAINSTORM) == []


def test_standing_queries_empty_at_dream_with_placeholder_vision():
    placeholder = Vision(premise="TODO: ...", genre="TODO", tone="TODO", scope="micro")
    assert research.standing_queries(placeholder, Stage.DREAM) == []


def test_standing_queries_empty_at_dream_even_with_a_filled_in_vision():
    # DREAM's head never actually holds a filled-in vision, but the rule
    # is keyed on stage too -- defensive against a future caller passing
    # one anyway (design doc 02 §1's DREAM amendment).
    assert research.standing_queries(_vision(), Stage.DREAM) == []


def test_standing_queries_empty_for_placeholder_fields_past_dream():
    placeholder = Vision(premise="TODO", genre="TODO", tone="TODO", scope="micro")
    assert research.standing_queries(placeholder, Stage.SEED) == []


def test_standing_queries_covers_genre_subgenre_tone_and_themes():
    qs = research.standing_queries(_vision(), Stage.BRAINSTORM)
    assert "gothic mystery locked-room" in qs
    assert "tense, melancholy" in qs
    assert "trust" in qs
    assert "the cost of secrets" in qs


def test_standing_queries_no_subgenre_falls_back_to_genre_only():
    qs = research.standing_queries(_vision(subgenre=""), Stage.BRAINSTORM)
    assert "gothic mystery" in qs


def test_standing_queries_strips_empty_and_todo_themes():
    v = _vision(themes=["trust", "", "TODO", "TODO: fill in later"])
    qs = research.standing_queries(v, Stage.BRAINSTORM)
    assert qs.count("trust") == 1
    assert "" not in qs
    assert not any(q.upper().startswith("TODO") for q in qs)


def test_standing_queries_deterministic():
    v = _vision()
    assert research.standing_queries(v, Stage.BRAINSTORM) == research.standing_queries(
        v, Stage.BRAINSTORM
    )


def test_standing_queries_same_for_every_stage_from_brainstorm_on():
    v = _vision()
    baseline = research.standing_queries(v, Stage.SEED)
    for stage in (Stage.BRAINSTORM, Stage.GROW, Stage.POLISH, Stage.FILL, Stage.DRESS):
        assert research.standing_queries(v, stage) == baseline


# ---------------------------------------------------------------------------
# corpus_fingerprint
# ---------------------------------------------------------------------------


def test_corpus_fingerprint_stable_across_runs():
    cfg = _cfg()
    assert research.corpus_fingerprint(cfg, CORPUS) == research.corpus_fingerprint(cfg, CORPUS)


def test_corpus_fingerprint_changes_when_a_file_changes(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    cfg = _cfg(corpus=str(corpus))
    before = research.corpus_fingerprint(cfg, corpus)
    note = corpus / "craft" / "pacing.md"
    note.write_text(note.read_text() + "\nOne more line.\n")
    after = research.corpus_fingerprint(cfg, corpus)
    assert before != after


def test_corpus_fingerprint_ignores_out_of_scope_folders(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    cfg = _cfg(corpus=str(corpus), folders=["craft"])
    before = research.corpus_fingerprint(cfg, corpus)
    (corpus / "offtopic" / "tabletop.md").write_text("changed entirely\n")
    after = research.corpus_fingerprint(cfg, corpus)
    assert before == after


def test_corpus_fingerprint_reacts_to_change_inside_scoped_folder(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    cfg = _cfg(corpus=str(corpus), folders=["craft"])
    before = research.corpus_fingerprint(cfg, corpus)
    (corpus / "craft" / "pacing.md").write_text("changed entirely\n")
    after = research.corpus_fingerprint(cfg, corpus)
    assert before != after


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------


def test_retrieve_keyword_mode_needs_no_provider(tmp_path, monkeypatch):
    def _boom(cfg):
        raise AssertionError("keyword mode must not need an embedding provider")

    monkeypatch.setattr(research, "_embedding_provider", _boom)
    cfg = _cfg(search_mode="keyword", top_k=2)
    text = research.retrieve(
        cfg, CORPUS, tmp_path / "cache", Stage.BRAINSTORM, [("standing", "branching pacing")]
    )
    assert "## branching pacing" in text


def test_retrieve_honors_top_k(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=1, folders=["craft"])
    text = research.retrieve(
        cfg,
        CORPUS,
        tmp_path / "cache",
        Stage.BRAINSTORM,
        [("standing", "structure pacing branching endings dilemma")],
    )
    body = research.digest_body(text)
    assert body.count("### ") <= 1


def test_retrieve_folder_scoping_excludes_offtopic(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=4, folders=["craft", "style"])
    text = research.retrieve(
        cfg,
        CORPUS,
        tmp_path / "cache",
        Stage.BRAINSTORM,
        [("standing", "encounter budgeting tabletop session")],
    )
    # The query text itself echoes "tabletop" into the frontmatter, so
    # check the body (source-attributed snippets) and source list, not
    # the raw digest text.
    body = research.digest_body(text)
    assert "offtopic" not in body
    meta = research.digest_meta(text)
    assert all("offtopic" not in src for src in meta["sources"])


def test_retrieve_words_per_query_truncation(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=4, words_per_query=15, folders=["craft"])
    text = research.retrieve(
        cfg,
        CORPUS,
        tmp_path / "cache",
        Stage.BRAINSTORM,
        [("standing", "pacing commit beats spacing quiet")],
    )
    body = research.digest_body(text)
    assert "### craft/pacing.md" in body  # a real match was found, not a vacuous pass
    snippet_words = sum(
        len(line.split())
        for line in body.splitlines()
        if line and not line.startswith(("#", "---"))
    )
    assert snippet_words <= 15


def test_retrieve_byte_identical_across_two_calls(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=3)
    queries = [("standing", "branching structure"), ("librarian", "voice tone diction")]
    first = research.retrieve(cfg, CORPUS, tmp_path / "cache-a", Stage.SEED, queries)
    second = research.retrieve(cfg, CORPUS, tmp_path / "cache-b", Stage.SEED, queries)
    assert first == second


def test_retrieve_fresh_vs_warm_cache_dir_same_digest(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=2)
    queries = [("standing", "endings salience")]
    cache = tmp_path / "cache"
    first = research.retrieve(cfg, CORPUS, cache, Stage.GROW, queries)
    second = research.retrieve(cfg, CORPUS, cache, Stage.GROW, queries)  # warm reuse
    assert first == second


def test_retrieve_multi_folder_merge_is_stable(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=4, folders=["craft", "style"])
    queries = [("standing", "voice tone pacing branching")]
    first = research.retrieve(cfg, CORPUS, tmp_path / "cache-1", Stage.SEED, queries)
    second = research.retrieve(cfg, CORPUS, tmp_path / "cache-2", Stage.SEED, queries)
    assert first == second


def test_retrieve_hybrid_mode_uses_embedding_provider_seam(tmp_path, fake_provider):
    cfg = _cfg(search_mode="hybrid", top_k=2)
    text = research.retrieve(
        cfg, CORPUS, tmp_path / "cache", Stage.SEED, [("standing", "narrative voice register")]
    )
    assert "## narrative voice register" in text


def test_retrieve_hybrid_mode_byte_identical_across_two_calls(tmp_path, fake_provider):
    cfg = _cfg(search_mode="hybrid", top_k=3, folders=["style"])
    queries = [("standing", "voice diction register tone")]
    first = research.retrieve(cfg, CORPUS, tmp_path / "cache-a", Stage.SEED, queries)
    second = research.retrieve(cfg, CORPUS, tmp_path / "cache-b", Stage.SEED, queries)
    assert first == second


def test_retrieve_frontmatter_has_required_keys(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=2, folders=["craft"])
    text = research.retrieve(
        cfg,
        CORPUS,
        tmp_path / "cache",
        Stage.SEED,
        [("standing", "pacing"), ("librarian", "dilemma stakes")],
    )
    meta = research.digest_meta(text)
    for key in (
        "stage",
        "corpus_fingerprint",
        "standing_queries",
        "librarian_queries",
        "top_k",
        "sources",
    ):
        assert key in meta
    assert meta["stage"] == "seed"
    assert meta["standing_queries"] == ["pacing"]
    assert meta["librarian_queries"] == ["dilemma stakes"]
    assert meta["top_k"] == 2
    assert meta["sources"] == sorted(meta["sources"])


def test_retrieve_no_timestamp_like_content(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=2)
    text = research.retrieve(cfg, CORPUS, tmp_path / "cache", Stage.SEED, [("standing", "pacing")])
    assert not re.search(r"\d{4}-\d{2}-\d{2}", text)
    assert not re.search(r"\d{2}:\d{2}:\d{2}", text)


def test_retrieve_no_matches_still_renders_section(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=2)
    text = research.retrieve(
        cfg, CORPUS, tmp_path / "cache", Stage.SEED, [("standing", "xyzzy nonexistent gibberish")]
    )
    assert "## xyzzy nonexistent gibberish" in text
    assert "(no matches)" in text


# ---------------------------------------------------------------------------
# digest_body / digest_meta
# ---------------------------------------------------------------------------


def test_digest_round_trip(tmp_path):
    cfg = _cfg(search_mode="keyword", top_k=2, folders=["craft"])
    text = research.retrieve(cfg, CORPUS, tmp_path / "cache", Stage.SEED, [("standing", "pacing")])
    body = research.digest_body(text)
    assert body.startswith("## pacing")
    meta = research.digest_meta(text)
    assert isinstance(meta, dict)
    assert meta["stage"] == "seed"


def test_digest_meta_ignores_body():
    text = "---\nstage: seed\ntop_k: 3\n---\n\n## a query\n\nsome body text\n"
    assert research.digest_meta(text) == {"stage": "seed", "top_k": 3}
    assert research.digest_body(text) == "## a query\n\nsome body text\n"


# ---------------------------------------------------------------------------
# research_pass: skip_if matrix (mini-ADR A17)
# ---------------------------------------------------------------------------


def _rp_project(tmp_path, craft: CraftConfig | None = None, vision: Vision | None = None):
    project = scaffold_project(tmp_path, "t", "micro")
    if vision is not None:
        project.vision = vision
    project.craft = craft
    return project


def test_skip_when_no_craft_corpus_configured(tmp_path):
    project = _rp_project(tmp_path)
    spec = research.research_pass(Stage.BRAINSTORM)
    reason = spec.skip_if(project)
    assert reason is not None
    assert "no craft corpus" in reason


def test_runs_when_corpus_configured_and_no_digest_yet(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    assert spec.skip_if(project) is None


def test_skips_when_the_digest_is_fresh(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    spec.apply(ResearchProposal(queries=[]), project)

    reason = spec.skip_if(project)
    assert reason is not None
    assert "fresh" in reason
    assert "research/brainstorm.md" in reason


def test_runs_again_when_the_corpus_content_changes(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    project = _rp_project(tmp_path / "project", craft=_cfg(corpus=str(corpus)), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    spec.apply(ResearchProposal(queries=[]), project)
    assert spec.skip_if(project) is not None  # fresh right after apply

    (corpus / "craft" / "pacing.md").write_text("changed entirely\n")

    assert spec.skip_if(project) is None  # corpus fingerprint drifted -> stale


def test_runs_again_when_a_vision_edit_changes_standing_queries(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    spec.apply(ResearchProposal(queries=[]), project)
    assert spec.skip_if(project) is not None  # fresh right after apply

    project.vision.themes = ["an entirely different theme"]

    assert spec.skip_if(project) is None  # standing queries drifted -> stale


def test_dream_head_never_skips_for_freshness_reasons_it_still_runs_once(tmp_path):
    """DREAM's context has no vision yet (design doc 02 §1's DREAM
    amendment): standing_queries() is always [] there, so DREAM's
    freshness keys on the premise hash instead — an unchanged premise
    reuses the digest, and the pass runs exactly once per DREAM attempt,
    same as any other stage."""
    project = _rp_project(tmp_path, craft=_cfg())
    spec = research.research_pass(Stage.DREAM)
    assert spec.skip_if(project) is None
    spec.apply(ResearchProposal(queries=[]), project)
    assert spec.skip_if(project) is not None


def test_dream_runs_again_when_the_premise_changes(tmp_path):
    """A premise-grounded digest records a premise hash (A17): editing
    the premise and rerunning DREAM must re-retrieve, not silently reuse
    research about a story that no longer exists."""
    project = _rp_project(tmp_path, craft=_cfg())
    spec = research.research_pass(Stage.DREAM)
    spec.apply(ResearchProposal(queries=[]), project)
    assert spec.skip_if(project) is not None  # fresh right after apply

    project.vision.premise = "An entirely different story about a clockwork whale."
    assert spec.skip_if(project) is None


def test_missing_library_fails_loud_naming_the_extra(tmp_path, monkeypatch):
    """A configured corpus with the retrieval library missing is
    invocation misconfiguration: RunnerError (the CLI's clean-error
    path), raised before any LLM spend."""
    import sys

    from questfoundry.pipeline.runner import RunnerError

    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    monkeypatch.setitem(sys.modules, "markdown_vault_mcp", None)
    with pytest.raises(RunnerError, match="craft"):
        research.research_pass(Stage.BRAINSTORM).build_context(project)


def test_missing_corpus_dir_fails_loud(tmp_path):
    from questfoundry.pipeline.runner import RunnerError

    project = _rp_project(
        tmp_path, craft=CraftConfig(corpus=str(tmp_path / "nope")), vision=_vision()
    )
    with pytest.raises(RunnerError, match="not found"):
        research.research_pass(Stage.BRAINSTORM).build_context(project)


# ---------------------------------------------------------------------------
# research_pass: apply behavior
# ---------------------------------------------------------------------------


def test_apply_rejects_too_many_queries(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(max_queries=2), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    proposal = ResearchProposal(
        queries=[ResearchQuery(query=q) for q in ("one", "two", "three")]
    )
    with pytest.raises(ApplyError, match="exceed the cap"):
        spec.apply(proposal, project)


def test_apply_drops_duplicate_of_standing_query_with_a_note(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    standing = research.standing_queries(project.vision, Stage.BRAINSTORM)
    proposal = ResearchProposal(
        queries=[
            ResearchQuery(query=standing[0].upper()),  # case-insensitive duplicate
            ResearchQuery(query="a genuinely new librarian query"),
        ]
    )
    lines = spec.apply(proposal, project)
    assert any("1 duplicate/empty librarian" in line for line in lines)
    meta = research.digest_meta(project.research[Stage.BRAINSTORM.value])
    assert meta["librarian_queries"] == ["a genuinely new librarian query"]


def test_apply_drops_empty_librarian_queries_with_a_note(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    proposal = ResearchProposal(queries=[ResearchQuery(query="   "), ResearchQuery(query="")])
    lines = spec.apply(proposal, project)
    assert any("2 duplicate/empty librarian" in line for line in lines)
    meta = research.digest_meta(project.research[Stage.BRAINSTORM.value])
    assert meta["librarian_queries"] == []


def test_apply_no_note_line_when_nothing_is_dropped(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    proposal = ResearchProposal(queries=[ResearchQuery(query="a fresh librarian query")])
    lines = spec.apply(proposal, project)
    assert not any("dropped" in line for line in lines)


def test_apply_lines_carry_the_corpus_fingerprint_prefix(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.BRAINSTORM)
    lines = spec.apply(ResearchProposal(queries=[]), project)
    meta = research.digest_meta(project.research[Stage.BRAINSTORM.value])
    assert lines[0].startswith(f"corpus {meta['corpus_fingerprint'][:12]}: ")


def test_apply_sets_project_research_for_the_stage(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.SEED)
    assert Stage.SEED.value not in project.research
    spec.apply(ResearchProposal(queries=[]), project)
    assert Stage.SEED.value in project.research
    assert project.research[Stage.SEED.value].startswith("---\n")


def test_reapplying_the_same_proposal_is_byte_identical(tmp_path):
    project = _rp_project(tmp_path, craft=_cfg(), vision=_vision())
    spec = research.research_pass(Stage.SEED)
    proposal = ResearchProposal(queries=[ResearchQuery(query="pacing and dilemma stakes")])
    spec.apply(proposal, project)
    first = project.research[Stage.SEED.value]
    spec.apply(proposal, project)
    second = project.research[Stage.SEED.value]
    assert first == second


# ---------------------------------------------------------------------------
# with_research
# ---------------------------------------------------------------------------


def test_every_impl_has_research_first_static_and_callable(golden):
    from questfoundry.pipeline.stages import IMPLS

    for stage, impl in IMPLS.items():
        passes = impl.passes(golden) if callable(impl.passes) else impl.passes
        assert passes[0].name == "research", stage


def test_dress_review_closures_are_fresh_per_passes_resolution(golden):
    from questfoundry.pipeline.review import ReviewFinding, ReviewVerdict
    from questfoundry.pipeline.stages import IMPLS
    from questfoundry.pipeline.stages.dress import CodexItem, CodexProposal

    def _fail(reason):
        return ReviewVerdict(
            verdict="needs_work",
            findings=[
                ReviewFinding(
                    rule="conditional_stated_as_fact",
                    assessment="fail",
                    confidence="high",
                    quote="the entry sentence",
                    reason=reason,
                    recovery_action="pose it as an open question",
                )
            ],
        )

    class ScriptedAdapter:
        def __init__(self, script):
            self.script = list(script)

        def complete(self, *, system, prompt, schema, role):
            return self.script.pop(0)

    dress_impl = IMPLS[Stage.DRESS]
    first = dress_impl.passes(golden)
    second = dress_impl.passes(golden)
    codex_first = next(p for p in first if p.name == "codex")
    codex_second = next(p for p in second if p.name == "codex")
    assert codex_first.review is not codex_second.review

    proposal = CodexProposal(entries=[CodexItem(entity="entity:x", title="t", body="b")])

    # codex_first's closure remembers this failure ...
    adapter1 = ScriptedAdapter([_fail("real defect")])
    assert "real defect" in codex_first.review(proposal, golden, adapter1)[0]

    # ... but codex_second is a brand-new closure (fresh `prior`): a single
    # failure resolves without arbitration, proving it did not inherit
    # codex_first's state. If the closures shared state this would try to
    # pop a second (architect) response from adapter2's one-item script
    # and raise IndexError instead.
    adapter2 = ScriptedAdapter([_fail("a different issue")])
    assert "a different issue" in codex_second.review(proposal, golden, adapter2)[0]


def test_with_research_preserves_fill_work_queue_after_the_head(golden):
    from questfoundry.pipeline.stages import IMPLS
    from questfoundry.pipeline.stages.fill import FILL_STAGE

    wrapped = IMPLS[Stage.FILL].passes(golden)
    original = FILL_STAGE.passes(golden)

    assert wrapped[0].name == "research"
    assert [p.name for p in wrapped[1:]] == [p.name for p in original]
    assert wrapped[1].name == "voice"
    assert any(p.name.startswith("write:") for p in wrapped)
