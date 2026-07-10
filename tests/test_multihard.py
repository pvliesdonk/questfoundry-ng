"""Multi-hard weaving (M5): nested hard forks, per-world instantiation,
and the invariant refinements the tensor model demands (design doc 01 §5).

Stories here are built through the real weave — plan, candidates,
realize — never by hand-wiring the nested topology."""

from __future__ import annotations

import pytest

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.drama import DilemmaRole
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    ImpactEffect,
    StructuralPurpose,
)
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import _derive_flags
from questfoundry.play.simulate import walk_all_arcs
from tests.conftest import make_dilemma, narrative_beat
from tests.test_weave import scaffold

G3 = {"I3", "I4", "I5", "I6", "I7", "I8", "I9", "G3-FLAGS"}


def _errors(g, vision, stage=Stage.GROW, checks=G3):
    issues = run_checks(g, vision, stage)
    return [i for i in issues if i.severity == Severity.ERROR and i.check in checks]


def two_hard_story(g: StoryGraph, *, soft: bool = False, wraps_hards: bool = False):
    """Setup + two hard Ys ('main', 'twist'), optionally a soft 'sub'."""
    d1, p1a, p1b = make_dilemma(g, "main", role=DilemmaRole.HARD)
    d2, p2a, p2b = make_dilemma(g, "twist", role=DilemmaRole.HARD)
    mutations.add_beat(
        g,
        Beat(
            id="beat:opening",
            created_by=Stage.SEED,
            summary="opening",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.SETUP,
        ),
        [],
    )
    scaffold(g, "main", d1, p1a, p1b)
    scaffold(g, "twist", d2, p2a, p2b)
    if wraps_hards:
        mutations.add_dilemma_relation(g, EdgeKind.WRAPS, d2, d1)
    if soft:
        d3, p3a, p3b = make_dilemma(g, "sub", role=DilemmaRole.SOFT)
        scaffold(g, "sub", d3, p3a, p3b, endings=False)
        mutations.add_dilemma_relation(g, EdgeKind.SERIAL, d1, d3)


def realize_first(g: StoryGraph, predicate=None) -> weave.RealizeReport:
    planned = weave.plan(g)
    orders = weave.candidates(planned)
    order = next(o for o in orders if predicate is None or predicate(o))
    return weave.realize(g, planned, order)


# -- candidate enumeration ------------------------------------------------------


def test_candidates_cover_both_nestings():
    g = StoryGraph()
    two_hard_story(g)
    orders = weave.candidates(weave.plan(g))
    climaxes = {order[-1] for order in orders}
    assert climaxes == {"resolve:dilemma:main", "resolve:dilemma:twist"}


def test_wraps_between_hards_forces_the_nesting():
    g = StoryGraph()
    two_hard_story(g, wraps_hards=True)  # twist wraps main: main resolves first
    orders = weave.candidates(weave.plan(g))
    assert orders
    for order in orders:
        assert order[-1] == "resolve:dilemma:twist"
        assert order.index("pre:beat:twist-pre0") < order.index("pre:beat:main-pre0")


# -- realization ------------------------------------------------------------------


def test_realize_instantiates_the_climax_y_per_world(vision):
    g = StoryGraph()
    two_hard_story(g)
    report = realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")

    # symmetric per-world instances; the template Y is gone
    for side in ("a", "b"):
        for kind in ("commit", "post"):
            template = f"beat:twist-{kind}-{side}"
            assert template not in g
            assert report.clones[template] == [
                f"{template}--main-a",
                f"{template}--main-b",
            ]
            for clone_id in report.clones[template]:
                clone = g.node(clone_id)
                assert isinstance(clone, Beat)
                assert clone.created_by == Stage.GROW
    # clones keep membership and function: one commit per world per path
    for side in ("a", "b"):
        commits = queries.commit_beats(g, f"path:twist-{side}")
        assert commits == [
            f"beat:twist-commit-{side}--main-a",
            f"beat:twist-commit-{side}--main-b",
        ]
        assert {queries.world_of(g, c) for c in commits} == {
            frozenset({"beat:main-commit-a"}),
            frozenset({"beat:main-commit-b"}),
        }
    # the first fork's tails stopped being endings; the climax's did not
    assert sorted(report.de_ended) == ["beat:main-post-a", "beat:main-post-b"]
    for tail in report.de_ended:
        assert not g.node(tail).is_ending
    endings = [b.id for b in g.nodes_of(Beat) if b.is_ending]
    assert len(endings) == 4  # 2 hard dilemmas -> endings multiply

    _derive_flags(g)
    assert len(queries.roots(g)) == 1
    assert len(queries.arc_selections(g)) == 4
    assert _errors(g, vision) == []
    walks = walk_all_arcs(g)
    assert len(walks) == 4
    assert all(not w.problems for w in walks)
    assert len({w.ending for w in walks}) == 4


