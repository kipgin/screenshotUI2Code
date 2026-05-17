"""Central application settings — reads from environment / .env file.

All secrets, URLs, and model names live here (loaded from .env).
No other module should hardcode these values.

Usage:
    from settings import settings
    cfg = settings.small_model_config()
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Small / local model (OpenAI-compatible endpoint) ──────────────────────
    # Rename-friendly: "small model" = the local fast model (OpenVINO, Ollama, etc.)
    SMALL_MODEL_PROVIDER: str = Field(default="openai")
    SMALL_MODEL_NAME: str = Field(default="qwen2.5-coder-ov")
    SMALL_MODEL_BASE_URL: str = Field(default="http://localhost:8000/v1")
    SMALL_MODEL_API_KEY: str = Field(default="local-gpu")

    # ── Agent ──────────────────────────────────────────────────────────────────
    AGENT_MAX_ITERATIONS: int = Field(default=10)
    HISTORY_SUMMARIZE_THRESHOLD: int = Field(default=6000)

    # ── Parallelism ────────────────────────────────────────────────────────────
    ENABLE_PARALLEL_GENERATION: bool = Field(default=False)

    # ── Git ───────────────────────────────────────────────────────────────────
    GIT_AUTO_COMMIT: bool = Field(default=True)
    GIT_WORKSPACE_ROOT: str = Field(default="./workspaces")

    # ── Storage ───────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = Field(default="./uploads")

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8001)
    DEBUG: bool = Field(default=False)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    # ── Convenience factories ──────────────────────────────────────────────────

    def small_model_config(self) -> "LLMConfig":
        """Return an LLMConfig for the local small/fast model."""
        from llm.config import LLMConfig
        return LLMConfig(
            provider=self.SMALL_MODEL_PROVIDER,  # type: ignore[arg-type]
            model=self.SMALL_MODEL_NAME,
            base_url=self.SMALL_MODEL_BASE_URL,
            api_key=self.SMALL_MODEL_API_KEY,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()


# Module-level singleton — import this everywhere
settings = get_settings()
