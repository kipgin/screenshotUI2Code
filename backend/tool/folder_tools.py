"""Folder tools — create, list, delete directories in the session workspace."""

from __future__ import annotations

import shutil
from pathlib import Path

from .registry import registry
from .schema import ToolResult, CreateFolderArgs, DeleteFolderArgs


def _resolve(workspace: str, rel_path: str) -> Path:
    root = Path(workspace).resolve()
    target = (root / rel_path).resolve()
    # Security: prevent path traversal outside workspace (case-insensitive for OS compatibility)
    if not str(target).lower().startswith(str(root).lower()):
        raise ValueError(f"Path traversal attempt blocked: {rel_path}")
    return target


@registry.register(
    name="create_folder",
    description="Create a directory (including parents) in the workspace.",
    args_schema=CreateFolderArgs,
)
async def create_folder(path: str, workspace: str) -> ToolResult:
    target = _resolve(workspace, path)
    target.mkdir(parents=True, exist_ok=True)
    return ToolResult(
        tool_name="create_folder",
        success=True,
        output=f"Created folder: {path}",
        data={"path": str(target)},
    )


@registry.register(
    name="list_folder",
    description="List the files and sub-folders in a workspace directory.",
)
async def list_folder(path: str = ".", workspace: str = "") -> ToolResult:
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="list_folder",
            success=False,
            output="",
            error=f"Folder not found: {path}",
        )
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = []
    for entry in entries:
        prefix = "📁 " if entry.is_dir() else "📄 "
        lines.append(prefix + entry.name)
    listing = "\n".join(lines) or "(empty)"
    return ToolResult(
        tool_name="list_folder",
        success=True,
        output=listing,
        data={"entries": [e.name for e in entries]},
    )


@registry.register(
    name="delete_folder",
    description="Delete a directory. Set recursive=true to delete non-empty directories.",
    args_schema=DeleteFolderArgs,
)
async def delete_folder(
    path: str, workspace: str, recursive: bool = False
) -> ToolResult:
    target = _resolve(workspace, path)
    if not target.exists():
        return ToolResult(
            tool_name="delete_folder",
            success=False,
            output="",
            error=f"Folder not found: {path}",
        )
    if recursive:
        shutil.rmtree(target)
    else:
        try:
            target.rmdir()
        except OSError as exc:
            return ToolResult(
                tool_name="delete_folder",
                success=False,
                output="",
                error=f"Folder not empty. Use recursive=true. Detail: {exc}",
            )
    return ToolResult(
        tool_name="delete_folder",
        success=True,
        output=f"Deleted folder: {path}",
    )
