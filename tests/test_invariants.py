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


# -- locked dilemmas (single explored path; design doc 01 §4) ---------------


def test_b1_pre_triage_overgeneration_within_allowance(vision):
    g = StoryGraph()
    make_dilemma(g, "main", role=DilemmaRole.HARD, explore=0)
    make_dilemma(g, "sub", explore=0)
    make_dilemma(g, "extra", explore=0)  # micro allows 1 locked...
    make_dilemma(g, "spare", explore=0)  # ...plus 1 reserved (W2)
    assert errors_for("B1", g, vision, Stage.BRAINSTORM) == []
    make_dilemma(g, "surplus", explore=0)
    issues = errors_for("B1", g, vision, Stage.BRAINSTORM)
    assert any("at most 1 to lock plus 1 to reserve" in i.message for i in issues)


def test_b1_pre_triage_branched_shortfall_flagged(vision):
    g = StoryGraph()
    make_dilemma(g, "sub", explore=0)  # no hard dilemma at all
    issues = errors_for("B1", g, vision, Stage.BRAINSTORM)
    assert any(">=1 hard" in i.message for i in issues)


def test_b1_post_triage_locked_counts(vision):
    g = StoryGraph()
    make_dilemma(g, "main", role=DilemmaRole.HARD)
    make_dilemma(g, "sub")
    make_dilemma(g, "herring", explore=1)
    assert errors_for("B1", g, vision, Stage.BRAINSTORM) == []
    make_dilemma(g, "surplus", explore=1)
    issues = errors_for("B1", g, vision, Stage.BRAINSTORM)
    assert any("2 locked dilemma(s)" in i.message for i in issues)


def test_b1_post_triage_locked_hard_leaves_branched_shortfall(vision):
    g = StoryGraph()
    make_dilemma(g, "main", role=DilemmaRole.HARD, explore=1)  # locked, not branched
    make_dilemma(g, "sub")
    issues = errors_for("B1", g, vision, Stage.BRAINSTORM)
    assert any("expects 1 branched hard" in i.message for i in issues)


def test_i3_locked_chain_needs_resolution_lead_in_and_aftermath(vision):
    g = StoryGraph()
    d, path, _ = make_dilemma(g, "lock", explore=1)
    mutations.add_beat(g, narrative_beat("lock-lead", d), [path])
    issues = errors_for("I3", g, vision, Stage.SEED)
    assert any("no resolution" in i.message for i in issues)
    mutations.add_beat(g, narrative_beat("lock-resolve", d, ImpactEffect.COMMITS), [path])
    mutations.add_ordering(g, "beat:lock-lead", "beat:lock-resolve")
    issues = errors_for("I3", g, vision, Stage.SEED)
    assert any("no aftermath beat" in i.message for i in issues)
    mutations.add_beat(g, narrative_beat("lock-after", d), [path])
    mutations.add_ordering(g, "beat:lock-resolve", "beat:lock-after")
    assert errors_for("I3", g, vision, Stage.SEED) == []


def test_i3_locked_resolution_first_has_no_lead_in(vision):
    g = StoryGraph()
    d, path, _ = make_dilemma(g, "lock", explore=1)
    mutations.add_beat(g, narrative_beat("lock-resolve", d, ImpactEffect.COMMITS), [path])
    mutations.add_beat(g, narrative_beat("lock-after", d), [path])
    mutations.add_ordering(g, "beat:lock-resolve", "beat:lock-after")
    issues = errors_for("I3", g, vision, Stage.SEED)
    assert any("no lead-in beat" in i.message for i in issues)


def test_i6_every_arc_must_resolve_a_locked_dilemma(vision):
    from tests.conftest import make_locked_chain

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "main", role=DilemmaRole.HARD)
    make_y_scaffold(g, "main", d, pa, pb)
    dl, path, _ = make_dilemma(g, "lock", explore=1)
    make_locked_chain(g, "lock", dl, path)
    # woven into ONE branch only: the path:main-b arc never resolves it
    g.node("beat:main-post-a").is_ending = False
    mutations.add_ordering(g, "beat:main-commit-a", "beat:lock-lead")
    mutations.add_ordering(g, "beat:lock-after", "beat:main-post-a")
    issues = errors_for("I6", g, vision)
    assert any("never commits path path:lock-a" in i.message for i in issues)


