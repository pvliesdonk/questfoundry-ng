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
    ArmSpec,
    AuditEntry,
    AuditProposal,
    EdgeLabelSpec,
    FalseBranchSpec,
    FinalizeProposal,
    ForkSpec,
    LabelsProposal,
    ResidueSpec,
    SummaryProposal,
    VariantSpec,
    _audit_apply,
    _finalize_apply,
    _groups,
    _labels_apply,
    _light_needs,
    _summary_apply,
    _variant_needs,
)
from questfoundry.pipeline.types import ApplyError
from questfoundry.project.io import Project
from tests.conftest import make_dilemma, narrative_beat
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
        "path:tell": ["flag:elias-knows"],
        "path:hide": ["flag:lie-between"],
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


def _build_passages(project: Project) -> None:
    """Apply the whole passage layer through the decomposed per-group passes
    (what the runner's finalize-expansion drives): one `summary:<group>` apply
    per collapse group, then one `labels:<group>` apply per source group. Uses
    the same capped grouping the applies index into, so group numbers align."""
    g = project.graph
    groups = _groups(project)
    variant_needs = _variant_needs(g)
    for i, group in enumerate(groups):
        needs = [flags for c, flags in variant_needs.items() if c in group]
        variants = [
            VariantSpec(flag=f, id=f"passage:p{i}-v{j}", summary=f"variant {j}")
            for j, f in enumerate(needs[0])
        ] if needs else []
        proposal = SummaryProposal(
            id=f"passage:p{i}",
            summary=f"group {i}",
            ending_title="An End" if pc.ending_beat(g, group) else "",
            variants=variants,
        )
        _summary_apply(i)(proposal, project)
    edges = pc.group_edges(groups, g)
    for a in sorted({x for x, _ in edges}):
        labels = [
            EdgeLabelSpec.model_validate({"to": b, "label": f"onward {a}-{b}"})
            for x, b in edges
            if x == a
        ]
        _labels_apply(a)(LabelsProposal(labels=labels), project)


def _polish_errors(g, vision) -> list:
    relevant = {"I10", "I11", "I12", "I13", "G4"}
    issues = run_checks(g, vision, Stage.POLISH)
    return [i for i in issues if i.severity == Severity.ERROR and i.check in relevant]


def test_heavy_residue_creates_gated_variants(vision, tmp_path):
    g = StoryGraph()
    _woven_story(g, ResidueWeight.HEAVY)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    # heavy needs no residue beats (variants carry it); cadence sites may
    # still engage finalize, so assert the residue claim directly
    assert not _light_needs(project)

    _build_passages(project)
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
    # each variant persists its gating flag on the passage (so choice-wiring
    # can recover it once creation and wiring are separate passes)
    assert {g.node(va).variant_flag, g.node(vb).variant_flag} == {"flag:sub-a", "flag:sub-b"}
    # and each variant's persisted flag matches the gate on its incoming choice
    for e in g.edges:
        if e.kind == EdgeKind.CHOICE and e.dst in holders:
            assert e.payload["requires"] == [g.node(e.dst).variant_flag]
    # a non-variant passage carries no variant_flag
    non_variant = next(p for p in g.nodes_of(Passage) if p.id not in holders)
    assert non_variant.variant_flag is None

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
    groups = _groups(project)
    # the heavy-residue frontier group's summary pass must emit variants
    i = next(i for i, grp in enumerate(groups) if _variant_needs(g).keys() & set(grp))
    proposal = SummaryProposal(id=f"passage:p{i}", summary="s", variants=[])
    with pytest.raises(ApplyError, match="heavy residue"):
        _summary_apply(i)(proposal, project)


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
        requires_flags=[need.path_flags["path:sub-a"][0]],
    )
    followup = Beat(
        id="beat:afterglow-2",
        created_by=Stage.POLISH,
        summary="s2",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
        requires_flags=[need.path_flags["path:sub-a"][0]],
    )
    pc.insert_residue_chain(g, [beat, followup], "path:sub-a", need.rejoin)
    issues = run_checks(g, vision, Stage.GROW)
    assert [i for i in issues if i.check == "I9"] == []  # freeze intact
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:afterglow", "beat:afterglow-2")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:afterglow-2", need.rejoin[0])
    # an identically gated chain collapses into ONE gated passage
    groups = pc.collapse_groups(g)
    assert ["beat:afterglow", "beat:afterglow-2"] in groups


