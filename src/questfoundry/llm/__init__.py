"""The LLM adapter package (design doc 03 §5): one call pattern for
structured, schema-valid output, provider-agnostic. Used only by
`pipeline` (03 §2 dependency rule).
"""

from __future__ import annotations

from questfoundry.llm.adapter import AdapterError, LLMAdapter, LLMResult, ModelRole, Provider, Usage
from questfoundry.llm.providers import AnthropicProvider, MockProvider

__all__ = [
    "AdapterError",
    "AnthropicProvider",
    "LLMAdapter",
    "LLMResult",
    "MockProvider",
    "ModelRole",
    "Provider",
    "Usage",
]
