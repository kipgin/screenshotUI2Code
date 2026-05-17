"""ResponseFixer — detect bad-format LLM responses and request a correction.

When the agent receives a response that doesn't match the expected format
(e.g. a tool call block is malformed, or no code block was generated when
one was required), ResponseFixer sends a correction prompt and retries
before the response is added to conversation history.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class FormatError(Exception):
    """Raised when a response fails a format check."""


class ResponseFixer:
    """Validate and auto-correct LLM responses before they enter history.

    Usage:
        fixer = ResponseFixer(max_retries=2)

        async def check(text: str) -> bool:
            return "```html" in text

        corrected = await fixer.fix(
            response=raw_text,
            check_fn=check,
            correction_prompt="You forgot to wrap the HTML in a code block.",
            llm_client=client,
            messages=messages,
        )

    The fixer will:
        1. Run ``check_fn(response)``.
        2. If it fails, append a correction message and call the LLM again.
        3. Retry up to ``max_retries`` times.
        4. If all retries fail, return the last response with a warning logged.
    """

    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    async def fix(
        self,
        response: str,
        check_fn: Callable[[str], bool],
        correction_prompt: str,
        llm_client: Any,          # BaseLLMClient — avoid circular import
        messages: list[dict[str, Any]],
        **llm_kwargs: Any,
    ) -> str:
        """Return a validated (and possibly corrected) response.

        Args:
            response:          The initial LLM response to validate.
            check_fn:          Function that returns True if format is correct.
            correction_prompt: Message to send to the LLM asking it to fix its output.
            llm_client:        Any BaseLLMClient subclass.
            messages:          Current conversation history (will not be mutated).
            **llm_kwargs:      Passed through to llm_client.chat().

        Returns:
            The validated response string.
        """
        current = response
        history = list(messages)  # shallow copy — do not mutate caller's list

        for attempt in range(self.max_retries + 1):
            if check_fn(current):
                return current

            if attempt == self.max_retries:
                logger.warning(
                    "ResponseFixer: all %d retries exhausted. Returning last response.",
                    self.max_retries,
                )
                return current

            logger.info(
                "ResponseFixer: attempt %d/%d — format check failed, requesting correction.",
                attempt + 1,
                self.max_retries,
            )
            history.append({"role": "assistant", "content": current})
            history.append({"role": "user", "content": correction_prompt})
            current = await llm_client.chat(history, **llm_kwargs)

        return current  # unreachable but satisfies type checkers


# ── Reusable format checkers ──────────────────────────────────────────────────

def requires_code_block(lang: str) -> Callable[[str], bool]:
    """Return a checker that passes only if the response contains a ```<lang> block."""
    fence = f"```{lang}"
    def _check(text: str) -> bool:
        return fence in text
    return _check


def requires_json_block(text: str) -> bool:
    """Pass if the response contains a ```json block or a bare JSON object/array."""
    from .code_parser import extract_json_block
    return extract_json_block(text) is not None


def requires_non_empty(text: str) -> bool:
    return bool(text and text.strip())
