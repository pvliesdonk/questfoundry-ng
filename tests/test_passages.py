"""POLISH's deterministic core: collapse, choice topology, residue and
false-branch splicing, variants for heavy residue. The golden story is
the oracle: the hand-authored passage layer is what the engine must
compute."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import DilemmaRole, ResidueWeight
from questfoundry.models.presentation import Passage
from questfoundry.models.structure import Beat, BeatClass, StructuralPurpose
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import _derive_flags
from questfoundry.pipeline.stages.polish import (
    AuditEntry,
    AuditProposal,
    LabelSpec,
    PassageSpec,
    PassagesProposal,
    VariantSpec,
    _audit_apply,
    _finalize_skip,
    _passages_apply,
    _variant_needs,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.conftest import make_dilemma
from tests.test_weave import scaffold


def test_collapse_reproduces_the_golden_grouping(golden):
    g = golden.graph
    computed = sorted(tuple(sorted(grp)) for grp in pc.collapse_groups(g))
    authored = sorted(
        tuple(sorted(queries.beats_of_passage(g, p.id))) for p in g.nodes_of(Passage)
    )
    assert computed == authored


def test_choice_topology_matches_the_golden_choices(golden):
    g = golden.graph
    groups = pc.collapse_groups(g)
    passage_of = {}
    for p in g.nodes_of(Passage):
        beats = frozenset(queries.beats_of_passage(g, p.id))
        passage_of[beats] = p.id
    computed = set()
    for a, b in pc.group_edges(groups, g):
        computed.add(
            (
                passage_of[frozenset(groups[a])],
                passage_of[frozenset(groups[b])],
                tuple(pc.choice_requires(g, groups[b])),
                tuple(pc.choice_grants(g, groups[b])),
            )
        )
    authored = {
        (e.src, e.dst, tuple(sorted(e.payload["requires"])), tuple(sorted(e.payload["grants"])))
        for e in g.edges
        if e.kind == EdgeKind.CHOICE
    }
    assert computed == authored


def test_convergence_needs_on_golden(golden):
    (need,) = pc.convergence_needs(golden.graph)
    assert need.dilemma == "dilemma:truth"
    assert need.weight == ResidueWeight.LIGHT
    assert need.rejoin == ("beat:tremor",)
    assert need.path_flags == {
        "path:tell": "flag:elias-knows",
        "path:hide": "flag:lie-between",
    }


def _woven_story(g: StoryGraph, sub_residue: ResidueWeight) -> None:
    """hard 'main' wrapping soft 'sub', woven so a shared main beat
    follows sub's diamond (the convergence lands on a shared beat)."""
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD, residue=ResidueWeight.HEAVY)
    d2, p2a, p2b = make_dilemma(g, "sub", role=DilemmaRole.SOFT, residue=sub_residue)
    scaffold(g, "main", d1, p1a, p1b)
    scaffold(g, "sub", d2, p2a, p2b, endings=False)
    mutations.add_dilemma_relation(g, EdgeKind.WRAPS, d1, d2)
    planned = weave.plan(g)
    chosen = next(
        order
        for order in weave.candidates(planned)
        if order.index("resolve:dilemma:sub") < order.index("pre:beat:main-pre1")
    )
    weave.realize(g, planned, chosen)
    _derive_flags(g)


def _proposal_for(g: StoryGraph) -> PassagesProposal:
    """Build a mechanically valid proposal for the current groups."""
    groups = pc.collapse_groups(g)
    variant_needs = _variant_needs(g)
    specs = []
    for i, group in enumerate(groups):
        needs = [flags for c, flags in variant_needs.items() if c in group]
        variants = [
            VariantSpec(flag=f, id=f"passage:p{i}-v{j}", summary=f"variant {j}")
            for j, f in enumerate(needs[0])
        ] if needs else []
        specs.append(
            PassageSpec(
                group=i,
                id=f"passage:p{i}",
                summary=f"group {i}",
                ending_title="An End" if pc.ending_beat(g, group) else "",
                variants=variants,
            )
        )
    labels = [
        LabelSpec.model_validate({"from": a, "to": b, "label": f"onward {a}-{b}"})
        for a, b in pc.group_edges(groups, g)
    ]
    return PassagesProposal(passages=specs, labels=labels)


