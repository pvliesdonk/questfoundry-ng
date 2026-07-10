import hashlib
import math
import re
from pathlib import Path

import pytest
from markdown_vault_mcp.providers import EmbeddingProvider

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
CORPUS = Path(__file__).parent / "fixtures" / "corpus"


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed bag-of-words embedding provider, so
    research-pass tests drive true `markdown-vault-mcp` hybrid search
    without a model download or a network call. Each word hashes to one
    of 64 dimensions; the vector is L2-normalized so cosine similarity
    behaves like a real embedding's."""

    _DIM = 64

    def __init__(self, model_name: str = "fake-hashing-embedder") -> None:
        self._model_name = model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    @classmethod
    def _embed_one(cls, text: str) -> list[float]:
        vector = [0.0] * cls._DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            bucket = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16) % cls._DIM
            vector[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    @property
    def dimension(self) -> int:
        return self._DIM

    @property
    def context_length(self) -> int | None:
        return 512

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "fake-hashing"


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
    residue: ResidueWeight = ResidueWeight.LIGHT,
    explore: int = 2,
) -> tuple[str, str, str]:
    """Add a dilemma with `explore` explored paths (2 = branched, 1 =
    locked, 0 = pre-triage). Returns (dilemma, path_a, path_b); unexplored
    slots are empty strings."""
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
            residue_weight=residue,
            ending_salience=EndingSalience.LOW,
        ),
        (
            Answer(id=f"answer:{slug}-a", created_by=Stage.BRAINSTORM, text="a"),
            Answer(id=f"answer:{slug}-b", created_by=Stage.BRAINSTORM, text="b"),
        ),
        [entity],
    )
    paths = []
    for side in ("a", "b")[:explore]:
        pid = f"path:{slug}-{side}"
        mutations.add_path(
            g,
            StoryPath(id=pid, created_by=Stage.SEED),
            f"answer:{slug}-{side}",
            [Consequence(id=f"consequence:{slug}-{side}", created_by=Stage.SEED, text="t")],
        )
        paths.append(pid)
    paths += [""] * (2 - len(paths))
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


def make_locked_chain(g: StoryGraph, slug: str, dilemma: str, path: str) -> None:
    """Wire a minimal valid locked storyline: lead -> resolve (commit) -> after."""
    mutations.add_beat(g, narrative_beat(f"{slug}-lead", dilemma), [path])
    mutations.add_beat(g, narrative_beat(f"{slug}-resolve", dilemma, ImpactEffect.COMMITS), [path])
    mutations.add_beat(g, narrative_beat(f"{slug}-after", dilemma), [path])
    mutations.add_ordering(g, f"beat:{slug}-lead", f"beat:{slug}-resolve")
    mutations.add_ordering(g, f"beat:{slug}-resolve", f"beat:{slug}-after")


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
