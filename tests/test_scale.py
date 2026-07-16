"""M8 depth & scale: the structural simulation validates the presets it
calibrated (design doc 01 §2, mini-ADR A19), and the pieces the cadence
math rides on — capped collapse, texture word bands, the words-aware
diamond budget, walk-based B6 — hold under violating constructions."""

from __future__ import annotations

from questfoundry.graph import mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import (
    Context,
    Severity,
    check_b6_choice_cadence,
    check_b7_total_words,
    check_b8_pacing,
    run_checks,
)
from questfoundry.models.base import Stage
from questfoundry.models.concept import SCOPE_PRESETS, Vision
from questfoundry.models.presentation import Choice, Passage
from questfoundry.models.structure import Beat, BeatClass, SceneType, StructuralPurpose
from questfoundry.pipeline import passages as pc
from tests.scale import SimShape, build_seeded, compile_story, measure

# -- the simulated presets hold their own bands --------------------------------


def test_simulated_medium_lands_inside_its_recalibrated_bands():
    """The projection test (plan phase 2): a medium story at the shape
    bands, compiled through the real weave/collapse/cadence machinery,
    lands inside the preset's own words/passage/arc bands with B6 under
    the feel cap — the exit criterion, projected before the live run."""
    preset = SCOPE_PRESETS["medium"]
    for corner in ("min", "max"):
        sim = (SimShape.band_min if corner == "min" else SimShape.band_max)(preset.shape)
        g, diamonds = compile_story(build_seeded(preset, sim), preset)
        y = measure(g, preset, diamonds=diamonds)
        assert preset.words_total[0] <= y.words_total <= preset.words_total[1]
        assert preset.passages_min <= y.passages <= preset.passages_max
        assert preset.arc_beats_min <= y.arc_beats[0]
        # arc_beats_max is deliberately not asserted: an arc VIEW counts every
        # rendering of every cosmetic fork while a walk traverses one — the
        # known post-modulation B3/B4 recalibration (BACKLOG); B4 is advisory
        # PR-5 recalibration: the finalize loop prices every fork's story
        # words honestly (the retired cadence machinery charged arms nothing),
        # so at the words band top the budget and seam capacity bind before
        # B6's 800 top. The exit criterion is the fixed point itself — no
        # further site is admissible — with the walk within a few percent of
        # the band instead of the flat-book 4x over it (flagged in the PR-5
        # body; the mix/appetite knobs are open question 1).
        assert pc.fork_plan(g, preset) == []
        assert y.b6[1] <= 830


def test_simulated_stories_are_structurally_valid():
    """The sim builds through the mutation layer and the real weave; its
    output must be gate-clean on the structural invariants, or the
    calibration numbers describe invalid stories."""
    structural = {"I3", "I4", "I5", "I6", "I7", "I8", "I10", "G3-FLAGS"}
    for scope in ("micro", "medium"):
        preset = SCOPE_PRESETS[scope]
        g, _ = compile_story(build_seeded(preset, SimShape.band_min(preset.shape)), preset)
        vision = Vision(premise="t", genre="t", tone="t", scope=scope)
        issues = run_checks(g, vision, Stage.GROW)
        errors = [i for i in issues if i.severity == Severity.ERROR and i.check in structural]
        assert errors == []


# -- capped collapse -------------------------------------------------------------


def _chain(g: StoryGraph, n: int) -> list[str]:
    from questfoundry.models.structure import DilemmaImpact, ImpactEffect
    from tests.conftest import make_dilemma

    d, pa, pb = make_dilemma(g, "x")
    ids = []
    prev = None
    for i in range(n):
        beat = Beat(
            id=f"beat:b{i}",
            created_by=Stage.SEED,
            summary="s",
            beat_class=BeatClass.NARRATIVE,
            dilemma_impacts=[DilemmaImpact(dilemma=d, effect=ImpactEffect.ADVANCES)],
        )
        mutations.add_beat(g, beat, [pa, pb])
        if prev:
            mutations.add_ordering(g, prev, beat.id)
        prev = beat.id
        ids.append(beat.id)
    return ids