def _polish_errors(g, vision) -> list:
    relevant = {"I10", "I11", "I12", "I13", "G4"}
    issues = run_checks(g, vision, Stage.POLISH)
    return [i for i in issues if i.severity == Severity.ERROR and i.check in relevant]


def test_heavy_residue_creates_gated_variants(vision, tmp_path):
    g = StoryGraph()
    _woven_story(g, ResidueWeight.HEAVY)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    assert _finalize_skip(project)  # heavy needs no residue beats; runs are short

    _passages_apply(_proposal_for(g), project)
    (convergence,) = [n.rejoin[0] for n in pc.convergence_needs(g)]
    holders = queries.passages_of_beat(g, convergence)
    assert len(holders) == 2
    va, vb = sorted(holders)
    linked = set(g.out_ids(va, EdgeKind.VARIANT_OF)) | set(g.in_ids(va, EdgeKind.VARIANT_OF))
    assert vb in linked
    # incoming choices are gated per variant, one flag each, disjoint
    gates = sorted(
        tuple(e.payload["requires"])
        for e in g.edges
        if e.kind == EdgeKind.CHOICE and e.dst in holders
    )
    assert gates == [("flag:sub-a",), ("flag:sub-b",)]

    proposal = AuditProposal(
        audit=[
            AuditEntry(passage=p.id, irrelevant=[])
            for p in sorted(g.nodes_of(Passage), key=lambda p: p.id)
            if pc.active_flags(g, queries.beats_of_passage(g, p.id))
        ]
    )
    _audit_apply(proposal, project)
    assert _polish_errors(g, vision) == []


def test_variants_missing_where_needed_is_repairable(vision, tmp_path):
    g = StoryGraph()
    _woven_story(g, ResidueWeight.HEAVY)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    proposal = _proposal_for(g)
    stripped = [spec.model_copy(update={"variants": []}) for spec in proposal.passages]
    with pytest.raises(ApplyError, match="heavy residue"):
        _passages_apply(PassagesProposal(passages=stripped, labels=proposal.labels), project)


def test_residue_insertion_preserves_convergence(vision):
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    (need,) = [n for n in pc.convergence_needs(g) if n.weight == ResidueWeight.LIGHT]
    mutations.freeze_topology(g)
    beat = Beat(
        id="beat:afterglow",
        created_by=Stage.POLISH,
        summary="s",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
        requires_flags=[need.path_flags["path:sub-a"]],
    )
    pc.insert_residue_beat(g, beat, "path:sub-a", need.rejoin)
    issues = run_checks(g, vision, Stage.GROW)
    assert [i for i in issues if i.check == "I9"] == []  # freeze intact
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:afterglow", need.rejoin[0])
    # gated beats become singleton passages
    groups = pc.collapse_groups(g)
    assert ["beat:afterglow"] in groups


def _fork_rejoin_story(g: StoryGraph, sub_residue: ResidueWeight) -> None:
    """Same story, woven so the soft diamond feeds the hard fork directly —
    no shared beat between sub's payoff and main's commits. The rejoin is
    per world (each hard commit)."""
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD, residue=sub_residue)
    d2, p2a, p2b = make_dilemma(g, "sub", role=DilemmaRole.SOFT, residue=sub_residue)
    scaffold(g, "main", d1, p1a, p1b)
    scaffold(g, "sub", d2, p2a, p2b, endings=False)
    mutations.add_dilemma_relation(g, EdgeKind.WRAPS, d1, d2)
    planned = weave.plan(g)
    chosen = next(
        order
        for order in weave.candidates(planned)
        if tuple(order[-2:]) == ("resolve:dilemma:sub", "resolve:dilemma:main")
    )
    weave.realize(g, planned, chosen)
    _derive_flags(g)


