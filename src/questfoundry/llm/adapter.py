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
    # `schema` is the proposal's JSON Schema, offered so a provider can
    # enforce it natively (constrained decoding). Providers are free to
    # ignore it — acceptance is always the adapter's Pydantic validation,
    # so enforcement differs per provider but the contract never does.
    def generate(
        self, *, system: str, prompt: str, model: str, max_tokens: int, schema: dict | None = None
    ) -> LLMResult: ...


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


def _repair_feedback(exc: Exception) -> str:
    """Render a failed attempt as a correction brief: what went wrong,
    where, and what was expected — never a raw exception dump. Only the
    retry path sees this, so it costs nothing when the first attempt is
    valid; weaker models need the specifics to actually correct."""
    if isinstance(exc, ValidationError):
        errors = exc.errors()
        lines = []
        for err in errors[:12]:
            loc = ".".join(str(p) for p in err["loc"]) or "<root>"
            got = repr(err.get("input"))
            if len(got) > 120:
                got = got[:120] + "…"
            lines.append(f"- at `{loc}`: {err['msg']} (got: {got})")
        if len(errors) > 12:
            lines.append(f"- …and {len(errors) - 12} more problem(s) like the above")
        return (
            "Your previous response was invalid JSON for the schema. Problems found:\n"
            + "\n".join(lines)
            + "\nKeep the same content, corrected so every listed field satisfies the "
            "JSON Schema above (exact field names, types, and required fields). "
            "Return ONLY corrected JSON."
        )
    if isinstance(exc, json.JSONDecodeError):
        start = max(exc.pos - 60, 0)
        snippet = exc.doc[start : exc.pos + 60]
        return (
            "Your previous response was invalid: not parseable as JSON. "
            f"Parse error at line {exc.lineno} column {exc.colno}: {exc.msg}, near:\n"
            f"…{snippet}…\n"
            "Expected one JSON object matching the schema above — no prose, no markdown "
            "fences. Return ONLY corrected JSON."
        )
    return f"Your previous response was invalid: {exc}. Return ONLY corrected JSON."


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

        # One derivation serves both channels: embedded in the prompt (the
        # id contract rides along; grounds every provider) and offered to
        # the provider for native enforcement. There is no second schema.
        schema_dict = schema.model_json_schema()
        full_prompt = f"{prompt}\n\n{_JSON_INSTRUCTION}\n{json.dumps(schema_dict)}"

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
                system=system,
                prompt=attempt_prompt,
                model=model,
                max_tokens=self._max_tokens,
                schema=schema_dict,
            )
            last_text = response.text
            try:
                parsed = _loads(_extract_json(response.text))
                result = schema.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                attempt_prompt = f"{full_prompt}\n\n{_repair_feedback(exc)}"
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
