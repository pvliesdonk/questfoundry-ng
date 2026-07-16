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


def test_fork_segments_excise_around_disqualified_beats():
    g = StoryGraph()
    preset = _micro_vision_preset()
    # 12-beat run behind a root: beats 0..11 after head "r"
    ids = chain(g, ["r"] + [f"b{i}" for i in range(12)])
    # a gated beat mid-run disqualifies its window position
    g.node("beat:b7").requires_flags = ["flag:x"]
    mutations.add_beat(g, setup_beat("tail"), [])
    mutations.add_ordering(g, ids[-1], "beat:tail")
    segments, _ = pc.fork_segments(g, preset)
    # every segment is qualifying, seam-aligned at its start, and excised
    # around the gated beat; scene-tier segments stay >= cap
    for seg in segments:
        assert "beat:b7" not in seg
        assert all(not g.node(b).requires_flags for b in seg)


def test_fork_segments_skip_short_and_rootless():
    g = StoryGraph()
    preset = _micro_vision_preset()
    chain(g, [f"c{i}" for i in range(4)])  # rootless-headed short chain
    assert pc.fork_segments(g, preset) == ([], [])


# -- plan + cadence interplay ----------------------------------------------------


def test_legacy_mirrored_cadence_structures_still_validate(vision):
    """The mirrored-cadence machinery is retired (cosmetic-forks ratified
    decision 1), but the checked-in exemplars carry its output: texture
    twins whose `mirrors` point at FALSE_BRANCH beats spliced inside a
    mirrored stretch, with the trunk edge removed. The restated I15 keeps
    those structures valid — a mirrored FALSE_BRANCH beat is not contracted
    and the twin edges project onto it."""
    g = StoryGraph()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    # the legacy shape, built by hand: a diamond on trunk t4->t5 (edge
    # removed), each fb arm twinned into the texture arm between a4->a5
    fb = []
    for side in ("a", "b"):
        beat = Beat(
            id=f"beat:fb-{side}",
            created_by=Stage.POLISH,
            summary="flavor",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.FALSE_BRANCH,
        )
        fb.append(beat)
    pc.insert_cosmetic_fork(g, [[fb[0]], [fb[1]]], before="beat:t4", after="beat:t5")
    mutations.remove_ordering(g, "beat:a4", "beat:a5")
    for side in ("a", "b"):
        twin = arm_beat(
            f"tw-{side}",
            mirrors=f"beat:fb-{side}",
            scene_type=SceneType.MICRO_BEAT,
            narration_scope=NarrationScope.LIMITED,
        )
        mutations.add_beat(g, twin, [])
        mutations.add_ordering(g, "beat:a4", twin.id)
        mutations.add_ordering(g, twin.id, "beat:a5")
    assert i15_errors(g, vision) == []


def _finalize_project(tmp_path, vision):
    from questfoundry.project.io import Project

    g = StoryGraph()
    chain(g, ["r"] + [f"b{i}" for i in range(20)])
    return Project(
        root=tmp_path, name="t", stage=Stage.POLISH, vision=vision, graph=g
    )


def test_fork_schema_pins_arm_count_and_beat_count(vision, tmp_path):
    """The budgets stopped being model-fillable (the engine plans and
    assigns); what remains model-facing is pinned at the schema: exactly the
    assigned rendering count, exact beat counts for a segment site, and no
    `gated` field at all when the site offers no keywords."""
    from questfoundry.pipeline.stages.polish import _fork_schema

    project = _finalize_project(tmp_path, vision)
    (site,) = [s for s in pc.fork_plan(project.graph, vision.preset) if s.segment]
    schema = _fork_schema(site)(project)
    props = schema.model_json_schema()
    assert props["properties"]["renderings"]["minItems"] == site.arms
    assert props["properties"]["renderings"]["maxItems"] == site.arms
    assert "gated" not in props["properties"]
    beats = props["$defs"]["RenderingSpec"]["properties"]["beats"]
    assert beats["minItems"] == len(site.segment)
    assert beats["maxItems"] == len(site.segment)