def test_locked_dilemmas_make_no_worlds_and_need_no_flags(vision):
    from questfoundry.graph import queries
    from questfoundry.models.structure import FlagSource, StateFlag
    from tests.conftest import make_locked_chain

    g = StoryGraph()
    d, path, _ = make_dilemma(g, "lock", role=DilemmaRole.HARD, explore=1)
    make_locked_chain(g, "lock", d, path)
    # a locked hard-role dilemma never forks: no worlds, no arc multiplication
    assert queries.hard_commit_beats(g) == set()
    assert queries.world_of(g, "beat:lock-after") == frozenset()
    assert queries.arc_selections(g) == [{}]
    # its consequence is exempt from flag derivation...
    assert errors_for("G3-FLAGS", g, vision) == []
    # ...and granting a flag from a locked path is itself an error
    mutations.add_flag(
        g,
        StateFlag(
            id="flag:lock-a",
            created_by=Stage.GROW,
            description="d",
            source=FlagSource.DILEMMA,
            path=path,
        ),
    )
    issues = errors_for("G3-FLAGS", g, vision)
    assert any("world fact" in i.message for i in issues)


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


def test_g5_missing_prose_flagged(golden):
    g = golden.graph
    g.node("passage:p-tremor").prose = ""
    issues = errors_for("G5", g, golden.vision, Stage.FILL)
    assert any("no prose" in i.message for i in issues)


def test_b5_word_budget_is_advisory(golden):
    g = golden.graph
    g.node("passage:p-tremor").prose = "barely any words here"
    issues = run_checks(g, golden.vision, Stage.FILL)
    warnings = [i for i in issues if i.check == "B5"]
    assert warnings and all(i.severity == Severity.WARNING for i in warnings)


def test_golden_story_passes_all_gates(golden):
    issues = run_checks(golden.graph, golden.vision, golden.stage, enrichment=golden.enrichment)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == []
    # band-clean under the words-primary scale table (M8): the golden
    # fixture anchors micro's floor
    assert issues == []


def test_g4_arc_references_fail_loud():
    """A dangling arc reference silently corrupts FILL's arc positions
    downstream — the gate catches it (this session's own authoring slip:
    `beat:the-offer` for `beat:offer` sailed through validation)."""
    from questfoundry.graph.validate import Severity, run_checks
    from questfoundry.models.base import Stage
    from questfoundry.models.world import ArcPivot, EntityArc, PathEnd
    from questfoundry.project import load_project
    from tests.conftest import GOLDEN

    project = load_project(GOLDEN)
    project.graph.node("character:sleeper").arc = EntityArc(
        begins="asleep",
        pivots=[ArcPivot(beat="beat:the-offer", becomes="waking")],
        ends=[PathEnd(path="path:no-such", state="gone")],
    )
    issues = [
        i
        for i in run_checks(project.graph, project.vision, Stage.POLISH)
        if i.severity == Severity.ERROR and i.check == "G4"
    ]
    assert any("beat:the-offer" in i.message for i in issues)
    assert any("path:no-such" in i.message for i in issues)


