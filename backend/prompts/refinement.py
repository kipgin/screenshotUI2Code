"""Prompt: refinement — apply multi-turn user feedback to existing code."""


def refinement_prompt(current_code: str, feedback: str) -> str:
    """Return the refinement instruction prompt.

    Args:
        current_code: The complete current version of the generated code.
        feedback:     The user's natural-language change request.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    return f"""\
The user has provided feedback on the current version of the frontend code. \
Apply their changes carefully.

## Current code
```
{current_code}
```

## User feedback
"{feedback}"

## Rules
1. Read the feedback carefully. Identify the minimum set of changes needed.
2. Do NOT rewrite sections unrelated to the feedback.
3. If the feedback is ambiguous, pick the most sensible interpretation and note it briefly.
4. If the change requires a structural refactor (e.g. switching from absolute to flex layout), \
do it completely — half-done refactors break things.
5. After editing, use the `edit_file` tool to apply changes to the workspace files.
6. Confirm what changed in one sentence.

## Output format
Use the `edit_file` tool for targeted changes, or `create_file` for a full replacement \
if the change is large. Then state: "Done — [what changed]."
"""
