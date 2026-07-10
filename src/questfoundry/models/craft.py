"""Craft-corpus configuration (design doc 03 §10, mini-ADR A13): the
project.yaml `craft:` block that turns on the engine-side research pass.
Absent entirely, a project behaves exactly as it did before M6.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CraftConfig(BaseModel):
    """Points the research pass at a markdown vault and bounds its cost."""

    model_config = ConfigDict(extra="forbid")

    corpus: str  # root, absolute or project-relative
    folders: list[str] = []  # eligible subtrees; [] = whole corpus
    top_k: int = 4
    max_queries: int = 5  # librarian cap; exceeding it -> ApplyError
    words_per_query: int = 200
    search_mode: Literal["hybrid", "keyword"] = "hybrid"  # keyword = offline degradation
    embedding_model: str = "BAAI/bge-small-en-v1.5"
