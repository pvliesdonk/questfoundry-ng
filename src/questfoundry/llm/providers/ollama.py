"""Ollama provider (design doc 03 §5) — local and Ollama-cloud models
over the `ollama` SDK, mirroring the other providers' contract. The SDK
is imported lazily so the mock-only test path never needs it.

This is the one provider that consumes the adapter's schema pass-through:
`format` turns on grammar-constrained decoding, which makes small local
models emit schema-shaped JSON they could not reliably produce free-form.
Acceptance stays the adapter's Pydantic validation either way — the
grammar is a pre-filter, never the contract (mini-ADR A20).

Context is the local-model trap: Ollama *truncates* a prompt that
exceeds the window instead of erroring, and the window is a hardware
budget the author may have turned down to fit VRAM. The provider owns
`num_ctx` explicitly and fails loud when a call lands near the limit.
"""

from __future__ import annotations

import os

from questfoundry.llm.adapter import LLMResult, Usage

# A prompt evaluated to within this margin of num_ctx was almost
# certainly truncated (Ollama clamps silently server-side) — and even a
# legitimately near-full window leaves no room for output. Detection is
# post-hoc and best-effort: a server-side KV-cache hit lowers
# prompt_eval_count, which can mask truncation on repeat calls, so the
# common first call is the one this reliably catches.
_CTX_MARGIN = 256

_DEFAULT_NUM_CTX = 32768
_TIMEOUT_SECONDS = 600.0  # read timeout between stream chunks; model load is slow


class OllamaContextError(Exception):
    """The prompt (nearly) filled the context window — the model saw a
    truncated prompt and its output cannot be trusted."""


class OllamaProvider:
    def __init__(
        self,
        host: str | None = None,
        *,
        num_ctx: int = _DEFAULT_NUM_CTX,
        temperature: float | None = None,
        keep_alive: str | int | None = None,
        think: bool | str | None = None,
        api_key: str | None = None,
    ) -> None:
        # host=None lets the SDK read OLLAMA_HOST (default localhost);
        # set https://ollama.com to hit cloud models without a local daemon.
        self._host = host
        self._num_ctx = num_ctx
        self._temperature = temperature
        self._keep_alive = keep_alive
        # None sends no think config: the model's own default applies.
        # Thinking (when on) streams separately from content, so it never
        # pollutes the JSON payload.
        self._think = think
        self._api_key = api_key
        self._client = None

    def _client_instance(self):
        if self._client is None:
            import ollama

            key = self._api_key or os.environ.get("OLLAMA_API_KEY")
            headers = {"Authorization": f"Bearer {key}"} if key else None
            self._client = ollama.Client(
                host=self._host, headers=headers, timeout=_TIMEOUT_SECONDS
            )
        return self._client

    def generate(
        self, *, system: str, prompt: str, model: str, max_tokens: int, schema: dict | None = None
    ) -> LLMResult:
        import ollama

        try:
            return self._generate_once(
                system=system, prompt=prompt, model=model, max_tokens=max_tokens, schema=schema
            )
        except ollama.ResponseError as e:
            # Ollama's cloud tier documents no structured-output support and
            # is expected to *ignore* `format`; if a host instead rejects
            # it, degrade once to unconstrained — the prompt-embedded
            # schema + adapter validation still enforce the contract.
            # Anything else (bad model name, auth) re-raises untouched.
            rejected_format = (
                schema is not None
                and 400 <= getattr(e, "status_code", 0) < 500
                and "format" in str(getattr(e, "error", e)).lower()
            )
            if not rejected_format:
                raise
            return self._generate_once(
                system=system, prompt=prompt, model=model, max_tokens=max_tokens, schema=None
            )

    def _generate_once(
        self, *, system: str, prompt: str, model: str, max_tokens: int, schema: dict | None
    ) -> LLMResult:
        client = self._client_instance()
        options: dict = {"num_ctx": self._num_ctx, "num_predict": max_tokens}
        if self._temperature is not None:
            options["temperature"] = self._temperature
        # Stream and collect, like the Anthropic/Gemini providers: a
        # direct-to-cloud call holds a silent connection for minutes
        # otherwise, and locally the chunks are free progress signal.
        parts: list[str] = []
        prompt_eval = 0
        eval_count = 0
        for chunk in client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            format=schema,
            options=options,
            keep_alive=self._keep_alive,
            think=self._think,
            stream=True,
        ):
            content = chunk.message.content if chunk.message else None
            if content:
                parts.append(content)
            if getattr(chunk, "prompt_eval_count", None):
                prompt_eval = chunk.prompt_eval_count
            if getattr(chunk, "eval_count", None):
                eval_count = chunk.eval_count
        if prompt_eval >= self._num_ctx - _CTX_MARGIN:
            raise OllamaContextError(
                f"prompt evaluated at {prompt_eval} tokens against a {self._num_ctx}-token "
                f"window (model {model!r}) — Ollama truncates silently, so this output is "
                "untrustworthy. Raise llm.num_ctx in project.yaml (and check it fits VRAM)."
            )
        return LLMResult(
            text="".join(parts),
            model=model,
            usage=Usage(input_tokens=prompt_eval, output_tokens=eval_count),
        )
