"""POLISH's deterministic core: collapse, choice topology, residue and
false-branch splicing, variants for heavy residue. The golden story is
the oracle: the hand-authored passage layer is what the engine must
compute."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import SCOPE_PRESETS
from questfoundry.models.drama import DilemmaRole, ResidueWeight
from questfoundry.models.presentation import Choice, Passage
from questfoundry.models.structure import Beat, BeatClass, StructuralPurpose
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import _derive_flags
from questfoundry.pipeline.stages.polish import (
    AuditEntry,
    AuditProposal,
    EdgeLabelSpec,
    FinalizeProposal,
    ForkSpec,
    LabelsProposal,
    ResidueSpec,
    SummaryProposal,
    VariantSpec,
    _audit_apply,
    _finalize_apply,
    _finalize_context,
    _groups,
    _labels_apply,
    _labels_context,
    _labels_schema,
    _light_needs,
    _polish_expand,
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

    # the variants themselves carry NO ambiguous state — their gate
    # determines the dilemma for everyone who arrives (passage_gate_flags
    # feeds the I12 conditioning), so the audit does not list them
    for vid in holders:
        assert (
            queries.ambiguous_dilemma_groups(
                g, queries.beats_of_passage(g, vid), queries.passage_gate_flags(g, vid)
            )
            == []
        )
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage=p.id, irrelevant=[])
            for p in sorted(g.nodes_of(Passage), key=lambda p: p.id)
            if queries.ambiguous_dilemma_groups(
                g,
                queries.beats_of_passage(g, p.id),
                queries.passage_gate_flags(g, p.id),
            )
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
            if queries.ambiguous_flags(
                g, queries.beats_of_passage(g, p.id), queries.passage_gate_flags(g, p.id)
            )
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


def test_fork_beat_id_collision_is_repairable(vision, tmp_path):
    """A rendering beat reusing an existing id is a repairable ApplyError
    carrying the fork's location, not a crash (the false-branch splice once
    let the store's KeyError escape uncaught)."""
    from questfoundry.pipeline.stages.polish import (
        ForkBeatSpec,
        ForkProposal,
        RenderingSpec,
        _fork_apply,
    )

    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    mutations.freeze_topology(g)
    run = pc.collapse_groups(g)[pc.long_linear_runs(pc.collapse_groups(g))[0]]
    site = pc.ForkSite(before=run[0], after=run[1], segment=(), arms=1, keywords=())
    proposal = ForkProposal(
        renderings=[
            RenderingSpec(premise="p", beats=[ForkBeatSpec(id=run[0], summary="s")])
        ]
    )
    with pytest.raises(ApplyError, match="cosmetic fork"):
        _fork_apply(site)(proposal, project)


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


def test_ambiguous_flags_mirrors_i12(golden):
    g = golden.graph
    group = next(
        grp for grp in pc.collapse_groups(g) if "beat:keep-ending" in grp
    )
    # flag:bound-to-light is granted on every route here (its commit is
    # the only side upstream) — a fact, not a state to honor (I12);
    # the reconverged soft dilemma's pair stays ambiguous
    assert queries.ambiguous_flags(g, group) == [
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

    # 4 ambiguous FLAGS are 2 dilemma STATES (the unit correction,
    # 2026-07-14: a path derives one flag per consequence, any of them
    # identifies the path) — two states sit within the cap, no error
    mutations.add_passage(
        g,
        Passage(id="passage:p-trunk", created_by=Stage.POLISH, summary="s"),
        ["beat:main-pre1"],
    )
    groups = queries.ambiguous_dilemma_groups(g, ["beat:main-pre1"])
    assert groups == [["flag:sub1-a", "flag:sub1-b"], ["flag:sub2-a", "flag:sub2-b"]]
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
        if queries.ambiguous_flags(
                g, queries.beats_of_passage(g, p.id), queries.passage_gate_flags(g, p.id)
            )
    ]
    assert flagged
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage=pid.split(":", 1)[1], irrelevant=[])  # slug form
            for pid in flagged
        ]
    )
    _audit_apply(proposal, project)  # normalized, no ApplyError


