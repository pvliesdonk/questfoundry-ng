"""Tensored texture worlds (docs/plans/structural-depth.md W3): the
run-scale parallel-world splice, its mirror-parity invariant (I15), site
detection, the sizing plan, and the mirrored cadence interplay."""

import pytest

from questfoundry.graph import mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import SCOPE_PRESETS
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    NarrationScope,
    SceneType,
    StructuralPurpose,
)
from questfoundry.pipeline import passages as pc


def i15_errors(g, vision):
    return [
        i
        for i in run_checks(g, vision, Stage.POLISH)
        if i.check == "I15" and i.severity == Severity.ERROR
    ]


def setup_beat(slug: str, **kwargs) -> Beat:
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.SEED,
        summary=slug,
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.SETUP,
        **kwargs,
    )


def arm_beat(slug: str, **kwargs) -> Beat:
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.POLISH,
        summary=slug,
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.TEXTURE_WORLD,
        **kwargs,
    )


def chain(g: StoryGraph, slugs: list[str], **beat_kwargs) -> list[str]:
    ids = []
    for slug in slugs:
        beat = setup_beat(slug, **beat_kwargs)
        mutations.add_beat(g, beat, [])
        if ids:
            mutations.add_ordering(g, ids[-1], beat.id)
        ids.append(beat.id)
    return ids


# -- the splice ----------------------------------------------------------------


def test_splice_wires_and_mirrors():
    g = StoryGraph()
    ids = chain(g, ["p", "t1", "t2", "t3", "s"])
    g.node("beat:t2").scene_type = SceneType.SEQUEL
    g.node("beat:t2").viewpoint = "character:x"
    arm = [arm_beat(f"a{i}") for i in range(3)]
    pc.insert_texture_world(g, arm, ids[1:4])

    # trunk untouched; arm parallel: p -> a0 .. a2 -> s
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:t1", "beat:t2")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:p", "beat:a0")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:a2", "beat:s")
    a0, a1, a2 = (g.node(f"beat:a{i}") for i in range(3))
    assert (a0.mirrors, a1.mirrors, a2.mirrors) == ("beat:t1", "beat:t2", "beat:t3")
    # effective annotations copied: t1 unannotated setup -> scene fallback,
    # t2 annotated sequel + head
    assert a0.scene_type == SceneType.SCENE
    assert a1.scene_type == SceneType.SEQUEL
    assert a1.viewpoint == "character:x"
    assert a1.narration_scope == NarrationScope.LIMITED


def test_splice_rejects_bad_shapes():
    g = StoryGraph()
    ids = chain(g, ["p", "t1", "t2", "t3", "s"])
    with pytest.raises(mutations.MutationError, match="beat-for-beat"):
        pc.insert_texture_world(g, [arm_beat("a0")], ids[1:3])
    with pytest.raises(mutations.MutationError, match="root or ending"):
        pc.insert_texture_world(g, [arm_beat("a0")], ids[:1])  # root-headed
    with pytest.raises(mutations.MutationError, match="not adjacent"):
        pc.insert_texture_world(
            g, [arm_beat("a0"), arm_beat("a1")], [ids[1], ids[3]]
        )
    with pytest.raises(mutations.MutationError, match="purpose texture_world"):
        pc.insert_texture_world(g, [setup_beat("a0")], ids[1:2])


def test_splice_rejects_consequence_bearing_stretch():
    g = StoryGraph()
    ids = chain(g, ["p", "t1", "s"])
    gated = setup_beat("gated", requires_flags=["flag:x"])
    # construct in isolation; only the twin check matters
    g2 = StoryGraph()
    chain(g2, ["p"])
    mutations.add_beat(g2, gated, [])
    mutations.add_ordering(g2, "beat:p", "beat:gated")
    mutations.add_beat(g2, setup_beat("s"), [])
    mutations.add_ordering(g2, "beat:gated", "beat:s")
    with pytest.raises(mutations.MutationError, match="consequence-free"):
        pc.insert_texture_world(g2, [arm_beat("a0")], ["beat:gated"])
    del ids


def test_model_rejects_mirrors_on_non_texture_beat():
    with pytest.raises(ValueError, match="mirrors"):
        setup_beat("x", mirrors="beat:y")


# -- I15 -----------------------------------------------------------------------


