"""SEED scaffold apply: proposal-shape rules the repair loop can act on.
Violating constructions from the first thinking-off Sonnet 5 run
(2026-07-09), which marked endings on one hard dilemma's tails but not
the other's and under-built a soft arm — both undetected until GROW's
unrepairable gate."""

from __future__ import annotations

import pytest

from questfoundry.graph import queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.concept import Vision
from questfoundry.models.drama import DilemmaRole
from questfoundry.pipeline.stages.seed import (
    BeatSpec,
    ConsequenceSpec,
    DilemmaScaffold,
    LockedScaffold,
    LockSpec,
    PathScaffold,
    PathSpec,
    ScaffoldProposal,
    TriageProposal,
    _scaffold_apply,
    _triage_apply,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.conftest import make_dilemma


def _spec(slug: str, is_ending: bool = False) -> BeatSpec:
    return BeatSpec(id=f"beat:{slug}", summary=slug, is_ending=is_ending)


def _y(dilemma: str, slug: str, *, tail_endings: bool, payoff: int = 1) -> DilemmaScaffold:
    return DilemmaScaffold(
        dilemma=dilemma,
        pre_commit=[_spec(f"{slug}-pre")],
        paths=[
            PathScaffold(
                path=f"path:{slug}-{side}",
                commit=_spec(f"{slug}-commit-{side}"),
                post_commit=[
                    *(_spec(f"{slug}-post-{side}-{i}") for i in range(payoff - 1)),
                    _spec(f"{slug}-end-{side}", is_ending=tail_endings),
                ],
            )
            for side in ("a", "b")
        ],
    )


def _project(tmp_path, role: DilemmaRole, scope: str = "micro") -> tuple[Project, str]:
    g = StoryGraph()
    did, _, _ = make_dilemma(g, "x", role=role)
    vision = Vision(premise="t", genre="t", tone="t", scope=scope)
    return Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g), did


def test_hard_path_tail_must_be_ending(tmp_path):
    project, did = _project(tmp_path, DilemmaRole.HARD)
    with pytest.raises(ApplyError, match="must set is_ending"):
        _scaffold_apply(ScaffoldProposal(scaffolds=[_y(did, "x", tail_endings=False)]), project)


def test_ending_off_a_hard_tail_is_rejected(tmp_path):
    project, did = _project(tmp_path, DilemmaRole.SOFT)
    with pytest.raises(ApplyError, match="not a hard path's final"):
        _scaffold_apply(ScaffoldProposal(scaffolds=[_y(did, "x", tail_endings=True)]), project)


def test_soft_path_needs_scope_payoff_beats(tmp_path):
    project, did = _project(tmp_path, DilemmaRole.SOFT, scope="medium")
    with pytest.raises(ApplyError, match="requires >= 2"):
        _scaffold_apply(
            ScaffoldProposal(scaffolds=[_y(did, "x", tail_endings=False, payoff=1)]), project
        )


def test_scaffold_shape_errors_arrive_batched(tmp_path):
    """Every shape violation in one ApplyError: reporting one arm per
    repair round is whack-a-mole — the model fixes the named arm while a
    sibling has the same defect (live run 7 lost SEED to this)."""
    g = StoryGraph()
    d1, _, _ = make_dilemma(g, "x", role=DilemmaRole.SOFT)
    d2, _, _ = make_dilemma(g, "y", role=DilemmaRole.SOFT)
    vision = Vision(premise="t", genre="t", tone="t", scope="medium")
    project = Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)
    with pytest.raises(ApplyError) as exc:
        _scaffold_apply(
            ScaffoldProposal(
                scaffolds=[
                    _y(d1, "x", tail_endings=False, payoff=1),
                    _y(d2, "y", tail_endings=False, payoff=1),
                ]
            ),
            project,
        )
    # both under-built arms named in the same repair round
    assert "dilemma:x" in str(exc.value) and "dilemma:y" in str(exc.value)


# -- triage dispositions (branched vs locked; design doc 01 §4) --------------


def _path(slug: str, answer: str) -> PathSpec:
    return PathSpec(
        id=f"path:{slug}",
        explores=answer,
        consequences=[ConsequenceSpec(id=f"consequence:{slug}", text="t")],
    )


def _triage_project(tmp_path, *, extra_soft: int = 1) -> Project:
    g = StoryGraph()
    make_dilemma(g, "main", role=DilemmaRole.HARD, explore=0)
    make_dilemma(g, "sub", explore=0)
    for i in range(extra_soft):
        make_dilemma(g, f"herring{i}", explore=0)
    vision = Vision(premise="t", genre="t", tone="t", scope="micro")
    return Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)


def _branch_both(slug: str) -> list[PathSpec]:
    return [_path(f"{slug}-{s}", f"answer:{slug}-{s}") for s in ("a", "b")]


def test_triage_locked_disposition_applies(tmp_path):
    project = _triage_project(tmp_path)
    proposal = TriageProposal(
        locked=[LockSpec(dilemma="dilemma:herring0", reason="red herring")],
        paths=[*_branch_both("main"), *_branch_both("sub"), _path("h", "answer:herring0-a")],
    )
    lines = _triage_apply(proposal, project)
    assert queries.locked_dilemmas(project.graph) == ["dilemma:herring0"]
    assert queries.branched_dilemmas(project.graph) == ["dilemma:main", "dilemma:sub"]
    assert any("locked: dilemma:herring0" in line for line in lines)


