"""Structural scale simulation (M8 phase 0; docs/plans/m8-depth-scale.md D3).

Synthetic stories at parameterized dilemma mixes and chain depths, built
and compiled through the real machinery — SEED-shaped graph construction,
weave plan/candidates/realize, GROW flag derivation, POLISH residue-arm
splices and the words-aware cadence budget, capped passage collapse — so
preset bands are calibrated against what the engine actually yields
rather than against stories generated under the old bands (the
calibration-circularity risk).

Word projections are walk-based: for each arc a deterministic playthrough
walks the passage-group graph taking the first live choice, so a cosmetic
diamond contributes one arm's words and one offered decision — what a
reader experiences — where an arc view would count both arms and no
decision policy at all. This mirrors B6's post-M8 semantics.

Run the table: ``uv run python -m tests.scale``
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from questfoundry.graph import mutations, queries
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import EdgeKind, Stage
from questfoundry.models.concept import SCOPE_PRESETS, ScaffoldShape, ScopePreset
from questfoundry.models.drama import DilemmaRole
from questfoundry.models.structure import (
    Beat,
    BeatClass,
    ImpactEffect,
    StateFlag,
    StructuralPurpose,
)
from questfoundry.pipeline import passages as pc
from questfoundry.pipeline import weave
from questfoundry.pipeline.stages.grow import _derive_flags
from tests.conftest import make_dilemma, narrative_beat

# -- configuration -----------------------------------------------------------


@dataclass(frozen=True)
class SimShape:
    """Concrete chain depths (one point inside a ScaffoldShape's bands)."""

    setup: int
    pre: int
    post: int
    lead_in: int
    aftermath: int

    @classmethod
    def band_min(cls, shape: ScaffoldShape) -> SimShape:
        return cls(
            shape.setup[0],
            shape.pre_commit[0],
            shape.post_commit[0],
            shape.locked_lead_in[0],
            shape.locked_aftermath[0],
        )

    @classmethod
    def band_max(cls, shape: ScaffoldShape) -> SimShape:
        return cls(
            shape.setup[1],
            shape.pre_commit[1],
            shape.post_commit[1],
            shape.locked_lead_in[1],
            shape.locked_aftermath[1],
        )


@dataclass
class Yield:
    beats: int
    passages: int
    arcs: int
    arc_beats: tuple[int, int]
    words_total: int
    diamonds: int
    b6: tuple[int, int]  # (min, max) walk words per offered decision
    real_per_arc: float
    cosmetic_per_arc: float


# -- builder -----------------------------------------------------------------


def build_seeded(preset: ScopePreset, sim: SimShape, *, locked: int | None = None) -> StoryGraph:
    """A SEED-complete graph at the preset's dilemma mix: setup chain, one
    Y per branched dilemma at the given depths, one chain per locked
    dilemma. The first hard dilemma wraps every other (the backbone shape
    every live run chose)."""
    g = StoryGraph()
    prev = None
    for i in range(sim.setup):
        beat = Beat(
            id=f"beat:setup-{i}",
            created_by=Stage.SEED,
            summary=f"setup {i}",
            beat_class=BeatClass.STRUCTURAL,
            purpose=StructuralPurpose.SETUP,
        )
        mutations.add_beat(g, beat, [])
        if prev:
            mutations.add_ordering(g, prev, beat.id)
        prev = beat.id

    dilemmas: list[str] = []

    def y_scaffold(slug: str, dilemma: str, path_a: str, path_b: str, *, endings: bool) -> None:
        prev = None
        for i in range(sim.pre):
            beat = narrative_beat(f"{slug}-pre{i}", dilemma)
            mutations.add_beat(g, beat, [path_a, path_b])
            if prev:
                mutations.add_ordering(g, prev, beat.id)
            prev = beat.id
        for side, path in (("a", path_a), ("b", path_b)):
            commit = narrative_beat(f"{slug}-commit-{side}", dilemma, ImpactEffect.COMMITS)
            mutations.add_beat(g, commit, [path])
            mutations.add_ordering(g, prev, commit.id)
            chain_prev = commit.id
            for i in range(sim.post):
                beat = narrative_beat(
                    f"{slug}-post-{side}{i}",
                    dilemma,
                    is_ending=endings and i == sim.post - 1,
                )
                mutations.add_beat(g, beat, [path])
                mutations.add_ordering(g, chain_prev, beat.id)
                chain_prev = beat.id

    for n in range(preset.hard_dilemmas):
        d, pa, pb = make_dilemma(g, f"hard{n}", role=DilemmaRole.HARD)
        y_scaffold(f"hard{n}", d, pa, pb, endings=True)
        dilemmas.append(d)
    for n in range(preset.soft_dilemmas):
        d, pa, pb = make_dilemma(g, f"soft{n}", role=DilemmaRole.SOFT)
        y_scaffold(f"soft{n}", d, pa, pb, endings=False)
        dilemmas.append(d)
    for n in range(preset.locked_dilemmas if locked is None else locked):
        d, path, _ = make_dilemma(g, f"lock{n}", explore=1)
        chain = (
            [narrative_beat(f"lock{n}-lead{i}", d) for i in range(sim.lead_in)]
            + [narrative_beat(f"lock{n}-resolve", d, ImpactEffect.COMMITS)]
            + [narrative_beat(f"lock{n}-after{i}", d) for i in range(sim.aftermath)]
        )
        for beat in chain:
            mutations.add_beat(g, beat, [path])
        for a, b in zip(chain, chain[1:], strict=False):
            mutations.add_ordering(g, a.id, b.id)
        dilemmas.append(d)

    for d in dilemmas[1:]:
        mutations.add_dilemma_relation(g, EdgeKind.WRAPS, dilemmas[0], d)
    return g


def _slug(world_label: str) -> str:
    return world_label.replace("path:", "").replace("+", "-") or "shared"


def add_residue_arms(g: StoryGraph, *, arm_beats: int = 1, fork: bool = False) -> None:
    """One flag-gated arm per path per world for every light-residue soft
    convergence, exactly as POLISH's finalize splices them; with `fork`,
    every arm is tensored — two same-gate branches (PR-1b)."""
    for need in pc.convergence_needs(g):
        if need.weight != "light":
            continue
        for path, flags in sorted(need.path_flags.items()):
            pslug = path.removeprefix("path:")

            def branch(tag: str, path=path, flags=flags, need=need, pslug=pslug):
                return [
                    Beat(
                        id=f"beat:res-{pslug}-{_slug(need.world)}{tag}-{i}",
                        created_by=Stage.POLISH,
                        summary="residue",
                        beat_class=BeatClass.STRUCTURAL,
                        purpose=StructuralPurpose.RESIDUE,
                        requires_flags=[flags[0]],
                    )
                    for i in range(arm_beats)
                ]

            if fork:
                pc.insert_residue_diamond(g, branch(""), branch("-alt"), path, list(need.rejoin))
            else:
                pc.insert_residue_chain(g, branch(""), path, list(need.rejoin))


def fill_cadence_budget(g: StoryGraph, preset: ScopePreset) -> int:
    """Insert the engine-computed diamond budget (pc.cadence_plan) with
    1-beat arms at the suggested edges, as the finalize prompt asks the
    model to. Returns the number of diamonds inserted."""
    plan = pc.cadence_plan(g, preset)
    inserted = 0
    for _run_idx, edges in sorted(plan.items()):
        for before, after in edges:
            arms = [
                [
                    Beat(
                        id=f"beat:fb-{inserted}-{side}",
                        created_by=Stage.POLISH,
                        summary="flavor",
                        beat_class=BeatClass.STRUCTURAL,
                        purpose=StructuralPurpose.FALSE_BRANCH,
                    )
                ]
                for side in ("a", "b")
            ]
            pc.insert_false_branch(g, arms[0], arms[1], before, after)
            inserted += 1
    return inserted


def compile_story(
    g: StoryGraph,
    preset: ScopePreset,
    *,
    order_index: int = 0,
    arm_beats: int = 1,
    tensored_arms: bool = False,
) -> tuple[StoryGraph, int]:
    """GROW + the structural half of POLISH, deterministically: weave one
    candidate order, derive flags, splice residue arms, fill the cadence
    budget. Returns (compiled graph, diamonds inserted)."""
    g = copy.deepcopy(g)
    planned = weave.plan(g)
    orders = weave.candidates(planned)
    weave.realize(g, planned, orders[min(order_index, len(orders) - 1)])
    _derive_flags(g)
    add_residue_arms(g, arm_beats=arm_beats, fork=tensored_arms)
    diamonds = fill_cadence_budget(g, preset)
    return g, diamonds


# -- measurement ---------------------------------------------------------------


def measure(g: StoryGraph, preset: ScopePreset, *, diamonds: int = 0) -> Yield:
    groups = pc.collapse_groups(g, max_beats=preset.passage_beats_max)
    edges = pc.group_edges(groups, g)
    succ: dict[int, list[int]] = {}
    for a, b in edges:
        succ.setdefault(a, []).append(b)
    group_of = {b: i for i, grp in enumerate(groups) for b in grp}
    commit_groups = {
        group_of[c]
        for d in queries.branched_dilemmas(g)
        for p in queries.explored_paths(g, d)
        for c in queries.commit_beats(g, p)
    }
    root_groups = {group_of[r] for r in queries.roots(g)}

    selections = queries.arc_selections(g)
    arc_beat_counts: list[int] = []
    b6s: list[int] = []
    reals: list[int] = []
    cosmetics: list[int] = []
    for selection in selections:
        view = queries.arc_view(g, selection)
        arc_beat_counts.append(len(view))
        held = {
            f.id
            for f in g.nodes_of(StateFlag)
            if any(grant in view for grant in queries.grant_beats(g, f.id))
        }
        in_view = [all(b in view for b in grp) for grp in groups]
        cur = min(i for i in root_groups if in_view[i])
        walk_words = real = cosmetic = 0
        while True:
            walk_words += pc.projected_group_words(g, groups[cur], preset)
            live = [
                t
                for t in succ.get(cur, [])
                if all(req in held for req in pc.choice_requires(g, groups[t]))
            ]
            if len(live) >= 2:
                if any(t in commit_groups for t in live):
                    real += 1
                else:
                    cosmetic += 1
            nxt = [t for t in live if in_view[t]]
            if not nxt:
                break
            cur = nxt[0]
        b6s.append(round(walk_words / max(real + cosmetic, 1)))
        reals.append(real)
        cosmetics.append(cosmetic)

    return Yield(
        beats=len(queries.beat_ids(g)),
        passages=len(groups),
        arcs=len(selections),
        arc_beats=(min(arc_beat_counts), max(arc_beat_counts)),
        words_total=sum(pc.projected_group_words(g, grp, preset) for grp in groups),
        diamonds=diamonds,
        b6=(min(b6s), max(b6s)),
        real_per_arc=sum(reals) / len(reals),
        cosmetic_per_arc=sum(cosmetics) / len(cosmetics),
    )


def simulate(scope: str, corner: str = "min", *, order_index: int = 0) -> Yield:
    """Build + compile + measure one scope at a band corner."""
    preset = SCOPE_PRESETS[scope]
    sim = (SimShape.band_min if corner == "min" else SimShape.band_max)(preset.shape)
    g, diamonds = compile_story(build_seeded(preset, sim), preset, order_index=order_index)
    return measure(g, preset, diamonds=diamonds)


if __name__ == "__main__":
    header = (
        f"{'scope':<8}{'corner':<7}{'beats':>6}{'psgs':>6}{'arcs':>5}"
        f"{'arc-beats':>11}{'words':>8}{'dia':>5}{'B6':>11}{'r/c':>9}"
    )
    print(header)
    for scope in SCOPE_PRESETS:
        for corner in ("min", "max"):
            y = simulate(scope, corner)
            print(
                f"{scope:<8}{corner:<7}{y.beats:>6}{y.passages:>6}{y.arcs:>5}"
                f"{y.arc_beats[0]:>5}-{y.arc_beats[1]:<5}{y.words_total:>8}{y.diamonds:>5}"
                f"{y.b6[0]:>5}-{y.b6[1]:<5}{y.real_per_arc:>5.1f}/{y.cosmetic_per_arc:<3.0f}"
            )
