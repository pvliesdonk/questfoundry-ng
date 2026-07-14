"""Material density (docs/plans/structural-depth.md, W1): the dilemma
budget couples to the words target so a scope earns its length (or
shrinks), and B9 flags the stretching signal (bridge share)."""

from questfoundry.graph import mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.graph.validate import Severity, run_checks
from questfoundry.models.base import Stage
from questfoundry.models.concept import SCOPE_PRESETS, Vision
from questfoundry.models.drama import DilemmaRole
from questfoundry.models.structure import Beat, BeatClass, StructuralPurpose
from tests.conftest import make_dilemma, narrative_beat


def issues_for(check: str, g, vision, stage, severity):
    return [
        i
        for i in run_checks(g, vision, stage)
        if i.check == check and i.severity == severity
    ]


# -- budget_for ---------------------------------------------------------------


def test_budget_uncoupled_matches_table():
    for preset in SCOPE_PRESETS.values():
        b = preset.budget_for(None)
        assert (b.hard, b.soft, b.locked) == (
            preset.hard_dilemmas,
            preset.soft_dilemmas,
            preset.locked_dilemmas,
        )


def test_budget_soft_scales_with_words_target():
    medium = SCOPE_PRESETS["medium"]
    assert medium.budget_for(55000).soft == 4  # the band top earns one more soft
    assert medium.budget_for(49300).soft == 3  # the anchor is the table budget
    assert medium.budget_for(37500).soft == 2  # the band middle shrinks
    assert medium.budget_for(20000).soft == 1  # the band floor clamps at one


def test_budget_hard_and_locked_never_move():
    medium = SCOPE_PRESETS["medium"]
    for target in (20000, 37500, 55000):
        b = medium.budget_for(target)
        assert b.hard == medium.hard_dilemmas
        assert b.locked == medium.locked_dilemmas


def test_budget_soft_upper_clamp():
    # short's rate says 22k is worth +3 softs; the clamp holds at +2
    # (cast_max stays fixed while dilemmas grow — each needs anchoring)
    short = SCOPE_PRESETS["short"]
    assert short.budget_for(22000).soft == short.soft_dilemmas + 2


def test_micro_is_exempt_from_coupling():
    micro = SCOPE_PRESETS["micro"]
    assert micro.budget_for(9000) == micro.budget_for(None)
    assert micro.budget_for(2400) == micro.budget_for(None)


# -- G0 -----------------------------------------------------------------------


def _vision(scope: str, words_target: int | None) -> Vision:
    return Vision(
        premise="p",
        genre="g",
        tone="t",
        themes=["a", "b"],
        scope=scope,
        words_target=words_target,
    )


def test_g0_words_target_outside_band_flagged():
    issues = issues_for(
        "G0", StoryGraph(), _vision("medium", 5000), Stage.DREAM, Severity.ERROR
    )
    assert any("words_target" in i.message for i in issues)


def test_g0_words_target_inside_band_passes():
    assert not issues_for(
        "G0", StoryGraph(), _vision("medium", 40000), Stage.DREAM, Severity.ERROR
    )


# -- B1 coupling --------------------------------------------------------------


def test_b1_words_target_raises_the_soft_budget():
    g = StoryGraph()
    for i in range(2):
        make_dilemma(g, f"hard-{i}", role=DilemmaRole.HARD, explore=0)
    for i in range(3):
        make_dilemma(g, f"soft-{i}", explore=0)
    # the table budget (2 hard + 3 soft) satisfies the uncoupled scope
    assert not issues_for(
        "B1", g, _vision("medium", None), Stage.BRAINSTORM, Severity.ERROR
    )
    # a band-top words target derives a 4th soft and names the derivation
    issues = issues_for(
        "B1", g, _vision("medium", 55000), Stage.BRAINSTORM, Severity.ERROR
    )
    assert any(
        "at words_target 55000" in i.message and ">=4 soft" in i.message for i in issues
    )


def test_b1_words_target_shrinks_the_soft_budget():
    g = StoryGraph()
    for i in range(2):
        make_dilemma(g, f"hard-{i}", role=DilemmaRole.HARD)
    for i in range(2):
        make_dilemma(g, f"soft-{i}")
    # 2 branched softs fail the table budget of 3...
    issues = issues_for(
        "B1", g, _vision("medium", None), Stage.BRAINSTORM, Severity.ERROR
    )
    assert any("expects 3 branched soft" in i.message for i in issues)
    # ...but exactly match a band-middle words target: the scope shrank honestly
    assert not issues_for(
        "B1", g, _vision("medium", 37500), Stage.BRAINSTORM, Severity.ERROR
    )


# -- B9 bridge share ----------------------------------------------------------


def _bridge(g: StoryGraph, i: int) -> None:
    mutations.add_beat(
        g,
        Beat(
            id=f"beat:bridge-{i}",
            created_by=Stage.GROW,
            summary="b",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.BRIDGE,
        ),
        [],
    )


def test_b9_bridge_share_above_threshold_warns(vision):
    g = StoryGraph()
    d, pa, _ = make_dilemma(g, "one")
    for i in range(4):
        mutations.add_beat(g, narrative_beat(f"n-{i}", d), [pa])
    for i in range(4):  # 4 of 8 beats are bridges: 50%
        _bridge(g, i)
    issues = issues_for("B9", g, vision, Stage.GROW, Severity.WARNING)
    assert any("stretching" in i.message for i in issues)


def test_b9_bridge_share_below_threshold_quiet(vision):
    g = StoryGraph()
    d, pa, _ = make_dilemma(g, "one")
    for i in range(9):
        mutations.add_beat(g, narrative_beat(f"n-{i}", d), [pa])
    _bridge(g, 0)  # 1 of 10 beats: 10%
    assert not issues_for("B9", g, vision, Stage.GROW, Severity.WARNING)