def test_freeze_records_per_world_forks(vision):
    g = StoryGraph()
    two_hard_story(g)
    realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")
    _derive_flags(g)
    record = mutations.freeze_topology(g)
    assert record.forks["dilemma:main"] == ["beat:main-commit-a", "beat:main-commit-b"]
    assert record.forks["dilemma:twist"] == [
        "beat:twist-commit-a--main-a",
        "beat:twist-commit-a--main-b",
        "beat:twist-commit-b--main-a",
        "beat:twist-commit-b--main-b",
    ]
    assert record.convergences == {}
    assert _errors(g, vision, checks={"I9"}) == []


# -- a locked storyline inside the worlds -----------------------------------------


def test_between_fork_locked_chain_lives_per_world(vision):
    from questfoundry.pipeline.stages.grow import _clone_targets
    from tests.conftest import make_locked_chain

    g = StoryGraph()
    two_hard_story(g)
    dl, path, _ = make_dilemma(g, "lock", explore=1)
    make_locked_chain(g, "lock", dl, path)
    # serial(main, lock): the chain enters after main's fork, so every
    # beat of it is instantiated once per world like any other unit
    mutations.add_dilemma_relation(g, EdgeKind.SERIAL, "dilemma:main", dl)
    report = realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")
    _derive_flags(g)

    for slug in ("lock-lead", "lock-resolve", "lock-after"):
        assert f"beat:{slug}" not in g
        assert report.clones[f"beat:{slug}"] == [
            f"beat:{slug}--main-a",
            f"beat:{slug}--main-b",
        ]
    commits = queries.commit_beats(g, path)
    assert commits == ["beat:lock-resolve--main-a", "beat:lock-resolve--main-b"]
    assert {queries.world_of(g, c) for c in commits} == {
        frozenset({"beat:main-commit-a"}),
        frozenset({"beat:main-commit-b"}),
    }
    # I3 (one resolution per world), I6 (every arc resolves it once) hold
    assert _errors(g, vision) == []
    for selection in queries.arc_selections(g):
        view = queries.arc_view(g, selection)
        assert len([c for c in commits if c in view]) == 1
    # the clones are contextualize targets like any per-world instance
    clone_ids = {b.id for b in _clone_targets(g)}
    assert {f"beat:lock-resolve--main-{w}" for w in ("a", "b")} <= clone_ids


# -- a soft dilemma inside the worlds ---------------------------------------------


def between_fork_soft(g: StoryGraph) -> weave.RealizeReport:
    """serial(main, sub) forces the soft dilemma after the first fork, so
    its whole Y is instantiated per world. The chosen order keeps one
    twist pre-commit beat after the soft diamond, giving each world a
    single-beat convergence."""
    two_hard_story(g, soft=True)

    def shape(order):
        return (
            order[-1] == "resolve:dilemma:twist"
            and order.index("pre:beat:twist-pre1") > order.index("resolve:dilemma:sub")
        )

    report = realize_first(g, shape)
    _derive_flags(g)
    return report


