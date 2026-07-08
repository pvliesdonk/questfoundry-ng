"""Deterministic fixture-backed provider (design doc 03 §5) for tests and
offline development. In replay mode it plays back recorded calls in
order; in record mode it delegates to a live provider and writes each
response as the next fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

from questfoundry.llm.adapter import LLMResult, Provider, Usage


class MockProviderError(Exception):
    """Raised when replay fixtures are exhausted or missing."""


class MockProvider:
    def __init__(self, fixtures_dir: Path, record_with: Provider | None = None) -> None:
        self._fixtures_dir = fixtures_dir
        self._record_with = record_with
        self._cursor = 0

    def generate(self, *, system: str, prompt: str, model: str, max_tokens: int) -> LLMResult:
        if self._record_with is not None:
            return self._record(system=system, prompt=prompt, model=model, max_tokens=max_tokens)
        return self._replay(model)

    def _record(self, *, system: str, prompt: str, model: str, max_tokens: int) -> LLMResult:
        result = self._record_with.generate(
            system=system, prompt=prompt, model=model, max_tokens=max_tokens
        )
        calls_dir = self._fixtures_dir / "calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        path = calls_dir / f"{self._cursor:03d}.json"
        path.write_text(json.dumps({"text": result.text}), encoding="utf-8")
        self._cursor += 1
        return result

    def _replay(self, model: str) -> LLMResult:
        calls_dir = self._fixtures_dir / "calls"
        path = calls_dir / f"{self._cursor:03d}.json"
        if not path.exists():
            available = (
                sorted(p.name for p in calls_dir.glob("*.json")) if calls_dir.is_dir() else []
            )
            raise MockProviderError(
                f"MockProvider exhausted: made {self._cursor} call(s) against "
                f"{calls_dir}, no fixture at {path.name}; available fixtures: {available}"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        self._cursor += 1
        return LLMResult(text=data["text"], model=model, usage=Usage(0, 0))
