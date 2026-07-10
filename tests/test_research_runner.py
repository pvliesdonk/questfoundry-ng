"""M6 runner integration (design doc 02 §1, mini-ADR A13/A17): the
research pass exercised through the real `pipeline.runner` loop —
checkpoints, `--keep`, crash resume, `prepare_rerun`, and the A16 stage
fingerprint. Uses the low-level `runner.run_stage` harness (see
`test_runner.py`/`test_rerun.py`/`test_resume.py`) with a real corpus
(`tests/fixtures/corpus`, keyword mode — no embedding provider needed)
rather than the full keeper e2e fixtures, so each behavior stays
isolated and cheap.
"""

from __future__ import annotations

import shutil

import pytest

from questfoundry.models.base import Stage
from questfoundry.models.craft import CraftConfig
from questfoundry.pipeline import research, runner
from questfoundry.pipeline.research import (
    ResearchProposal,
    ResearchQuery,
    digest_meta,
    with_research,
)
from questfoundry.pipeline.types import StageImpl
from questfoundry.project.io import load_project, save_project
from tests.conftest import CORPUS
from tests.test_runner import FakeAdapter, VisionProposal, _scaffold, _vision_pass


def _use_test_templates_with_research(monkeypatch) -> None:
    """Registers a `research.j2` alongside the plain `vision.j2` fixture
    template `_use_test_templates` wires up, so passes prepended by
    `with_research` can render through the same `DictLoader` seam."""
    from jinja2 import DictLoader, Environment, StrictUndefined

    from tests.test_runner import TEMPLATE_NAME, TEMPLATE_SOURCE

    env = Environment(
        loader=DictLoader(
            {
                TEMPLATE_NAME: TEMPLATE_SOURCE,
                "research.j2": (
                    "stage={{ stage }} premise={{ premise }}\n"
                    "{% for e in repair_errors %}Repair error: {{ e }}\n{% endfor %}"
                ),
            }
        ),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    monkeypatch.setattr(runner, "_environment", lambda: env)


def _dream_impl() -> StageImpl:
    return with_research(
        StageImpl(stage=Stage.DREAM, passes=(_vision_pass(),), gate=lambda p: [])
    )


def _craft(corpus=CORPUS) -> CraftConfig:
    return CraftConfig(corpus=str(corpus), search_mode="keyword", top_k=2, max_queries=5)


def _scaffold_with_craft(tmp_path, corpus=CORPUS):
    project = _scaffold(tmp_path)
    project.craft = _craft(corpus)
    save_project(project)  # persist the craft block before any crash simulation
    return project


# ---------------------------------------------------------------------------
# checkpoint + report
# ---------------------------------------------------------------------------


def test_snapshot_and_report_carry_the_research_digest(tmp_path, monkeypatch):
    _use_test_templates_with_research(monkeypatch)
    project = _scaffold_with_craft(tmp_path)
    adapter = FakeAdapter(
        [
            ResearchProposal(queries=[ResearchQuery(query="lighthouse isolation pacing")]),
            VisionProposal(audience="teens"),
        ]
    )

    report = runner.run_stage(project, _dream_impl(), adapter)

    assert report.success
    digest = (tmp_path / "research" / "dream.md").read_text(encoding="utf-8")
    assert digest.startswith("---\n")
    snap_digest = (tmp_path / "snapshots" / "dream" / "research" / "dream.md").read_text(
        encoding="utf-8"
    )
    assert snap_digest == digest

    fp = digest_meta(digest)["corpus_fingerprint"]
    report_text = (tmp_path / "reports" / "dream.md").read_text(encoding="utf-8")
    assert fp[:12] in report_text


# ---------------------------------------------------------------------------
# --keep research
# ---------------------------------------------------------------------------


def test_keep_research_replays_without_an_llm_call_byte_identical(tmp_path, monkeypatch):
    _use_test_templates_with_research(monkeypatch)
    craft = _craft()
    query_payload = {"queries": [{"query": "lighthouse isolation pacing", "reason": ""}]}

    # Reference: what a live apply of this exact proposal produces.
    reference = _scaffold(tmp_path / "reference")
    reference.craft = craft
    spec = research.research_pass(Stage.DREAM)
    spec.apply(ResearchProposal.model_validate(query_payload), reference)
    reference_digest = reference.research[Stage.DREAM.value]

    project = _scaffold_with_craft(tmp_path / "kept", corpus=CORPUS)
    adapter = FakeAdapter([VisionProposal(audience="teens")])  # only "vision" may call

    report = runner.run_stage(project, _dream_impl(), adapter, keep={"research": query_payload})

    assert report.success
    assert report.passes[0].name == "research"
    assert report.passes[0].attempts == 0
    assert report.passes[0].applied[0].startswith("kept: corpus ")
    assert project.research[Stage.DREAM.value] == reference_digest
    assert (tmp_path / "kept" / "research" / "dream.md").read_text(
        encoding="utf-8"
    ) == reference_digest


# ---------------------------------------------------------------------------
# prepare_rerun
# ---------------------------------------------------------------------------


def test_prepare_rerun_preserves_target_digest_and_restores_the_rest(tmp_path, monkeypatch):
    _use_test_templates_with_research(monkeypatch)
    project = _scaffold_with_craft(tmp_path)

    q1 = ResearchProposal(queries=[ResearchQuery(query="lighthouse isolation pacing")])
    runner.run_stage(project, _dream_impl(), FakeAdapter([q1, VisionProposal(audience="teens")]))
    assert project.stage == Stage.DREAM

    brainstorm_impl = with_research(
        StageImpl(stage=Stage.BRAINSTORM, passes=(_vision_pass("cast"),), gate=lambda p: [])
    )
    q2 = ResearchProposal(queries=[ResearchQuery(query="ensemble cast archetypes")])
    runner.run_stage(
        project, brainstorm_impl, FakeAdapter([q2, VisionProposal(audience="teens")])
    )
    assert project.stage == Stage.BRAINSTORM

    dream_digest_before = (tmp_path / "research" / "dream.md").read_text(encoding="utf-8")
    brainstorm_digest_before = (tmp_path / "research" / "brainstorm.md").read_text(
        encoding="utf-8"
    )

    # An on-disk clobber of a NON-target digest must be undone by the rewind.
    (tmp_path / "research" / "dream.md").write_text(
        "---\nstage: dream\n---\n\nclobbered\n", encoding="utf-8"
    )

    runner.prepare_rerun(tmp_path, Stage.BRAINSTORM)

    assert (tmp_path / "research" / "dream.md").read_text(encoding="utf-8") == dream_digest_before
    # the target's own digest survives untouched (mini-ADR A17)
    assert (tmp_path / "research" / "brainstorm.md").read_text(
        encoding="utf-8"
    ) == brainstorm_digest_before


# ---------------------------------------------------------------------------
# A16 stage fingerprint
# ---------------------------------------------------------------------------


def test_corpus_edit_changes_the_stage_fingerprint(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    project = _scaffold(tmp_path / "project")
    project.craft = _craft(corpus)

    before = runner._stage_fingerprint(project, "")
    (corpus / "craft" / "pacing.md").write_text("changed entirely\n")
    after = runner._stage_fingerprint(project, "")

    assert before != after


def test_corpus_less_project_fingerprint_ignores_an_unconfigured_corpus_dir(tmp_path):
    """`craft` off (the common case) must fingerprint byte-identically to
    pre-M6 regardless of what happens to sit on disk — only `project.craft`
    (the `craft:` block) may add the "craft" knob, never a directory's mere
    presence."""
    with_dir = _scaffold(tmp_path / "with-dir")
    (tmp_path / "with-dir" / "unrelated-corpus-looking-dir").mkdir()
    without_dir = _scaffold(tmp_path / "without-dir")

    assert with_dir.craft is None
    assert without_dir.craft is None
    assert runner._stage_fingerprint(with_dir, "") == runner._stage_fingerprint(without_dir, "")


# ---------------------------------------------------------------------------
# crash resume
# ---------------------------------------------------------------------------


def test_crash_after_research_pass_resumes_with_zero_adapter_calls(tmp_path, monkeypatch):
    _use_test_templates_with_research(monkeypatch)
    q = ResearchProposal(queries=[ResearchQuery(query="lighthouse isolation pacing")])

    control = _scaffold_with_craft(tmp_path / "control")
    runner.run_stage(control, _dream_impl(), FakeAdapter([q, VisionProposal(audience="teens")]))
    control_digest = (tmp_path / "control" / "research" / "dream.md").read_text(encoding="utf-8")

    project = _scaffold_with_craft(tmp_path / "crashed")
    impl = _dream_impl()
    with pytest.raises(IndexError):
        # the research pass lands (queue exhausted right after); the
        # vision pass then dies calling an adapter with nothing left
        runner.run_stage(project, impl, FakeAdapter([q]))

    assert project.stage == Stage.NEW  # never advanced
    ledger_entry = tmp_path / "crashed" / "inflight" / "dream" / "proposals" / "research.json"
    assert ledger_entry.exists()
    assert not (tmp_path / "crashed" / "research" / "dream.md").exists()  # no gate, no checkpoint

    resumed = load_project(tmp_path / "crashed")
    adapter = FakeAdapter([VisionProposal(audience="teens")])
    report = runner.run_stage(resumed, impl, adapter)

    assert report.success
    assert report.passes[0].name == "research"
    assert report.passes[0].attempts == 0
    assert report.passes[0].applied[0].startswith("resumed: corpus ")
    assert len(adapter.prompts) == 1  # only the vision pass ever reached the adapter
    resumed_digest = (tmp_path / "crashed" / "research" / "dream.md").read_text(encoding="utf-8")
    assert resumed_digest == control_digest