def test_between_fork_soft_dilemma_lives_per_world(vision):
    g = StoryGraph()
    between_fork_soft(g)

    # the soft Y was instantiated per world, dual membership intact
    for world in ("main-a", "main-b"):
        pre = g.node(f"beat:sub-pre0--{world}")
        assert isinstance(pre, Beat)
        assert queries.paths_of_beat(g, pre.id) == ["path:sub-a", "path:sub-b"]
    assert queries.commit_beats(g, "path:sub-a") == [
        "beat:sub-commit-a--main-a",
        "beat:sub-commit-a--main-b",
    ]
    (flag_a,) = [f for f in queries.dilemma_flags(g, "dilemma:sub").values() if "sub-a" in f]
    assert queries.grant_beats(g, flag_a) == [
        "beat:sub-commit-a--main-a",
        "beat:sub-commit-a--main-b",
    ]

    # per-world single-beat convergence on the cloned twist pre beat
    frontiers = queries.soft_rejoin_frontiers(g, "dilemma:sub")
    assert frontiers == [
        (frozenset({"beat:main-commit-a"}), ["beat:twist-pre1--main-a"]),
        (frozenset({"beat:main-commit-b"}), ["beat:twist-pre1--main-b"]),
    ]
    record = mutations.freeze_topology(g)
    assert record.convergences["dilemma:sub"] == [
        "beat:twist-pre1--main-a",
        "beat:twist-pre1--main-b",
    ]

    assert len(queries.arc_selections(g)) == 8
    assert _errors(g, vision) == []
    walks = walk_all_arcs(g)
    assert all(not w.problems for w in walks)
    assert len({w.ending for w in walks}) == 4  # soft collapses; hard multiplies


def test_per_world_convergence_needs_and_residue_coverage(vision):
    g = StoryGraph()
    between_fork_soft(g)
    needs = [n for n in pc.convergence_needs(g) if n.dilemma == "dilemma:sub"]
    assert [n.world for n in needs] == ["path:main-a", "path:main-b"]

    def residue(world_slug: str) -> Beat:
        return Beat(
            id=f"beat:afterglow-{world_slug}",
            created_by=Stage.POLISH,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.RESIDUE,
            requires_flags=[needs[0].path_flags["path:sub-a"]],
        )

    mutations.freeze_topology(g)
    # G4 runs on graphs with passages; one dummy passage arms the check
    from questfoundry.models.presentation import Passage

    mutations.add_passage(
        g,
        Passage(id="passage:p-opening", created_by=Stage.POLISH, summary="s"),
        ["beat:opening"],
    )
    # covering one world only is a violating construction: G4 names the other
    pc.insert_residue_beat(g, residue("main-a"), "path:sub-a", needs[0].rejoin)
    issues = run_checks(g, vision, Stage.POLISH)
    uncovered = [
        i
        for i in issues
        if i.check == "G4" and "residue" in i.message and "path:main-b" in i.message
    ]
    assert uncovered
    # covering both worlds clears it, and no arc dead-ends at the splices
    pc.insert_residue_beat(g, residue("main-b"), "path:sub-a", needs[1].rejoin)
    issues = run_checks(g, vision, Stage.POLISH)
    assert not [i for i in issues if i.check == "G4" and "residue" in i.message]
    assert _errors(g, vision, checks={"I6"}) == []


# -- the contextualize pass -------------------------------------------------------


CLONE_IDS = {
    f"beat:twist-{kind}-{side}--{world}"
    for kind in ("commit", "post")
    for side in ("a", "b")
    for world in ("main-a", "main-b")
}


