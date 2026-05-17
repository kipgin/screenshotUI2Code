"""Tests for the tool module: file CRUD, git, diff."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tool.schema import ToolCall, ToolResult
from tool.file_tools import create_file, read_file, edit_file, delete_file
from tool.folder_tools import create_folder, list_folder, delete_folder
from tool.diff_tools import generate_diff, preview_diff
from tool import registry


# ── File tools ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_read_file(tmp_path):
    ws = str(tmp_path)
    result = await create_file("test.html", "<h1>Hello</h1>", ws)
    assert result.success
    assert (tmp_path / "test.html").exists()

    read = await read_file("test.html", ws)
    assert read.success
    assert read.data["content"] == "<h1>Hello</h1>"


@pytest.mark.asyncio
async def test_edit_file(tmp_path):
    ws = str(tmp_path)
    await create_file("style.css", "body { color: red; }", ws)
    result = await edit_file("style.css", "color: red;", "color: blue;", ws)
    assert result.success
    content = (tmp_path / "style.css").read_text()
    assert "color: blue;" in content


@pytest.mark.asyncio
async def test_edit_file_old_content_not_found(tmp_path):
    ws = str(tmp_path)
    await create_file("a.html", "<p>Hello</p>", ws)
    result = await edit_file("a.html", "does not exist", "replacement", ws)
    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_delete_file(tmp_path):
    ws = str(tmp_path)
    await create_file("del_me.txt", "bye", ws)
    result = await delete_file("del_me.txt", ws)
    assert result.success
    assert not (tmp_path / "del_me.txt").exists()


@pytest.mark.asyncio
async def test_path_traversal_blocked(tmp_path):
    ws = str(tmp_path)
    try:
        result = await create_file("../../evil.txt", "oops", ws)
        # If it returns a ToolResult, it should be a failure
        assert not result.success
    except ValueError:
        # ValueError is also an acceptable way to block traversal
        pass
    assert not (Path(ws).parent.parent / "evil.txt").exists()


# ── Folder tools ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_list_folder(tmp_path):
    ws = str(tmp_path)
    result = await create_folder("components", ws)
    assert result.success
    list_result = await list_folder(".", ws)
    assert "components" in list_result.data["entries"]


@pytest.mark.asyncio
async def test_delete_empty_folder(tmp_path):
    ws = str(tmp_path)
    await create_folder("empty_dir", ws)
    result = await delete_folder("empty_dir", ws)
    assert result.success


# ── Diff tools ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_diff_shows_changes(tmp_path):
    ws = str(tmp_path)
    old = "line1\nline2\nline3"
    new = "line1\nLINE2_CHANGED\nline3"
    result = await generate_diff("file.txt", old, new, ws)
    assert result.success
    assert "LINE2_CHANGED" in result.data["diff"]


@pytest.mark.asyncio
async def test_generate_diff_no_change(tmp_path):
    ws = str(tmp_path)
    result = await generate_diff("file.txt", "same", "same", ws)
    assert result.success
    assert result.data["diff"] == ""


# ── Registry dispatch ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_registry_dispatch_create_file(tmp_path):
    ws = str(tmp_path)
    tc = ToolCall(name="create_file", arguments={"path": "dispatch_test.html", "content": "<p>ok</p>"})
    result = await registry.dispatch(tc, ws)
    assert result.success


@pytest.mark.asyncio
async def test_registry_dispatch_unknown_tool(tmp_path):
    tc = ToolCall(name="nonexistent_tool", arguments={})
    result = await registry.dispatch(tc, str(tmp_path))
    assert not result.success
    assert "Unknown tool" in result.error
