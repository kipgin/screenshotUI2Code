"""Tool call schema — shared Pydantic models for all tool modules."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Represents a single tool call parsed from the LLM output."""

    name: str = Field(..., description="Tool function name, e.g. 'create_file'.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments for the tool, parsed from JSON.",
    )
    call_id: Optional[str] = Field(
        default=None,
        description="Optional ID from the LLM (used in OpenAI function-calling).",
    )


class ToolResult(BaseModel):
    """Result returned by a tool handler to the agent."""

    tool_name: str
    success: bool
    output: str = Field(..., description="Human-readable result message.")
    data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured data (e.g. file contents, diff text).",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if success=False.",
    )

    def to_message(self) -> str:
        """Format for injection into conversation history as a tool result."""
        if self.success:
            msg = f"[tool:{self.tool_name}] {self.output}"
            if self.data and "content" in self.data:
                msg += f"\n\nFile Content:\n```\n{self.data['content']}\n```"
            return msg
        return f"[tool:{self.tool_name}] ERROR: {self.error}"


# ── Sub-tool argument schemas (for validation and documentation) ───────────────

class CreateFileArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")
    content: str = Field(..., description="File content to write.")

class ReadFileArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")

class EditFileArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")
    old_content: str = Field(..., description="Exact string to find and replace (indentation is ignored during matching).")
    new_content: str = Field(..., description="Replacement string.")

class DeleteFileArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")

class CreateFolderArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")

class DeleteFolderArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")
    recursive: bool = Field(default=False)

class GenerateDiffArgs(BaseModel):
    path: str = Field(..., description="Relative path from workspace root.")
    old_content: str
    new_content: str

class GitCommitArgs(BaseModel):
    message: str = Field(..., description="Commit message.")
    workspace: str = Field(..., description="Absolute workspace directory path.")

class GitCreateBranchArgs(BaseModel):
    branch_name: str
    workspace: str

class GitCheckoutArgs(BaseModel):
    commit_hash: str = Field(..., description="The git commit SHA or branch name to checkout.")
    workspace: str = Field(..., description="Absolute workspace directory path.")
