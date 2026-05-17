"""LLMConfig — provider-agnostic configuration for any LLM client.

Preset factory functions read all sensitive values (URLs, keys, model names)
from ``settings.py`` which loads them from ``.env``.
No URLs or API keys are hardcoded here.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


Provider = Literal["openai", "anthropic", "gemini"]


class LLMConfig(BaseModel):
    """Configuration for a single LLM provider instance.

    Designed to be provider-agnostic. Fields that are not relevant to
    a given provider are silently ignored by that provider's client.
    """

    provider: Provider = Field(
        default="openai",
        description="Which LLM provider backend to use.",
    )
    model: str = Field(
        default="",
        description="Model identifier string (e.g. 'gpt-4o', 'claude-3-5-sonnet').",
    )
    base_url: Optional[str] = Field(
        default=None,
        description=(
            "Override the API base URL. Required for local/self-hosted servers. "
            "Set via SMALL_MODEL_BASE_URL in .env."
        ),
    )
    api_key: str = Field(
        default="",
        description="API key. For local servers any non-empty string works. Set via .env.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature. Lower = more deterministic.",
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum number of tokens to generate.",
    )
    stream: bool = Field(
        default=True,
        description="Whether to use streaming mode.",
    )
    timeout: float = Field(
        default=120.0,
        gt=0,
        description="Request timeout in seconds.",
    )

    model_config = {"frozen": False}


# ── Preset factory functions — read from settings, never hardcoded ────────────

def small_model_config() -> LLMConfig:
    """Return an LLMConfig for the local small/fast model.

    All values are loaded from settings (SMALL_MODEL_* env vars).
    Use this for the local OpenVINO / Ollama / any lightweight endpoint.
    """
    from settings import settings
    return LLMConfig(
        provider=settings.SMALL_MODEL_PROVIDER,  # type: ignore[arg-type]
        model=settings.SMALL_MODEL_NAME,
        base_url=settings.SMALL_MODEL_BASE_URL,
        api_key=settings.SMALL_MODEL_API_KEY,
        temperature=0.2,
        max_tokens=4096,
        stream=True,
    )


def openai_cloud_config(
    model: str = "",
    api_key: str = "",
) -> LLMConfig:
    """Return an LLMConfig for the OpenAI cloud API.

    Args:
        model:   Override model name (e.g. "gpt-4o"). If empty, reads from env.
        api_key: Override API key. If empty, reads from env.
    """
    import os
    return LLMConfig(
        provider="openai",
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
        temperature=0.2,
        max_tokens=4096,
        stream=True,
    )
