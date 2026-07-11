"""SEED scaffold apply: proposal-shape rules the repair loop can act on.
Violating constructions from the first thinking-off Sonnet 5 run
(2026-07-09), which marked endings on one hard dilemma's tails but not
the other's and under-built a soft arm — both undetected until GROW's
unrepairable gate."""

from __future__ import annotations

import copy

import pytest

from questfoundry.graph import queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.concept import Vision
from questfoundry.models.drama import Dilemma, DilemmaRole
from questfoundry.pipeline.stages.seed import (
    SEED_STAGE,
    BeatSpec,
    ConsequenceSpec,
    DilemmaScaffold,
    LockedScaffold,
    LockSpec,
    OrderProposal,
    PathScaffold,
    PathSpec,
    RelationSpec,
    ScaffoldProposal,
    TriageProposal,
    _order_apply,
    _scaffold_apply,
    _triage_apply,
    triage_proposal_schema,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.conftest import make_dilemma, make_locked_chain, make_y_scaffold


def _spec(slug: str, is_ending: bool = False) -> BeatSpec:
    return BeatSpec(id=f"beat:{slug}", summary=slug, is_ending=is_ending)


def _y(
    dilemma: str, slug: str, *, tail_endings: bool, payoff: int = 1, pre: int = 2
) -> DilemmaScaffold:
    return DilemmaScaffold(
        dilemma=dilemma,
        pre_commit=[_spec(f"{slug}-pre{i}") for i in range(pre)],
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
    with pytest.raises(ApplyError, match="requires >= 3"):
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


# -- triage schema: `explores` pinned to real answer ids (issue #40) ---------
# Two unrelated strong model families invented dangling answer slugs at
# triage and exhausted repairs (Ollama live validation, 2026-07-11); the
# enum makes the reference constraint schema-level for every provider.


def _answer_ids(project: Project) -> list[str]:
    g = project.graph
    return [a for d in g.nodes_of(Dilemma) for a in queries.answers_of(g, d.id)]


def _path_payload(slug: str, answer: str) -> dict:
    return {
        "id": f"path:{slug}",
        "explores": answer,
        "consequences": [{"id": f"consequence:{slug}", "text": "t"}],
    }


def test_triage_schema_rejects_dangling_explores(tmp_path):
    project = _triage_project(tmp_path)
    schema = triage_proposal_schema(_answer_ids(project))

    with pytest.raises(Exception) as exc:
        schema.model_validate(
            {"paths": [_path_payload("a", "answer:main-a"), _path_payload("b", "answer:open-gate")]}
        )
    # the correction brief inherits this message: the valid ids are named
    assert "answer:main-a" in str(exc.value)
    assert "answer:open-gate" in str(exc.value)


def test_triage_schema_accepts_real_answer_ids(tmp_path):
    project = _triage_project(tmp_path)
    schema = triage_proposal_schema(_answer_ids(project))

    proposal = schema.model_validate(
        {"paths": [_path_payload("a", "answer:main-a"), _path_payload("b", "answer:main-b")]}
    )
    assert isinstance(proposal, TriageProposal)  # apply-compatible via inheritance
    assert proposal.paths[1].explores == "answer:main-b"


def test_triage_schema_enum_keeps_graph_order(tmp_path):
    """Answers are strictly equal (iron rule 3): the enum's order is the
    graph's, never a ranking we impose."""
    project = _triage_project(tmp_path)
    ids = _answer_ids(project)
    schema = triage_proposal_schema(ids)

    defs = schema.model_json_schema()["$defs"]
    assert defs["PathSpec"]["properties"]["explores"]["enum"] == ids


def test_triage_schema_without_answers_falls_back_to_base(tmp_path):
    assert triage_proposal_schema([]) is TriageProposal


# -- triage schema: `locked[].dilemma` pinned to real dilemma ids ------------
# `explores`'s sibling. A live gpt-oss:120b-cloud --to seed run (Ollama
# cloud validation, 2026-07-11) cleared the #40 explores enum, then failed
# triage the identical way on `locked[].dilemma` (an unprefixed dilemma
# slug). Same discipline: pin the reference to the real dilemma ids.


def _dilemma_ids(project: Project) -> list[str]:
    return [d.id for d in project.graph.nodes_of(Dilemma)]


def test_triage_schema_rejects_dangling_locked_dilemma(tmp_path):
    project = _triage_project(tmp_path)
    schema = triage_proposal_schema(_answer_ids(project), _dilemma_ids(project))

    with pytest.raises(Exception) as exc:
        schema.model_validate(
            {
                "locked": [{"dilemma": "herring0", "reason": "red herring"}],
                "paths": [_path_payload("a", "answer:main-a"), _path_payload("b", "answer:main-b")],
            }
        )
    # the correction brief inherits this message: the valid ids are named
    assert "dilemma:herring0" in str(exc.value)


def test_triage_schema_accepts_real_locked_dilemma(tmp_path):
    project = _triage_project(tmp_path)
    schema = triage_proposal_schema(_answer_ids(project), _dilemma_ids(project))

    proposal = schema.model_validate(
        {
            "locked": [{"dilemma": "dilemma:herring0", "reason": "red herring"}],
            "paths": [_path_payload("a", "answer:main-a"), _path_payload("b", "answer:main-b")],
        }
    )
    assert isinstance(proposal, TriageProposal)  # apply-compatible via inheritance
    assert proposal.locked[0].dilemma == "dilemma:herring0"


def test_seed_stage_wires_dynamic_locked_enum(tmp_path):
    project = _triage_project(tmp_path)
    triage_spec = SEED_STAGE.passes(project)[0]

    with pytest.raises(Exception, match="dilemma:herring0"):
        triage_spec.schema.model_validate(
            {
                "locked": [{"dilemma": "herring0", "reason": "red herring"}],
                "paths": [_path_payload("a", "answer:main-a"), _path_payload("b", "answer:main-b")],
            }
        )


def test_seed_stage_wires_dynamic_triage_schema(tmp_path):
    project = _triage_project(tmp_path)
    triage_spec = SEED_STAGE.passes(project)[0]

    assert triage_spec.name == "triage"
    with pytest.raises(Exception, match="answer:main-a"):
        triage_spec.schema.model_validate(
            {"paths": [_path_payload("a", "answer:invented"), _path_payload("b", "answer:main-b")]}
        )


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


# -- order relations (weave feasibility; live run 8) --------------------------


def test_order_relations_that_wedge_the_weave_are_repairable(tmp_path):
    """Pairwise-acyclic relations can leave no feasible climax: live run 8
    chained serial(hard A, hard B) + serial(hard B, locked chain), so the
    locked storyline had to follow the only possible climax's resolution —
    and nothing may follow the endings. The order apply probes the weave
    so this dies in a repair round, not at GROW's unrepairable gate."""
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "fb", role=DilemmaRole.HARD)
    d2, p2a, p2b = make_dilemma(g, "al", role=DilemmaRole.HARD)
    dl, lpath, _ = make_dilemma(g, "cc", explore=1)
    make_y_scaffold(g, "fb", d1, p1a, p1b)
    make_y_scaffold(g, "al", d2, p2a, p2b)
    make_locked_chain(g, "cc", dl, lpath)
    vision = Vision(premise="t", genre="t", tone="t", scope="medium")
    project = Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)
    bad = OrderProposal(
        relations=[
            RelationSpec(kind="serial", a=d1, b=d2),
            RelationSpec(kind="serial", a=d2, b=dl),
        ]
    )
    # probe on a copy: the runner restores the graph on failed applies
    scratch = Project(
        root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=copy.deepcopy(g)
    )
    with pytest.raises(ApplyError, match="no valid interleaving"):
        _order_apply(bad, scratch)

    good = OrderProposal(
        relations=[
            RelationSpec(kind="serial", a=d1, b=d2),
            RelationSpec(kind="wraps", a=d2, b=dl),
        ]
    )
    lines = _order_apply(good, project)
    assert any("wraps" in line for line in lines)


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
        ScaffoldProposal(
            setup=[_spec("setup-0")], scaffolds=[], locked_scaffolds=[_locked(did, path)]
        ),
        project,
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
                setup=[_spec("setup-0")],
                scaffolds=[],
                locked_scaffolds=[_locked(did, "path:lock-b")],
            ),
            project,
        )