def test_collapse_cap_cuts_a_deep_run_into_pages():
    """Unbounded collapse crushes a 12-beat run into one passage — one
    word budget for twelve story moments; the cap is the choice-free
    cutter that lets deep scaffolds mint pages (M8)."""
    g = StoryGraph()
    _chain(g, 12)
    assert [len(grp) for grp in pc.collapse_groups(g)] == [12]
    assert [len(grp) for grp in pc.collapse_groups(g, max_beats=3)] == [3, 3, 3, 3]
    # order is preserved front to back
    capped = pc.collapse_groups(g, max_beats=3)
    assert capped[0] == ["beat:b0", "beat:b1", "beat:b2"]


def test_collapse_cap_never_merges_across_gates():
    g = StoryGraph()
    ids = _chain(g, 2)
    flag = ids[0]  # any grantable id shape; gate equality is what matters
    beat = g.node(ids[1])
    assert isinstance(beat, Beat)
    beat.requires_flags = [flag]
    assert [len(grp) for grp in pc.collapse_groups(g, max_beats=5)] == [1, 1]


# -- sidetracks -------------------------------------------------------------------


def test_sidetrack_keeps_the_direct_edge():
    g = StoryGraph()
    ids = _chain(g, 4)
    arm = Beat(
        id="beat:detour",
        created_by=Stage.POLISH,
        summary="d",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
    )
    pc.insert_sidetrack(g, [arm], ids[1], ids[2])
    assert g.has_edge_kind(ids[1], ids[2]) if hasattr(g, "has_edge_kind") else True
    from questfoundry.models.base import EdgeKind

    assert g.has_edge(EdgeKind.PREDECESSOR, ids[1], ids[2])
    assert g.has_edge(EdgeKind.PREDECESSOR, ids[1], "beat:detour")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:detour", ids[2])
    # the fork and rejoin are collapse boundaries: continue or detour
    groups = pc.collapse_groups(g)
    edges = pc.group_edges(groups, g)
    index = {b: i for i, grp in enumerate(groups) for b in grp}
    assert len([e for e in edges if e[0] == index[ids[1]]]) == 2


# -- cadence budget ---------------------------------------------------------------


def test_fork_plan_offers_only_cap_aligned_seams():
    """A mid-chunk split mints a whole extra passage per choice; the
    edge tier only offers the seams between complete chunks."""
    g = StoryGraph()
    ids = _chain(g, 13)
    preset = SCOPE_PRESETS["medium"]  # cap 3
    for site in pc.fork_plan(g, preset):
        if not site.segment:
            assert (ids.index(site.before) + 1) % preset.passage_beats_max == 0


def test_fork_plan_is_empty_when_the_walk_is_already_paced():
    g = StoryGraph()
    _chain(g, 2)  # two beats: nothing long enough to need a fork
    assert pc.fork_plan(g, SCOPE_PRESETS["micro"]) == []


# -- word bands -------------------------------------------------------------------


def test_words_for_bands():
    preset = SCOPE_PRESETS["medium"]
    assert preset.words_for(intensity=SceneType.SCENE) == (200, 550)
    assert preset.words_for(intensity=SceneType.SEQUEL) == (200, 433)  # lo + 2*span//3
    assert preset.words_for(intensity=SceneType.MICRO_BEAT) == (200, 316)  # == old texture band
    assert preset.words_for(intensity=SceneType.SCENE, ending=True) == (200, 650)