def test_tensored_residue_arm_is_a_gated_choice_on_one_side(vision, tmp_path):
    """PR-1b: a light residue arm may fork into two same-gate branches —
    the reader who made the matching upstream choice gets a choice in
    how to carry it. Both branches collapse into their own gated
    passage, either satisfies G4's coverage, and the passage graph
    stays clean (I10-I13)."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    (need,) = _light_needs(project)
    mutations.freeze_topology(g)
    proposal = FinalizeProposal(
        residue=[
            ResidueSpec(
                dilemma="dilemma:sub",
                path="path:sub-a",
                id="beat:mem-a",
                summary="s",
                fork=ForkSpec(id="beat:mem-a-alt", summary="s2"),
            ),
            ResidueSpec(dilemma="dilemma:sub", path="path:sub-b", id="beat:mem-b", summary="s"),
        ]
    )
    lines = _finalize_apply(proposal, project)
    assert any("beat:mem-a" in line and "beat:mem-a-alt" in line for line in lines)
    flag = need.path_flags["path:sub-a"][0]
    for b in ("beat:mem-a", "beat:mem-a-alt"):
        beat = g.node(b)
        assert isinstance(beat, Beat)
        assert beat.requires_flags == [flag]
        assert g.has_edge(EdgeKind.PREDECESSOR, b, need.rejoin[0])
    # each branch is its own gated passage; the freeze holds
    groups = pc.collapse_groups(g)
    assert ["beat:mem-a"] in groups and ["beat:mem-a-alt"] in groups
    issues = run_checks(g, vision, Stage.GROW)
    assert [i for i in issues if i.check == "I9"] == []

    _build_passages(project)
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage=p.id, irrelevant=[])
            for p in sorted(g.nodes_of(Passage), key=lambda p: p.id)
            if pc.active_flags(g, queries.beats_of_passage(g, p.id))
        ]
    )
    _audit_apply(proposal, project)
    assert _polish_errors(g, vision) == []
    # the fork is an offered choice: the tail passage carries two choices
    # gated on the same flag (distinct labels), one per branch passage
    branch_passages = {
        queries.passages_of_beat(g, b)[0] for b in ("beat:mem-a", "beat:mem-a-alt")
    }
    sources = {
        e.src
        for e in g.edges
        if e.kind == EdgeKind.CHOICE and e.dst in branch_passages
    }
    assert len(sources) == 1
    gated = [
        e
        for e in g.out_edges(sources.pop(), EdgeKind.CHOICE)
        if e.dst in branch_passages
    ]
    assert len(gated) == 2
    assert all(e.payload["requires"] == [flag] for e in gated)


def test_residue_diamond_rejects_an_empty_branch(vision):
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    (need,) = [n for n in pc.convergence_needs(g) if n.weight == ResidueWeight.LIGHT]
    arm = Beat(
        id="beat:solo",
        created_by=Stage.POLISH,
        summary="s",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
        requires_flags=[need.path_flags["path:sub-a"][0]],
    )
    with pytest.raises(mutations.MutationError, match="empty"):
        pc.insert_residue_diamond(g, [arm], [], "path:sub-a", need.rejoin)


def test_residue_beat_id_collision_is_repairable(vision):
    """A residue arm whose new beat reuses an existing beat id raises a
    repairable MutationError, not the store's bare KeyError. Before the
    mutation-boundary fix this KeyError escaped the runner's repair loop:
    the residue path caught it, but the symmetric false-branch path did
    not, so a colliding false-branch id crashed the run. This is the
    weak-tier failure (gpt-oss:120b named a residue beat after an existing
    commit beat) — now a named, recoverable error, not an id-decode crash."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    (need,) = [n for n in pc.convergence_needs(g) if n.weight == ResidueWeight.LIGHT]
    mutations.freeze_topology(g)
    taken = sorted(b.id for b in g.nodes_of(Beat))[0]  # collide with a real beat id
    clash = Beat(
        id=taken,
        created_by=Stage.POLISH,
        summary="s",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
        requires_flags=[need.path_flags["path:sub-a"][0]],
    )
    with pytest.raises(mutations.MutationError, match="already used"):
        pc.insert_residue_chain(g, [clash], "path:sub-a", need.rejoin)