def _four_soft_trunk(vision, tmp_path):
    """A trunk passage after FOUR soft convergences: 4 ambiguous dilemma
    states, one over the I12 cap — the medium/long regime the audit must
    resolve honestly (irrelevant where true, split_on where not)."""
    g = StoryGraph()
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD)
    softs = [make_dilemma(g, f"sub{i}", role=DilemmaRole.SOFT) for i in range(1, 5)]
    scaffold(g, "main", d1, p1a, p1b)
    for i, (d, pa, pb) in enumerate(softs, start=1):
        scaffold(g, f"sub{i}", d, pa, pb, endings=False)
    planned = weave.plan(g)
    order = ["pre:beat:main-pre0"]
    for i in range(1, 5):
        order += [f"pre:beat:sub{i}-pre0", f"pre:beat:sub{i}-pre1", f"resolve:dilemma:sub{i}"]
    order += ["pre:beat:main-pre1", "resolve:dilemma:main"]
    weave.realize(g, planned, order)
    _derive_flags(g)
    mutations.add_passage(
        g,
        Passage(id="passage:p-feeder", created_by=Stage.POLISH, summary="s"),
        ["beat:sub4-pre1"],
    )
    mutations.add_passage(
        g,
        Passage(id="passage:p-trunk", created_by=Stage.POLISH, summary="s"),
        ["beat:main-pre1"],
    )
    mutations.add_choice(
        g, "passage:p-feeder", "passage:p-trunk", Choice(label="on", requires=[], grants=[])
    )
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    return g, project


def test_audit_apply_enforces_the_i12_cap_repairably(vision, tmp_path):
    """Texture-trial live run (2026-07-14): the prompt's cap rule was
    stated and trusted, the model under-marked, and I12 exploded at the
    unrepairable gate; the repair loop then got ONE violation per round
    and exhausted playing whack-a-mole. The apply now enforces the cap in
    the honest unit (dilemma states) with ALL violations batched."""
    g, project = _four_soft_trunk(vision, tmp_path)
    groups = queries.ambiguous_dilemma_groups(g, ["beat:main-pre1"])
    assert len(groups) == 4  # one over the cap
    feeder = AuditEntry(passage="passage:p-feeder", irrelevant=[])  # 3 states: at cap
    under_marked = AuditProposal(
        audit=[feeder, AuditEntry(passage="passage:p-trunk", irrelevant=[])]
    )
    with pytest.raises(ApplyError) as exc:
        _audit_apply(under_marked, project)
    msg = str(exc.value)
    assert "4 dilemma states relevant" in msg
    assert "split_on" in msg and "fix ALL" in msg
    # honest resolution 1: a state the scene doesn't touch, fully marked
    fixed = AuditProposal(
        audit=[
            feeder,
            AuditEntry(
                passage="passage:p-trunk", irrelevant=["flag:sub1-a", "flag:sub1-b"]
            ),
        ]
    )
    _audit_apply(fixed, project)


def test_audit_split_on_creates_gated_variants_and_clears_i12(vision, tmp_path):
    """The escape valve when every state genuinely matters: split_on keys
    the passage on a dilemma — the engine re-presents it as gated
    variants, arrivals hold a known side, and I12 clears without a single
    dishonest irrelevance mark."""
    g, project = _four_soft_trunk(vision, tmp_path)
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage="passage:p-feeder", irrelevant=[]),
            AuditEntry(passage="passage:p-trunk", irrelevant=[], split_on=["dilemma:sub1"]),
        ]
    )
    lines = _audit_apply(proposal, project)
    assert any("split on" in line for line in lines)
    sibling = g.node("passage:p-trunk--s1")
    assert sibling is not None and sibling.variant_flag == "flag:sub1-b"
    assert g.node("passage:p-trunk").variant_flag == "flag:sub1-a"
    # in-choices gated per side; each variant's arrivals hold a known side
    gates = sorted(
        tuple(e.payload["requires"])
        for e in g.edges
        if e.kind == EdgeKind.CHOICE and e.dst.startswith("passage:p-trunk")
    )
    assert gates == [("flag:sub1-a",), ("flag:sub1-b",)]
    # the keyed state is determined inside each variant: 3 remain, at cap
    for pid in ("passage:p-trunk", "passage:p-trunk--s1"):
        remaining = queries.ambiguous_dilemma_groups(
            g, queries.beats_of_passage(g, pid), queries.passage_gate_flags(g, pid)
        )
        assert len(remaining) == 3
    issues = run_checks(g, vision, Stage.POLISH)
    assert [i for i in issues if i.check == "I12"] == []


