import pytest

from questfoundry.graph import mutations, queries
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from questfoundry.models.base import Stage
from questfoundry.models.structure import IntersectionGroup
from tests.conftest import make_dilemma, make_y_scaffold, narrative_beat


def test_cross_dilemma_dual_belongs_to_is_rejected():
    g = StoryGraph()
    d1, p1a, _ = make_dilemma(g, "one")
    d2, p2a, _ = make_dilemma(g, "two")
    with pytest.raises(MutationError, match="cross-dilemma"):
        mutations.add_beat(g, narrative_beat("bad", d1), [p1a, p2a])


def test_commit_beat_must_belong_to_one_path():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    from questfoundry.models.structure import ImpactEffect

    with pytest.raises(MutationError, match="exactly one path"):
        mutations.add_beat(g, narrative_beat("bad", d, ImpactEffect.COMMITS), [pa, pb])


def test_ordering_rejects_cycles():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    with pytest.raises(MutationError, match="cycle"):
        mutations.add_ordering(g, "beat:one-post-a", "beat:one-pre")


def test_remove_ordering_requires_an_existing_edge():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    from questfoundry.models.base import EdgeKind

    mutations.remove_ordering(g, "beat:one-pre", "beat:one-commit-a")
    assert not g.has_edge(EdgeKind.PREDECESSOR, "beat:one-pre", "beat:one-commit-a")
    with pytest.raises(MutationError, match="no ordering"):
        mutations.remove_ordering(g, "beat:one-pre", "beat:one-commit-a")


def test_freeze_blocks_beat_removal():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.remove_beat(g, "beat:one-post-a")  # fine before freeze
    mutations.add_beat(g, narrative_beat("one-post-a", d, is_ending=True), [pa])
    mutations.add_ordering(g, "beat:one-commit-a", "beat:one-post-a")
    mutations.freeze_topology(g)
    with pytest.raises(MutationError, match="frozen"):
        mutations.remove_beat(g, "beat:one-post-a")


def test_intersection_rejects_same_dilemma_members():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    group = IntersectionGroup(id="intersection:x", created_by=Stage.GROW)
    with pytest.raises(MutationError, match="dilemma"):
        mutations.add_intersection(g, group, ["beat:one-commit-a", "beat:one-pre"])


def test_answer_cannot_be_explored_twice():
    g = StoryGraph()
    make_dilemma(g, "one")
    from questfoundry.models.drama import Path as StoryPath

    with pytest.raises(MutationError, match="already explored"):
        mutations.add_path(g, StoryPath(id="path:dup", created_by=Stage.SEED), "answer:one-a", [])


def test_freeze_records_forks_and_convergence():
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    record = mutations.freeze_topology(g)
    assert record.forks[d] == ["beat:one-commit-a", "beat:one-commit-b"]
    assert d not in record.convergences  # posts are endings; paths never rejoin
    assert queries.commit_beats(g, pa) == ["beat:one-commit-a"]


# -- entity arcs (plan: docs/plans/prose-quality.md W5) ------------------------


def _golden():
    from questfoundry.project import load_project
    from tests.conftest import GOLDEN

    return load_project(GOLDEN)


def test_set_entity_arc_validates_references_and_order():
    import pytest

    from questfoundry.graph.mutations import MutationError, set_entity_arc
    from questfoundry.models.world import ArcPivot, EntityArc, PathEnd

    g = _golden().graph
    with pytest.raises(MutationError, match="not a beat"):
        set_entity_arc(
            g,
            "character:sleeper",
            EntityArc(begins="asleep", pivots=[ArcPivot(beat="beat:no-such", becomes="x")]),
        )
    with pytest.raises(MutationError, match="not a path"):
        set_entity_arc(
            g,
            "character:sleeper",
            EntityArc(begins="asleep", ends=[PathEnd(path="path:no-such", state="x")]),
        )
    # the repair brief names the listed order AND the required order — a
    # model cannot recover from a restated rule when the offense is the
    # engine's own linearization (live kimi-k2.5 exhaustion, 2026-07-14)
    with pytest.raises(
        MutationError,
        match=r"listed as \['beat:offer', 'beat:storm-glass'\].*"
        r"occur as \['beat:storm-glass', 'beat:offer'\]",
    ):
        set_entity_arc(
            g,
            "character:sleeper",
            EntityArc(
                begins="asleep",
                pivots=[
                    ArcPivot(beat="beat:offer", becomes="later"),
                    ArcPivot(beat="beat:storm-glass", becomes="earlier"),
                ],
            ),
        )
    assert g.node("character:sleeper").arc is None  # nothing landed