def test_multi_flag_path_residue_covers_via_any_flag(vision):
    """A path with two consequences derives two flags (live run 7). The
    residue arm gates on one; G4 must accept any of the path's flags —
    and must not depend on flag insertion order, which differs between a
    live graph and a reloaded one (the old path->flag dict kept an
    order-dependent winner, so the stage gate and qf validate diverged)."""
    from questfoundry.models.structure import FlagSource, StateFlag

    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    # a second consequence's flag on the same path, inserted after the first
    mutations.add_flag(
        g,
        StateFlag(
            id="flag:sub-a-second",
            created_by=Stage.GROW,
            description="d",
            source=FlagSource.DILEMMA,
            path="path:sub-a",
        ),
    )
    (need,) = [n for n in pc.convergence_needs(g) if n.weight == ResidueWeight.LIGHT]
    assert need.path_flags["path:sub-a"] == ["flag:sub-a", "flag:sub-a-second"]
    mutations.freeze_topology(g)
    for path in ("path:sub-a", "path:sub-b"):
        arm = Beat(
            id=f"beat:memory-{path.removeprefix('path:')}",
            created_by=Stage.POLISH,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.RESIDUE,
            # gate on the FIRST flag only; the second must still count as covered
            requires_flags=[need.path_flags[path][0]],
        )
        pc.insert_residue_chain(g, [arm], path, need.rejoin)
    issues = run_checks(g, vision, Stage.POLISH)
    assert [i for i in issues if i.check == "G4" and "residue" in i.message] == []


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
    # sub commits before the fork: one shared-region pairing whose
    # frontier is the hard fork itself, one beat per world
    assert queries.soft_rejoin_frontiers(g, "dilemma:sub") == [
        (frozenset(), ["beat:main-commit-a", "beat:main-commit-b"])
    ]
    (need,) = pc.convergence_needs(g)
    assert need.world == ""
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
        requires_flags=[need.path_flags["path:sub-a"][0]],
    )
    pc.insert_residue_chain(g, [beat], "path:sub-a", need.rejoin)
    assert set(queries.successors(g, "beat:afterglow")) == set(need.rejoin)
    issues = run_checks(g, vision, Stage.GROW)
    errors = [i for i in issues if i.check in ("I6", "I9") and i.severity == Severity.ERROR]
    assert errors == []


def test_residue_apply_error_names_the_expected_dilemmas(vision, tmp_path):
    """Live-run lesson (gpt-5, 2026-07-08): the model echoed the prompt's
    '(residue: light)' annotation into the dilemma field, and the old error
    ('needs no residue beat') taught nothing across two repair rounds.
    Repair errors name the expected values (id-contract decision)."""
    from questfoundry.pipeline.stages.polish import (
        FinalizeProposal,
        ResidueSpec,
        _finalize_apply,
    )

    g = StoryGraph()
    _fork_rejoin_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    proposal = FinalizeProposal(
        residue=[
            ResidueSpec(
                dilemma="dilemma:sub (residue: light)",
                path="path:sub-a",
                id="beat:afterglow",
                summary="s",
            )
        ]
    )
    with pytest.raises(ApplyError, match=r"of \['dilemma dilemma:sub'\]"):
        _finalize_apply(proposal, project)