def test_fork_apply_splices_segment_site_with_premises(vision, tmp_path):
    from questfoundry.pipeline.stages.polish import (
        ForkBeatSpec,
        ForkProposal,
        RenderingSpec,
        _fork_apply,
    )

    project = _finalize_project(tmp_path, vision)
    g = project.graph
    (site,) = [s for s in pc.fork_plan(g, vision.preset) if s.segment]
    segment = list(site.segment)
    proposal = ForkProposal(
        trunk_premise="the crossing goes along the coast road",
        renderings=[
            RenderingSpec(
                premise="the crossing goes over the mountain pass",
                beats=[
                    ForkBeatSpec(id=f"beat:mountain-{i}", summary=f"m{i}")
                    for i in range(len(segment))
                ],
            )
        ],
    )
    lines = _fork_apply(site)(proposal, project)
    assert any("two-worlds" in line for line in lines)
    arm0 = g.node("beat:mountain-0")
    assert arm0.purpose == StructuralPurpose.TEXTURE_WORLD
    assert arm0.mirrors == segment[0]
    assert arm0.texture_premise == "the crossing goes over the mountain pass"
    # rendering 0 (PR-2 §2): the trunk segment's own (frozen) beats carry the
    # trunk premise — renderings are peers, both worlds named
    assert all(
        g.node(tb).texture_premise == "the crossing goes along the coast road"
        for tb in segment
    )
    # minting (PR-5 §4): one keyword per non-empty rendering, granted on the
    # rendering heads — rendering 0's segment head included
    from questfoundry.graph import queries
    from questfoundry.models.structure import FlagSource, StateFlag

    minted = [f for f in g.nodes_of(StateFlag) if f.source == FlagSource.COSMETIC]
    assert len(minted) == 2
    grant_heads = {b for f in minted for b in queries.grant_beats(g, f.id)}
    assert grant_heads == {segment[0], "beat:mountain-0"}
    # descriptions carry the premises (what later consumption prompts read)
    assert {f.description for f in minted} == {
        "the crossing goes along the coast road",
        "the crossing goes over the mountain pass",
    }
    # both premises reach their readers on the exact expressions those readers
    # use: FILL's per-passage gathering and the entry-label context
    def fill_premise(beats):
        return sorted({g.node(b).texture_premise for b in beats if g.node(b).texture_premise})

    arm_ids = [f"beat:mountain-{i}" for i in range(len(segment))]
    assert fill_premise(segment) == ["the crossing goes along the coast road"]
    assert fill_premise(arm_ids) == ["the crossing goes over the mountain pass"]
    from questfoundry.pipeline.stages.polish import _groups, _labels_context

    groups = _groups(project)
    entry_premises = {
        d["premise"]
        for a in sorted({x for x, _ in pc.group_edges(groups, g)})
        for d in _labels_context(a)(project)["dests"]
        if d["premise"]
    }
    assert "the crossing goes along the coast road" in entry_premises
    assert "the crossing goes over the mountain pass" in entry_premises
    assert i15_errors(g, vision) == []


def test_fork_apply_rejects_wrong_arm_length_and_empty_premise(vision, tmp_path):
    from questfoundry.pipeline.stages.polish import (
        ForkBeatSpec,
        ForkProposal,
        RenderingSpec,
        _fork_apply,
    )
    from questfoundry.pipeline.types import ApplyError

    project = _finalize_project(tmp_path, vision)
    (site,) = [s for s in pc.fork_plan(project.graph, vision.preset) if s.segment]
    short = ForkProposal(
        trunk_premise="q",
        renderings=[
            RenderingSpec(premise="p", beats=[ForkBeatSpec(id="beat:m0", summary="m")])
        ],
    )
    with pytest.raises(ApplyError, match="beat-for-beat"):
        _fork_apply(site)(short, project)
    blank = ForkProposal(
        trunk_premise="the trunk backdrop",
        renderings=[
            RenderingSpec(
                premise="  ",
                beats=[
                    ForkBeatSpec(id=f"beat:m{i}", summary="m")
                    for i in range(len(site.segment))
                ],
            )
        ],
    )
    with pytest.raises(ApplyError, match="empty premise"):
        _fork_apply(site)(blank, project)
    no_trunk = ForkProposal(
        renderings=[
            RenderingSpec(
                premise="p",
                beats=[
                    ForkBeatSpec(id=f"beat:m{i}", summary="m")
                    for i in range(len(site.segment))
                ],
            )
        ],
    )
    with pytest.raises(ApplyError, match="trunk_premise"):
        _fork_apply(site)(no_trunk, project)


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


# -- PR-5: segment tiers, recursion, scene-fork counting ---------------------------


