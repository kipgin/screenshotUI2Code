"""File tools — create, read, edit, delete files in the session workspace."""

from __future__ import annotations

import os
from pathlib import Path

from .registry import registry
from .schema import ToolResult, CreateFileArgs, ReadFileArgs, EditFileArgs, DeleteFileArgs


def _resolve(workspace: str, rel_path: str) -> Path:
    """Resolve a relative path safely within the workspace root."""
    root = Path(workspace).resolve()
    target = (root / rel_path).resolve()
    # Security: prevent path traversal outside workspace (case-insensitive for OS compatibility)
    if not str(target).lower().startswith(str(root).lower()):
        raise ValueError(f"Path traversal attempt blocked: {rel_path}")
    return target


@registry.register(
    name="create_file",
    description="Create a new file (or overwrite it) with the given content.",
    args_schema=CreateFileArgs,
)
async def create_file(path: str, content: str, workspace: str) -> ToolResult:
    target = _resolve(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return ToolResult(
        tool_name="create_file",
        success=True,
        output=f"Created file: {path}",
        data={"path": path},
    )


@registry.register(
    name="read_file",
    description="Read and return the full content of a file.",
    args_schema=ReadFileArgs,
)
async def read_file(path: str, workspace: str) -> ToolResult:
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="read_file",
            success=False,
            output="",
            error=f"File not found: {path}",
        )
    content = target.read_text(encoding="utf-8")
    return ToolResult(
        tool_name="read_file",
        success=True,
        output=f"Read {len(content)} chars from {path}",
        data={"path": str(target), "content": content},
    )


@registry.register(
    name="edit_file",
    description=(
        "Replace a specific block of text in a file. "
        "old_content is matched ignoring leading/trailing whitespace and indentation."
    ),
    args_schema=EditFileArgs,
)
async def edit_file(
    path: str, old_content: str, new_content: str, workspace: str
) -> ToolResult:
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="edit_file",
            success=False,
            output="",
            error=f"File not found: {path}",
        )
    current = target.read_text(encoding="utf-8")
    
    # 1. Try exact match first
    if old_content in current:
        updated = current.replace(old_content, new_content, 1)
        target.write_text(updated, encoding="utf-8")
        return ToolResult(
            tool_name="edit_file",
            success=True,
            output=f"Edited file: {path} (Exact match)",
            data={"path": path},
        )
        
    # 2. Fuzzy match ignoring indentation
    current_lines = current.splitlines()
    old_lines = old_content.strip().splitlines()
    
    if not old_lines:
        return ToolResult(
            tool_name="edit_file",
            success=False,
            output="",
            error="old_content is empty.",
        )
        
    # Find a window of lines that matches after stripping
    found_idx = -1
    for i in range(len(current_lines) - len(old_lines) + 1):
        match = True
        for j, old_line in enumerate(old_lines):
            if current_lines[i+j].strip() != old_line.strip():
                match = False
                break
        if match:
            found_idx = i
            break
            
    if found_idx == -1:
        return ToolResult(
            tool_name="edit_file",
            success=False,
            output="",
            error="old_content not found in file (even ignoring indentation). No changes made.",
        )
        
    prefix = current_lines[:found_idx]
    suffix = current_lines[found_idx + len(old_lines):]
    
    updated = "\n".join(prefix + [new_content] + suffix)
    target.write_text(updated, encoding="utf-8")
    
    return ToolResult(
        tool_name="edit_file",
        success=True,
        output=f"Edited file: {path} (Fuzzy whitespace match)",
        data={"path": path},
    )


@registry.register(
    name="delete_file",
    description="Permanently delete a file from the workspace.",
    args_schema=DeleteFileArgs,
)
async def delete_file(path: str, workspace: str) -> ToolResult:
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="delete_file",
            success=False,
            output="",
            error=f"File not found: {path}",
        )
    target.unlink()
    return ToolResult(
        tool_name="delete_file",
        success=True,
        output=f"Deleted file: {path}",
    )