def test_audit_split_on_rejects_a_non_ambiguous_dilemma(vision, tmp_path):
    g, project = _four_soft_trunk(vision, tmp_path)
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage="passage:p-feeder", irrelevant=[]),
            AuditEntry(passage="passage:p-trunk", irrelevant=[], split_on=["dilemma:main"]),
        ]
    )
    with pytest.raises(ApplyError, match="name no ambiguous state"):
        _audit_apply(proposal, project)
    del g


def test_audit_split_on_rejects_an_ending(vision, tmp_path):
    """Endings never split — variants would multiply the story's ending
    set, fixed at the freeze (I12's documented exception). The refusal
    must give that reason, not the false 'already determined' claim."""
    from questfoundry.models.presentation import Ending

    g, project = _four_soft_trunk(vision, tmp_path)
    mutations.add_passage(
        g,
        Passage(
            id="passage:p-final",
            created_by=Stage.POLISH,
            summary="s",
            ending=Ending(id="ending:p-final", title="t"),
        ),
        ["beat:main-post-a"],
    )
    assert queries.ambiguous_dilemma_groups(g, ["beat:main-post-a"])
    proposal = AuditProposal(
        audit=[
            AuditEntry(passage="passage:p-feeder", irrelevant=[]),
            AuditEntry(passage="passage:p-trunk", irrelevant=[], split_on=["dilemma:sub1"]),
            AuditEntry(passage="passage:p-final", irrelevant=[], split_on=["dilemma:sub2"]),
        ]
    )
    with pytest.raises(ApplyError, match="ending set, fixed at the freeze"):
        _audit_apply(proposal, project)


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


# -- exit-label residue: cosmetic rejoins (cosmetic-forks §5) -------------------


def _sidetrack_project(g: StoryGraph, vision, tmp_path) -> tuple[Project, str, str]:
    """A woven spine with one FALSE_BRANCH sidetrack spliced onto its first
    long run; returns the project and the (before, after) trunk edge."""
    _woven_story(g, ResidueWeight.LIGHT)
    mutations.freeze_topology(g)
    run = pc.collapse_groups(g)[pc.long_linear_runs(pc.collapse_groups(g))[0]]
    before, after = run[0], run[1]
    arm = Beat(
        id="beat:detour",
        created_by=Stage.POLISH,
        summary="a quiet detour",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
    )
    pc.insert_sidetrack(g, [arm], before, after)
    project = Project(root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g)
    return project, before, after


def _apply_summaries(project: Project) -> None:
    g = project.graph
    for i, group in enumerate(_groups(project)):
        _summary_apply(i)(
            SummaryProposal(
                id=f"passage:p{i}",
                summary=f"group {i}",
                ending_title="An End" if pc.ending_beat(g, group) else "",
            ),
            project,
        )


def test_cosmetic_rejoin_sources_flags_the_arm_not_the_trunk(vision, tmp_path):
    g = StoryGraph()
    project, before, _ = _sidetrack_project(g, vision, tmp_path)
    groups = _groups(project)
    sources = pc.cosmetic_rejoin_sources(groups, g)
    arm_idx = next(i for i, grp in enumerate(groups) if "beat:detour" in grp)
    before_idx = next(i for i, grp in enumerate(groups) if before in grp)
    assert arm_idx in sources  # the rendering rejoins a shared destination
    assert before_idx not in sources  # the trunk is worded first, freely


