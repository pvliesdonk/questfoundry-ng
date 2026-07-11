"""Tests for the LLM adapter: schema validation, retry/repair, caching,
the spend ledger, and the mock provider's replay/record modes. No
network access and no `anthropic` SDK usage — everything runs against a
fake in-process provider or `MockProvider`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from questfoundry.llm import AdapterError, LLMAdapter, LLMResult, MockProvider, Usage
from questfoundry.llm import ledger as ledger_mod
from questfoundry.llm.providers.mock import MockProviderError


class Answer(BaseModel):
    value: str
    count: int


class FakeProvider:
    """Returns queued responses in call order; records every call it saw."""

    def __init__(self, responses: list[LLMResult]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def generate(
        self, *, system: str, prompt: str, model: str, max_tokens: int, schema: dict | None = None
    ) -> LLMResult:
        idx = len(self.calls)
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "model": model,
                "max_tokens": max_tokens,
                "schema": schema,
            }
        )
        return self._responses[idx]


MODEL_MAP = {"architect": "model-a", "writer": "model-w", "utility": "model-u"}


def test_happy_path(tmp_path: Path) -> None:
    provider = FakeProvider(
        [
            LLMResult(
                text=json.dumps({"value": "x", "count": 1}), model="model-u", usage=Usage(10, 5)
            )
        ]
    )
    ledger_path = tmp_path / "ledger.jsonl"
    adapter = LLMAdapter(provider, MODEL_MAP, ledger_path=ledger_path)

    result = adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility")

    assert result == Answer(value="x", count=1)
    entries = ledger_mod.read(ledger_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["role"] == "utility"
    assert entry["model"] == "model-u"
    assert entry["input_tokens"] == 10
    assert entry["output_tokens"] == 5
    assert entry["cached"] is False
    assert entry["retries"] == 0
    assert "ts" in entry


def test_schema_offered_to_provider() -> None:
    """The provider is offered the same JSON Schema the prompt embeds —
    one derivation, two channels (constrained decoding is provider-local)."""
    provider = FakeProvider(
        [
            LLMResult(
                text=json.dumps({"value": "x", "count": 1}), model="model-u", usage=Usage(1, 1)
            )
        ]
    )
    adapter = LLMAdapter(provider, MODEL_MAP)

    adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility")

    assert provider.calls[0]["schema"] == Answer.model_json_schema()
    assert json.dumps(Answer.model_json_schema()) in provider.calls[0]["prompt"]


def test_validation_retry_feedback_names_field_and_value(tmp_path: Path) -> None:
    """Schema-invalid (but parseable) output retries with a correction
    brief: the failing field path, what was wrong, and the value seen —
    not a raw exception dump."""
    provider = FakeProvider(
        [
            LLMResult(
                text=json.dumps({"value": "x", "count": "not-a-number"}),
                model="model-u",
                usage=Usage(1, 1),
            ),
            LLMResult(
                text=json.dumps({"value": "x", "count": 2}), model="model-u", usage=Usage(1, 1)
            ),
        ]
    )
    adapter = LLMAdapter(provider, MODEL_MAP)

    result = adapter.complete(
        system="sys", prompt="do it", schema=Answer, role="utility", max_retries=1
    )

    assert result == Answer(value="x", count=2)
    retry_prompt = provider.calls[1]["prompt"]
    assert "Your previous response was invalid" in retry_prompt
    assert "`count`" in retry_prompt
    assert "'not-a-number'" in retry_prompt
    assert "Return ONLY corrected JSON" in retry_prompt


def test_retry_then_succeed(tmp_path: Path) -> None:
    provider = FakeProvider(
        [
            LLMResult(text="not json at all", model="model-u", usage=Usage(1, 1)),
            LLMResult(
                text=json.dumps({"value": "y", "count": 2}), model="model-u", usage=Usage(2, 2)
            ),
        ]
    )
    ledger_path = tmp_path / "ledger.jsonl"
    adapter = LLMAdapter(provider, MODEL_MAP, ledger_path=ledger_path)

    result = adapter.complete(
        system="sys", prompt="do it", schema=Answer, role="utility", max_retries=1
    )

    assert result == Answer(value="y", count=2)
    assert len(provider.calls) == 2
    assert "Your previous response was invalid" in provider.calls[1]["prompt"]
    assert "Return ONLY corrected JSON" in provider.calls[1]["prompt"]

    entries = ledger_mod.read(ledger_path)
    assert len(entries) == 1
    assert entries[0]["retries"] == 1


def test_retries_exhausted_raises(tmp_path: Path) -> None:
    provider = FakeProvider(
        [
            LLMResult(text="nope", model="model-u", usage=Usage(1, 1)),
            LLMResult(text="still nope", model="model-u", usage=Usage(1, 1)),
        ]
    )
    adapter = LLMAdapter(provider, MODEL_MAP)

    with pytest.raises(AdapterError):
        adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility", max_retries=1)

    assert len(provider.calls) == 2


def test_fenced_prose_wrapped_json_is_parsed() -> None:
    payload = json.dumps({"value": "z", "count": 3})
    text = f"Sure, here you go:\n```json\n{payload}\n```\nLet me know if you need more."
    provider = FakeProvider([LLMResult(text=text, model="model-u", usage=Usage(1, 1))])
    adapter = LLMAdapter(provider, MODEL_MAP)

    result = adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility")

    assert result == Answer(value="z", count=3)


def test_literal_newlines_inside_strings_are_parsed() -> None:
    """Prose-writing models emit real newlines inside JSON strings (first
    thinking-off Sonnet 5 FILL call, 2026-07-09); strict JSON rejects the
    control character but the intent is unambiguous."""
    text = '{"value": "line one\nline two", "count": 3}'
    provider = FakeProvider([LLMResult(text=text, model="model-u", usage=Usage(1, 1))])
    adapter = LLMAdapter(provider, MODEL_MAP)

    result = adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility")

    assert result == Answer(value="line one\nline two", count=3)
    assert len(provider.calls) == 1  # parsed first try, no retry burned


def test_cache_hit_skips_provider_and_is_free(tmp_path: Path) -> None:
    provider = FakeProvider(
        [
            LLMResult(
                text=json.dumps({"value": "cached", "count": 9}),
                model="model-u",
                usage=Usage(5, 5),
            )
        ]
    )
    cache_dir = tmp_path / "cache"
    ledger_path = tmp_path / "ledger.jsonl"
    adapter = LLMAdapter(provider, MODEL_MAP, cache_dir=cache_dir, ledger_path=ledger_path)

    first = adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility")
    second = adapter.complete(system="sys", prompt="do it", schema=Answer, role="utility")

    assert first == second == Answer(value="cached", count=9)
    assert len(provider.calls) == 1  # second call was a cache hit

    entries = ledger_mod.read(ledger_path)
    assert len(entries) == 2
    assert entries[0]["cached"] is False
    assert entries[1]["cached"] is True
    assert entries[1]["input_tokens"] == 0
    assert entries[1]["output_tokens"] == 0


def test_unknown_role_raises_adapter_error() -> None:
    provider = FakeProvider([])
    adapter = LLMAdapter(provider, MODEL_MAP)

    with pytest.raises(AdapterError):
        adapter.complete(system="sys", prompt="do it", schema=Answer, role="nonexistent")

    assert provider.calls == []


def test_mock_provider_replay_in_order_then_exhausts(tmp_path: Path) -> None:
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir(parents=True)
    (calls_dir / "000.json").write_text(json.dumps({"text": "first"}), encoding="utf-8")
    (calls_dir / "001.json").write_text(json.dumps({"text": "second"}), encoding="utf-8")

    provider = MockProvider(tmp_path)

    first = provider.generate(system="s", prompt="p", model="m", max_tokens=10)
    second = provider.generate(system="s", prompt="p", model="m", max_tokens=10)

    assert first.text == "first"
    assert first.model == "m"
    assert first.usage == Usage(0, 0)
    assert second.text == "second"

    with pytest.raises(MockProviderError):
        provider.generate(system="s", prompt="p", model="m", max_tokens=10)


def test_mock_provider_replay_missing_fixtures_dir(tmp_path: Path) -> None:
    provider = MockProvider(tmp_path / "does-not-exist")

    with pytest.raises(MockProviderError):
        provider.generate(system="s", prompt="p", model="m", max_tokens=10)


def test_mock_provider_record_writes_fixture_and_round_trips(tmp_path: Path) -> None:
    inner = FakeProvider([LLMResult(text="recorded", model="model-u", usage=Usage(3, 4))])
    provider = MockProvider(tmp_path, record_with=inner)

    result = provider.generate(system="s", prompt="p", model="model-u", max_tokens=10)

    assert result.text == "recorded"
    assert result.usage == Usage(3, 4)
    written_path = tmp_path / "calls" / "000.json"
    assert written_path.exists()
    assert json.loads(written_path.read_text(encoding="utf-8")) == {"text": "recorded"}

    # A second recorded call gets the next sequential filename.
    inner._responses.append(LLMResult(text="second", model="model-u", usage=Usage(1, 1)))
    provider.generate(system="s", prompt="p2", model="model-u", max_tokens=10)
    assert (tmp_path / "calls" / "001.json").exists()
