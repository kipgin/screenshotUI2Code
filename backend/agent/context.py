"""AgentContext — holds all mutable state for one design session."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from llm.config import LLMConfig, small_model_config


@dataclass
class AgentContext:
    """All state for a single user design session.

    One context is created per upload and lives for the lifetime of
    the session. It is passed through the agent run loop on every turn.
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Directory where generated files are written (one git repo per session)
    workspace_dir: Path = field(default_factory=lambda: Path("workspaces") / str(uuid.uuid4()))

    # Frontend framework requested by the user
    framework: str = "html/css"

    # LLM configuration for this session
    llm_config: LLMConfig = field(default_factory=small_model_config)

    # Path to the uploaded screenshot (may be None for text-only sessions)
    screenshot_path: Path | None = None

    # Whether to enable parallel module generation
    enable_parallel: bool = False

    # Maximum agent loop iterations per turn (safety limit)
    max_iterations: int = 10

    def __post_init__(self) -> None:
        self.workspace_dir = Path(self.workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    @property
    def workspace_str(self) -> str:
        return str(self.workspace_dir.resolve())