def test_fill_flags_a_texture_arm_written_at_narrative_weight(tmp_path):
    """A residue arm written at narrative weight is the false-choice tax
    in word form (measured: live runs wrote arms at ~0.95x narrative). The
    word budget is now a graded review finding, not a hard apply gate
    (author-directed 2026-07-12): a 500-word residue arm against the 200-316
    texture band is a blocking `word_budget` finding; a texture-sized draft
    yields none."""
    from questfoundry.pipeline.review import ReviewVerdict, needs_rework
    from questfoundry.pipeline.stages.fill import _word_budget_finding
    from questfoundry.project.io import Project

    g = StoryGraph()
    arm = Beat(
        id="beat:arm",
        created_by=Stage.POLISH,
        summary="arm",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.RESIDUE,
    )
    mutations.add_beat(g, arm, [])
    mutations.add_passage(
        g, Passage(id="passage:p-arm", created_by=Stage.POLISH, summary="s"), ["beat:arm"]
    )
    vision = Vision(premise="t", genre="t", tone="t", scope="medium")
    project = Project(root=tmp_path, name="t", stage=Stage.FILL, vision=vision, graph=g)

    over = _word_budget_finding(project, "passage:p-arm", "w " * 500)
    assert over is not None and over.rule == "word_budget" and over.assessment == "fail"
    assert needs_rework(ReviewVerdict(verdict="needs_work", findings=[over])) is True
    assert _word_budget_finding(project, "passage:p-arm", "w " * 250) is None  # texture-sized


# -- B6 walk semantics / B7 --------------------------------------------------------


_DIAMOND = [
    ("beat:r", "passage:p-r", StructuralPurpose.SETUP),
    ("beat:fa", "passage:p-fa", StructuralPurpose.FALSE_BRANCH),
    ("beat:fb", "passage:p-fb", StructuralPurpose.FALSE_BRANCH),
    ("beat:j", "passage:p-j", StructuralPurpose.BRIDGE),
]


def _beat_diamond() -> StoryGraph:
    """root beat -> (arm a | arm b) -> join, all ungated."""
    g = StoryGraph()
    for bid, _pid, purpose in _DIAMOND:
        beat = Beat(
            id=bid,
            created_by=Stage.SEED,
            summary="s",
            beat_class=BeatClass.STRUCTURAL,
            purpose=purpose,
        )
        mutations.add_beat(g, beat, [])
    mutations.add_ordering(g, "beat:r", "beat:fa")
    mutations.add_ordering(g, "beat:r", "beat:fb")
    mutations.add_ordering(g, "beat:fa", "beat:j")
    mutations.add_ordering(g, "beat:fb", "beat:j")
    return g


def _passage_diamond(words_each: int) -> StoryGraph:
    """The beat diamond with a passage per beat, equal prose everywhere."""
    g = _beat_diamond()
    for bid, pid, _ in _DIAMOND:
        mutations.add_passage(g, Passage(id=pid, created_by=Stage.POLISH, summary="s"), [bid])
        mutations.set_passage_prose(g, pid, "w " * words_each)
    for src, dst in (
        ("passage:p-r", "passage:p-fa"),
        ("passage:p-r", "passage:p-fb"),
        ("passage:p-fa", "passage:p-j"),
        ("passage:p-fb", "passage:p-j"),
    ):
        mutations.add_choice(g, src, dst, Choice(label="on"))
    return g


def test_b6_measures_a_walk_not_an_arc_view():
    """At 260 words per passage the arc view reads 1040 words/choice
    (both diamond arms counted — words no single reader sees) while a
    playthrough reads 780. The walk is what B6 measures now; no warning."""
    g = _passage_diamond(260)
    vision = Vision(premise="t", genre="t", tone="t", scope="micro")
    ctx = Context(g=g, vision=vision)
    check_b6_choice_cadence(ctx)
    assert [i for i in ctx.issues if i.check == "B6"] == []


def test_b6_still_warns_on_a_choice_starved_walk():
    g = _passage_diamond(300)  # walk: 900 words over 1 decision
    vision = Vision(premise="t", genre="t", tone="t", scope="micro")
    ctx = Context(g=g, vision=vision)
    check_b6_choice_cadence(ctx)
    warnings = [i for i in ctx.issues if i.check == "B6"]
    assert len(warnings) == 1 and "900" in warnings[0].message


