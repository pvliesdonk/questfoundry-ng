"""Braid metrics — the heritage phase model made countable.

Contract: docs/plans/weave-linearization.md §5. The metrics are
phase-aware, not uniform alternation: introduction clusters at an arc's
opening and consequence clusters at its end are correct; the middle is
where interleaving must be dense and commits spread out. Ground truth
is the arc — a reader reads one arc, and a well-braided spine can still
hand some arc a lump — so every consumer scores induced arc orders and
aggregates by worst arc.

Pure functions over token sequences: no graph or plan dependency, so
the weave (scoring candidates pre-tensor) and validate (B12 on the
realized graph) share one definition and can never disagree.
"""

from __future__ import annotations

from dataclasses import dataclass

MIDDLE_RUN_MAX = 3  # K: longest same-thread run tolerated in the middle
COMMIT_GAP_MIN = 2  # S: beats between consecutive commits
INTRO_WINDOW_FRACTION = 3  # N = ceil(len / this): intro window size
BRAID_FLOOR_THREADS = 2  # fewer distinct threads: phases don't apply


@dataclass(frozen=True)
class BraidToken:
    """One beat as the braid sees it: which storyline(s) it advances
    (empty = neutral connective tissue — setup, bridges) and whether it
    is a point of no return."""

    threads: frozenset[str]
    commit: bool = False


@dataclass(frozen=True)
class BraidScore:
    """Countable braid quality of one arc (or the worst over arcs).

    ``middle_run`` — longest same-thread consecutive run in the middle
    phase (after every thread present on the arc has introduced, before
    the final commit's span). ``late_intros`` — threads whose first
    beat falls outside the arc's intro window. ``commit_gap`` — the
    smallest number of beats between consecutive commits (None with
    fewer than two commits). ``ping_pong`` — length-1 runs in the
    middle (beat-by-beat alternation is as un-braided as a lump).
    ``degenerate`` — the arc sits below the thread floor; phase metrics
    do not apply and the score carries no signal.
    """

    middle_run: int = 0
    late_intros: int = 0
    commit_gap: int | None = None
    ping_pong: int = 0
    degenerate: bool = False

    def penalty(self) -> int:
        """Deterministic scalar for ranking; lower is better. Weights
        order the failure modes by how directly they violate the phase
        doctrine (the lump first), not by calibration."""
        if self.degenerate:
            return 0
        run_excess = max(0, self.middle_run - MIDDLE_RUN_MAX)
        gap_short = (
            max(0, COMMIT_GAP_MIN - self.commit_gap) if self.commit_gap is not None else 0
        )
        return 3 * run_excess + 2 * self.late_intros + 2 * gap_short + self.ping_pong


def score_arc(tokens: list[BraidToken]) -> BraidScore:
    """Score one arc's beat order against the phase model."""
    threads = sorted({t for tok in tokens for t in tok.threads})
    if len(threads) < BRAID_FLOOR_THREADS:
        return BraidScore(degenerate=True)

    first_seen = {}
    for i, tok in enumerate(tokens):
        for t in tok.threads:
            first_seen.setdefault(t, i)

    window = -(-len(tokens) // INTRO_WINDOW_FRACTION)  # ceil
    late_intros = sum(1 for pos in first_seen.values() if pos >= window)

    commit_positions = [i for i, tok in enumerate(tokens) if tok.commit]
    commit_gap = (
        min(b - a - 1 for a, b in zip(commit_positions, commit_positions[1:], strict=False))
        if len(commit_positions) > 1
        else None
    )

    # The middle phase: after the last thread's introduction, before the
    # final commit's span. Empty or inverted middles carry no run signal.
    middle_start = max(first_seen.values()) + 1
    middle_end = commit_positions[-1] if commit_positions else len(tokens)
    middle_run = 0
    ping_pong = 0
    run_thread: str | None = None
    run_len = 0

    def close_run() -> None:
        nonlocal middle_run, ping_pong, run_len, run_thread
        if run_len == 1:
            ping_pong += 1
        middle_run = max(middle_run, run_len)
        run_len = 0
        run_thread = None

    for tok in tokens[middle_start:middle_end]:
        single = next(iter(tok.threads)) if len(tok.threads) == 1 else None
        if single is not None and single == run_thread:
            run_len += 1
        else:
            close_run()
            if single is not None:
                run_thread = single
                run_len = 1
    close_run()

    return BraidScore(
        middle_run=middle_run,
        late_intros=late_intros,
        commit_gap=commit_gap,
        ping_pong=ping_pong,
    )


def worst(scores: list[BraidScore]) -> BraidScore:
    """Aggregate per-arc scores to the arc a reader would complain
    about. Degenerate arcs carry no signal and are skipped; all-
    degenerate aggregates stay degenerate."""
    live = [s for s in scores if not s.degenerate]
    if not live:
        return BraidScore(degenerate=True)
    gaps = [s.commit_gap for s in live if s.commit_gap is not None]
    return BraidScore(
        middle_run=max(s.middle_run for s in live),
        late_intros=max(s.late_intros for s in live),
        commit_gap=min(gaps) if gaps else None,
        ping_pong=max(s.ping_pong for s in live),
    )


def describe(score: BraidScore) -> str:
    """One prompt/report line; states the caps so the reader needs no
    other reference."""
    if score.degenerate:
        return "braid: too few storylines to braid (phases do not apply)"
    gap = "n/a" if score.commit_gap is None else str(score.commit_gap)
    return (
        f"braid: longest middle run {score.middle_run} (cap {MIDDLE_RUN_MAX}), "
        f"late intros {score.late_intros}, min commit gap {gap} "
        f"(floor {COMMIT_GAP_MIN}), ping-pong {score.ping_pong} — "
        f"penalty {score.penalty()} (lower is better)"
    )