def test_conforming_scaffolds_apply(tmp_path):
    project, did = _project(tmp_path, DilemmaRole.HARD)
    lines = _scaffold_apply(
        ScaffoldProposal(setup=[_spec("setup-0")], scaffolds=[_y(did, "x", tail_endings=True)]),
        project,
    )
    assert any("Y with 2 shared beat(s)" in line for line in lines)
    soft_project, soft_did = _project(tmp_path / "soft", DilemmaRole.SOFT, scope="medium")
    lines = _scaffold_apply(
        ScaffoldProposal(
            setup=[_spec("setup-0"), _spec("setup-1")],
            scaffolds=[_y(soft_did, "x", tail_endings=False, payoff=3, pre=4)],
        ),
        soft_project,
    )
    assert any("4 + 4 exclusive" in line for line in lines)


def test_scaffold_depth_bands_are_enforced(tmp_path):
    """M8: chain depths come from the scope's ScaffoldShape and violations
    batch repairably — a medium scaffold at micro depths dies at SEED,
    not at GROW's unrepairable gate."""
    project, did = _project(tmp_path, DilemmaRole.HARD, scope="medium")
    with pytest.raises(ApplyError) as exc:
        _scaffold_apply(
            ScaffoldProposal(
                setup=[_spec("setup-0")],
                scaffolds=[_y(did, "x", tail_endings=True, payoff=1, pre=2)],
            ),
            project,
        )
    message = str(exc.value)
    assert "setup has 1 beat(s); scope 'medium' wants 2-3" in message
    assert "pre_commit has 2 beat(s); scope 'medium' wants 4-6" in message
    assert "post_commit has 1 beat(s); scope 'medium' wants 3-5" in message


def test_locked_chain_depth_bands_are_enforced(tmp_path):
    g = StoryGraph()
    did, path, _ = make_dilemma(g, "lock", explore=1)
    vision = Vision(premise="t", genre="t", tone="t", scope="medium")
    project = Project(root=tmp_path, name="t", stage=Stage.SEED, vision=vision, graph=g)
    with pytest.raises(ApplyError) as exc:
        _scaffold_apply(
            ScaffoldProposal(
                setup=[_spec("setup-0"), _spec("setup-1")],
                scaffolds=[],
                locked_scaffolds=[_locked(did, path)],
            ),
            project,
        )
    message = str(exc.value)
    assert "lead_in has 1 beat(s); scope 'medium' wants 3-5" in message
    assert "aftermath has 1 beat(s); scope 'medium' wants 2-3" in message
