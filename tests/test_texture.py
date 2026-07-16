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
    pc.insert_cadence_diamond(g, [[fb[0]], [fb[1]]], "beat:t4", "beat:t5")
    # trunk got the diamond; the arm got mirrored texture twins of it
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:t4", "beat:t5")
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:a4", "beat:a5")
    twins = [b for b in g.nodes_of(Beat) if b.mirrors in ("beat:fb-a", "beat:fb-b")]
    assert len(twins) == 2
    assert all(b.purpose == StructuralPurpose.TEXTURE_WORLD for b in twins)
    assert i15_errors(g, vision) == []
    del preset


def test_cadence_sidetrack_mirrored_into_arm(vision):
    g = StoryGraph()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    detour = Beat(
        id="beat:st-detour",
        created_by=Stage.POLISH,
        summary="detour",
        beat_class=BeatClass.STRUCTURAL,
        purpose=StructuralPurpose.FALSE_BRANCH,
    )
    pc.insert_cadence_sidetrack(g, [detour], "beat:t4", "beat:t5")
    # both direct edges survive (declining the detour is the choice)...
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:t4", "beat:t5")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:a4", "beat:a5")
    # ...and the detour exists in both worlds, the arm's as a mirrored twin
    twins = [b for b in g.nodes_of(Beat) if b.mirrors == "beat:st-detour"]
    assert len(twins) == 1
    assert twins[0].purpose == StructuralPurpose.TEXTURE_WORLD
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:a4", twins[0].id)
    assert g.has_edge(EdgeKind.PREDECESSOR, twins[0].id, "beat:a5")
    assert i15_errors(g, vision) == []


def test_cadence_plan_skips_arm_runs():
    g = StoryGraph()
    preset = _micro_vision_preset()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    plan = pc.cadence_plan(g, preset)
    offered = {b for sites in plan.values() for before, after, _ in sites for b in (before, after)}
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


def test_texture_plan_respects_the_words_budget():
    g = StoryGraph()
    preset = _micro_vision_preset()
    chain(g, ["r"] + [f"b{i}" for i in range(20)])
    # uncapped: the band top admits the fork; a floor words_target does not
    assert pc.texture_plan(g, preset) != []
    assert pc.texture_plan(g, preset, words_target=2400) == []


# -- finalize integration (PR-4) --------------------------------------------------


def _finalize_project(tmp_path, vision):
    from questfoundry.project.io import Project

    g = StoryGraph()
    chain(g, ["r"] + [f"b{i}" for i in range(20)])
    return Project(
        root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g
    )


def test_finalize_texture_budget_is_mandatory(vision, tmp_path):
    from questfoundry.pipeline.stages.polish import (
        FinalizeProposal,
        _finalize_apply,
        _texture_and_cadence,
    )
    from questfoundry.pipeline.types import ApplyError

    project = _finalize_project(tmp_path, vision)
    sites, _, _ = _texture_and_cadence(project)
    assert sites  # the chain offers a stretch
    before = {b.id for b in project.graph.nodes_of(Beat)}
    with pytest.raises(ApplyError, match="texture-world budget is mandatory"):
        _finalize_apply(FinalizeProposal(), project)
    assert {b.id for b in project.graph.nodes_of(Beat)} == before  # nothing spliced