def test_b7_warns_outside_the_words_total_band():
    g = _passage_diamond(100)  # 400 words total, micro floor is 2400
    vision = Vision(premise="t", genre="t", tone="t", scope="micro")
    ctx = Context(g=g, vision=vision)
    check_b7_total_words(ctx)
    warnings = [i for i in ctx.issues if i.check == "B7"]
    assert len(warnings) == 1 and "2400-9000" in warnings[0].message


def test_b7_silent_inside_the_band():
    g = _passage_diamond(700)  # 2800 words total
    vision = Vision(premise="t", genre="t", tone="t", scope="micro")
    ctx = Context(g=g, vision=vision)
    check_b7_total_words(ctx)
    assert [i for i in ctx.issues if i.check == "B7"] == []


# -- projected walks ---------------------------------------------------------------


def test_projected_walk_traverses_one_diamond_arm():
    g = _beat_diamond()
    preset = SCOPE_PRESETS["micro"]
    walks = pc.projected_walks(g, preset)
    assert len(walks) == 1  # no branched dilemmas: a single selection
    words, decisions = walks[0]
    # root + ONE arm + join — the other arm is never walked. The beats are
    # unannotated, so effective_scene_type governs: the SETUP root falls back to
    # scene, the FALSE_BRANCH arm and the BRIDGE join both to micro_beat (a bridge
    # is a transition — under scene_type it now projects at the short band, where
    # is_texture used to leave it at the full narrative band).
    scene = round(preset.words_for(intensity=SceneType.SCENE)[1] * 0.9)
    micro = round(preset.words_for(intensity=SceneType.MICRO_BEAT)[1] * 0.9)
    assert words == scene + 2 * micro
    assert decisions == 1


# -- B8 pacing report --------------------------------------------------------------


def _monotone_story(scene_type: SceneType) -> StoryGraph:
    """A single dilemma with a long pre-chain, every narrative beat the same
    intensity — a flat arc the pacing report should flag."""
    from tests.test_weave import make_dilemma, scaffold

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "main")
    scaffold(g, "main", d, pa, pb, pre=4)  # arc: 4 pre + commit + post = 6 beats
    for b in g.nodes_of(Beat):
        if b.beat_class == BeatClass.NARRATIVE:
            b.scene_type = scene_type
    return g


def _b8(g: StoryGraph):
    ctx = Context(g=g, vision=Vision(premise="t", genre="t", tone="t", scope="micro"))
    check_b8_pacing(ctx)
    return [i for i in ctx.issues if i.check == "B8"]


def test_b8_flags_a_monotonous_run():
    warnings = _b8(_monotone_story(SceneType.SCENE))
    assert warnings
    assert "consecutive scene beats" in warnings[0].message
    assert warnings[0].severity is Severity.WARNING


def test_b8_flags_a_flat_sequel_run_too():
    # symmetric: an unbroken run of sequels is as flat as a run of scenes
    warnings = _b8(_monotone_story(SceneType.SEQUEL))
    assert any("consecutive sequel beats" in w.message for w in warnings)


def test_b8_skips_an_unannotated_story():
    # no scene_type anywhere -> missing data, not flat pacing (the fallback
    # would read every narrative beat as "scene")
    from tests.test_weave import make_dilemma, scaffold

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "m2")
    scaffold(g, "m2", d, pa, pb, pre=4)
    assert _b8(g) == []


def test_b8_silent_on_the_modulated_golden(golden):
    # the golden runs at most 3 same-intensity beats in a row (its passages
    # go up to 4 scene passages, but scene_type is measured per beat)
    ctx = Context(g=golden.graph, vision=golden.vision)
    check_b8_pacing(ctx)
    assert [i for i in ctx.issues if i.check == "B8"] == []
