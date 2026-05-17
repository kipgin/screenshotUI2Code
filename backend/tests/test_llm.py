"""Tests for the LLM module: config, factory, base class contracts."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.config import LLMConfig, small_model_config, openai_cloud_config
from llm.factory import get_llm_client
from llm.base import BaseLLMClient


# ── Config tests ──────────────────────────────────────────────────────────────

def test_small_model_config():
    cfg = small_model_config()
    assert cfg.provider == "openai"
    assert cfg.base_url == "http://localhost:8000/v1"
    assert cfg.stream is True


def test_openai_cloud_config():
    cfg = openai_cloud_config(api_key="sk-test")
    assert cfg.provider == "openai"
    assert cfg.api_key == "sk-test"
    assert cfg.model == "gpt-4o"


def test_llm_config_defaults():
    cfg = LLMConfig()
    assert cfg.temperature == 0.2
    assert cfg.max_tokens == 4096


# ── Factory tests ─────────────────────────────────────────────────────────────

def test_factory_returns_openai_client():
    from llm.openai_client import OpenAIClient
    cfg = small_model_config()
    client = get_llm_client(cfg)
    assert isinstance(client, OpenAIClient)


def test_factory_unknown_provider_raises():
    cfg = LLMConfig(provider="openai")  # start valid
    cfg.provider = "unknown"            # patch
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_client(cfg)


# ── BaseLLMClient helpers ─────────────────────────────────────────────────────

def test_base_build_text_message():
    # Use OpenAIClient as concrete instance
    from llm.openai_client import OpenAIClient
    client = OpenAIClient(small_model_config())
    msg = client.build_text_message("user", "hello")
    assert msg == {"role": "user", "content": "hello"}


def test_base_build_vision_message():
    from llm.openai_client import OpenAIClient
    client = OpenAIClient(small_model_config())
    msg = client.build_vision_message("user", "Analyse this", "BASE64DATA==", "image/png")
    assert msg["role"] == "user"
    assert isinstance(msg["content"], list)
    text_part = msg["content"][0]
    image_part = msg["content"][1]
    assert text_part["type"] == "text"
    assert "BASE64DATA" in image_part["image_url"]["url"]


def test_base_build_system_message():
    from llm.openai_client import OpenAIClient
    client = OpenAIClient(small_model_config())
    msg = client.build_system_message("You are an expert.")
    assert msg == {"role": "system", "content": "You are an expert."}


def test_count_tokens_heuristic():
    """When tiktoken is not available, falls back to chars/4 heuristic."""
    from llm.openai_client import OpenAIClient
    client = OpenAIClient(small_model_config())
    # "hello world" = 11 chars → ~2 tokens by heuristic
    count = client.count_tokens("hello world")
    assert count > 0


# ── Stub clients raise NotImplementedError ────────────────────────────────────

@pytest.mark.asyncio
async def test_anthropic_stub_raises():
    from llm.anthropic_client import AnthropicClient
    cfg = LLMConfig(provider="anthropic")
    client = AnthropicClient(cfg)
    with pytest.raises(NotImplementedError):
        await client.chat([])


@pytest.mark.asyncio
async def test_gemini_stub_raises():
    from llm.gemini_client import GeminiClient
    cfg = LLMConfig(provider="gemini")
    client = GeminiClient(cfg)
    with pytest.raises(NotImplementedError):
        await client.chat([])
