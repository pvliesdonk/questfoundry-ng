"""SEED scaffold apply: proposal-shape rules the repair loop can act on.
Violating constructions from the first thinking-off Sonnet 5 run
(2026-07-09), which marked endings on one hard dilemma's tails but not
the other's and under-built a soft arm — both undetected until GROW's
unrepairable gate."""

from __future__ import annotations

import pytest

from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.concept import Vision
from questfoundry.models.drama import DilemmaRole
from questfoundry.pipeline.stages.seed import (
    BeatSpec,
    DilemmaScaffold,
    PathScaffold,
    ScaffoldProposal,
    _scaffold_apply,
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
