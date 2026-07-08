"""Append-only JSONL spend ledger (design doc 03 §5).

One line per `LLMAdapter.complete()` call, cache hits included (with
zero token cost). `qf status` reads this to show spend against budget.
"""

from __future__ import annotations

import json
from pathlib import Path


def append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