def test_heavy_residue_at_fork_rejoin_needs_per_world_variants(vision, tmp_path):
    """A heavy-residue soft dilemma rejoining at a hard fork gets variant
    passages at every frontier beat — one set per world (M5)."""
    g = StoryGraph()
    _fork_rejoin_story(g, ResidueWeight.HEAVY)
    flags = sorted(fl[0] for fl in queries.dilemma_flags(g, "dilemma:sub").values())
    assert _variant_needs(g) == {
        "beat:main-commit-a": flags,
        "beat:main-commit-b": flags,
    }
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    _build_passages(project)
    issues = run_checks(g, vision, Stage.POLISH)
    assert not any(i.check == "G4" and "variant" in i.message for i in issues)
    for commit in ("beat:main-commit-a", "beat:main-commit-b"):
        assert len(queries.passages_of_beat(g, commit)) == 2


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
    arm_b2 = Beat(
        id="beat:shore-tidepools",
        created_by=Stage.POLISH,
        summary="b2",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
    )
    pc.insert_false_branch(g, [arm_a], [arm_b, arm_b2], before, after)
    assert not g.has_edge(EdgeKind.PREDECESSOR, before, after)
    new_groups = pc.collapse_groups(g)
    assert ["beat:via-the-cliffs"] in new_groups
    # a 2-beat arm collapses into one passage of its own
    assert ["beat:via-the-shore", "beat:shore-tidepools"] in new_groups
    # the diamond rejoins: both arms feed `after`
    assert set(queries.predecessors(g, after)) == {"beat:via-the-cliffs", "beat:shore-tidepools"}


def test_finalize_splices_false_branches_against_pristine_topology(vision, tmp_path, monkeypatch):
    """Both residue arms and cadence false branches add to the *frozen*
    topology, so a false branch validates and splices against the long
    runs the model was shown — BEFORE residue splicing shortens them.
    Otherwise a beat inside a long run at proposal time can be evicted by
    residue and its diamond wrongly rejected (the live gpt-oss:120b cloud
    finalize failure, 2026-07-11). Assert the order directly: the false
    branch is spliced before any residue arm."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    mutations.freeze_topology(g)
    run = pc.collapse_groups(g)[pc.long_linear_runs(pc.collapse_groups(g))[0]]

    order: list[str] = []
    for name in ("insert_sidetrack", "insert_residue_chain", "insert_residue_diamond"):
        real = getattr(pc, name)
        tag = "false" if name == "insert_sidetrack" else "residue"
        monkeypatch.setattr(
            pc, name, lambda *a, _r=real, _t=tag, **k: (order.append(_t), _r(*a, **k))[1]
        )

    proposal = FinalizeProposal(
        residue=[
            ResidueSpec(dilemma="dilemma:sub", path="path:sub-a", id="beat:mem-a", summary="s"),
            ResidueSpec(dilemma="dilemma:sub", path="path:sub-b", id="beat:mem-b", summary="s"),
        ],
        false_branches=[
            FalseBranchSpec(
                before=run[0], after=run[1], arms=[ArmSpec(id="beat:detour", summary="s")]
            )
        ],
    )
    _finalize_apply(proposal, project)
    assert order and order[0] == "false"  # the diamond lands before residue shortens the run
    assert order.count("residue") == 2  # both arms still applied
    assert isinstance(g.node("beat:detour"), Beat)


def test_finalize_false_branch_id_collision_is_repairable(vision, tmp_path):
    """The exact asymmetry the PR fixes: the false-branch splice once let a
    colliding new-beat id escape as an uncaught KeyError and crash the run
    (the residue path caught it, this one did not). Through _finalize_apply
    it is now a repairable ApplyError carrying false-branch location
    context, not a crash."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    mutations.freeze_topology(g)
    run = pc.collapse_groups(g)[pc.long_linear_runs(pc.collapse_groups(g))[0]]
    proposal = FinalizeProposal(
        false_branches=[
            # arm reuses an existing beat id (run[0]) — the collision
            FalseBranchSpec(before=run[0], after=run[1], arms=[ArmSpec(id=run[0], summary="s")])
        ]
    )
    with pytest.raises(ApplyError, match="false branch"):
        _finalize_apply(proposal, project)