def test_cosmetic_rejoin_sources_flags_both_diamond_arms(vision, tmp_path):
    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    mutations.freeze_topology(g)
    run = pc.collapse_groups(g)[pc.long_linear_runs(pc.collapse_groups(g))[0]]
    before, after = run[0], run[1]
    arms = [
        Beat(
            id=f"beat:arm-{side}",
            created_by=Stage.POLISH,
            summary=side,
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.FALSE_BRANCH,
        )
        for side in ("left", "right")
    ]
    pc.insert_false_branch(g, [arms[0]], [arms[1]], before, after)
    project = Project(root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g)
    groups = _groups(project)
    sources = pc.cosmetic_rejoin_sources(groups, g)
    left = next(i for i, grp in enumerate(groups) if "beat:arm-left" in grp)
    right = next(i for i, grp in enumerate(groups) if "beat:arm-right" in grp)
    before_idx = next(i for i, grp in enumerate(groups) if before in grp)
    assert {left, right} <= sources  # both arms converge on the rejoin
    assert before_idx not in sources


def test_polish_expand_orders_rejoin_renderings_after_their_siblings(vision, tmp_path):
    g = StoryGraph()
    project, before, _ = _sidetrack_project(g, vision, tmp_path)
    groups = _groups(project)
    arm_idx = next(i for i, grp in enumerate(groups) if "beat:detour" in grp)
    before_idx = next(i for i, grp in enumerate(groups) if before in grp)
    labels = [p.name for p in _polish_expand(project) if p.name.startswith("labels:")]
    # every summary precedes every labels pass (existing contract) ...
    names = [p.name for p in _polish_expand(project)]
    assert max(i for i, n in enumerate(names) if n.startswith("summary:")) < min(
        i for i, n in enumerate(names) if n.startswith("labels:")
    )
    # ... and the arm's rejoin label is worded after the trunk's
    assert labels.index(f"labels:{before_idx}") < labels.index(f"labels:{arm_idx}")


def test_rejoin_context_surfaces_the_trunk_label_as_a_sibling(vision, tmp_path):
    g = StoryGraph()
    project, before, after = _sidetrack_project(g, vision, tmp_path)
    groups = _groups(project)
    arm_idx = next(i for i, grp in enumerate(groups) if "beat:detour" in grp)
    before_idx = next(i for i, grp in enumerate(groups) if before in grp)
    after_idx = next(i for i, grp in enumerate(groups) if after in grp)
    _apply_summaries(project)
    # word the trunk pass first (what the ordering guarantees), then inspect
    # the arm pass's context — it must see the trunk's onward label
    trunk_dests = [b for x, b in pc.group_edges(groups, g) if x == before_idx]
    _labels_apply(before_idx)(
        LabelsProposal(
            labels=[
                EdgeLabelSpec.model_validate({"to": b, "label": f"walk on to {b}"})
                for b in trunk_dests
            ]
        ),
        project,
    )
    ctx = _labels_context(arm_idx)(project)
    assert ctx["is_rendering"] is True
    dest = next(d for d in ctx["dests"] if d["index"] == after_idx)
    assert f"walk on to {after_idx}" in dest["siblings"]
    # an ordinary (trunk) pass keeps its context unchanged: no siblings surfaced
    trunk_ctx = _labels_context(before_idx)(project)
    assert trunk_ctx["is_rendering"] is False
    assert all(not d["siblings"] for d in trunk_ctx["dests"])