def test_triage_single_path_needs_a_lock_entry(tmp_path):
    project = _triage_project(tmp_path)
    proposal = TriageProposal(
        paths=[*_branch_both("main"), *_branch_both("sub"), _path("h", "answer:herring0-a")],
    )
    with pytest.raises(ApplyError, match="declare it in locked"):
        _triage_apply(proposal, project)


def test_triage_locked_with_both_answers_rejected(tmp_path):
    project = _triage_project(tmp_path, extra_soft=0)
    proposal = TriageProposal(
        locked=[LockSpec(dilemma="dilemma:sub", reason="r")],
        paths=[*_branch_both("main"), *_branch_both("sub")],
    )
    with pytest.raises(ApplyError, match="explores exactly one"):
        _triage_apply(proposal, project)


def test_triage_undisposed_dilemma_rejected(tmp_path):
    project = _triage_project(tmp_path)
    proposal = TriageProposal(paths=[*_branch_both("main"), *_branch_both("sub")])
    with pytest.raises(ApplyError, match="has no path"):
        _triage_apply(proposal, project)


def test_triage_locking_a_budgeted_role_leaves_a_shortfall(tmp_path):
    project = _triage_project(tmp_path, extra_soft=0)
    proposal = TriageProposal(
        locked=[LockSpec(dilemma="dilemma:main", reason="r")],
        paths=[_path("main-a", "answer:main-a"), *_branch_both("sub")],
    )
    with pytest.raises(ApplyError, match="exactly 1 hard dilemma"):
        _triage_apply(proposal, project)


def test_triage_locked_allowance_enforced(tmp_path):
    project = _triage_project(tmp_path, extra_soft=2)  # micro allows 1 locked
    proposal = TriageProposal(
        locked=[
            LockSpec(dilemma="dilemma:herring0", reason="r"),
            LockSpec(dilemma="dilemma:herring1", reason="r"),
        ],
        paths=[
            *_branch_both("main"),
            *_branch_both("sub"),
            _path("h0", "answer:herring0-a"),
            _path("h1", "answer:herring1-b"),
        ],
    )
    with pytest.raises(ApplyError, match="at most 1 locked"):
        _triage_apply(proposal, project)


# -- locked scaffolds ---------------------------------------------------------


def _locked_project(tmp_path) -> tuple[Project, str, str]:
    g = StoryGraph()
    did, path, _ = make_dilemma(g, "lock", explore=1)
    vision = Vision(premise="t", genre="t", tone="t", scope="micro")
    return Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g), did, path


def _locked(dilemma: str, path: str, *, ending: bool = False) -> LockedScaffold:
    return LockedScaffold(
        dilemma=dilemma,
        path=path,
        lead_in=[_spec("lock-lead")],
        resolution=_spec("lock-resolve"),
        aftermath=[_spec("lock-after", is_ending=ending)],
    )


def test_locked_scaffold_applies_as_a_chain(tmp_path):
    project, did, path = _locked_project(tmp_path)
    lines = _scaffold_apply(
        ScaffoldProposal(scaffolds=[], locked_scaffolds=[_locked(did, path)]), project
    )
    assert any("(locked): chain of 3 beat(s)" in line for line in lines)
    g = project.graph
    assert queries.commit_beats(g, path) == ["beat:lock-resolve"]
    assert queries.successors(g, "beat:lock-lead") == ["beat:lock-resolve"]
    assert queries.successors(g, "beat:lock-resolve") == ["beat:lock-after"]


def test_locked_scaffold_must_cover_every_locked_dilemma(tmp_path):
    project, _, _ = _locked_project(tmp_path)
    with pytest.raises(ApplyError, match="locked_scaffolds must cover"):
        _scaffold_apply(ScaffoldProposal(scaffolds=[]), project)


def test_locked_chain_must_not_end_the_story(tmp_path):
    project, did, path = _locked_project(tmp_path)
    with pytest.raises(ApplyError, match="locked storyline"):
        _scaffold_apply(
            ScaffoldProposal(scaffolds=[], locked_scaffolds=[_locked(did, path, ending=True)]),
            project,
        )


def test_locked_scaffold_must_name_the_explored_path(tmp_path):
    project, did, _ = _locked_project(tmp_path)
    with pytest.raises(ApplyError, match="must name its explored path"):
        _scaffold_apply(
            ScaffoldProposal(
                scaffolds=[], locked_scaffolds=[_locked(did, "path:lock-b")]
            ),
            project,
        )


def test_conforming_scaffolds_apply(tmp_path):
    project, did = _project(tmp_path, DilemmaRole.HARD)
    lines = _scaffold_apply(ScaffoldProposal(scaffolds=[_y(did, "x", tail_endings=True)]), project)
    assert any("Y with 1 shared beat(s)" in line for line in lines)
    soft_project, soft_did = _project(tmp_path / "soft", DilemmaRole.SOFT, scope="medium")
    lines = _scaffold_apply(
        ScaffoldProposal(scaffolds=[_y(soft_did, "x", tail_endings=False, payoff=2)]),
        soft_project,
    )
    assert any("3 + 3 exclusive" in line for line in lines)