def test_llm_beat_entities_must_be_ids(vision, tmp_path):
    """Validation run (2026-07-09): a diamond arm carrying display names
    ('Wren') sailed through every gate until DRESS's brief check collided
    with it. Every apply that stores entity refs on a beat now resolves
    them through the id contract (exact id or unambiguous bare slug)."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    (need,) = [n for n in pc.convergence_needs(g) if n.weight == ResidueWeight.LIGHT]
    spec = ResidueSpec(
        dilemma=need.dilemma,
        path=sorted(need.path_flags)[0],
        world=need.world,
        id="beat:afterglow",
        summary="s",
        entities=["Wren"],
    )
    with pytest.raises(ApplyError, match="not an entity id"):
        _finalize_apply(FinalizeProposal(residue=[spec]), project)


def test_residue_world_on_shared_convergence_names_the_corrective(vision, tmp_path):
    """Closed Circle live run (2026-07-14): a residue arm attached a world to
    a convergence listed without one and exhausted repairs — the message
    showed the valid set but never the corrective. It now instructs (AGENTS
    error contract): a shared convergence takes no world."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    (need,) = [n for n in pc.convergence_needs(g) if n.weight == ResidueWeight.LIGHT]
    spec = ResidueSpec(
        dilemma=need.dilemma,
        path=sorted(need.path_flags)[0],
        world="path:not-a-world" if not need.world else "",
        id="beat:afterglow",
        summary="s",
    )
    with pytest.raises(ApplyError, match="listed WITHOUT a world is shared"):
        _finalize_apply(FinalizeProposal(residue=[spec]), project)


def test_b6_choice_cadence_measures_feel(golden):
    """B6 (advisory): story size FEELS like words traversed per genuine
    choice (calibration decision, 2026-07-09 — the medium live run read
    at ~1200 words/choice, double the balanced band). The golden micro
    sits inside the band; inflating its prose 4x pushes it out."""
    issues = run_checks(golden.graph, golden.vision, Stage.FILL)
    assert not [i for i in issues if i.check == "B6"]
    for p in golden.graph.nodes_of(Passage):
        p.prose = " ".join([p.prose] * 4)
    issues = run_checks(golden.graph, golden.vision, Stage.FILL)
    warns = [i for i in issues if i.check == "B6"]
    assert len(warns) == 1 and "words per genuine choice" in warns[0].message


def test_active_flags_mirrors_i12(golden):
    g = golden.graph
    group = next(
        grp for grp in pc.collapse_groups(g) if "beat:keep-ending" in grp
    )
    # flag:bound-to-light is granted on every route here (its commit is
    # the only side upstream) — a fact, not a state to honor (I12);
    # the reconverged soft dilemma's pair stays ambiguous
    assert pc.active_flags(g, group) == [
        "flag:elias-knows",
        "flag:lie-between",
    ]


