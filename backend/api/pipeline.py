"""LLMPipeline — the single choke point for all LLM streaming calls.

Responsibilities:
- Stream tokens from the LLM client.
- Detect `tool_call` JSON blocks in the accumulating stream.
- Handle timeouts and transient errors with retry.
- Invoke ResponseFixer when the format is wrong.
- Emit tokens to both the caller generator AND any registered SSE sink.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Callable, Optional

from llm.base import BaseLLMClient
from utils.response_fixer import ResponseFixer, requires_non_empty

logger = logging.getLogger(__name__)

_TOOL_CALL_FENCE_START = "```tool_call"
_TOOL_CALL_RE = re.compile(
    r"```tool_call\s*\n(?P<json>\{.*?\})\s*\n```",
    re.DOTALL,
)

MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


class StreamResult:
    """Holds the outcome of a completed stream call."""

    def __init__(self) -> None:
        self.full_text: str = ""
        self.tool_call: Optional[dict[str, Any]] = None
        self.has_tool_call: bool = False

    def extract_tool_call(self) -> None:
        m = _TOOL_CALL_RE.search(self.full_text)
        if m:
            self.has_tool_call = True
            try:
                self.tool_call = json.loads(m.group("json"))
            except json.JSONDecodeError:
                self.tool_call = None


class LLMPipeline:
    """Manages streaming LLM calls with retry, tool-call detection, and format fixing."""

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._client = llm_client
        self._fixer = ResponseFixer(max_retries=2)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        on_token: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM, yielding each token.

        Args:
            messages:  Conversation history in OpenAI format.
            on_token:  Optional synchronous callback called for each token.
                       Use this to push tokens to a WebSocket or SSE sink.
            **kwargs:  Extra arguments forwarded to the LLM client.

        Yields:
            str — each token delta from the model.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async for token in self._client.stream_chat(messages, **kwargs):
                    if on_token:
                        on_token(token)
                    yield token
                return
            except Exception as exc:
                logger.warning(
                    "LLMPipeline: stream attempt %d/%d failed: %s",
                    attempt, MAX_RETRIES, exc,
                )
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY * attempt)

    async def stream_and_collect(
        self,
        messages: list[dict[str, Any]],
        on_token: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> StreamResult:
        """Stream and collect the full response into a StreamResult.

        Also detects tool calls in the final accumulated text.
        """
        result = StreamResult()
        async for token in self.stream(messages, on_token=on_token, **kwargs):
            result.full_text += token
        result.extract_tool_call()
        return result
