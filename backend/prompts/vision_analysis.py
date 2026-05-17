"""Prompt: vision_analysis — screenshot layout analysis before code generation."""


def vision_analysis_prompt(framework: str) -> str:
    """Return the vision analysis instruction prompt.

    Args:
        framework: Target frontend framework (e.g. "html/css", "React/JSX").

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    return f"""\
Analyse the attached screenshot carefully. Describe the following in order:

1. **Layout structure**: How many columns? Is there a header/footer/sidebar? \
What is the overall page flow?
2. **Component inventory**: List every distinct UI component visible \
(navbar, hero, cards, buttons, forms, etc.).
3. **Typography**: Font sizes (relative), weights, text hierarchy.
4. **Colour palette**: Note the dominant background, text, primary action, and accent colours. \
Give rough hex values if possible.
5. **Spacing**: Estimate padding/margin density (tight / moderate / spacious).
6. **Interactive elements**: Identify buttons, inputs, dropdowns, toggles.
7. **Images/icons**: Note any images or icon sets used.

After the analysis, confirm: "Ready to generate {framework} code."
"""
