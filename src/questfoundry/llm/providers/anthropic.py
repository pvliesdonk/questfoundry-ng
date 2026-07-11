"""Anthropic provider (design doc 03 §5) — a thin wrapper around the
Messages API. No retry logic here: the SDK's own transport retries
handle 429/5xx, and the adapter owns retries for schema validity.

The `anthropic` SDK is imported lazily so that importing
`questfoundry.llm` never requires it at runtime for tests running
against the mock provider.
"""

from __future__ import annotations

from questfoundry.llm.adapter import LLMResult, Usage


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, thinking: str | None = None) -> None:
        self._api_key = api_key
        # "disabled" | "adaptive" | None. Models with thinking on by default
        # (Sonnet 5+) spend billed thinking tokens on every call; "disabled"
        # opts out. None sends no config: the model's own default applies.
        self._thinking = thinking
        self._client = None

    def _client_instance(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(
        self, *, system: str, prompt: str, model: str, max_tokens: int, schema: dict | None = None
    ) -> LLMResult:
        # `schema` deliberately unused: the API's native structured output
        # is documented incompatible with streaming (required here, see
        # below) and with extended thinking. The prompt-embedded schema +
        # adapter validation carry the contract.
        client = self._client_instance()
        # The SDK rejects non-streaming requests whose max_tokens implies a
        # >10-minute worst case; stream and collect the final message instead.
        extra = {"thinking": {"type": self._thinking}} if self._thinking else {}
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            **extra,
        ) as stream:
            response = stream.get_final_message()
        text = next((block.text for block in response.content if block.type == "text"), "")
        usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return LLMResult(text=text, model=model, usage=usage)