def test_fork_rejoin_frontier_is_per_world():
    g = StoryGraph()
    _fork_rejoin_story(g, ResidueWeight.LIGHT)
    assert queries.soft_rejoin_frontier(g, "dilemma:sub") == [
        "beat:main-commit-a",
        "beat:main-commit-b",
    ]
    assert queries.soft_convergence(g, "dilemma:sub") is None
    (need,) = pc.convergence_needs(g)
    assert need.rejoin == ("beat:main-commit-a", "beat:main-commit-b")


def test_residue_at_fork_rejoin_reaches_every_world(vision):
    """Violating construction (first fork-rejoin live story, 2026-07-08):
    a residue beat spliced before only one hard commit dead-ended every
    arc that took the other hard branch (I6)."""
    g = StoryGraph()
    _fork_rejoin_story(g, ResidueWeight.LIGHT)
    (need,) = pc.convergence_needs(g)
    mutations.freeze_topology(g)
    beat = Beat(
        id="beat:afterglow",
        created_by=Stage.POLISH,
        summary="s",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
        requires_flags=[need.path_flags["path:sub-a"]],
    )
    pc.insert_residue_beat(g, beat, "path:sub-a", need.rejoin)
    assert set(queries.successors(g, "beat:afterglow")) == set(need.rejoin)
    issues = run_checks(g, vision, Stage.GROW)
    errors = [i for i in issues if i.check in ("I6", "I9") and i.severity == Severity.ERROR]
    assert errors == []


def test_heavy_residue_at_fork_rejoin_is_reported_not_silent(vision, tmp_path):
    g = StoryGraph()
    _fork_rejoin_story(g, ResidueWeight.HEAVY)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    assert _variant_needs(g) == {}  # no convergence passage exists to hold variants
    _passages_apply(_proposal_for(g), project)
    issues = run_checks(g, vision, Stage.POLISH)
    assert any(i.check == "G4" and "hard fork" in i.message for i in issues)


def test_false_branch_splice_and_long_run_detection():
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    groups = pc.collapse_groups(g)
    long_runs = pc.long_linear_runs(groups, min_beats=3)
    assert long_runs, "expected at least one long run in the woven spine"
    run = groups[long_runs[0]]
    before, after = run[0], run[1]
    arm_a = Beat(
        id="beat:via-the-cliffs",
        created_by=Stage.POLISH,
        summary="a",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
    )
    arm_b = Beat(
        id="beat:via-the-shore",
        created_by=Stage.POLISH,
        summary="b",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
    )
    pc.insert_false_branch(g, arm_a, arm_b, before, after)
    assert not g.has_edge(EdgeKind.PREDECESSOR, before, after)
    new_groups = pc.collapse_groups(g)
    assert ["beat:via-the-cliffs"] in new_groups
    assert ["beat:via-the-shore"] in new_groups
    # the diamond rejoins: both arms feed `after`
    assert set(queries.predecessors(g, after)) == {"beat:via-the-cliffs", "beat:via-the-shore"}


def test_active_flags_mirrors_i12(golden):
    g = golden.graph
    group = next(
        grp for grp in pc.collapse_groups(g) if "beat:keep-ending" in grp
    )
    assert pc.active_flags(g, group) == [
        "flag:bound-to-light",
        "flag:elias-knows",
        "flag:lie-between",
    ]


def test_audit_accepts_slug_form_passage_ids(vision, tmp_path):
    """First live run (gpt-5, 2026-07-08): the model audited the right
    passages but dropped the id namespace ("p-x" for "passage:p-x"),
    exhausting repairs. The prefix is unambiguous, so accept the slug."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    _passages_apply(_proposal_for(g), project)
    flagged = [
        p.id
        for p in sorted(g.nodes_of(Passage), key=lambda p: p.id)
        if pc.active_flags(g, queries.beats_of_passage(g, p.id))
    ]
    assert flagged
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage=pid.split(":", 1)[1], irrelevant=[])  # slug form
            for pid in flagged
        ]
    )
    _audit_apply(proposal, project)  # normalized, no ApplyError
