"""OpenAI provider (design doc 03 §5) — a thin wrapper around the Chat
Completions API, mirroring the Anthropic provider's contract. The SDK is
imported lazily so the mock-only test path never needs it.

Reasoning models (gpt-5 family) take `max_completion_tokens` and spend
part of that budget on reasoning; the adapter's schema retries handle
any resulting truncation the same way they handle invalid JSON.
"""

from __future__ import annotations

from questfoundry.llm.adapter import LLMResult, Usage


class OpenAIProvider:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._client = None

    def _client_instance(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def generate(self, *, system: str, prompt: str, model: str, max_tokens: int) -> LLMResult:
        client = self._client_instance()
        response = client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        usage = Usage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        return LLMResult(
            text=response.choices[0].message.content or "", model=model, usage=usage
        )
