"""Git tools — auto-commit, branch management, and status for session workspaces.

Each session has its own git repository initialised in its workspace directory.
These tools wrap GitPython to provide commit, branch, log, and status operations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .registry import registry
from .schema import ToolResult, GitCommitArgs, GitCreateBranchArgs, GitCheckoutArgs

logger = logging.getLogger(__name__)


def _get_repo(workspace: str):
    """Return a git.Repo for the given workspace, initialising if needed."""
    try:
        import git
    except ImportError:
        raise RuntimeError("gitpython is not installed. Run: pip install gitpython")

    path = Path(workspace)
    git_dir = path / ".git"
    if not git_dir.exists():
        repo = git.Repo.init(str(path))
        # Stage any existing files in the workspace so they are not lost on checkout
        repo.git.add(A=True)
        repo.index.commit("Initial commit — workspace created by AI Frontend Designer")
        logger.info("Initialised git repo at %s with existing files", path)
    else:
        repo = git.Repo(str(path))
    return repo


@registry.register(
    name="git_commit",
    description=(
        "Stage all changes in the workspace and create a git commit. "
        "Call this after writing or editing files to save a checkpoint."
    ),
    args_schema=GitCommitArgs,
)
async def git_commit(message: str, workspace: str) -> ToolResult:
    try:
        repo = _get_repo(workspace)
        repo.git.add(A=True)
        if not repo.index.diff("HEAD") and not repo.untracked_files:
            return ToolResult(
                tool_name="git_commit",
                success=True,
                output="Nothing to commit — working tree is clean.",
            )
        commit = repo.index.commit(message)
        return ToolResult(
            tool_name="git_commit",
            success=True,
            output=f"Committed: {commit.hexsha[:8]} — {message}",
            data={"sha": commit.hexsha, "message": message},
        )
    except Exception as exc:
        logger.exception("git_commit failed")
        return ToolResult(
            tool_name="git_commit",
            success=False,
            output="",
            error=str(exc),
        )


@registry.register(
    name="git_create_branch",
    description="Create and checkout a new git branch in the workspace.",
    args_schema=GitCreateBranchArgs,
)
async def git_create_branch(branch_name: str, workspace: str) -> ToolResult:
    try:
        repo = _get_repo(workspace)
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        return ToolResult(
            tool_name="git_create_branch",
            success=True,
            output=f"Created and checked out branch: {branch_name}",
            data={"branch": branch_name},
        )
    except Exception as exc:
        return ToolResult(
            tool_name="git_create_branch",
            success=False,
            output="",
            error=str(exc),
        )


@registry.register(
    name="git_log",
    description="Return the recent git commit log for the workspace.",
)
async def git_log(workspace: str, max_entries: int = 10) -> ToolResult:
    try:
        repo = _get_repo(workspace)
        
        # Safe log: query master or main branches first so newer commits remain visible when HEAD is detached
        commits_list = []
        for ref in ['master', 'main', 'refs/heads/master', 'refs/heads/main']:
            try:
                commits_list = list(repo.iter_commits(ref))
                if commits_list:
                    break
            except Exception:
                continue
                
        if not commits_list:
            try:
                commits_list = list(repo.iter_commits('--all'))
            except Exception:
                commits_list = list(repo.iter_commits())
                
        entries = []
        for commit in commits_list[:max_entries]:
            entries.append({
                "hash": commit.hexsha,
                "message": commit.message.strip()
            })
        log_lines = [f"{c['hash'][:8]}  {c['message']}" for c in entries]
        log_text = "\n".join(log_lines) or "(no commits)"
        return ToolResult(
            tool_name="git_log",
            success=True,
            output=log_text,
            data={"log": entries},
        )
    except Exception as exc:
        return ToolResult(
            tool_name="git_log",
            success=False,
            output="",
            error=str(exc),
        )


@registry.register(
    name="git_status",
    description="Show the current git status (modified, untracked, staged files).",
)
async def git_status(workspace: str) -> ToolResult:
    try:
        repo = _get_repo(workspace)
        status = repo.git.status("--short")
        return ToolResult(
            tool_name="git_status",
            success=True,
            output=status or "Clean — nothing to show.",
            data={"status": status},
        )
    except Exception as exc:
        return ToolResult(
            tool_name="git_status",
            success=False,
            output="",
            error=str(exc),
        )


@registry.register(
    name="git_checkout",
    description="Check out a specific commit or branch in the workspace.",
    args_schema=GitCheckoutArgs,
)
async def git_checkout(commit_hash: str, workspace: str) -> ToolResult:
    try:
        repo = _get_repo(workspace)
        repo.git.checkout(commit_hash)
        return ToolResult(
            tool_name="git_checkout",
            success=True,
            output=f"Checked out commit: {commit_hash}",
            data={"commit_hash": commit_hash},
        )
    except Exception as exc:
        logger.exception("git_checkout failed")
        return ToolResult(
            tool_name="git_checkout",
            success=False,
            output="",
            error=str(exc),
        )
