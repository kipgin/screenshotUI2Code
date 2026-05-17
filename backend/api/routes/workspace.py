"""Workspace REST endpoints — file and git operations for the frontend UI."""

from __future__ import annotations

import os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Body

from api.routes.design import _sessions

logger = logging.getLogger(__name__)


def build_file_tree(base_dir: Path, current_dir: Path) -> list[dict]:
    nodes = []
    try:
        for entry in sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if entry.name == ".git" or entry.name == "__pycache__":
                continue
            
            rel_path = entry.relative_to(base_dir).as_posix()
            node = {
                "name": entry.name,
                "path": rel_path,
                "isDir": entry.is_dir(),
            }
            if entry.is_dir():
                node["children"] = build_file_tree(base_dir, entry)
            nodes.append(node)
    except Exception as e:
        logger.exception("Error building file tree: %s", e)
    return nodes
from tool.file_tools import read_file, create_file, delete_file, edit_file
from tool.folder_tools import list_folder, create_folder, delete_folder
from tool.git_tools import git_status, git_log, git_checkout

router = APIRouter(prefix="/workspace/{session_id}", tags=["workspace"])

def _get_ws(session_id: str) -> str:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    context, _ = _sessions[session_id]
    return context.workspace_str

# ── Files & Folders ──────────────────────────────────────────────────────────

@router.get("/files")
async def get_file_tree(session_id: str, path: str = "."):
    ws = _get_ws(session_id)
    base_path = Path(ws).resolve()
    target_path = (base_path / path).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=400, detail="Path traversal attempt blocked.")
        
    if not target_path.exists():
        return []
        
    return build_file_tree(base_path, target_path)

@router.post("/folder")
async def create_dir(session_id: str, path: str = Body(..., embed=True)):
    ws = _get_ws(session_id)
    res = await create_folder(path, ws)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return res.data

@router.delete("/folder")
async def delete_dir(session_id: str, path: str, recursive: bool = False):
    ws = _get_ws(session_id)
    res = await delete_folder(path, ws, recursive)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return {"detail": "Folder deleted."}

@router.get("/file")
async def get_file(session_id: str, path: str):
    ws = _get_ws(session_id)
    res = await read_file(path, ws)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return {"content": res.data["content"]}

@router.post("/file")
async def write_file(session_id: str, path: str = Body(...), content: str = Body(...)):
    ws = _get_ws(session_id)
    res = await create_file(path, content, ws)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return {"detail": "File created/updated."}

@router.delete("/file")
async def remove_file(session_id: str, path: str):
    ws = _get_ws(session_id)
    res = await delete_file(path, ws)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return {"detail": "File deleted."}

# ── Git ──────────────────────────────────────────────────────────────────────

@router.get("/git/status")
async def get_git_status(session_id: str):
    ws = _get_ws(session_id)
    res = await git_status(ws)
    return res.data if res.success else {"status": ""}

@router.get("/git/log")
async def get_git_log(session_id: str):
    ws = _get_ws(session_id)
    res = await git_log(ws)
    return res.data["log"] if res.success else []


@router.post("/git/checkout")
async def checkout_git_commit(session_id: str, commit_hash: str = Body(..., embed=True)):
    ws = _get_ws(session_id)
    res = await git_checkout(commit_hash, ws)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return {"detail": f"Checked out commit {commit_hash}."}