def test_fork_segments_tiers_and_seam_edges():
    """fork_segments generalizes texture_sites (cosmetic-forks §1): the same
    aligned-window walk, but a run-tail span shorter than the cap — seam-
    aligned start, ending at a run end that has an exit — is admitted as a
    *small two-worlds* segment instead of discarded, and the cap-aligned
    interior seam edges of long runs ride along as the edge-scale tier."""
    preset = SCOPE_PRESETS["short"]  # cap = 3
    g = StoryGraph()
    # run [r, p, c0, c1, c2] (len 5) feeding a convergence with a second
    # parent: the span [3..4] is a 2-beat aligned tail with an exit
    ids = chain(g, ["r", "p", "c0", "c1", "c2"])
    mutations.add_beat(g, setup_beat("q"), [])
    mutations.add_beat(g, setup_beat("cv"), [])
    mutations.add_ordering(g, ids[-1], "beat:cv")
    mutations.add_ordering(g, "beat:q", "beat:cv")
    segments, edge_runs = pc.fork_segments(g, preset)
    edges = [e for run in edge_runs for e in run]
    assert [s for s in segments if len(s) < 3] == [["beat:c1", "beat:c2"]]
    assert ("beat:c1", "beat:c2") not in edges  # smalls are segments, not seams
    assert ("beat:c0", "beat:c1") in edges  # (e+1) % cap == 0 seam of the 5-run


def test_fork_segments_include_arm_interiors_and_exclude_decoration():
    """Recursion (cosmetic-forks §3): a texture arm's interior seam edges
    and sub-stretches qualify like any run — a segment inside a rendering is
    just a segment the next round may fork. FALSE_BRANCH decoration never
    qualifies as segment content (it is never re-rendered)."""
    preset = SCOPE_PRESETS["short"]  # cap = 3
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
    pc.insert_sidetrack(g, [detour], "beat:t4", "beat:t5")
    segments, edge_runs = pc.fork_segments(g, preset)
    edges = [e for run in edge_runs for e in run]
    assert any(b.startswith("beat:a") for b, _ in edges)  # arm seams offered
    assert all("beat:st-detour" not in seg for seg in segments)


def test_scene_fork_count_counts_only_cap_or_longer_chains():
    preset = SCOPE_PRESETS["short"]  # cap = 3
    g = StoryGraph()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    assert pc.scene_fork_count(g, preset.passage_beats_max) == 0
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    assert pc.scene_fork_count(g, preset.passage_beats_max) == 1
    # a small two-worlds fork (2 mirror beats) does not count as scene-scale
    mutations.add_beat(g, setup_beat("u0"), [])
    mutations.add_beat(g, setup_beat("u1"), [])
    mutations.add_ordering(g, "beat:s", "beat:u0")
    mutations.add_ordering(g, "beat:u0", "beat:u1")
    mutations.add_beat(g, setup_beat("v"), [])
    mutations.add_ordering(g, "beat:u1", "beat:v")
    pc.insert_texture_world(g, [arm_beat("w0"), arm_beat("w1")], ["beat:u0", "beat:u1"])
    assert pc.scene_fork_count(g, preset.passage_beats_max) == 1


def test_nested_texture_splice_is_legal():
    """Worlds nest (cosmetic-forks §3): a stretch inside an existing arm is
    just a segment; its rendering mirrors arm beats, grounding out in the
    trunk transitively."""
    g = StoryGraph()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    inner = [arm_beat(f"n{i}") for i in range(3)]
    pc.insert_texture_world(g, inner, ["beat:a3", "beat:a4", "beat:a5"])
    assert g.node("beat:n0").mirrors == "beat:a3"
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:a2", "beat:n0")
    assert g.has_edge(EdgeKind.PREDECESSOR, "beat:n2", "beat:a6")


# -- PR-5: the round planner -------------------------------------------------------


def _cosmetic(g, slug, path=None):
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


def test_fork_plan_is_deterministic_and_terminal_at_target():
    preset = _micro_vision_preset()
    g = StoryGraph()
    chain(g, ["r"] + [f"b{i}" for i in range(20)])
    plan = pc.fork_plan(g, preset)
    assert plan == pc.fork_plan(g, preset)
    assert plan  # a choice-less 21-beat run is far above the B6 target
    # a short chain projects under the target: nothing to admit
    g2 = StoryGraph()
    chain(g2, ["r", "a", "b"])
    assert pc.fork_plan(g2, preset) == []


def test_fork_plan_words_admission_blocks_scenes_before_edges():
    """The words budget is per-site marginal (cosmetic-forks §6): a scene
    segment costs its stretch re-printed, an edge site a micro chunk per
    arm — a tight target starves the scene tier first."""
    preset = _micro_vision_preset()
    g = StoryGraph()
    chain(g, ["r"] + [f"b{i}" for i in range(20)])
    wide = pc.fork_plan(g, preset)  # band top: the scene segment fits
    assert any(s.segment for s in wide)
    tight = pc.fork_plan(g, preset, words_target=2700)
    assert tight and all(not s.segment for s in tight)


