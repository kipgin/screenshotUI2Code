"""AnthropicClient — STUB.

To implement:
    1. pip install anthropic
    2. Replace every `raise NotImplementedError` with real Anthropic SDK calls.
    3. Override `build_vision_message` — Anthropic uses a different format:
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}},
                {"type": "text", "text": "..."}
            ]
        }
    4. Register in factory.py: case "anthropic" → return AnthropicClient(config)

Reference implementation: openai_client.py
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from .base import BaseLLMClient
from .config import LLMConfig


class AnthropicClient(BaseLLMClient):
    """Stub implementation of BaseLLMClient for Anthropic Claude."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        # TODO: import anthropic; self._client = anthropic.AsyncAnthropic(api_key=config.api_key)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """TODO: implement using anthropic.AsyncAnthropic.messages.stream()"""
        raise NotImplementedError("AnthropicClient.stream_chat not yet implemented.")
        yield  # make this an async generator

    async def chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """TODO: implement using anthropic.AsyncAnthropic.messages.create()"""
        raise NotImplementedError("AnthropicClient.chat not yet implemented.")

    def count_tokens(self, text: str) -> int:
        """TODO: use anthropic.Anthropic().count_tokens(text) or heuristic."""
        return max(1, len(text) // 4)

    def build_vision_message(
        self,
        role: str,
        text: str,
        image_b64: str,
        media_type: str = "image/png",
    ) -> dict[str, Any]:
        """Anthropic vision format — different from the OpenAI default."""
        # TODO: verify with latest Anthropic SDK docs
        return {
            "role": role,
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_b64,
                    },
                },
                {"type": "text", "text": text},
            ],
        }
