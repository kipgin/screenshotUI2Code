"""Prompt: code_generation — generate initial frontend code from a screenshot analysis."""


def code_generation_prompt(framework: str) -> str:
    """Return the code generation instruction prompt.

    Args:
        framework: Target frontend framework.
            Supported values: "html/css", "React/JSX", "Tailwind", "Vue".

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    framework_rules = _framework_rules(framework)

    return f"""\
Based on your screenshot analysis, generate the complete frontend code using **{framework}**.

## Framework-specific rules

{framework_rules}

## Quality requirements
- **Pixel-perfect**: Match colours, spacing, and font sizes from the screenshot.
- **Responsive**: The layout must work on mobile (≤ 768 px) and desktop.
- **Accessible**: Use semantic HTML tags, `alt` attributes, and ARIA labels where appropriate.
- **No placeholders**: Replace "Lorem ipsum" with realistic placeholder text.
- **No external image CDN links**: Use SVG icons or CSS shapes instead of `<img src="https://...">`.

## Output format
**CRITICAL INSTRUCTION:** Do NOT output raw code blocks. You MUST use the `create_file` tool format to write each file.
For example, to write an HTML file, do NOT output ```html. Instead, output:
```tool_call
{{
  "name": "create_file",
  "arguments": {{
    "path": "index.html",
    "content": "<!DOCTYPE html>\n..."
  }}
}}
```
After all files are created, summarise what you built in one short paragraph.
"""


def _framework_rules(framework: str) -> str:
    """Return the framework-specific subsection of the code generation prompt."""
    fw = framework.lower().replace("/", "").replace(" ", "")

    if fw in ("htmlcss", "html", "css"):
        return """\
### HTML / CSS (Plain)
- Single `index.html` file embedding all CSS in `<style>` and JS in `<script>`.
- Use CSS custom properties (variables) for colours and spacing.
- Use Flexbox or CSS Grid for layout."""

    if fw in ("reactjsx", "react", "jsx"):
        return """\
### React / JSX
- Output a single `App.jsx` component (or split into logical sub-components, one file each).
- Use functional components and hooks.
- Use inline styles or a separate `App.css` — clearly separate the files."""

    if fw in ("tailwind", "tailwindcss"):
        return """\
### Tailwind CSS
- Use Tailwind utility classes exclusively. Do not write custom CSS unless absolutely necessary.
- Assume Tailwind is loaded via CDN or config — do not include the build step."""

    if fw == "vue":
        return """\
### Vue
- Output a single-file component (`App.vue`) with `<template>`, `<script setup>`, \
and `<style scoped>`."""

    # Fallback: generic rules
    return f"""\
### {framework}
- Follow the conventions of {framework}.
- Produce self-contained, runnable output.
- Add a brief comment at the top of each file indicating its role."""
