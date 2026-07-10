"""Gemini provider (design doc 03 §5) — a thin wrapper around the
google-genai SDK, mirroring the Anthropic provider's contract. The SDK
is imported lazily so the mock-only test path never needs it.

Thinking models (gemini-2.5+/3 families) spend part of the output budget
on thoughts; the adapter's schema retries handle any resulting truncation
the same way they handle invalid JSON. Thought tokens are billed as
output, so the ledger counts them there.
"""

from __future__ import annotations

import time

from questfoundry.llm.adapter import LLMResult, Usage

# Transport-level drops survive even streaming: a thinking model can go
# seconds-to-minutes between chunks and an idle-intolerant middlebox
# kills the quiet connection (live run 8, repeatedly). generate() is
# idempotent from the caller's side — nothing was applied — so a short
# bounded retry belongs here; whole-run resilience is M10's.
_TRANSPORT_RETRIES = 3
_BACKOFF_SECONDS = 2.0


class GeminiProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._client = None

    def _client_instance(self):
        if self._client is None:
            from google import genai

            # api_key=None lets the SDK read GEMINI_API_KEY / GOOGLE_API_KEY.
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def generate(self, *, system: str, prompt: str, model: str, max_tokens: int) -> LLMResult:
        import httpx
        from google.genai import errors

        # ServerError is the SDK's 5xx class (503 UNAVAILABLE killed live
        # run 8 after the transport retry landed) — as transient as a
        # dropped connection. ClientError (4xx) stays fatal: retrying a
        # bad request only re-bills it.
        last: Exception | None = None
        for attempt in range(_TRANSPORT_RETRIES + 1):
            if attempt:
                time.sleep(_BACKOFF_SECONDS * attempt)
            try:
                return self._generate_once(
                    system=system, prompt=prompt, model=model, max_tokens=max_tokens
                )
            except (httpx.TransportError, errors.ServerError) as e:
                last = e
        assert last is not None
        raise last

    def _generate_once(
        self, *, system: str, prompt: str, model: str, max_tokens: int
    ) -> LLMResult:
        from google.genai import types

        client = self._client_instance()
        # Stream and collect. A non-streaming call holds a silent HTTP
        # response for the whole generation — minutes on a thinking
        # writer call — and idle-intolerant middleboxes kill it
        # ("Server disconnected without sending a response", live run 8,
        # twice). Same contract as non-streaming otherwise; the last
        # chunk carries cumulative usage metadata. Mirrors the Anthropic
        # provider's streaming rationale (Sonnet evaluation, STATUS).
        parts: list[str] = []
        meta = None
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        ):
            if chunk.text:
                parts.append(chunk.text)
            if chunk.usage_metadata is not None:
                meta = chunk.usage_metadata
        usage = Usage(
            input_tokens=(meta.prompt_token_count or 0) if meta else 0,
            output_tokens=(
                (meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)
            )
            if meta
            else 0,
        )
        return LLMResult(text="".join(parts), model=model, usage=usage)
