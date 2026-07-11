"""Tests for the Ollama provider: schema-to-format pass-through, option
mapping, streaming collection, the format-rejection fallback, and the
context-overflow guard. The `ollama` SDK is faked in sys.modules — no
network, no dependency on the real package.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from questfoundry.llm.providers.ollama import OllamaContextError, OllamaProvider


class FakeResponseError(Exception):
    def __init__(self, error: str, status_code: int = -1) -> None:
        super().__init__(error)
        self.error = error
        self.status_code = status_code


def _chunk(content: str | None = None, prompt_eval: int | None = None, evaled: int | None = None):
    return SimpleNamespace(
        message=SimpleNamespace(content=content),
        prompt_eval_count=prompt_eval,
        eval_count=evaled,
    )


class FakeClient:
    def __init__(self, chunks=None, errors=None, **kwargs) -> None:
        self.init_kwargs = kwargs
        self.chat_calls: list[dict] = []
        self._chunks = chunks or []
        self._errors = list(errors or [])

    def chat(self, **kwargs):
        self.chat_calls.append(kwargs)
        if self._errors:
            raise self._errors.pop(0)
        return iter(self._chunks)


@pytest.fixture
def fake_ollama(monkeypatch):
    """Install a fake `ollama` module; returns it so tests can attach a
    client factory."""
    mod = types.ModuleType("ollama")
    mod.ResponseError = FakeResponseError
    monkeypatch.setitem(sys.modules, "ollama", mod)
    return mod


def _install_client(fake_ollama, client: FakeClient):
    def factory(**kwargs):
        client.init_kwargs = kwargs
        return client

    fake_ollama.Client = factory
    return client


SCHEMA = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}


def test_streams_collects_and_passes_format(fake_ollama) -> None:
    client = _install_client(
        fake_ollama,
        FakeClient(
            chunks=[
                _chunk('{"x": '),
                _chunk('"y"}'),
                _chunk(None, prompt_eval=120, evaled=8),
            ]
        ),
    )
    provider = OllamaProvider(num_ctx=4096, temperature=0.7, keep_alive="10m", think=False)

    result = provider.generate(
        system="sys", prompt="do it", model="qwen3.5:test", max_tokens=256, schema=SCHEMA
    )

    assert result.text == '{"x": "y"}'
    assert result.usage.input_tokens == 120
    assert result.usage.output_tokens == 8
    call = client.chat_calls[0]
    assert call["format"] == SCHEMA
    assert call["options"] == {"num_ctx": 4096, "num_predict": 256, "temperature": 0.7}
    assert call["keep_alive"] == "10m"
    assert call["think"] is False
    assert call["stream"] is True
    assert call["messages"][0] == {"role": "system", "content": "sys"}


def test_no_schema_means_no_format_and_no_optional_options(fake_ollama) -> None:
    client = _install_client(
        fake_ollama, FakeClient(chunks=[_chunk("hi", prompt_eval=5, evaled=1)])
    )
    provider = OllamaProvider(num_ctx=4096)

    provider.generate(system="s", prompt="p", model="m", max_tokens=64)

    call = client.chat_calls[0]
    assert call["format"] is None
    assert "temperature" not in call["options"]
    assert call["keep_alive"] is None
    assert call["think"] is None


def test_format_rejection_falls_back_once_without_format(fake_ollama) -> None:
    """A host that rejects `format` (rather than ignoring it, as Ollama
    cloud is documented to) gets one unconstrained retry — the
    prompt-embedded schema still carries the contract."""
    client = _install_client(
        fake_ollama,
        FakeClient(
            chunks=[_chunk('{"x": "y"}', prompt_eval=10, evaled=4)],
            errors=[FakeResponseError("format is not supported", 400)],
        ),
    )
    provider = OllamaProvider(num_ctx=4096)

    result = provider.generate(system="s", prompt="p", model="m", max_tokens=64, schema=SCHEMA)

    assert result.text == '{"x": "y"}'
    assert len(client.chat_calls) == 2
    assert client.chat_calls[0]["format"] == SCHEMA
    assert client.chat_calls[1]["format"] is None


def test_unrelated_error_propagates_without_retry(fake_ollama) -> None:
    client = _install_client(
        fake_ollama,
        FakeClient(errors=[FakeResponseError("model 'nope' not found", 404)]),
    )
    provider = OllamaProvider(num_ctx=4096)

    with pytest.raises(FakeResponseError, match="not found"):
        provider.generate(system="s", prompt="p", model="nope", max_tokens=64, schema=SCHEMA)

    assert len(client.chat_calls) == 1


def test_prompt_near_context_limit_fails_loud(fake_ollama) -> None:
    """Ollama truncates an oversized prompt silently; a prompt_eval_count
    at the window is the tell, and trusting that output would be the
    quiet-wrong failure mode."""
    client = _install_client(
        fake_ollama,
        FakeClient(chunks=[_chunk("text", prompt_eval=4090, evaled=3)]),
    )
    provider = OllamaProvider(num_ctx=4096)

    with pytest.raises(OllamaContextError, match="num_ctx"):
        provider.generate(system="s", prompt="p" * 100, model="m", max_tokens=64)

    assert len(client.chat_calls) == 1


def test_api_key_becomes_bearer_header(fake_ollama, monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "sk-test")
    client = _install_client(
        fake_ollama, FakeClient(chunks=[_chunk("ok", prompt_eval=2, evaled=1)])
    )
    provider = OllamaProvider(host="https://ollama.com", num_ctx=4096)

    provider.generate(system="s", prompt="p", model="glm-5.2:cloud", max_tokens=64)

    assert client.init_kwargs["host"] == "https://ollama.com"
    assert client.init_kwargs["headers"] == {"Authorization": "Bearer sk-test"}


def test_no_api_key_no_headers(fake_ollama, monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    client = _install_client(
        fake_ollama, FakeClient(chunks=[_chunk("ok", prompt_eval=2, evaled=1)])
    )
    provider = OllamaProvider(num_ctx=4096)

    provider.generate(system="s", prompt="p", model="m", max_tokens=64)

    assert client.init_kwargs["host"] is None
    assert client.init_kwargs["headers"] is None