def test_finalize_splices_texture_world_with_premise(vision, tmp_path):
    from questfoundry.pipeline.stages.polish import (
        ArmSpec,
        FalseBranchSpec,
        FinalizeProposal,
        TextureBeatSpec,
        TextureWorldSpec,
        _finalize_apply,
        _texture_and_cadence,
    )

    project = _finalize_project(tmp_path, vision)
    g = project.graph
    sites, cadence, _ = _texture_and_cadence(project)
    (site,) = sites
    proposal = FinalizeProposal(
        texture_worlds=[
            TextureWorldSpec(
                site=0,
                premise="the crossing goes over the mountain pass",
                trunk_premise="the crossing goes along the coast road",
                beats=[
                    TextureBeatSpec(id=f"beat:mountain-{i}", summary=f"m{i}")
                    for i in range(len(site))
                ],
            )
        ],
        false_branches=[
            FalseBranchSpec(
                before=before,
                after=after,
                arms=[ArmSpec(id=f"beat:fb-{i}-{j}", summary="s") for j in range(n)],
            )
            for i, (before, after, n) in enumerate(
                (b, a, n)
                for run in cadence
                for (b, a), n in zip(run["edges"], run["arm_counts"], strict=True)
            )
        ],
    )
    lines = _finalize_apply(proposal, project)
    assert any("texture world" in line for line in lines)
    arm0 = g.node("beat:mountain-0")
    assert arm0.purpose == StructuralPurpose.TEXTURE_WORLD
    assert arm0.mirrors == site[0]
    assert arm0.texture_premise == "the crossing goes over the mountain pass"
    # rendering 0 (PR-2 §2): the trunk segment's own (frozen) beats carry the
    # trunk premise — renderings are peers, both worlds named
    assert all(
        g.node(tb).texture_premise == "the crossing goes along the coast road" for tb in site
    )
    # both premises reach their readers on the exact expressions those readers
    # use: FILL's per-passage gathering (fill.py `{b.texture_premise for b in
    # beats}`) yields each rendering's world, and the entry-label context reads
    # the destination group's head-beat premise (_labels_context).
    def fill_premise(beats):
        return sorted({g.node(b).texture_premise for b in beats if g.node(b).texture_premise})

    arm_ids = [f"beat:mountain-{i}" for i in range(len(site))]
    assert fill_premise(site) == ["the crossing goes along the coast road"]  # FILL: trunk world
    assert fill_premise(arm_ids) == ["the crossing goes over the mountain pass"]  # FILL: arm world
    # entry labels: _labels_context itself surfaces each destination's head-beat
    # premise (the "premise" key polish_labels.j2 consumes), naming both worlds
    from questfoundry.pipeline.stages.polish import _groups, _labels_context

    groups = _groups(project)
    entry_premises = {
        d["premise"]
        for a in sorted({x for x, _ in pc.group_edges(groups, g)})
        for d in _labels_context(a)(project)["dests"]
        if d["premise"]
    }
    assert "the crossing goes along the coast road" in entry_premises  # rendering 0 (trunk)
    assert "the crossing goes over the mountain pass" in entry_premises  # the fresh arm
    # cadence diamonds inside the mirrored stretch got mirrored twins
    # carrying the arm's premise (both worlds keep the same topology)
    twins = [b for b in g.nodes_of(Beat) if b.mirrors and b.mirrors.startswith("beat:fb-")]
    assert twins
    assert all(b.texture_premise == arm0.texture_premise for b in twins)
    assert i15_errors(g, vision) == []


def test_finalize_rejects_wrong_arm_length_and_empty_premise(vision, tmp_path):
    from questfoundry.pipeline.stages.polish import (
        FinalizeProposal,
        TextureBeatSpec,
        TextureWorldSpec,
        _finalize_apply,
        _texture_and_cadence,
    )
    from questfoundry.pipeline.types import ApplyError

    project = _finalize_project(tmp_path, vision)
    sites, _, _ = _texture_and_cadence(project)
    (site,) = sites
    short = FinalizeProposal(
        texture_worlds=[
            TextureWorldSpec(
                site=0,
                premise="p",
                trunk_premise="q",
                beats=[TextureBeatSpec(id="beat:m0", summary="m")],
            )
        ]
    )
    with pytest.raises(ApplyError, match="beat-for-beat"):
        _finalize_apply(short, project)
    blank = FinalizeProposal(
        texture_worlds=[
            TextureWorldSpec(
                site=0,
                premise="  ",
                trunk_premise="the trunk backdrop",
                beats=[
                    TextureBeatSpec(id=f"beat:m{i}", summary="m")
                    for i in range(len(site))
                ],
            )
        ]
    )
    with pytest.raises(ApplyError, match="empty premise"):
        _finalize_apply(blank, project)


