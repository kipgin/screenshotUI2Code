"""
BaseLLMClient — the authoritative ABC for all LLM providers.

To add a new provider (e.g. Anthropic, Gemini), create a subclass and
implement every method marked with @abstractmethod. The docstrings below
describe the exact contract each method must fulfil.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any


class BaseLLMClient(ABC):
    """Abstract base class for LLM provider clients.

    Concrete subclasses:
        - OpenAIClient  (backend/llm/openai_client.py)  — fully implemented
        - AnthropicClient (backend/llm/anthropic_client.py)  — stub
        - GeminiClient  (backend/llm/gemini_client.py)  — stub
    """

    # ------------------------------------------------------------------
    # Core interface — MUST be implemented by every subclass
    # ------------------------------------------------------------------

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Yield text tokens one-by-one from the LLM stream.

        Args:
            messages: OpenAI-style message list, e.g.
                [{"role": "user", "content": "Hello"}]
                Vision messages may embed base64 images in the content list.
            **kwargs: Extra provider-specific overrides (temperature, max_tokens, …).

        Yields:
            str — the next text delta (may be an empty string; never None).

        Notes:
            - MUST respect ``self.config.stream = True`` implicitly.
            - The generator MUST close cleanly if the caller breaks early.
        """
        ...
        # satisfy the type checker; concrete methods must 'yield'
        yield  # type: ignore[misc]

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """Return the complete LLM response as a single string (non-streaming).

        Args:
            messages: Same format as ``stream_chat``.
            **kwargs: Extra provider-specific overrides.

        Returns:
            str — the full assistant reply.
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate the number of tokens in *text* for this provider/model.

        Args:
            text: Arbitrary string.

        Returns:
            int — token count estimate. Accuracy requirements:
                - Within ±10 % of the provider's actual count.
                - Must never raise; return 0 for empty input.
        """
        ...

    # ------------------------------------------------------------------
    # Shared helpers — available to all subclasses, no override needed
    # ------------------------------------------------------------------

    def build_text_message(self, role: str, content: str) -> dict[str, Any]:
        """Build a standard text-only message dict.

        Example:
            >>> client.build_text_message("user", "Hello")
            {"role": "user", "content": "Hello"}
        """
        return {"role": role, "content": content}

    def build_vision_message(
        self,
        role: str,
        text: str,
        image_b64: str,
        media_type: str = "image/png",
    ) -> dict[str, Any]:
        """Build a vision (multimodal) message dict in OpenAI vision format.

        Args:
            role:       Usually "user".
            text:       Text instruction accompanying the image.
            image_b64:  Base64-encoded image data (no data URI prefix).
            media_type: MIME type, e.g. "image/png", "image/jpeg".

        Returns:
            dict in OpenAI vision message format:
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "..."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
                ]
            }

        Notes:
            Subclasses that use a different vision format (e.g. Anthropic)
            should override this method.
        """
        return {
            "role": role,
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_b64}"
                    },
                },
            ],
        }

    def build_system_message(self, content: str) -> dict[str, Any]:
        """Build a system message dict."""
        return {"role": "system", "content": content}
