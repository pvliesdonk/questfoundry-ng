"""Each invariant gets a violating construction and the golden conforming case."""

from questfoundry.graph import mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import Stage
from questfoundry.models.drama import DilemmaRole
from questfoundry.models.structure import ImpactEffect
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat


def errors_for(check: str, g, vision, stage=Stage.GROW):
    issues = run_checks(g, vision, stage)
    return [i for i in issues if i.check == check and i.severity == Severity.ERROR]


def test_i3_incomplete_scaffold_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    # commit beats only: no pre-commit chain, no post-commit payoff
    mutations.add_beat(g, narrative_beat("c-a", d, ImpactEffect.COMMITS), [pa])
    mutations.add_beat(g, narrative_beat("c-b", d, ImpactEffect.COMMITS), [pb])
    issues = errors_for("I3", g, vision, Stage.SEED)
    assert any("no shared pre-commit" in i.message for i in issues)
    assert any("no exclusive post-commit" in i.message for i in issues)


def test_i4_two_roots_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.add_beat(g, narrative_beat("floater", d), [pa])  # no ordering edges
    assert errors_for("I4", g, vision)


def test_i6_dead_end_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    # a non-ending beat hanging off one arc's ending
    mutations.add_beat(g, narrative_beat("stub", d), [pa])
    mutations.add_ordering(g, "beat:one-post-a", "beat:stub")
    assert any("dead-ends" in i.message for i in errors_for("I6", g, vision))


def test_i7_hard_dilemma_must_not_reconverge(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one", role=DilemmaRole.HARD)
    make_y_scaffold(g, "one", d, pa, pb)
    # force a reconvergence: both posts feed one shared ending
    from questfoundry.models.structure import Beat, BeatClass, StructuralPurpose

    mutations.add_beat(
        g,
        Beat(
            id="beat:shared-end",
            created_by=Stage.SEED,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.EPILOGUE,
            is_ending=True,
        ),
        [],
    )
    mutations.add_ordering(g, "beat:one-post-a", "beat:shared-end")
    mutations.add_ordering(g, "beat:one-post-b", "beat:shared-end")
    assert any("reconverge" in i.message for i in errors_for("I7", g, vision))


def test_i7_soft_dilemma_must_reconverge(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one", role=DilemmaRole.SOFT)
    make_y_scaffold(g, "one", d, pa, pb)  # posts are separate endings: never rejoin
    assert any("never reconverge" in i.message for i in errors_for("I7", g, vision))


def test_i9_fork_change_after_freeze_flagged(golden, vision):
    g = golden.graph
    g.frozen.forks["dilemma:truth"] = ["beat:tell-commit"]  # pretend the fork moved
    assert any("fork changed" in i.message for i in errors_for("I9", g, golden.vision))


def test_golden_story_passes_all_gates(golden):
    issues = run_checks(golden.graph, golden.vision, golden.stage)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == []
    # the fixture is deliberately smaller than the micro passage target
    assert any(i.check == "B3" for i in issues)
