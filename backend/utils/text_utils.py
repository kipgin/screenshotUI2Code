"""Text utility helpers: token estimation, truncation, cleaning."""

from __future__ import annotations


_CHARS_PER_TOKEN = 4  # rough heuristic


def estimate_tokens(text: str) -> int:
    """Estimate the token count of *text* using the 4 chars/token heuristic.

    For a more accurate count use ``BaseLLMClient.count_tokens(text)``.
    """
    return max(0, len(text) // _CHARS_PER_TOKEN)


def truncate_to_token_limit(text: str, limit: int) -> str:
    """Truncate *text* to approximately *limit* tokens.

    Truncation happens at a newline boundary where possible to avoid
    cutting mid-sentence.

    Args:
        text:  Input string.
        limit: Maximum token count.

    Returns:
        Truncated string (may be shorter than the limit).
    """
    max_chars = limit * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # Try to break at the last newline
    last_nl = truncated.rfind("\n")
    if last_nl > max_chars // 2:
        return truncated[:last_nl]
    return truncated


def clean_llm_response(text: str) -> str:
    """Strip leading/trailing whitespace and common LLM artefacts."""
    text = text.strip()
    # Remove leading "```" if the whole response is wrapped in a code fence
    if text.startswith("```") and text.endswith("```") and text.count("```") == 2:
        text = text[3:-3].strip()
        # Remove the language identifier on the first line if present
        first_nl = text.find("\n")
        if first_nl != -1:
            first_line = text[:first_nl].strip()
            if first_line and " " not in first_line:
                text = text[first_nl + 1:].strip()
    return text


def messages_to_text(messages: list[dict]) -> str:
    """Flatten a messages list to a plain text string (for token counting)."""
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Vision message — extract text parts only
            text_parts = [
                p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
            ]
            content = " ".join(text_parts)
        parts.append(f"{role}: {content}")
    return "\n".join(parts)