def test_i12_counts_only_ambiguous_flags(vision):
    """Refined by the medium live run (2026-07-09): the climax endings
    of a multi-hard story carry 4+ upstream flags that are all facts
    there (only their own side upstream), while a trunk passage after
    two soft convergences carries genuinely ambiguous ones. I12 caps
    ambiguity, not upstream grants."""
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD)
    d2, p2a, p2b = make_dilemma(g, "sub1", role=DilemmaRole.SOFT)
    d3, p3a, p3b = make_dilemma(g, "sub2", role=DilemmaRole.SOFT)
    scaffold(g, "main", d1, p1a, p1b)
    scaffold(g, "sub1", d2, p2a, p2b, endings=False)
    scaffold(g, "sub2", d3, p3a, p3b, endings=False)
    planned = weave.plan(g)
    # both softs resolve before main's last shared beat — constructed
    # directly (a valid topological order; realize checks it), not fished
    # out of the candidate sample, whose composition is an enumeration
    # policy detail
    order = [
        "pre:beat:main-pre0",
        "pre:beat:sub1-pre0",
        "pre:beat:sub1-pre1",
        "resolve:dilemma:sub1",
        "pre:beat:sub2-pre0",
        "pre:beat:sub2-pre1",
        "resolve:dilemma:sub2",
        "pre:beat:main-pre1",
        "resolve:dilemma:main",
    ]
    weave.realize(g, planned, order)
    _derive_flags(g)

    # the trunk after both soft convergences: two ambiguous pairs
    trunk = queries.ambiguous_flags(g, ["beat:main-pre1"])
    assert trunk == ["flag:sub1-a", "flag:sub1-b", "flag:sub2-a", "flag:sub2-b"]
    # past main's commit its flag is granted on every route — never counted
    beyond = [b for b in queries.beat_ids(g) if "main-post-a" in b]
    assert beyond
    for flag in queries.ambiguous_flags(g, beyond):
        assert "main" not in flag
    # a beat gated on one sub1 flag determines that dilemma for arrivals
    gated = Beat(
        id="beat:afterglow",
        created_by=Stage.POLISH,
        summary="s",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
        requires_flags=["flag:sub1-a"],
    )
    mutations.add_beat(g, gated, [])
    mutations.add_ordering(g, "beat:main-pre1", "beat:afterglow")
    assert queries.ambiguous_flags(g, ["beat:afterglow"]) == ["flag:sub2-a", "flag:sub2-b"]

    # I12 fires on the 4 ambiguous states and clears when one is audited away
    mutations.add_passage(
        g,
        Passage(id="passage:p-trunk", created_by=Stage.POLISH, summary="s"),
        ["beat:main-pre1"],
    )
    issues = run_checks(g, vision, Stage.POLISH)
    i12 = [i for i in issues if i.check == "I12"]
    assert len(i12) == 1 and "4 ambiguous states" in i12[0].message
    g.node("passage:p-trunk").irrelevant_flags = ["flag:sub1-a"]
    issues = run_checks(g, vision, Stage.POLISH)
    assert [i for i in issues if i.check == "I12"] == []


def test_audit_accepts_slug_form_passage_ids(vision, tmp_path):
    """First live run (gpt-5, 2026-07-08): the model audited the right
    passages but dropped the id namespace ("p-x" for "passage:p-x"),
    exhausting repairs. The prefix is unambiguous, so accept the slug."""
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    _build_passages(project)
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


# -- arcs pass (plan: docs/plans/prose-quality.md W5) --------------------------


def test_arcs_apply_stores_arcs_and_rejects_duplicates(golden):
    from questfoundry.pipeline.stages.polish import (
        ArcSpec,
        ArcsProposal,
        _arcs_apply,
    )

    g = golden.graph
    # golden's keeper and cartographer already carry hand-authored arcs;
    # the sleeper is the remaining arc-worthy character
    proposal = ArcsProposal(
        arcs=[
            ArcSpec(
                entity="sleeper",  # bare-slug affordance resolves
                begins="asleep, patient as tide",
                pivots=[{"beat": "beat:tremor", "becomes": "stirring; the light's hold slips"}],
                ends=[{"path": "path:break", "state": "awake and following"}],
            )
        ]
    )
    lines = _arcs_apply(proposal, golden)
    assert lines == ["character:sleeper: 1 pivot(s), 1 path end(s)"]
    assert g.node("character:sleeper").arc.pivots[0].beat == "beat:tremor"

    # a duplicate inside one proposal is caught before the mutation layer
    # (id and slug forms are the same entity)
    from questfoundry.project import load_project
    from tests.conftest import GOLDEN

    fresh = load_project(GOLDEN)
    fresh.graph.node("character:sleeper").arc = None
    twice = ArcsProposal(
        arcs=[
            ArcSpec(entity="character:sleeper", begins="x"),
            ArcSpec(entity="sleeper", begins="y"),
        ]
    )
    with pytest.raises(ApplyError, match="arced twice"):
        _arcs_apply(twice, fresh)


