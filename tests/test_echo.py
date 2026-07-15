"""Echo detection primitives (plan: docs/plans/prose-quality.md W1)."""

from __future__ import annotations

from questfoundry.pipeline.echo import contains_phrase, longest_shared_run, shared_runs, tokens


def test_tokens_normalize_case_and_punctuation():
    assert tokens('He said: "the Wide, lateral stance!"') == [
        "he",
        "said",
        "the",
        "wide",
        "lateral",
        "stance",
    ]


def test_contains_phrase_matches_across_punctuation():
    prose = "He settles, as always, into the wide lateral stance — of a classical fencer."
    assert contains_phrase(prose, "the wide lateral stance of a classical fencer", 4)


def test_contains_phrase_ignores_short_values():
    # a three-token fact cannot reasonably be avoided in prose
    assert not contains_phrase("the velvet smoking jacket hung there", "velvet smoking jacket", 4)


def test_contains_phrase_requires_contiguity():
    prose = "the stance he takes is wide, and lateral in its way"
    assert not contains_phrase(prose, "the wide lateral stance", 4)


def test_longest_shared_run_grows_past_the_seed():
    a = "morning found the lamp room cold and the brass dull with salt"
    b = "she remembered how morning found the lamp room cold and the brass shining"
    assert longest_shared_run(a, b, 4) == "morning found the lamp room cold and the brass"


def test_longest_shared_run_none_below_threshold():
    a = "the lamp room was cold"
    b = "a cold lamp room greeted her"
    assert longest_shared_run(a, b, 4) is None


def test_shared_runs_finds_every_independent_lift():
    """A draft can lift several runs from one neighbor; the texture-trial
    live run exhausted repairs because only the first was reported per
    round. Both maximal runs must surface at once."""
    a = (
        "morning found the lamp room cold and the brass dull. later, "
        "the promise of safety tugged at the edge of her resolve"
    )
    b = (
        "she recalled how morning found the lamp room cold while "
        "the promise of safety tugged at the edge of her mind"
    )
    assert shared_runs(a, b, 4) == [
        "morning found the lamp room cold",
        "the promise of safety tugged at the edge of her",
    ]


def test_shared_runs_drops_contained_sub_runs():
    a = "morning found the lamp room cold and the brass dull with salt"
    b = "she remembered how morning found the lamp room cold and the brass shining"
    assert shared_runs(a, b, 4) == ["morning found the lamp room cold and the brass"]
