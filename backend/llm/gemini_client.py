"""GeminiClient — STUB.

To implement:
    1. pip install google-generativeai
    2. Replace every `raise NotImplementedError` with real Gemini SDK calls.
    3. Note: Gemini uses `google.generativeai.GenerativeModel.generate_content_async()`
       with `stream=True` for streaming.
    4. Override `build_vision_message` — Gemini uses PIL images or inline_data parts:
        [{"inline_data": {"mime_type": "image/png", "data": "<base64>"}}, "text here"]
       Wrap into the message dict as needed by the Gemini Python SDK.
    5. Register in factory.py: case "gemini" → return GeminiClient(config)

Reference implementation: openai_client.py
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from .base import BaseLLMClient
from .config import LLMConfig


class GeminiClient(BaseLLMClient):
    """Stub implementation of BaseLLMClient for Google Gemini."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        # TODO: import google.generativeai as genai
        #       genai.configure(api_key=config.api_key)
        #       self._model = genai.GenerativeModel(config.model)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """TODO: convert messages to Gemini format, call generate_content_async(stream=True)"""
        raise NotImplementedError("GeminiClient.stream_chat not yet implemented.")
        yield

    async def chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """TODO: convert messages to Gemini format, call generate_content_async()"""
        raise NotImplementedError("GeminiClient.chat not yet implemented.")

    def count_tokens(self, text: str) -> int:
        """TODO: use self._model.count_tokens(text).total_tokens"""
        return max(1, len(text) // 4)

    def build_vision_message(
        self,
        role: str,
        text: str,
        image_b64: str,
        media_type: str = "image/png",
    ) -> dict[str, Any]:
        """Gemini vision format — uses inline_data parts.
        NOTE: The exact structure depends on whether you use the low-level
        genai.types.Part API or the higher-level GenerativeModel interface.
        """
        # TODO: verify with latest google-generativeai SDK docs
        return {
            "role": role,
            "parts": [
                {"inline_data": {"mime_type": media_type, "data": image_b64}},
                {"text": text},
            ],
        }
