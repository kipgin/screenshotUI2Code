"""Diff tools — generate, preview, and apply unified diffs."""

from __future__ import annotations

import difflib
from pathlib import Path

from .registry import registry
from .schema import ToolResult, GenerateDiffArgs


def _resolve(workspace: str, rel_path: str) -> Path:
    root = Path(workspace).resolve()
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Path traversal attempt blocked: {rel_path}")
    return target


def _unified_diff(old: str, new: str, filename: str = "file") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


@registry.register(
    name="generate_diff",
    description=(
        "Generate a unified diff between old_content and new_content for a file. "
        "Use this to preview changes before applying them."
    ),
    args_schema=GenerateDiffArgs,
)
async def generate_diff(
    path: str, old_content: str, new_content: str, workspace: str
) -> ToolResult:
    diff_text = _unified_diff(old_content, new_content, filename=path)
    if not diff_text:
        return ToolResult(
            tool_name="generate_diff",
            success=True,
            output="No differences found.",
            data={"diff": "", "path": path, "old_content": old_content, "new_content": new_content},
        )
    return ToolResult(
        tool_name="generate_diff",
        success=True,
        output=f"Diff for {path}:\n{diff_text}",
        data={"diff": diff_text, "path": path, "old_content": old_content, "new_content": new_content},
    )


@registry.register(
    name="preview_diff",
    description="Show the diff between the current file on disk and new_content.",
)
async def preview_diff(path: str, new_content: str, workspace: str) -> ToolResult:
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="preview_diff",
            success=False,
            output="",
            error=f"File not found: {path}",
        )
    old_content = target.read_text(encoding="utf-8")
    diff_text = _unified_diff(old_content, new_content, filename=path)
    return ToolResult(
        tool_name="preview_diff",
        success=True,
        output=diff_text or "No differences.",
        data={"diff": diff_text, "path": path, "old_content": old_content, "new_content": new_content},
    )


@registry.register(
    name="apply_diff",
    description=(
        "Apply a unified diff patch to a file. "
        "The diff must be in standard unified diff format."
    ),
)
async def apply_diff(path: str, diff_text: str, workspace: str) -> ToolResult:
    """Apply a unified diff using Python's patch logic (line-by-line)."""
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="apply_diff",
            success=False,
            output="",
            error=f"File not found: {path}",
        )

    original = target.read_text(encoding="utf-8").splitlines()
    patched = list(original)

    # Simple hunk parser for unified diff
    try:
        patched = _apply_unified_diff(original, diff_text)
    except Exception as exc:
        return ToolResult(
            tool_name="apply_diff",
            success=False,
            output="",
            error=f"Failed to apply diff: {exc}",
        )

    target.write_text("\n".join(patched), encoding="utf-8")
    return ToolResult(
        tool_name="apply_diff",
        success=True,
        output=f"Applied diff to {path}",
    )


def _apply_unified_diff(original: list[str], diff_text: str) -> list[str]:
    """Minimal unified diff apply (handles simple add/remove hunks)."""
    result = list(original)
    offset = 0
    i = 0
    lines = diff_text.splitlines()
    while i < len(lines):
        line = lines[i]
        if line.startswith("@@"):
            # Parse @@ -start,count +start,count @@
            import re
            m = re.search(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not m:
                i += 1
                continue
            src_start = int(m.group(1)) - 1 + offset
            i += 1
            hunk_old: list[str] = []
            hunk_new: list[str] = []
            while i < len(lines) and not lines[i].startswith("@@") and not lines[i].startswith("diff"):
                hl = lines[i]
                if hl.startswith("-"):
                    hunk_old.append(hl[1:])
                elif hl.startswith("+"):
                    hunk_new.append(hl[1:])
                else:
                    hunk_old.append(hl[1:] if hl.startswith(" ") else hl)
                    hunk_new.append(hl[1:] if hl.startswith(" ") else hl)
                i += 1
            result[src_start: src_start + len(hunk_old)] = hunk_new
            offset += len(hunk_new) - len(hunk_old)
        else:
            i += 1
    return result
