"""Deterministic echo detection for FILL (plan: docs/plans/prose-quality.md W1).

Live run 8's book-scale read found verbatim recurring descriptions: a
fact discovered once was rendered into every later write context and
performed verbatim by the writer, passage after passage. These checks
run at the write apply — the ordinary repair loop — and are
deliberately modest: they catch the verbatim floor; the prompt's
input-role framing is the real fix.

All comparison happens over normalized token sequences (lowercased,
punctuation stripped), so markdown, quotes, and sentence boundaries
don't hide an echo.
"""

from __future__ import annotations

import re

# A fact value of this many tokens appearing verbatim in prose is the
# stamp (facts are constraints, not choreography); shorter values
# ("velvet smoking jacket") cannot reasonably be avoided.
FACT_ECHO_TOKENS = 4

# A verbatim run this long shared with adjacent prose is a lift, not a
# collocation: names and stock phrases don't reach eight tokens, a
# copied sentence does.
WINDOW_ECHO_TOKENS = 8

# A micro-detail value longer than this is prose, not a fact — the
# brief register in a number.
DETAIL_VALUE_MAX_WORDS = 12

_TOKEN = re.compile(r"[a-z0-9']+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _ngrams(seq: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(seq[i : i + n]) for i in range(len(seq) - n + 1)}


def contains_phrase(text: str, phrase: str, min_tokens: int) -> bool:
    """True when `phrase` has at least `min_tokens` tokens and appears
    verbatim (as a contiguous token run) in `text`."""
    needle = tokens(phrase)
    if len(needle) < min_tokens:
        return False
    hay = tokens(text)
    target = tuple(needle)
    n = len(needle)
    return any(tuple(hay[i : i + n]) == target for i in range(len(hay) - n + 1))


def _contains(hay: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    n = len(needle)
    return any(hay[i : i + n] == needle for i in range(len(hay) - n + 1))


def shared_runs(a: str, b: str, min_tokens: int) -> list[str]:
    """Every maximal contiguous token run shared by `a` and `b` that
    reaches `min_tokens`, as space-joined phrases in order of appearance
    in `a`. A draft can carry several independent lifts; reporting one
    per repair round taught whack-a-mole (texture-trial live run: each
    round surfaced the next lift until repairs exhausted), so the caller
    gets them all at once."""
    ta, tb = tokens(a), tokens(b)
    if len(ta) < min_tokens or len(tb) < min_tokens:
        return []
    seed = _ngrams(ta, min_tokens) & _ngrams(tb, min_tokens)
    if not seed:
        return []
    # Grow each seed: for each shared min-length n-gram occurrence in
    # `a`, extend while `b` still contains the longer run.
    b_grams: dict[int, set[tuple[str, ...]]] = {min_tokens: _ngrams(tb, min_tokens)}
    found: list[tuple[str, ...]] = []
    for i in range(len(ta) - min_tokens + 1):
        gram = tuple(ta[i : i + min_tokens])
        if gram not in seed:
            continue
        n = min_tokens
        while i + n < len(ta):
            grown = tuple(ta[i : i + n + 1])
            if n + 1 not in b_grams:
                b_grams[n + 1] = _ngrams(tb, n + 1)
            if grown not in b_grams[n + 1]:
                break
            gram, n = grown, n + 1
        found.append(gram)
    maximal: list[tuple[str, ...]] = []
    for gram in found:
        if any(len(other) > len(gram) and _contains(other, gram) for other in found):
            continue
        if gram not in maximal:
            maximal.append(gram)
    return [" ".join(g) for g in maximal]


def longest_shared_run(a: str, b: str, min_tokens: int) -> str | None:
    """The longest contiguous token run shared by `a` and `b`, as a
    space-joined phrase, when it reaches `min_tokens`; else None."""
    runs = shared_runs(a, b, min_tokens)
    return max(runs, key=lambda p: len(tokens(p))) if runs else None
