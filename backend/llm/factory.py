"""Factory: instantiate the right LLM client from a LLMConfig."""

from __future__ import annotations

from .base import BaseLLMClient
from .config import LLMConfig


def get_llm_client(config: LLMConfig) -> BaseLLMClient:
    """Return a concrete BaseLLMClient for the given config.

    Args:
        config: LLMConfig specifying provider, model, API key, etc.

    Returns:
        A ready-to-use BaseLLMClient subclass.

    Raises:
        ValueError: if config.provider is not recognized.
    """
    match config.provider:
        case "openai":
            from .openai_client import OpenAIClient
            return OpenAIClient(config)
        case "anthropic":
            from .anthropic_client import AnthropicClient
            return AnthropicClient(config)
        case "gemini":
            from .gemini_client import GeminiClient
            return GeminiClient(config)
        case _:
            raise ValueError(
                f"Unknown LLM provider: '{config.provider}'. "
                f"Valid options: 'openai', 'anthropic', 'gemini'."
            )