def test_sim_with_texture_keeps_b6_in_band():
    from tests.scale import SimShape, build_seeded, compile_story, measure

    preset = SCOPE_PRESETS["medium"]
    g = build_seeded(preset, SimShape.band_max(preset.shape))
    compiled, diamonds = compile_story(g, preset, texture_worlds=True)
    y = measure(compiled, preset, diamonds=diamonds)
    lo, hi = 250, 800
    assert lo <= y.b6[0] and y.b6[1] <= hi


def test_cosmetic_fork_primitive_reproduces_the_three_shapes():
    """The one splice (01 §6) behind the three shipped adapters: an edge-scale
    diamond (two fresh, no walk-on) removes the direct edge; an edge-scale
    sidetrack (walk-on + fresh) keeps it; a segment-scale texture (segment +
    fresh) keeps the trunk and mirrors it beat-for-beat."""
    from questfoundry.graph import queries
    from questfoundry.pipeline.passages import (
        EMPTY_RENDERING,
        SEGMENT_RENDERING,
        insert_cosmetic_fork,
    )

    g = StoryGraph()
    chain(g, ["t0", "t1", "t2", "t3", "t4", "t5"])
    # diamond on t0 -> t1: two fresh arms, direct edge gone
    insert_cosmetic_fork(
        g, [[setup_beat("da")], [setup_beat("db")]], before="beat:t0", after="beat:t1"
    )
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:t0", "beat:t1")
    assert set(queries.successors(g, "beat:t0")) == {"beat:da", "beat:db"}
    assert set(queries.predecessors(g, "beat:t1")) == {"beat:da", "beat:db"}
    # sidetrack on t1 -> t2: the walk-on edge stays, one fresh detour added
    insert_cosmetic_fork(
        g, [EMPTY_RENDERING, [setup_beat("sd")]], before="beat:t1", after="beat:t2"
    )
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:t1", "beat:t2")
    assert "beat:sd" in queries.successors(g, "beat:t1")
    # texture over [t3, t4]: the trunk stays, one fresh arm mirrors it
    insert_cosmetic_fork(
        g, [SEGMENT_RENDERING, [arm_beat("wa"), arm_beat("wb")]], segment=["beat:t3", "beat:t4"]
    )
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:t3", "beat:t4")  # trunk untouched
    assert (g.node("beat:wa").mirrors, g.node("beat:wb").mirrors) == ("beat:t3", "beat:t4")
    assert "beat:wa" in queries.successors(g, "beat:t2")  # arm forks from the boundary
    assert "beat:t5" in queries.successors(g, "beat:wb")  # and rejoins it


def test_cosmetic_fork_rejects_degenerate_rendering_sets():
    from questfoundry.pipeline.passages import (
        EMPTY_RENDERING,
        SEGMENT_RENDERING,
        insert_cosmetic_fork,
    )

    g = StoryGraph()
    chain(g, ["a", "b", "c", "d"])
    fresh = [setup_beat("x")]
    with pytest.raises(mutations.MutationError, match="at least two renderings"):
        insert_cosmetic_fork(g, [fresh], before="beat:a", after="beat:b")
    with pytest.raises(mutations.MutationError, match="at least one fresh"):
        insert_cosmetic_fork(g, [EMPTY_RENDERING, EMPTY_RENDERING], before="beat:a", after="beat:b")
    # scale/marker contract (hardened for PR-5's looser callers): at most one of
    # each marker, and the two scales are exclusive
    with pytest.raises(mutations.MutationError, match="at most one"):
        insert_cosmetic_fork(
            g, [EMPTY_RENDERING, EMPTY_RENDERING, fresh], before="beat:a", after="beat:b"
        )
    with pytest.raises(mutations.MutationError, match="SEGMENT_RENDERING needs a non-empty"):
        insert_cosmetic_fork(g, [SEGMENT_RENDERING, fresh], before="beat:a", after="beat:b")
    with pytest.raises(mutations.MutationError, match="EMPTY_RENDERING is edge-scale only"):
        insert_cosmetic_fork(
            g, [SEGMENT_RENDERING, EMPTY_RENDERING, [arm_beat("y")]], segment=["beat:b"]
        )
    with pytest.raises(mutations.MutationError, match="exactly one SEGMENT_RENDERING"):
        insert_cosmetic_fork(g, [[arm_beat("y")], [arm_beat("z")]], segment=["beat:b"])