def test_fork_plan_caps_scene_forks_story_total():
    preset = SCOPE_PRESETS["short"]  # cap 3, TEXTURE_WORLDS_MAX 3
    g = StoryGraph()
    chain(g, [f"c{i}" for i in range(18)])
    for k, lo in enumerate((3, 6, 9)):
        stretch = [f"beat:c{i}" for i in range(lo, lo + 3)]
        pc.insert_texture_world(g, [arm_beat(f"w{k}-{i}") for i in range(3)], stretch)
    assert pc.scene_fork_count(g, 3) == 3
    plan = pc.fork_plan(g, preset)
    cap = preset.passage_beats_max
    assert all(len(s.segment) < cap for s in plan)


def test_fork_plan_shape_cycle_offsets_by_minted_keywords():
    """Resume determinism: the shape-mix cycle position is a pure function
    of the graph — offset by the cosmetic flags already minted."""
    preset = _micro_vision_preset()
    cycle = preset.cadence_arm_cycle
    g = StoryGraph()
    chain(g, ["r"] + [f"b{i}" for i in range(20)])
    plan = pc.fork_plan(g, preset, words_target=3200)
    assert plan and all(not s.segment for s in plan)
    # the first-admitted edge (bisection order: the run's middle seam, b8->b9)
    # has ample headroom, so its shape is the pure cycle value — later sites
    # may be degraded to sidetracks at the budget boundary
    first = next(s for s in plan if s.before == "beat:b8")
    assert first.arms == cycle[0]
    _cosmetic(g, "minted")
    shifted = pc.fork_plan(g, preset, words_target=3200)
    assert next(s for s in shifted if s.before == "beat:b8").arms == cycle[1]


def test_offered_keywords_upstream_unconsumed_capped():
    g = StoryGraph()
    chain(g, ["a", "b", "c", "d"])
    flags = [_cosmetic(g, f"k{i}") for i in range(10)]
    downstream = _cosmetic(g, "late")
    consumed = _cosmetic(g, "used")
    for f in [*flags, consumed]:
        mutations.add_beat_flag_grant(g, "beat:a", f)
    mutations.add_beat_flag_grant(g, "beat:d", downstream)
    g.node("beat:c").requires_flags = [consumed]
    offered = pc.offered_keywords(g, "beat:c")
    assert len(offered) == 8
    assert consumed not in offered and downstream not in offered
    assert set(offered) <= set(flags)


# -- PR-5: I15 restated (composition-closed, budget parity) -------------------------


def test_i15_accepts_nesting_and_unmirrored_decoration(vision):
    """The restated shape half (cosmetic-forks §3, ratified decision 1):
    un-mirrored FALSE_BRANCH decoration is contracted before projection, so
    a diamond spliced inside either side of a two-worlds fork no longer
    breaks parity — per-walk B6 owns choice fairness now — and a rendering
    over an arm stretch (nesting) projects level-by-level."""
    g = StoryGraph()
    ids = chain(g, ["p"] + [f"t{i}" for i in range(10)] + ["s"])
    pc.insert_texture_world(g, [arm_beat(f"a{i}") for i in range(10)], ids[1:11])
    # nested world over an arm stretch
    pc.insert_texture_world(
        g, [arm_beat(f"n{i}") for i in range(3)], ["beat:a3", "beat:a4", "beat:a5"]
    )
    # un-mirrored diamond inside the mirrored trunk stretch (removes t6->t7)
    def fb(slug):
        return Beat(
            id=f"beat:{slug}",
            created_by=Stage.POLISH,
            summary=slug,
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.FALSE_BRANCH,
        )

    pc.insert_false_branch(g, [fb("d-a")], [fb("d-b")], "beat:t6", "beat:t7")
    # and an un-mirrored sidetrack inside the arm
    pc.insert_sidetrack(g, [fb("d-c")], "beat:a6", "beat:a7")
    assert i15_errors(g, vision) == []


def test_i15_mirror_cycle_does_not_ground_out(vision):
    g = StoryGraph()
    chain(g, ["p", "s"])
    for slug, twin in (("x", "beat:y"), ("y", "beat:x")):
        mutations.add_beat(g, arm_beat(slug, mirrors=twin), [])
    for slug in ("x", "y"):
        mutations.add_ordering(g, "beat:p", f"beat:{slug}")
        mutations.add_ordering(g, f"beat:{slug}", "beat:s")
    assert any("ground out" in i.message for i in i15_errors(g, vision))
