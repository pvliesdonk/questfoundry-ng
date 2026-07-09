"""The LLM adapter (design doc 03 §5): one call pattern for structured,
schema-valid output. Providers are swappable; caching and the spend
ledger are cross-cutting and owned here, not by providers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from questfoundry.llm import cache, ledger

ModelRole = Literal["architect", "writer", "utility"]

M = TypeVar("M", bound=BaseModel)

_JSON_INSTRUCTION = (
    "Respond with ONLY a JSON object matching this JSON Schema "
    "(no prose, no markdown fences). Wherever a field refers to a node, "
    "use the full `kind:slug` id exactly as it appears above (for example "
    "`passage:p-arrival`, never `p-arrival` or a display name):"
)


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    usage: Usage
    cached: bool = False


class Provider(Protocol):
    def generate(self, *, system: str, prompt: str, model: str, max_tokens: int) -> LLMResult: ...


class AdapterError(Exception):
    """Raised when the model cannot produce schema-valid output after retries."""


def _loads(text: str):
    # strict=False accepts literal control characters (real newlines) inside
    # strings — models writing prose payloads emit these; the intent is
    # unambiguous and structural errors still raise.
    return json.loads(text, strict=False)


def _extract_json(text: str) -> str:
    """Parse `text` as JSON, tolerating a fenced block or surrounding prose.

    Tries a direct parse first; on failure, extracts the first balanced
    top-level ``{...}`` span (this naturally skips ```json fences and any
    leading/trailing prose without needing to special-case them).
    """
    stripped = text.strip()
    try:
        _loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start == -1:
        return stripped

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(stripped)):
        c = stripped[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : i + 1]
    return stripped[start:]


class LLMAdapter:
    def __init__(
        self,
        provider: Provider,
        model_map: dict[str, str],
        *,
        cache_dir: Path | None = None,
        ledger_path: Path | None = None,
        # Reasoning models (Anthropic adaptive thinking, gpt-5 family) spend
        # thinking tokens from this same budget before any text; 8192 starved
        # claude-sonnet-5 into empty responses. Unused budget costs nothing.
        max_tokens: int = 32768,
    ) -> None:
        self._provider = provider
        self._model_map = model_map
        self._cache_dir = cache_dir
        self._ledger_path = ledger_path
        self._max_tokens = max_tokens

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[M],
        role: str,
        max_retries: int = 1,
    ) -> M:
        try:
            model = self._model_map[role]
        except KeyError:
            raise AdapterError(
                f"unknown model role {role!r}; configured roles: {sorted(self._model_map)}"
            ) from None

        full_prompt = f"{prompt}\n\n{_JSON_INSTRUCTION}\n{json.dumps(schema.model_json_schema())}"

        key = None
        if self._cache_dir is not None:
            key = cache.compute_key(model, system, full_prompt, schema)
            cached_text = cache.get(self._cache_dir, key)
            if cached_text is not None:
                result = schema.model_validate(_loads(_extract_json(cached_text)))
                self._log(role, model, Usage(0, 0), cached=True, retries=0)
                return result

        last_error: Exception | None = None
        last_text = ""
        attempt_prompt = full_prompt
        for attempt in range(max_retries + 1):
            response = self._provider.generate(
                system=system, prompt=attempt_prompt, model=model, max_tokens=self._max_tokens
            )
            last_text = response.text
            try:
                parsed = _loads(_extract_json(response.text))
                result = schema.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                attempt_prompt = (
                    f"{full_prompt}\n\nYour previous response was invalid: {exc}. "
                    "Return ONLY corrected JSON."
                )
                continue

            if key is not None:
                cache.put(self._cache_dir, key, response.text)
            self._log(role, model, response.usage, cached=False, retries=attempt)
            return result

        snippet = last_text[:500]
        raise AdapterError(
            f"model failed to produce schema-valid output for role {role!r} "
            f"after {max_retries + 1} attempt(s): {last_error}; last response: {snippet!r}"
        )

    def _log(self, role: str, model: str, usage: Usage, *, cached: bool, retries: int) -> None:
        if self._ledger_path is None:
            return
        ledger.append(
            self._ledger_path,
            {
                "ts": datetime.now(UTC).isoformat(),
                "role": role,
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached": cached,
                "retries": retries,
            },
        )
