"""Prompt: summarization — compress old conversation history into a short paragraph."""


def summarization_prompt(conversation: str) -> str:
    """Return the summarization instruction prompt.

    Args:
        conversation: The raw conversation text to be summarised (already
                      flattened to plain text via ``messages_to_text()``).

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    return f"""\
The following is the beginning of a conversation between a user and an AI frontend \
design assistant. Summarise this conversation history into a concise paragraph that captures:

1. The original design request and what screenshot/description was provided.
2. The framework chosen.
3. All major changes made in subsequent turns (bullet-point the changes, do not omit any).
4. The current state of the design (what it looks like now).

Keep the summary under 300 words. Begin with: "Session summary: "

## Conversation to summarise
{conversation}
"""