def test_finalize_context_exposes_the_entity_roster(vision, tmp_path):
    """The finalize schema pins every `entities` value to the retained cast's
    ids, but the prompt showed the model only beat summaries — so a summary
    naming an entity whose id differs from its name led the weak tier to coin
    a name-derived id (`character:finch` for `character:marshal`, live medium
    halt 2026-07-15). The context must carry the id roster the schema enforces
    so the prompt can list it."""
    from questfoundry.models.world import Entity

    g = StoryGraph()
    _woven_story(g, ResidueWeight.LIGHT)
    mutations.freeze_topology(g)
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    ctx = _finalize_context(project)
    retained = {e.id for e in g.nodes_of(Entity) if e.retained}
    assert retained, "the woven story should retain at least one entity"
    assert {e.id for e in ctx["cast"]} == retained


def test_audit_decomposes_per_passage(vision, tmp_path):
    """The joint audit call over every ambiguous-state passage degenerated
    into wholesale repetition at medium scale (137 passages doubled, live
    2026-07-15). It is now decomposed: a planner skips the joint call and
    expands one `audit:<pid>` pass per passage, each an independent I12
    resolution (the cap is per-passage; a split leaves variants <= cap)."""
    from questfoundry.pipeline.stages.polish import (
        POLISH_STAGE,
        _audit_expand,
        _audit_one_apply,
    )

    g, project = _four_soft_trunk(vision, tmp_path)
    # the planner makes no LLM call and names the decomposition
    audit_spec = next(p for p in POLISH_STAGE.passes if p.name == "audit")
    assert audit_spec.skip_if is not None
    reason = audit_spec.skip_if(project)
    assert reason and "2 per-passage" in reason
    # one pass per ambiguous-state passage, deterministically id-sorted
    assert [p.name for p in _audit_expand(project)] == [
        "audit:passage:p-feeder",
        "audit:passage:p-trunk",
    ]
    # a per-passage apply enforces the cap for ITS OWN passage in isolation
    # (the over-cap p-trunk, under-marked, still fails repairably) ...
    over_cap = AuditProposal(audit=[AuditEntry(passage="passage:p-trunk", irrelevant=[])])
    with pytest.raises(ApplyError) as exc:
        _audit_one_apply("passage:p-trunk")(over_cap, project)
    assert "4 dilemma states relevant" in str(exc.value)
    # ... and resolves it WITHOUT the other audited passage in the proposal
    # (the joint apply demanded full coverage; per-passage does not)
    resolved = AuditProposal(
        audit=[AuditEntry(passage="passage:p-trunk", irrelevant=["flag:sub1-a", "flag:sub1-b"])]
    )
    _audit_one_apply("passage:p-trunk")(resolved, project)


def test_audit_prompt_marks_endings_as_unsplittable(vision):
    """The apply forbids split_on for endings (variants would multiply the
    fixed ending set), but that rule lived only in the error message — so the
    weak-tier medium run tried to split an over-cap ending and exhausted its
    repairs (live 2026-07-15). The prompt now marks endings and states the
    rule up front, steering them to irrelevant-only."""
    from questfoundry.models.presentation import Ending, Passage
    from questfoundry.pipeline.runner import _environment

    end = Passage(
        id="passage:p-finale",
        created_by=Stage.POLISH,
        summary="the end",
        ending=Ending(id="e-finale", title="The End"),
    )
    mid = Passage(id="passage:p-mid", created_by=Stage.POLISH, summary="a scene")
    state = {"dilemma": "dilemma:d", "question": "q?", "flags": [("flag:f", "t")]}
    out = _environment().get_template("polish_audit.j2").render(
        vision=vision,
        cap=3,
        passages=[
            {"passage": end, "states": [state] * 4, "over": 1},
            {"passage": mid, "states": [state] * 2, "over": 0},
        ],
        notes=None,
        repair_errors=None,
        research=None,
    )
    # the ending is flagged in the passage list, with the rule at the point of use
    assert "p-finale [ENDING — resolve over-cap by irrelevant only, never split]" in out
    assert "irrelevant only" in out  # its over-cap note steers away from split_on
    assert "p-mid [ENDING" not in out  # a non-ending passage is not marked
    assert "passage cannot" in out  # the rule is also stated in the split_on body