def test_b6_walker_holds_cosmetic_flags_only_via_traversed_grants(vision):
    """B6's walk must not count a keyword-gated entry as a live decision
    when the walk never took the granting rendering (cosmetic-forks §4,
    open question 5 — cosmetic holds accrue from traversed choice grants,
    not grant-beats-in-view)."""
    from questfoundry.models.presentation import Choice, Passage
    from questfoundry.models.structure import FlagSource, StateFlag

    g = StoryGraph()

    def structural(slug, purpose, **kwargs):
        mutations.add_beat(
            g,
            Beat(
                id=f"beat:{slug}",
                created_by=Stage.POLISH,
                summary=slug,
                beat_class=BeatClass.STRUCTURAL,
                purpose=purpose,
                **kwargs,
            ),
            [],
        )

    for slug in ("a", "d", "f"):
        structural(slug, StructuralPurpose.BRIDGE)
    for slug in ("x", "y"):
        mutations.add_flag(
            g,
            StateFlag(
                id=f"flag:cw-{slug}",
                created_by=Stage.POLISH,
                description=slug,
                source=FlagSource.COSMETIC,
            ),
        )
        structural(slug, StructuralPurpose.FALSE_BRANCH, grants_flags=[f"flag:cw-{slug}"])
    structural("gy", StructuralPurpose.FALSE_BRANCH, requires_flags=["flag:cw-y"])
    for src, dst in [
        ("a", "x"), ("a", "y"), ("x", "d"), ("y", "d"),
        ("d", "gy"), ("gy", "f"), ("d", "f"),
    ]:
        mutations.add_ordering(g, f"beat:{src}", f"beat:{dst}")

    prose = {"pa": 300, "px": 300, "py": 300, "pd": 200, "pgy": 50, "pf": 100}
    for pid, beat in [
        ("pa", "a"), ("px", "x"), ("py", "y"), ("pd", "d"), ("pgy", "gy"), ("pf", "f"),
    ]:
        mutations.add_passage(
            g,
            Passage(
                id=f"passage:{pid}",
                created_by=Stage.POLISH,
                summary=pid,
                prose="w " * prose[pid],
            ),
            [f"beat:{beat}"],
        )
    for src, dst, req, grants in [
        ("pa", "px", [], ["flag:cw-x"]),
        ("pa", "py", [], ["flag:cw-y"]),
        ("px", "pd", [], []),
        ("py", "pd", [], []),
        ("pd", "pgy", ["flag:cw-y"], []),
        ("pgy", "pf", [], []),
        ("pd", "pf", [], []),
    ]:
        mutations.add_choice(
            g,
            f"passage:{src}",
            f"passage:{dst}",
            Choice(label=f"{src}->{dst}", requires=req, grants=grants),
        )
    # the walk: pa (decision: px/py live) -> px -> pd -> pf. cw-y was never
    # granted along it, so pd offers no second live choice: 900 words / 1
    # decision = 900, above the band -> B6 warns. View-derived holding would
    # have counted 2 decisions (450, in band) and stayed silent.
    b6 = [i for i in run_checks(g, vision, Stage.FILL) if i.check == "B6"]
    assert b6 and "900" in b6[0].message


def _i16(g, vision):
    return [
        i
        for i in run_checks(g, vision, Stage.POLISH)
        if i.check == "I16" and i.severity == Severity.ERROR
    ]


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


def test_i16_cosmetic_gate_on_non_rendering_beat_is_an_error(vision):
    """I16 (cosmetic-gate locality): a keyword may gate only a cosmetic-fork
    rendering — a narrative beat depending on one is a dilemma in costume."""
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    cw = _cosmetic_flag(g, "pine")
    beat = g.node("beat:one-pre")
    beat.requires_flags = [cw]
    issues = _i16(g, vision)
    assert issues and "beat:one-pre" in issues[0].message
    assert "rendering" in issues[0].message


def test_i16_cosmetic_gate_on_ordinary_choice_is_an_error(vision):
    from questfoundry.models.presentation import Choice, Passage

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    cw = _cosmetic_flag(g, "pine")
    mutations.add_passage(
        g,
        Passage(id="passage:src", created_by=Stage.POLISH, summary="s"),
        ["beat:one-pre"],
    )
    mutations.add_passage(
        g,
        Passage(id="passage:dst", created_by=Stage.POLISH, summary="d"),
        ["beat:one-commit-a"],
    )
    mutations.add_choice(
        g, "passage:src", "passage:dst", Choice(label="go", requires=[cw])
    )
    issues = _i16(g, vision)
    assert issues and "passage:dst" in issues[0].message


def test_i16_accepts_a_gated_rendering(vision):
    g = StoryGraph()
    cw = _cosmetic_flag(g, "pine")
    mutations.add_beat(
        g,
        Beat(
            id="beat:gated-arm",
            created_by=Stage.POLISH,
            summary="only holders see this",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.FALSE_BRANCH,
            requires_flags=[cw],
        ),
        [],
    )
    assert _i16(g, vision) == []
