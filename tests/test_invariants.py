"""Each invariant gets a violating construction and the golden conforming case."""

from questfoundry.graph import mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import Stage
from questfoundry.models.drama import DilemmaRole
from questfoundry.models.structure import Beat, BeatClass, ImpactEffect, StructuralPurpose
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat


def errors_for(check: str, g, vision, stage=Stage.GROW):
    issues = run_checks(g, vision, stage)
    return [i for i in issues if i.check == check and i.severity == Severity.ERROR]


def test_g1_disjoint_dilemmas_flagged(vision):
    g = StoryGraph()
    make_dilemma(g, "one")  # each helper dilemma gets its own anchor entity,
    make_dilemma(g, "two")  # so two of them share nothing
    issues = errors_for("G1", g, vision, Stage.BRAINSTORM)
    assert any("share an anchored entity" in i.message for i in issues)


def test_g1_unanchored_entity_warned(vision):
    from questfoundry.models.world import Entity

    g = StoryGraph()
    make_dilemma(g, "one")
    mutations.add_entity(
        g, Entity(id="character:extra", created_by=Stage.BRAINSTORM, name="X", concept="c")
    )
    issues = run_checks(g, vision, Stage.BRAINSTORM)
    warnings = [i for i in issues if i.check == "G1" and i.severity == Severity.WARNING]
    assert any("character:extra" in i.message for i in warnings)


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


def _passage_layer(g, d, pa, pb):
    """Wrap a Y-scaffold in a minimal passage graph: pre -> (a|b endings)."""
    from questfoundry.models.presentation import Choice, Ending, Passage
    from questfoundry.models.structure import FlagSource, StateFlag

    mutations.add_flag(
        g,
        StateFlag(
            id="flag:x", created_by=Stage.GROW, description="x", source=FlagSource.DILEMMA, path=pa
        ),
    )

    def passage(slug, beats, ending=False):
        node = Passage(
            id=f"passage:{slug}",
            created_by=Stage.POLISH,
            summary=slug,
            ending=Ending(id=f"e-{slug}", title=slug) if ending else None,
        )
        mutations.add_passage(g, node, beats)
        return node.id

    pre = passage("pre", ["beat:one-pre"])
    end_a = passage("end-a", ["beat:one-commit-a", "beat:one-post-a"], ending=True)
    end_b = passage("end-b", ["beat:one-commit-b", "beat:one-post-b"], ending=True)
    mutations.add_choice(g, pre, end_a, Choice(label="a", grants=["flag:x"]))
    mutations.add_choice(g, pre, end_b, Choice(label="b"))
    return pre, end_a, end_b


def test_i10_unsatisfiable_gate_flagged(vision):
    from questfoundry.models.presentation import Choice

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    pre, end_a, end_b = _passage_layer(g, d, pa, pb)
    # flag:x is granted at path a's commit — never before the start passage,
    # so a gate on a choice OUT of the start passage can never be satisfied
    mutations.add_beat(
        g,
        Beat(
            id="beat:extra",
            created_by=Stage.POLISH,
            summary="x",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.BRIDGE,
        ),
        [],
    )
    mutations.add_ordering(g, "beat:one-pre", "beat:extra")
    mutations.add_ordering(g, "beat:extra", "beat:one-commit-a")
    from questfoundry.models.presentation import Passage

    mutations.add_passage(
        g, Passage(id="passage:extra", created_by=Stage.POLISH, summary="x"), ["beat:extra"]
    )
    mutations.add_choice(g, pre, "passage:extra", Choice(label="gated", requires=["flag:x"]))
    mutations.add_choice(g, "passage:extra", end_a, Choice(label="on"))
    issues = errors_for("I10", g, vision, Stage.POLISH)
    assert any("no arc can satisfy" in i.message for i in issues)


def test_i11_beat_in_unrelated_passages_flagged(vision):
    from questfoundry.models.presentation import Passage

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    _passage_layer(g, d, pa, pb)
    # the same beat re-presented by a second passage with no variant link
    mutations.add_passage(
        g,
        Passage(id="passage:dup", created_by=Stage.POLISH, summary="dup"),
        ["beat:one-post-a"],
    )
    issues = errors_for("I11", g, vision, Stage.POLISH)
    assert any("unrelated passages" in i.message for i in issues)


def test_i13_second_start_and_choiceless_passage_flagged(vision):
    from questfoundry.models.presentation import Passage

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    _passage_layer(g, d, pa, pb)
    # an orphan passage: no incoming choice (second start), no outgoing choice
    mutations.add_beat(
        g,
        Beat(
            id="beat:orphan",
            created_by=Stage.POLISH,
            summary="o",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.BRIDGE,
        ),
        [],
    )
    mutations.add_passage(
        g, Passage(id="passage:orphan", created_by=Stage.POLISH, summary="o"), ["beat:orphan"]
    )
    issues = errors_for("I13", g, vision, Stage.POLISH)
    assert any("exactly one start" in i.message for i in issues)


def test_g3_underived_consequence_flagged(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    issues = errors_for("G3-FLAGS", g, vision)
    assert len(issues) == 2  # one consequence per path, neither derived
    from questfoundry.pipeline.stages.grow import _derive_flags

    _derive_flags(g)
    assert errors_for("G3-FLAGS", g, vision) == []


def test_b4_arc_beat_budget_is_advisory(vision):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)  # 3 beats per arc; micro targets >=8
    issues = run_checks(g, vision, Stage.GROW)
    warnings = [i for i in issues if i.check == "B4"]
    assert warnings and all(i.severity == Severity.WARNING for i in warnings)


def test_g4_duplicate_sibling_labels_flagged(golden):
    from questfoundry.models.presentation import Choice

    g = golden.graph
    # a second identically labeled, identically gated choice from p-tremor
    mutations.add_choice(
        g,
        "passage:p-tremor",
        "passage:p-fair-weather",
        Choice(label="Send the ship away and tend the light", requires=[], grants=[]),
    )
    issues = errors_for("G4", g, golden.vision, Stage.POLISH)
    assert any("two choices labeled" in i.message for i in issues)


def test_g4_missing_residue_coverage_flagged(vision):
    from questfoundry.models.presentation import Passage
    from questfoundry.pipeline.stages.grow import _derive_flags

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")  # soft, light residue
    make_y_scaffold(g, "one", d, pa, pb)
    # force a convergence so the light dilemma demands a residue beat
    for beat_id in ("beat:one-post-a", "beat:one-post-b"):
        g.node(beat_id).is_ending = False
    mutations.add_beat(
        g,
        Beat(
            id="beat:one-after",
            created_by=Stage.SEED,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.EPILOGUE,
            is_ending=True,
        ),
        [],
    )
    mutations.add_ordering(g, "beat:one-post-a", "beat:one-after")
    mutations.add_ordering(g, "beat:one-post-b", "beat:one-after")
    _derive_flags(g)
    mutations.add_passage(
        g, Passage(id="passage:p-one", created_by=Stage.POLISH, summary="s"), ["beat:one-after"]
    )
    issues = errors_for("G4", g, vision, Stage.POLISH)
    assert any("no residue beat" in i.message for i in issues)


def test_golden_story_passes_all_gates(golden):
    issues = run_checks(golden.graph, golden.vision, golden.stage)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == []
    # the fixture is deliberately smaller than the micro passage target
    assert any(i.check == "B3" for i in issues)
