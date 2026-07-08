from pathlib import Path

import pytest

from questfoundry.graph import mutations
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.concept import Vision
from questfoundry.models.drama import (
    Answer,
    Consequence,
    Dilemma,
    DilemmaRole,
    EndingSalience,
    ResidueWeight,
)
from questfoundry.models.drama import (
    Path as StoryPath,
)
from questfoundry.models.structure import Beat, BeatClass, DilemmaImpact, ImpactEffect
from questfoundry.models.world import Entity
from questfoundry.project import load_project

GOLDEN = Path(__file__).parent.parent / "examples" / "keepers-bargain"


@pytest.fixture()
def golden():
    return load_project(GOLDEN)


@pytest.fixture()
def vision():
    return Vision(premise="test", genre="test", tone="test", scope="micro")


def make_dilemma(
    g: StoryGraph,
    slug: str,
    role: DilemmaRole = DilemmaRole.SOFT,
    entity: str | None = None,
) -> tuple[str, str, str]:
    """Add a dilemma with two explored paths. Returns (dilemma, path_a, path_b)."""
    if entity is None:
        entity = f"character:{slug}-anchor"
        mutations.add_entity(
            g, Entity(id=entity, created_by=Stage.BRAINSTORM, name="A", concept="c")
        )
    did = f"dilemma:{slug}"
    mutations.add_dilemma(
        g,
        Dilemma(
            id=did,
            created_by=Stage.BRAINSTORM,
            question="?",
            why_it_matters="stakes",
            role=role,
            residue_weight=ResidueWeight.LIGHT,
            ending_salience=EndingSalience.LOW,
        ),
        (
            Answer(id=f"answer:{slug}-a", created_by=Stage.BRAINSTORM, text="a"),
            Answer(id=f"answer:{slug}-b", created_by=Stage.BRAINSTORM, text="b"),
        ),
        [entity],
    )
    paths = []
    for side in ("a", "b"):
        pid = f"path:{slug}-{side}"
        mutations.add_path(
            g,
            StoryPath(id=pid, created_by=Stage.SEED),
            f"answer:{slug}-{side}",
            [Consequence(id=f"consequence:{slug}-{side}", created_by=Stage.SEED, text="t")],
        )
        paths.append(pid)
    return did, paths[0], paths[1]


def narrative_beat(
    slug: str,
    dilemma: str,
    effect: ImpactEffect = ImpactEffect.ADVANCES,
    is_ending: bool = False,
) -> Beat:
    return Beat(
        id=f"beat:{slug}",
        created_by=Stage.SEED,
        summary=slug,
        beat_class=BeatClass.NARRATIVE,
        dilemma_impacts=[DilemmaImpact(dilemma=dilemma, effect=effect)],
        is_ending=is_ending,
    )


def make_y_scaffold(g: StoryGraph, slug: str, dilemma: str, path_a: str, path_b: str) -> None:
    """Wire a minimal valid Y: pre -> (commit_a -> post_a[end], commit_b -> post_b[end])."""
    mutations.add_beat(g, narrative_beat(f"{slug}-pre", dilemma), [path_a, path_b])
    for side, path in (("a", path_a), ("b", path_b)):
        mutations.add_beat(
            g, narrative_beat(f"{slug}-commit-{side}", dilemma, ImpactEffect.COMMITS), [path]
        )
        mutations.add_beat(
            g,
            narrative_beat(f"{slug}-post-{side}", dilemma, is_ending=True),
            [path],
        )
        mutations.add_ordering(g, f"beat:{slug}-pre", f"beat:{slug}-commit-{side}")
        mutations.add_ordering(g, f"beat:{slug}-commit-{side}", f"beat:{slug}-post-{side}")