def test_fork_prompt_mark_instruction_is_shape_neutral(vision):
    """PR-0's exit-label residue paragraph was once written in sidetrack-only
    vocabulary ("the detour", "declined"), which both biased shape selection
    and mis-instructed diamond arms. The per-site fork prompt's mark rule
    must speak to both shapes."""
    from questfoundry.pipeline.runner import _environment

    out = _environment().get_template("polish_fork.j2").render(
        vision=vision,
        cast=[],
        reserve=[],
        segment=[],
        before=Beat(
            id="beat:a",
            created_by=Stage.GROW,
            summary="a",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.BRIDGE,
        ),
        after=Beat(
            id="beat:b",
            created_by=Stage.GROW,
            summary="b",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.BRIDGE,
        ),
        arms=2,
        keywords=[],
        host_premise="",
        notes=None,
        repair_errors=None,
        research=None,
    )
    mark = out[out.index("Each arm's beat summaries") : out.index("That mark is textural")]
    assert "sibling" in mark  # the mark rule speaks to arms with siblings
    assert "detour" not in mark and "declined" not in mark  # not sidetrack-only


# -- cosmetic grant model (cosmetic-forks PR-4) --------------------------------


def _cosmetic_grant_graph(*, grant: bool, require: bool):
    """root -> grant_head -> gated -> end. The cosmetic flag cw is granted by
    grant_head (grants_flags) iff `grant`, and required by gated iff `require`."""
    from questfoundry.models.structure import FlagSource, StateFlag

    g = StoryGraph()
    mutations.add_flag(
        g,
        StateFlag(
            id="flag:cw",
            created_by=Stage.POLISH,
            source=FlagSource.COSMETIC,
            description="the pine path",
        ),
    )

    def beat(slug, **kw):
        b = Beat(
            id=f"beat:{slug}",
            created_by=Stage.POLISH,
            summary=slug,
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.FALSE_BRANCH,
            **kw,
        )
        mutations.add_beat(g, b, [])
        return b.id

    root = beat("root")
    head = beat("grant-head", grants_flags=["flag:cw"] if grant else [])
    gated = beat("gated", requires_flags=["flag:cw"] if require else [])
    end = beat("end", is_ending=True)
    mutations.add_ordering(g, root, head)
    mutations.add_ordering(g, head, gated)
    mutations.add_ordering(g, gated, end)
    return g


def test_grant_beats_and_choice_grants_cover_cosmetic_flags():
    g = _cosmetic_grant_graph(grant=True, require=False)
    # grant_beats returns the rendering head that lists the flag (was [] pre-PR-4)
    assert queries.grant_beats(g, "flag:cw") == ["beat:grant-head"]
    # choice_grants projects it: an entry into the passage holding the head grants it
    assert pc.choice_grants(g, ["beat:grant-head"]) == ["flag:cw"]
    assert pc.choice_grants(g, ["beat:root"]) == []  # a passage without the head grants nothing


def test_i10_accepts_a_granted_cosmetic_flag(vision):
    g = _cosmetic_grant_graph(grant=True, require=True)
    # gated requires cw, granted upstream at grant-head (its DAG ancestor) — I10 clean
    i10 = [i for i in run_checks(g, vision, Stage.POLISH) if i.check == "I10"]
    assert i10 == []


def test_i10_flags_an_ungranted_cosmetic_requirement(vision):
    g = _cosmetic_grant_graph(grant=False, require=True)  # required, never granted
    i10 = [i for i in run_checks(g, vision, Stage.POLISH) if i.check == "I10"]
    assert any(
        "beat:gated requires" in i.message and "no arc can satisfy" in i.message for i in i10
    )


def test_grants_flags_round_trips(vision, tmp_path):
    from questfoundry.project.io import load_project, save_project

    g = _cosmetic_grant_graph(grant=True, require=False)
    save_project(Project(root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g))
    reloaded = load_project(tmp_path)
    assert reloaded.graph.node("beat:grant-head").grants_flags == ["flag:cw"]
    assert reloaded.graph.node("beat:root").grants_flags == []  # default preserved