def test_texture_premise_legal_on_any_beat_engine_set_on_frozen_trunk():
    """PR-2 §2: premise per rendering. The model guard no longer couples
    texture_premise to texture_world purpose (rendering 0's beats are GROW
    beats), and the freeze permits it as a presentation addition on a frozen
    trunk beat (a topological freeze — no beat moves)."""
    from questfoundry.graph.store import FreezeRecord

    # the model accepts a premise on a plain (non-texture) beat
    b = setup_beat("trunk", texture_premise="the road runs along the coast")
    assert b.purpose is not StructuralPurpose.TEXTURE_WORLD
    assert b.texture_premise == "the road runs along the coast"

    # and the mutation sets it on a FROZEN beat (scene_type/summary would reject)
    g = StoryGraph()
    mutations.add_beat(g, setup_beat("t0"), [])
    g.frozen = FreezeRecord(beats=["beat:t0"], forks={}, convergences={})
    with pytest.raises(mutations.MutationError, match="frozen"):
        mutations.set_beat_summary(g, "beat:t0", "reworded")  # content: rejected
    mutations.set_beat_texture_premise(g, "beat:t0", "the coast road")  # addition: allowed
    assert g.node("beat:t0").texture_premise == "the coast road"
    with pytest.raises(mutations.MutationError, match="empty"):
        mutations.set_beat_texture_premise(g, "beat:t0", "   ")


def test_cadence_plan_assigns_the_engine_shape_mix():
    """PR-3: shape is engine-assigned, not model-chosen (given the choice a
    weak tier placed 44/44 sidetracks). cadence_plan tags each site with an
    arm count cycled from the preset mix, front-loaded so even a few-site book
    gets a diamond — the diamond/sidetrack ratio holds book-wide."""
    g = StoryGraph()
    preset = _micro_vision_preset()  # cadence_arm_cycle default (2, 1, 1, 3, 1, 1)
    chain(g, ["r"] + [f"b{i}" for i in range(20)] + ["s"])
    plan = pc.cadence_plan(g, preset)
    counts = [n for sites in plan.values() for _, _, n in sites]
    assert counts and set(counts) <= {1, 2, 3}
    assert counts[0] >= 2  # the 44/44 fix: never all-sidetracks — a diamond leads
    assert counts == list(preset.cadence_arm_cycle)[: len(counts)]  # the cycle, in order


def test_cadence_diamond_three_arms_splices_and_mirrors(vision):
    """PR-3: a diamond may carry a third arm. insert_cadence_diamond takes k
    fresh arms, splices them all before->after (direct edge gone), and mirrors
    each into any texture arm paralleling the edge."""
    g = StoryGraph()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    arms = [
        [
            Beat(
                id=f"beat:fb-{j}",
                created_by=Stage.POLISH,
                summary="flavor",
                beat_class=BeatClass.STRUCTURAL,
                purpose=StructuralPurpose.FALSE_BRANCH,
            )
        ]
        for j in range(3)
    ]
    pc.insert_cadence_diamond(g, arms, "beat:t4", "beat:t5")
    from questfoundry.graph import queries

    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:t4", "beat:t5")  # spine removed
    assert set(queries.successors(g, "beat:t4")) == {"beat:fb-0", "beat:fb-1", "beat:fb-2"}
    # all three arms mirrored into the parallel texture arm (both worlds match)
    twins = [b for b in g.nodes_of(Beat) if b.mirrors in {"beat:fb-0", "beat:fb-1", "beat:fb-2"}]
    assert len(twins) == 3
    assert i15_errors(g, vision) == []
