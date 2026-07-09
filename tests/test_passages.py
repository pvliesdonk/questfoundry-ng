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
    FinalizeProposal,
    LabelSpec,
    PassageSpec,
    PassagesProposal,
    ResidueSpec,
    VariantSpec,
    _audit_apply,
    _finalize_apply,
    _light_needs,
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
    # heavy needs no residue beats (variants carry it); cadence sites may
    # still engage finalize, so assert the residue claim directly
    assert not _light_needs(project)

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
        requires_flags=[need.path_flags["path:sub-a"]],
    )
    pc.insert_residue_beat(g, beat, "path:sub-a", need.rejoin)
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
    flags = sorted(queries.dilemma_flags(g, "dilemma:sub").values())
    assert _variant_needs(g) == {
        "beat:main-commit-a": flags,
        "beat:main-commit-b": flags,
    }
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    _passages_apply(_proposal_for(g), project)
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
    order = next(
        o
        for o in weave.candidates(planned)
        if o.index("resolve:dilemma:sub1") < o.index("pre:beat:main-pre1")
        and o.index("resolve:dilemma:sub2") < o.index("pre:beat:main-pre1")
    )
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