def test_set_entity_arc_is_stable_once_set():
    import pytest

    from questfoundry.graph.mutations import MutationError, set_entity_arc
    from questfoundry.models.world import EntityArc

    g = _golden().graph
    arc = EntityArc(begins="asleep, patient")
    set_entity_arc(g, "character:sleeper", arc)
    set_entity_arc(g, "character:sleeper", EntityArc(begins="asleep, patient"))  # no-op
    with pytest.raises(MutationError, match="stable once set"):
        set_entity_arc(g, "character:sleeper", EntityArc(begins="different"))


def test_add_beat_duplicate_id_is_actionable_mutation_error():
    """A new beat reusing an existing id must raise a repairable
    MutationError (not the store's bare KeyError, which the runner never
    catches), and the message must tell the model how to recover — pick a
    fresh id — not merely that the id is taken (weak-tier live run:
    gpt-oss:120b reused a commit-beat id for a residue beat and could not
    recover from a bare "duplicate node id" message across repairs)."""
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    mutations.add_beat(g, narrative_beat("dup", d), [pa])
    with pytest.raises(MutationError, match="already used") as exc:
        mutations.add_beat(g, narrative_beat("dup", d), [pb])
    assert "fresh, unique id" in str(exc.value)  # recovery_action, not just reason


def test_duplicate_edge_raises_graph_error():
    """A repeated relation raises the store's GraphError (a KeyError
    subclass the runner catches as repairable), with a recovery_action —
    not a bare, uncaught KeyError."""
    from questfoundry.graph.store import GraphError

    g = StoryGraph()
    d, pa, _ = make_dilemma(g, "one")
    mutations.add_beat(g, narrative_beat("a", d), [pa])
    mutations.add_beat(g, narrative_beat("b", d), [pa])
    mutations.add_ordering(g, "beat:a", "beat:b")
    with pytest.raises(GraphError, match="already exists") as exc:
        mutations.add_ordering(g, "beat:a", "beat:b")
    assert "do not" in str(exc.value)  # recovery_action, not just a diagnostic


def test_split_passage_rejects_an_ending():
    """Endings never split — variants would multiply the story's ending
    set, fixed at the freeze (I12's documented exception)."""
    from questfoundry.models.presentation import Ending, Passage
    from questfoundry.models.structure import FlagSource, StateFlag

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    for flag_id, path in (("flag:one-a", pa), ("flag:one-b", pb)):
        mutations.add_flag(
            g,
            StateFlag(
                id=flag_id,
                created_by=Stage.GROW,
                description="d",
                source=FlagSource.DILEMMA,
                path=path,
            ),
        )
    mutations.add_passage(
        g,
        Passage(
            id="passage:p-final",
            created_by=Stage.POLISH,
            summary="s",
            ending=Ending(id="ending:p-final", title="t"),
        ),
        ["beat:one-post-a"],
    )
    with pytest.raises(MutationError, match="ending set, fixed at the freeze"):
        mutations.split_passage(g, "passage:p-final", [["flag:one-a"], ["flag:one-b"]])


def test_add_beat_flag_grant_lands_sorted_and_idempotent_on_frozen_beats():
    """The rendering-0 head annotation (cosmetic-forks PR-5): a cosmetic
    grant is a legal presentation addition on a frozen beat — the freeze
    (I9) is topological. Grants stay sorted and re-granting is a no-op."""
    from questfoundry.models.structure import FlagSource, StateFlag

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.freeze_topology(g)
    for slug in ("cw-b", "cw-a"):
        mutations.add_flag(
            g,
            StateFlag(
                id=f"flag:{slug}",
                created_by=Stage.POLISH,
                description="took the rendering",
                source=FlagSource.COSMETIC,
            ),
        )
    mutations.add_beat_flag_grant(g, "beat:one-pre", "flag:cw-b")
    mutations.add_beat_flag_grant(g, "beat:one-pre", "flag:cw-a")
    mutations.add_beat_flag_grant(g, "beat:one-pre", "flag:cw-b")
    assert g.node("beat:one-pre").grants_flags == ["flag:cw-a", "flag:cw-b"]


def test_add_beat_flag_grant_rejects_bad_references_and_dilemma_flags():
    """Only cosmetic flags are granted via grants_flags; a dilemma flag is
    granted at its path's commit. Errors carry the corrective."""
    from questfoundry.models.structure import FlagSource, StateFlag

    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    mutations.add_flag(
        g,
        StateFlag(
            id="flag:one-a",
            created_by=Stage.GROW,
            description="d",
            source=FlagSource.DILEMMA,
            path=pa,
        ),
    )
    with pytest.raises(MutationError, match="not a beat"):
        mutations.add_beat_flag_grant(g, "beat:missing", "flag:one-a")
    with pytest.raises(MutationError, match="not a flag"):
        mutations.add_beat_flag_grant(g, "beat:one-pre", "flag:missing")
    with pytest.raises(MutationError, match="commit") as exc:
        mutations.add_beat_flag_grant(g, "beat:one-pre", "flag:one-a")
    assert "cosmetic" in str(exc.value)