def _cosmetic_flag(g, slug):
    from questfoundry.models.structure import FlagSource, StateFlag

    mutations.add_flag(
        g,
        StateFlag(
            id=f"flag:cw-{slug}",
            created_by=Stage.POLISH,
            description=slug,
            source=FlagSource.COSMETIC,
        ),
    )
    return f"flag:cw-{slug}"


def _fb_beat(slug, **kwargs):
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.POLISH,
        summary=slug,
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
        **kwargs,
    )


def _bridge(slug):
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.GROW,
        summary=slug,
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.BRIDGE,
    )


def _diamond_keyword_graph(gated_on: str) -> StoryGraph:
    """a -> {x, y} -> b -> d -> {gd?, f}: a cosmetic diamond whose arms grant
    cw-x / cw-y, then a later entry gated on ``gated_on``. The projected walk
    deterministically takes arm x (topological group order)."""
    g = StoryGraph()
    for slug in ("a", "b", "d", "f"):
        mutations.add_beat(g, _bridge(slug), [])
    cw_x, cw_y = _cosmetic_flag(g, "x"), _cosmetic_flag(g, "y")
    mutations.add_beat(g, _fb_beat("x", grants_flags=[cw_x]), [])
    mutations.add_beat(g, _fb_beat("y", grants_flags=[cw_y]), [])
    mutations.add_beat(g, _fb_beat("gd", requires_flags=[gated_on]), [])
    for src, dst in [
        ("a", "x"), ("a", "y"), ("x", "b"), ("y", "b"), ("b", "d"),
        ("d", "gd"), ("gd", "f"), ("d", "f"),
    ]:
        mutations.add_ordering(g, f"beat:{src}", f"beat:{dst}")
    return g


def test_projected_walks_hold_cosmetic_flags_only_when_walked():
    """Open question 5, resolved: a cosmetic grant sits in every arc view,
    so view-derived holding counted keywords from detours the walk never
    took. Cosmetic flags accrue as the walk traverses the granting group;
    dilemma flags stay view-derived."""
    preset = SCOPE_PRESETS["micro"]
    # the walk takes arm x, so a cw-y-gated entry is never live: only the
    # diamond itself offers a decision
    g = _diamond_keyword_graph("flag:cw-y")
    ((_, decisions),) = pc.projected_walks(g, preset)
    assert decisions == 1
    # gated on the arm the walk DOES take, the entry is live: two decisions
    g = _diamond_keyword_graph("flag:cw-x")
    ((_, decisions),) = pc.projected_walks(g, preset)
    assert decisions == 2


# ---------------------------------------------------------------------------
# labels schema pin (medium run 2026-07-18, `labels:34`): a single-exit
# passage whose beats narrated several actions drew one label per action, all
# onto its one destination, and no repair round recovered because the schema
# let the malformed shape be expressed. The per-pass schema now pins `to` to
# the real out-destinations and fixes the list length to the exit count.
# ---------------------------------------------------------------------------


def _single_exit_source(project) -> int:
    """A source group with exactly one out-edge (the sidetrack arm's rejoin is
    one; assert we found a genuine single-exit group)."""
    groups = _groups(project)
    edges = pc.group_edges(groups, project.graph)
    from collections import Counter

    outdeg = Counter(x for x, _ in edges)
    return next(a for a, n in outdeg.items() if n == 1)


def test_labels_schema_forbids_two_labels_on_a_single_exit(vision, tmp_path):
    g = StoryGraph()
    project, _, _ = _sidetrack_project(g, vision, tmp_path)
    a = _single_exit_source(project)
    (dst,) = [b for x, b in pc.group_edges(_groups(project), g) if x == a]
    Schema = _labels_schema(a)(project)

    # the live failure shape — two labels onto the one exit — cannot validate
    with pytest.raises(ValidationError):
        Schema.model_validate(
            {"labels": [{"to": dst, "label": "one"}, {"to": dst, "label": "two"}]}
        )
    # the correct single label validates
    ok = Schema.model_validate({"labels": [{"to": dst, "label": "walk on"}]})
    assert len(ok.labels) == 1