def test_contextualize_targets_and_apply(vision, tmp_path):
    from questfoundry.pipeline.stages.grow import (
        ContextualizeProposal,
        RewriteSpec,
        _contextualize_apply,
        _contextualize_skip,
        _contextualize_targets,
    )
    from questfoundry.pipeline.types import ApplyError
    from questfoundry.project.io import Project

    g = StoryGraph()
    two_hard_story(g)
    realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")
    project = Project(root=tmp_path, name="t", stage=Stage.GROW, vision=vision, graph=g)
    assert _contextualize_skip(project) is None

    targets = _contextualize_targets(project)
    ids = {t["beat"].id for t in targets}
    assert ids == CLONE_IDS | {"beat:main-post-a", "beat:main-post-b"}
    by_id = {t["beat"].id: t for t in targets}
    clone = by_id["beat:twist-commit-a--main-a"]
    assert clone["kind"] == "clone"
    assert clone["world"] == "path:main-a"
    assert [f["answer"] for f in clone["facts"]] == ["a"]
    tail = by_id["beat:main-post-a"]
    assert tail["kind"] == "tail"
    assert tail["open_questions"] == ["?"]  # the climax question stays live

    rewrites = [RewriteSpec(beat=b, summary=f"in its world: {b}") for b in sorted(ids)]
    with pytest.raises(ApplyError, match="missing"):
        _contextualize_apply(ContextualizeProposal(rewrites=rewrites[:-1]), project)
    _contextualize_apply(ContextualizeProposal(rewrites=rewrites), project)
    assert g.node("beat:twist-post-a--main-b").summary.startswith("in its world")


def test_contextualize_skipped_on_single_hard(golden):
    from questfoundry.pipeline.stages.grow import _contextualize_skip

    assert _contextualize_skip(golden) is not None


# -- the passage layer over nested forks --------------------------------------------


def test_passage_layer_gets_four_titled_endings(vision, tmp_path):
    from questfoundry.models.presentation import Passage
    from questfoundry.pipeline.stages.polish import _passages_apply
    from questfoundry.project.io import Project
    from tests.test_passages import _proposal_for

    g = StoryGraph()
    two_hard_story(g)
    realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")
    _derive_flags(g)
    mutations.freeze_topology(g)
    project = Project(root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g)
    _passages_apply(_proposal_for(g), project)
    endings = [p for p in g.nodes_of(Passage) if p.ending is not None]
    assert len(endings) == 4
    issues = run_checks(g, vision, Stage.POLISH)
    polish_checks = {"I10", "I11", "I12", "I13", "G4"}
    assert [
        i for i in issues if i.severity == Severity.ERROR and i.check in polish_checks
    ] == []


# -- violating constructions -------------------------------------------------------


def test_i3_rejects_two_commits_in_one_world(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one", role=DilemmaRole.HARD)
    scaffold(g, "one", d, pa, pb)
    dup = narrative_beat("one-commit-a2", d, ImpactEffect.COMMITS)
    mutations.add_beat(g, dup, [pa])
    mutations.add_ordering(g, "beat:one-post-a", dup.id)
    issues = run_checks(g, vision, Stage.SEED)
    assert any(i.check == "I3" and "same world" in i.message for i in issues)


def test_i6_catches_a_world_that_never_commits(vision):
    """Realize a 2-hard weave, then strip world B's climax commit clone:
    every arc through world B must report the missing commit."""
    g = StoryGraph()
    two_hard_story(g)
    realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")
    _derive_flags(g)
    # pre-freeze removal so I9 stays silent; this leaves world B unable
    # to commit twist path a (its beats dead-end at the removed clone)
    mutations.remove_beat(g, "beat:twist-commit-a--main-b")
    issues = run_checks(g, vision, Stage.GROW)
    assert any(
        i.check == "I6" and "never commits path:twist-a" in i.message.replace("path ", "path:")
        for i in issues
    ) or any(
        i.check == "I6" and "path:twist-a" in i.message and "never commits" in i.message
        for i in issues
    )


def test_i7_catches_cross_world_reconvergence(vision):
    """Hard branches must not rejoin even via a deeper world: wiring one
    world's climax tail into the other world's beat is an I7/I3 break."""
    g = StoryGraph()
    two_hard_story(g)
    realize_first(g, lambda o: o[-1] == "resolve:dilemma:twist")
    _derive_flags(g)
    mutations.add_ordering(g, "beat:main-post-a", "beat:twist-commit-a--main-b")
    issues = run_checks(g, vision, Stage.GROW)
    assert any(i.check in ("I7", "I3") and i.severity == Severity.ERROR for i in issues)