def test_arcs_apply_accepts_every_retained_category(golden):
    """Author doctrine (2026-07-12): a location without an arc is a
    backdrop, an object a mcguffin, a faction a link — all four
    categories are arc-eligible. A cut entity still is not."""
    from questfoundry.pipeline.stages.polish import ArcSpec, ArcsProposal, _arcs_apply

    golden.graph.node("location:lighthouse").arc = None  # golden ships one; re-arc fresh
    lines = _arcs_apply(
        ArcsProposal(
            arcs=[
                ArcSpec(
                    entity="location:lighthouse",
                    begins="a working shelter; the bargain is invisible in it",
                )
            ]
        ),
        golden,
    )
    assert lines == ["location:lighthouse: 0 pivot(s), 0 path end(s)"]

    golden.graph.node("character:sleeper").retained = False
    with pytest.raises(ApplyError, match="not a retained entity"):
        _arcs_apply(ArcsProposal(arcs=[ArcSpec(entity="character:sleeper", begins="x")]), golden)


# -- collapse: viewpoint cut (rotating-pov-build.md) ---------------------------


def _viewpoint_chain(g: StoryGraph, heads: list[tuple[str | None, bool] | None]) -> list[str]:
    """A linear run of beats with the given per-beat (viewpoint, interlude)
    annotations (None = unannotated wildcard)."""
    d, pa, pb = make_dilemma(g, "one")
    ids = []
    prev = None
    for i, head in enumerate(heads):
        beat = narrative_beat(f"run{i}", d)
        if head is not None:
            beat.viewpoint, beat.interlude = head
        mutations.add_beat(g, beat, [pa, pb])
        if prev:
            mutations.add_ordering(g, prev, beat.id)
        prev = beat.id
        ids.append(beat.id)
    return ids


def test_collapse_cuts_at_a_head_switch():
    g = StoryGraph()
    a = ("character:eleanor", False)
    b = ("character:charles", False)
    ids = _viewpoint_chain(g, [a, a, b, b])
    groups = pc.collapse_groups(g, split_viewpoints=True)
    assert ids[:2] in groups and ids[2:] in groups


def test_collapse_default_mode_ignores_viewpoints():
    # the raw choice-topology runs (cadence planning) stay uncut: a
    # head-switch chunks prose, not choices
    g = StoryGraph()
    ids = _viewpoint_chain(g, [("character:eleanor", False), ("character:charles", False)])
    assert ids in pc.collapse_groups(g)


def test_collapse_wildcards_merge_across_and_ride_the_run_head():
    # an unannotated beat (bridge/residue/false-branch, wide coda) merges
    # anywhere; a later annotated beat is held to the group's settled head
    g = StoryGraph()
    a = ("character:eleanor", False)
    b = ("character:charles", False)
    ids = _viewpoint_chain(g, [a, None, a, None, b])
    groups = pc.collapse_groups(g, split_viewpoints=True)
    assert ids[:4] in groups and [ids[4]] in groups


def test_collapse_never_merges_interlude_with_base_register():
    # a journal entry and base narration never share a passage, even in
    # the same head
    g = StoryGraph()
    ids = _viewpoint_chain(
        g, [("character:eleanor", False), ("character:eleanor", True)]
    )
    groups = pc.collapse_groups(g, split_viewpoints=True)
    assert [ids[0]] in groups and [ids[1]] in groups


def test_collapse_headless_run_is_one_group():
    g = StoryGraph()
    ids = _viewpoint_chain(g, [None, None, None])
    assert ids in pc.collapse_groups(g, split_viewpoints=True)
