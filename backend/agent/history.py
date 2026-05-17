"""ConversationHistory — manages the message list for one session.

Features:
- Add messages in OpenAI-compatible dict format.
- Proactive summarisation: when token count exceeds the threshold, older
  non-system messages are replaced by a single summary message.
- The system message is always preserved at index 0.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from utils.text_utils import estimate_tokens, messages_to_text

logger = logging.getLogger(__name__)

# Default token threshold before summarisation kicks in
DEFAULT_SUMMARISE_THRESHOLD = 6000


class ConversationHistory:
    """Manages the in-memory conversation history for one agent session."""

    def __init__(
        self,
        system_prompt: str = "",
        summarise_threshold: int = DEFAULT_SUMMARISE_THRESHOLD,
    ) -> None:
        self._messages: list[dict[str, Any]] = []
        self._summarise_threshold = summarise_threshold

        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def add_user(self, content: Any) -> None:
        """Add a user message. content may be a string or a list (vision)."""
        self._messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Inject a tool result as a user-role message (visible to the LLM)."""
        self._messages.append({
            "role": "user",
            "content": f"[Tool result: {tool_name}]\n{result}",
        })

    def strip_old_base64_images(self) -> None:
        """Replace giant base64 image URLs in older messages with a placeholder.
        
        This prevents the history from growing excessively large and saves massive
        amounts of token context window and bandwidth on subsequent turns.
        """
        for i, msg in enumerate(self._messages):
            # Do not strip the very last message in the history if it was just added
            if i == len(self._messages) - 1:
                continue
                
            content = msg.get("content")
            if isinstance(content, list):
                new_content = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        url = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:image") and len(url) > 1000:
                            logger.info("Stripped giant base64 image from older history message.")
                            continue  # skip appending the image_url item
                    new_content.append(item)
                
                # If we stripped the image, make sure to add a small text placeholder if there wasn't one
                has_text = any(isinstance(x, dict) and x.get("type") == "text" for x in new_content)
                if not has_text:
                    new_content.append({
                        "type": "text",
                        "text": "[User uploaded screenshot of the UI design]"
                    })
                msg["content"] = new_content

    def get_messages(self) -> list[dict[str, Any]]:
        """Return a shallow copy of the current message list."""
        return list(self._messages)

    def set_system_prompt(self, prompt: str) -> None:
        """Replace (or insert) the system message."""
        if self._messages and self._messages[0]["role"] == "system":
            self._messages[0]["content"] = prompt
        else:
            self._messages.insert(0, {"role": "system", "content": prompt})

    # ------------------------------------------------------------------
    # Summarisation
    # ------------------------------------------------------------------

    def should_summarise(self) -> bool:
        """Return True if the history token count exceeds the threshold."""
        text = messages_to_text(self._messages)
        return estimate_tokens(text) > self._summarise_threshold

    async def summarise(self, llm_client: Any) -> None:
        """Replace older non-system messages with a one-paragraph summary.

        The system message (index 0) is always preserved.
        The most recent 4 messages are kept verbatim for continuity.
        Everything in between is summarised.
        """
        from utils.text_utils import truncate_to_token_limit

        non_system = [m for m in self._messages if m["role"] != "system"]
        system_msgs = [m for m in self._messages if m["role"] == "system"]

        if len(non_system) < 6:
            return  # Not enough history to summarise

        to_summarise = non_system[:-4]
        to_keep = non_system[-4:]

        text_to_summarise = messages_to_text(to_summarise)
        text_to_summarise = truncate_to_token_limit(text_to_summarise, 3000)

        from prompts.summarization import summarization_prompt
        summary_prompt = summarization_prompt(text_to_summarise)

        logger.info("ConversationHistory: summarising %d messages.", len(to_summarise))
        summary = await llm_client.chat(
            [{"role": "user", "content": summary_prompt}]
        )

        summary_message = {"role": "assistant", "content": summary}
        self._messages = system_msgs + [summary_message] + to_keep
        logger.info("ConversationHistory: summarisation complete.")

    def token_count(self) -> int:
        return estimate_tokens(messages_to_text(self._messages))

    def __len__(self) -> int:
        return len(self._messages)

    def clear(self, keep_system: bool = True) -> None:
        """Clear history, optionally preserving the system message."""
        if keep_system and self._messages and self._messages[0]["role"] == "system":
            self._messages = [self._messages[0]]
        else:
            self._messages = []
