"""Property tests: the mutation layer keeps the graph well-formed under fire."""

import contextlib

from hypothesis import given
from hypothesis import strategies as st

from questfoundry.graph import mutations, queries
from questfoundry.graph.mutations import MutationError
from questfoundry.graph.store import StoryGraph
from tests.conftest import make_dilemma, make_y_scaffold


@given(st.lists(st.tuples(st.integers(0, 6), st.integers(0, 6)), max_size=25))
def test_add_ordering_never_creates_a_cycle(pairs):
    g = StoryGraph()
    d, pa, pb = make_dilemma(g, "one")
    make_y_scaffold(g, "one", d, pa, pb)
    beats = sorted(queries.beat_ids(g))
    for i, j in pairs:
        with contextlib.suppress(MutationError, KeyError):
            mutations.add_ordering(g, beats[i % len(beats)], beats[j % len(beats)])
        # rejected proposals must leave the graph acyclic and unchanged
        assert queries.topological_order(g) is not None
