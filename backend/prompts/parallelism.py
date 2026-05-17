"""Prompt: parallelism — decompose a design task into independent parallel sub-tasks."""


def parallelism_prompt(design_description: str) -> str:
    """Return the task-decomposition prompt for parallel code generation.

    Args:
        design_description: High-level description of the UI to build.

    Returns:
        Formatted prompt string. The LLM must respond with a JSON array only.
    """
    return f"""\
The user wants to build the following UI: "{design_description}"

Your task is to decompose this into independent, parallelisable sub-tasks that can be \
generated simultaneously without depending on each other's output.

## Rules
1. Each sub-task must be a self-contained UI section or component \
(e.g. Navbar, Hero Section, Features Grid, Footer).
2. Sub-tasks must NOT depend on each other's code — they will be generated independently.
3. Specify the file each sub-task should produce (e.g. `components/Navbar.jsx`).
4. Keep the total number of sub-tasks between 2 and 6.

## Output format (strict JSON array)
```json
[
  {{
    "id": "navbar",
    "description": "A responsive navbar with logo and navigation links",
    "output_file": "components/Navbar.jsx"
  }},
  {{
    "id": "hero",
    "description": "A full-width hero section with a headline, subheading, and CTA button",
    "output_file": "components/Hero.jsx"
  }}
]
```
Output ONLY the JSON array. No prose.
"""
