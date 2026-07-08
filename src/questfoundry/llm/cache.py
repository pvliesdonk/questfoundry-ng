"""Content-addressed file cache for LLM calls (design doc 03 §5).

Key = sha256(model \\x00 system \\x00 prompt \\x00 sorted-schema-json), first
24 hex chars. Only the adapter decides *when* to cache — this module is a
plain key/value store over JSON files, one per key.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

_KEY_LEN = 24


def compute_key(model: str, system: str, prompt: str, schema: type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), sort_keys=True)
    payload = "\x00".join([model, system, prompt, schema_json]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:_KEY_LEN]


def get(cache_dir: Path, key: str) -> str | None:
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["text"]


def put(cache_dir: Path, key: str, text: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    path.write_text(json.dumps({"text": text}), encoding="utf-8")