def test_i15_clean_after_engine_splice(vision):
    g = StoryGraph()
    ids = chain(g, ["p", "t1", "t2", "t3", "s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(3)], ids[1:4])
    assert i15_errors(g, vision) == []


def test_i15_missing_and_dangling_mirrors(vision):
    g = StoryGraph()
    chain(g, ["p", "t1", "s"])
    mutations.add_beat(g, arm_beat("orphan"), [])
    mutations.add_ordering(g, "beat:p", "beat:orphan")
    mutations.add_ordering(g, "beat:orphan", "beat:s")
    issues = i15_errors(g, vision)
    assert any("names no mirrored trunk beat" in i.message for i in issues)
    g2 = StoryGraph()
    chain(g2, ["p", "t1", "s"])
    mutations.add_beat(g2, arm_beat("dangler", mirrors="beat:ghost"), [])
    mutations.add_ordering(g2, "beat:p", "beat:dangler")
    mutations.add_ordering(g2, "beat:dangler", "beat:s")
    assert any("is not a beat" in i.message for i in i15_errors(g2, vision))


def test_i15_annotation_parity(vision):
    g = StoryGraph()
    ids = chain(g, ["p", "t1", "s"])
    # arm beat claims a scene band its twin's effective annotation denies
    bad = arm_beat("a0", mirrors="beat:t1", scene_type=SceneType.MICRO_BEAT)
    mutations.add_beat(g, bad, [])
    mutations.add_ordering(g, "beat:p", "beat:a0")
    mutations.add_ordering(g, "beat:a0", "beat:s")
    issues = i15_errors(g, vision)
    assert any("effective" in i.message and "annotations" in i.message for i in issues)
    del ids


def test_i15_projection_catches_convergence_drift(vision):
    g = StoryGraph()
    ids = chain(g, ["p", "t1", "t2", "s", "later"])
    pc.insert_texture_world(g, [arm_beat("a0"), arm_beat("a1")], ids[1:3])
    assert i15_errors(g, vision) == []
    # the arm sneaks past the rejoin: a1 -> later has no trunk counterpart
    mutations.add_ordering(g, "beat:a1", "beat:later")
    issues = i15_errors(g, vision)
    assert any("projects onto" in i.message for i in issues)


# -- sites ---------------------------------------------------------------------


def _micro_vision_preset():
    return SCOPE_PRESETS["micro"]  # cap = 5


def test_texture_sites_excise_around_disqualified_beats():
    g = StoryGraph()
    preset = _micro_vision_preset()
    # 12-beat run behind a root: beats 0..11 after head "r"
    ids = chain(g, ["r"] + [f"b{i}" for i in range(12)])
    # a gated beat mid-run disqualifies its window position
    g.node("beat:b7").requires_flags = ["flag:x"]
    mutations.add_beat(g, setup_beat("tail"), [])
    mutations.add_ordering(g, ids[-1], "beat:tail")
    sites = pc.texture_sites(g, preset)
    # run = [r, b0..b11, tail?] -- tail merges into the run; windows split at b7.
    # window [r..b6] snaps to [cap..]: starts at offset 5, ends at offset 4? --
    # assert instead the invariant-level facts: every site is >= cap, aligned,
    # qualifying, and none contains the gated beat
    for site in sites:
        assert len(site) >= preset.passage_beats_max
        assert "beat:b7" not in site
        assert all(not g.node(b).requires_flags for b in site)


def test_texture_sites_skip_short_and_rootless():
    g = StoryGraph()
    preset = _micro_vision_preset()
    chain(g, [f"c{i}" for i in range(4)])  # rootless-headed short chain
    assert pc.texture_sites(g, preset) == []


# -- plan + cadence interplay ----------------------------------------------------


def test_cadence_diamond_mirrored_into_arm(vision):
    g = StoryGraph()
    preset = _micro_vision_preset()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    stretch = ids[1:11]
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], stretch)
    fb = [
        Beat(
            id=f"beat:fb-{side}",
            created_by=Stage.POLISH,
            summary="flavor",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.FALSE_BRANCH,
        )
        for side in ("a", "b")
    ]
    pc.insert_cadence_diamond(g, [fb[0]], [fb[1]], "beat:t4", "beat:t5")
    # trunk got the diamond; the arm got mirrored texture twins of it
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:t4", "beat:t5")
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:a4", "beat:a5")
    twins = [b for b in g.nodes_of(Beat) if b.mirrors in ("beat:fb-a", "beat:fb-b")]
    assert len(twins) == 2
    assert all(b.purpose == StructuralPurpose.TEXTURE_WORLD for b in twins)
    assert i15_errors(g, vision) == []
    del preset


def test_cadence_plan_skips_arm_runs():
    g = StoryGraph()
    preset = _micro_vision_preset()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    plan = pc.cadence_plan(g, preset)
    runs = pc.collapse_groups(g)
    offered = {b for i, edges in plan.items() for e in edges for b in e}
    del runs
    assert not any(b.startswith("beat:a") for b in offered)


def test_texture_plan_caps_and_adds_free_decisions():
    preset = SCOPE_PRESETS["short"]
    from questfoundry.pipeline import weave
    from tests.scale import SimShape, _derive_flags, add_residue_arms, build_seeded

    g = build_seeded(preset, SimShape.band_max(preset.shape))
    planned = weave.plan(g)
    weave.realize(g, planned, weave.candidates(planned)[0])
    _derive_flags(g)
    add_residue_arms(g)
    before = pc.projected_walks(g, preset)
    plan = pc.texture_plan(g, preset)
    assert 0 < len(plan) <= pc.TEXTURE_WORLDS_MAX
    for k, run in enumerate(plan):
        pc.insert_texture_world(
            g, [arm_beat(f"tex-{k}-{i}") for i in range(len(run))], run
        )
    after = pc.projected_walks(g, preset)
    words_before = sum(w for w, _ in before)
    words_after = sum(w for w, _ in after)
    decisions_before = sum(d for _, d in before)
    decisions_after = sum(d for _, d in after)
    assert decisions_after > decisions_before
    # near-zero traversed-word cost: the walk reads one world
    assert words_after <= words_before * 1.05


def test_sim_with_texture_keeps_b6_in_band():
    from tests.scale import SimShape, build_seeded, compile_story, measure

    preset = SCOPE_PRESETS["medium"]
    g = build_seeded(preset, SimShape.band_max(preset.shape))
    compiled, diamonds = compile_story(g, preset, texture_worlds=True)
    y = measure(compiled, preset, diamonds=diamonds)
    lo, hi = 250, 800
    assert lo <= y.b6[0] and y.b6[1] <= hi
