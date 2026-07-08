"""Gemini provider (design doc 03 §5) — a thin wrapper around the
google-genai SDK, mirroring the Anthropic provider's contract. The SDK
is imported lazily so the mock-only test path never needs it.

Thinking models (gemini-2.5+/3 families) spend part of the output budget
on thoughts; the adapter's schema retries handle any resulting truncation
the same way they handle invalid JSON. Thought tokens are billed as
output, so the ledger counts them there.
"""

from __future__ import annotations

from questfoundry.llm.adapter import LLMResult, Usage


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
        from google.genai import types

        client = self._client_instance()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        )
        meta = response.usage_metadata
        usage = Usage(
            input_tokens=(meta.prompt_token_count or 0) if meta else 0,
            output_tokens=(
                (meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)
            )
            if meta
            else 0,
        )
        return LLMResult(text=response.text or "", model=model, usage=usage)
