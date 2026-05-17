"""Code block extraction and reconstruction utilities.

Supports: html, css, js/javascript, jsx, tsx, ts, vue, python, json, yaml, bash.
"""

from __future__ import annotations

import re
from typing import Optional


# Languages we know how to handle
_LANG_ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "jsx": "jsx",
    "ts": "typescript",
    "typescript": "typescript",
    "tsx": "tsx",
    "html": "html",
    "css": "css",
    "vue": "vue",
    "python": "python",
    "py": "python",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
}

# Regex: ```<lang>\n<code>\n```
_CODE_BLOCK_RE = re.compile(
    r"```(?P<lang>[a-zA-Z0-9_+-]*)\n(?P<code>.*?)```",
    re.DOTALL,
)


def extract_code_blocks(text: str) -> dict[str, list[str]]:
    """Extract all fenced code blocks from *text*, grouped by language.

    Args:
        text: Raw LLM response text (may contain prose + code blocks).

    Returns:
        A dict mapping normalised language name → list of code strings.
        Example:
            {
                "html": ["<!DOCTYPE html>..."],
                "css": ["body { margin: 0; }"],
                "javascript": ["console.log('hi')"],
            }
        Languages not in ``_LANG_ALIASES`` are stored under their raw name.
    """
    result: dict[str, list[str]] = {}
    for match in _CODE_BLOCK_RE.finditer(text):
        raw_lang = match.group("lang").strip().lower()
        lang = _LANG_ALIASES.get(raw_lang, raw_lang) if raw_lang else "text"
        code = match.group("code").strip()
        result.setdefault(lang, []).append(code)
    return result


def reconstruct_html(
    html: str = "",
    css: str = "",
    js: str = "",
    title: str = "Preview",
) -> Optional[str]:
    """Assemble HTML + CSS + JS into a single standalone HTML document.

    Args:
        html: Body content HTML string.
        css:  CSS rules string.
        js:   JavaScript string.
        title: Document title for the <title> tag.

    Returns:
        A full ``<!DOCTYPE html>`` document, or None if all inputs are empty.
    """
    if not html and not css and not js:
        return None

    style_block = f"<style>\n{css}\n</style>" if css else ""
    script_block = f"<script>\n{js}\n</script>" if js else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    {style_block}
</head>
<body>
{html}
{script_block}
</body>
</html>"""


def extract_first_block(text: str, lang: str) -> Optional[str]:
    """Convenience: return the first code block for a given language, or None."""
    blocks = extract_code_blocks(text)
    normalised = _LANG_ALIASES.get(lang.lower(), lang.lower())
    items = blocks.get(normalised)
    return items[0] if items else None


def extract_json_block(text: str) -> Optional[str]:
    """Return the first JSON code block, or try to find a bare JSON object/array."""
    # Try fenced block first
    block = extract_first_block(text, "json")
    if block:
        return block

    # Fallback: find first {...} or [...]
    for pattern in (r"(\{.*\})", r"(\[.*\])"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return None
