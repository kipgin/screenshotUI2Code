"""OpenAIClient — fully implemented LLM client for OpenAI and any
OpenAI-compatible endpoint (including the local OpenVINO server).

Usage:
    config = LLMConfig(
        provider="openai",
        model="qwen2.5-coder-ov",
        base_url="http://localhost:8000/v1",
        api_key="local-gpu",
    )
    client = OpenAIClient(config)

    # Streaming
    async for token in client.stream_chat(messages):
        print(token, end="", flush=True)

    # Non-streaming
    response = await client.chat(messages)
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI, APIError

from .base import BaseLLMClient
from .config import LLMConfig


class OpenAIClient(BaseLLMClient):
    """Concrete LLM client for OpenAI and OpenAI-compatible endpoints.

    This is the reference implementation. When adding Anthropic or Gemini:
        1. Create AnthropicClient(BaseLLMClient) / GeminiClient(BaseLLMClient)
        2. Implement stream_chat, chat, count_tokens following the same structure
        3. Register in factory.py
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,       # None → uses OpenAI default
            timeout=config.timeout,
        )

    # ------------------------------------------------------------------
    # Core interface implementation
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the model one-by-one.

        Yields empty strings when a chunk carries no content delta
        (e.g. role-only chunks). Callers may safely ignore them.
        """
        params = self._build_params(messages, stream=True, **kwargs)
        try:
            stream = await self._client.chat.completions.create(**params)
            async for chunk in stream:
                delta = chunk.choices[0].delta
                yield delta.content or ""
        except APIError as exc:
            raise RuntimeError(f"OpenAI stream error: {exc}") from exc

    async def chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """Return the full response as a single string."""
        params = self._build_params(messages, stream=False, **kwargs)
        try:
            response = await self._client.chat.completions.create(**params)
            return response.choices[0].message.content or ""
        except APIError as exc:
            raise RuntimeError(f"OpenAI chat error: {exc}") from exc

    def count_tokens(self, text: str) -> int:
        """Estimate token count using a ~4 chars/token heuristic.

        The openai package's tiktoken is optional; if unavailable we fall
        back to the heuristic which is accurate to within ±10 % for English.
        """
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.config.model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback: 1 token ≈ 4 characters
            return max(1, len(text) // 4)

    # ------------------------------------------------------------------
    # Vision-message override (OpenAI format is the default in base)
    # ------------------------------------------------------------------
    # build_vision_message is inherited unchanged from BaseLLMClient —
    # OpenAI's vision format is the canonical one.

    # ------------------------------------------------------------------
    # Tool-call response parsing
    # ------------------------------------------------------------------

    def extract_tool_calls(self, chunk_or_message: Any) -> list[dict[str, Any]]:
        """Parse OpenAI tool-call fields from a response chunk or message.

        Returns a (possibly empty) list of tool call dicts:
            [{"id": ..., "name": ..., "arguments": {...}}, ...]
        """
        tool_calls = []
        raw = getattr(chunk_or_message, "tool_calls", None)
        if raw:
            for tc in raw:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
        return tool_calls

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_params(
        self,
        messages: list[dict[str, Any]],
        stream: bool,
        **overrides: Any,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": overrides.pop("temperature", self.config.temperature),
            "max_tokens": overrides.pop("max_tokens", self.config.max_tokens),
            "stream": stream,
        }
        params.update(overrides)
        return params
