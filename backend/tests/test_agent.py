"""Tests for the agent module: run loop, tool-call detection, history summarisation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend/ is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent import Agent, AgentEvent, _TOOL_CALL_RE
from agent.context import AgentContext
from agent.history import ConversationHistory


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def context(tmp_path):
    from llm.config import LLMConfig
    return AgentContext(
        session_id="test-session",
        workspace_dir=tmp_path / "workspace",
        framework="html/css",
        llm_config=LLMConfig(provider="openai", model="mock", api_key="x"),
    )


@pytest.fixture
def history():
    return ConversationHistory(system_prompt="You are a test assistant.")


# ── Tool-call regex tests ──────────────────────────────────────────────────────

def test_tool_call_regex_matches():
    text = 'Some prose\n```tool_call\n{"name": "create_file", "arguments": {"path": "a.html", "content": "hi"}}\n```\nmore prose'
    m = _TOOL_CALL_RE.search(text)
    assert m is not None
    assert '"name": "create_file"' in m.group("json")


def test_tool_call_regex_no_match():
    text = "No tool call here. Just code:\n```html\n<div></div>\n```"
    assert _TOOL_CALL_RE.search(text) is None


# ── History tests ──────────────────────────────────────────────────────────────

def test_history_add_messages():
    h = ConversationHistory(system_prompt="system")
    h.add_user("Hello")
    h.add_assistant("Hi there")
    msgs = h.get_messages()
    assert len(msgs) == 3  # system + user + assistant
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"


def test_history_token_count():
    h = ConversationHistory()
    h.add_user("Hello world this is a test message")
    assert h.token_count() > 0


def test_history_should_not_summarise_short():
    h = ConversationHistory()
    h.add_user("short")
    assert not h.should_summarise()


@pytest.mark.asyncio
async def test_history_summarise():
    h = ConversationHistory(system_prompt="system", summarise_threshold=10)
    for i in range(10):
        h.add_user(f"User message {i} with some longer text to fill up tokens")
        h.add_assistant(f"Assistant response {i} with some longer text to fill up tokens")

    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value="Session summary: User asked for code, assistant generated it.")
    await h.summarise(mock_client)

    msgs = h.get_messages()
    assert msgs[0]["role"] == "system"
    # After summarisation the history should be shorter
    assert len(msgs) < 22


# ── Agent run loop test (mocked LLM) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_simple_run(context, history):
    """Agent should emit tokens and a done event for a plain text response."""
    agent = Agent()

    async def mock_stream(*args, **kwargs):
        for token in ["Hello", " ", "world"]:
            yield token

    with patch("agent.agent.get_llm_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.stream_chat = mock_stream
        mock_client.chat = AsyncMock(return_value="Hello world")
        mock_client.build_vision_message = MagicMock(return_value={"role": "user", "content": []})
        mock_factory.return_value = mock_client

        events = []
        async for event in agent.run(context, history, "Hello"):
            events.append(event)

    types = [e.type for e in events]
    assert "token" in types
    assert "done" in types
    assert "error" not in types


@pytest.mark.asyncio
async def test_agent_tool_call_detected(context, history, tmp_path):
    """Agent should detect a tool_call block and dispatch it."""
    agent = Agent()
    tool_response = (
        'I will create a file.\n'
        '```tool_call\n'
        '{"name": "create_file", "arguments": {"path": "index.html", "content": "<h1>Hi</h1>"}}\n'
        '```'
    )
    plain_response = "Done!"

    call_count = 0

    async def mock_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            for token in tool_response:
                yield token
        else:
            for token in plain_response:
                yield token

    with patch("agent.agent.get_llm_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.stream_chat = mock_stream
        mock_client.chat = AsyncMock(return_value=plain_response)
        mock_client.build_vision_message = MagicMock(return_value={"role": "user", "content": []})
        mock_factory.return_value = mock_client

        events = []
        async for event in agent.run(context, history, "Create a file"):
            events.append(event)

    types = [e.type for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
