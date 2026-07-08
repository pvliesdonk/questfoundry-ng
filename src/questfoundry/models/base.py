"""Shared primitives: node/edge kinds, ids, provenance.

Node ids follow the ``kind:slug`` convention (``beat:keeper-lights-lamp``).
The kind prefix is a namespace, so ``character:mentor`` and
``location:mentor`` are distinct nodes.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

ID_RE = re.compile(r"^[a-z][a-z0-9_]*:[a-z0-9][a-z0-9-]*$")


class Stage(StrEnum):
    DREAM = "dream"
    BRAINSTORM = "brainstorm"
    SEED = "seed"
    GROW = "grow"
    POLISH = "polish"
    FILL = "fill"
    DRESS = "dress"
    SHIP = "ship"

    @property
    def order(self) -> int:
        return list(Stage).index(self)


class NodeKind(StrEnum):
    ENTITY = "entity"
    DILEMMA = "dilemma"
    ANSWER = "answer"
    PATH = "path"
    CONSEQUENCE = "consequence"
    BEAT = "beat"
    STATE_FLAG = "flag"
    INTERSECTION_GROUP = "intersection"
    PASSAGE = "passage"


class EdgeKind(StrEnum):
    # drama layer
    HAS_ANSWER = "has_answer"  # dilemma -> answer
    ANCHORED_TO = "anchored_to"  # dilemma -> entity
    EXPLORES = "explores"  # path -> answer
    HAS_CONSEQUENCE = "has_consequence"  # path -> consequence
    WRAPS = "wraps"  # dilemma -> dilemma
    SERIAL = "serial"  # dilemma -> dilemma (a resolves before b introduces)
    CONCURRENT = "concurrent"  # dilemma -> dilemma (symmetric, stored once)
    # structure layer
    BELONGS_TO = "belongs_to"  # beat -> path
    PREDECESSOR = "predecessor"  # beat -> beat (src comes before dst)
    IN_GROUP = "in_group"  # beat -> intersection group
    DERIVED_FROM = "derived_from"  # flag -> consequence
    # presentation layer
    GROUPED_IN = "grouped_in"  # beat -> passage
    CHOICE = "choice"  # passage -> passage (payload: Choice)
    VARIANT_OF = "variant_of"  # passage -> passage


class Node(BaseModel):
    """Base class for every graph node."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_by: Stage

    @field_validator("id")
    @classmethod
    def _well_formed_id(cls, v: str) -> str:
        if not ID_RE.match(v):
            raise ValueError(f"node id {v!r} must match 'kind:slug' ({ID_RE.pattern})")
        return v

    @property
    def kind_prefix(self) -> str:
        return self.id.split(":", 1)[0]


class Edge(BaseModel):
    """A typed edge. ``payload`` carries edge data (e.g. a Choice)."""

    model_config = ConfigDict(extra="forbid")

    kind: EdgeKind
    src: str
    dst: str
    payload: dict = {}

    def key(self) -> tuple[str, str, str]:
        return (self.kind.value, self.src, self.dst)