def test_labels_schema_pins_destination_to_the_real_exits(vision, tmp_path):
    g = StoryGraph()
    project, _, _ = _sidetrack_project(g, vision, tmp_path)
    a = _single_exit_source(project)
    (dst,) = [b for x, b in pc.group_edges(_groups(project), g) if x == a]
    Schema = _labels_schema(a)(project)

    # a destination that is not an actual out-edge is unrepresentable
    bogus = dst + 9999
    with pytest.raises(ValidationError):
        Schema.model_validate({"labels": [{"to": bogus, "label": "nowhere"}]})


def test_labels_schema_fixes_length_to_the_exit_count(vision, tmp_path):
    g = StoryGraph()
    project, before, _ = _sidetrack_project(g, vision, tmp_path)
    groups = _groups(project)
    before_idx = next(i for i, grp in enumerate(groups) if before in grp)
    out = [b for x, b in pc.group_edges(groups, g) if x == before_idx]
    assert len(out) >= 2  # the fork source has multiple exits
    Schema = _labels_schema(before_idx)(project)

    # too few entries (one label for a multi-exit passage) cannot validate
    with pytest.raises(ValidationError):
        Schema.model_validate({"labels": [{"to": out[0], "label": "only one"}]})
    # exactly one per exit validates
    ok = Schema.model_validate(
        {"labels": [{"to": b, "label": f"go {b}"} for b in out]}
    )
    assert len(ok.labels) == len(out)


def test_labels_apply_still_guards_duplicate_destination(vision, tmp_path):
    """The multi-exit duplicate the enum cannot forbid (both `to` values are
    valid members) stays caught by the apply-layer joint-constraint guard —
    the refpin.py division of labor, so the contract holds even if a provider
    ignores the schema length pin."""
    g = StoryGraph()
    project, before, _ = _sidetrack_project(g, vision, tmp_path)
    groups = _groups(project)
    before_idx = next(i for i, grp in enumerate(groups) if before in grp)
    out = [b for x, b in pc.group_edges(groups, g) if x == before_idx]
    _apply_summaries(project)
    with pytest.raises(ApplyError, match="labeled twice"):
        _labels_apply(before_idx)(
            LabelsProposal(
                labels=[
                    EdgeLabelSpec.model_validate({"to": out[0], "label": "a"}),
                    EdgeLabelSpec.model_validate({"to": out[0], "label": "b"}),
                ]
            ),
            project,
        )


def test_labels_prompt_drops_the_plural_differ_line_for_a_single_exit(vision, tmp_path):
    """The nudge behind the live failure: an unconditional 'labels must differ
    from one another' presupposes several labels even when a passage has one
    exit. It renders only when there is genuinely more than one destination."""
    from questfoundry.pipeline import runner

    env = runner._environment()
    tmpl = env.get_template("polish_labels.j2")

    def render(dests):
        return tmpl.render(
            vision=vision,
            index=0,
            beats=[],
            dests=dests,
            is_rendering=False,
            notes="",
            repair_errors=[],
            research="",
        )

    one = render([{"index": 5, "summary": "s", "requires": [], "grants": [],
                   "is_ending": False, "siblings": [], "premise": ""}])
    assert "must differ from one another" not in one
    assert "write exactly 1 label," in one

    two = render([
        {"index": 5, "summary": "s", "requires": [], "grants": [],
         "is_ending": False, "siblings": [], "premise": ""},
        {"index": 6, "summary": "t", "requires": [], "grants": [],
         "is_ending": False, "siblings": [], "premise": ""},
    ])
    assert "must differ from one another" in two
    assert "write exactly 2 labels," in two
