"""Drama layer: dilemmas, answers, paths, consequences.

Answers are strictly equal — no default/primary/canonical marker exists
(invariant I1; design doc 01 §4).
"""

from __future__ import annotations

from enum import StrEnum

from questfoundry.models.base import Node


class DilemmaRole(StrEnum):
    HARD = "hard"  # backbone: commits late, paths never reconverge
    SOFT = "soft"  # subplot: commits earlier, paths reconverge after payoff


class ResidueWeight(StrEnum):
    HEAVY = "heavy"  # variant passages
    LIGHT = "light"  # residue beat before shared passage
    COSMETIC = "cosmetic"  # handled in prose wording


class EndingSalience(StrEnum):
    HIGH = "high"
    LOW = "low"
    NONE = "none"


class Dilemma(Node):
    """A binary dramatic question. Its two answers are `has_answer` edges."""

    question: str
    why_it_matters: str
    role: DilemmaRole
    residue_weight: ResidueWeight
    ending_salience: EndingSalience
    # SEED triage's third disposition (structural-depth W2): kept as
    # unwoven feedstock — no path, no beats, invisible to the weave and
    # every downstream context except POLISH finalize's texture material.
    # Branched/locked stay derived from topology (design doc 01 §4);
    # reserve needs a stored marker because zero explored paths is also
    # the pre-triage state.
    reserved: bool = False


class Answer(Node):
    """One of exactly two responses to a dilemma. No answer is marked
    default, primary, or canonical — answers are strictly equal."""

    text: str


class Path(Node):
    """One answer explored as a storyline (links: explores, has_consequence).
    An answer with no path is a shadow."""

    name: str = ""


class Consequence(Node):
    """A narrative outcome of a path, phrased as world state
    ("the cartographer knows the truth"), never as player action."""

    text: str
