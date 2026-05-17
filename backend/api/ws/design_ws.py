"""WebSocket handler for real-time streaming design sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

from agent.agent import Agent, AgentEvent
from agent.context import AgentContext
from agent.history import ConversationHistory

logger = logging.getLogger(__name__)

_agent = Agent()
_sessions: dict[str, tuple[AgentContext, ConversationHistory]] = {}


async def design_ws_handler(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint handler for /ws/design/{session_id}.

    Protocol (JSON frames):
    - Client → Server: { "type": "feedback", "content": "..." }
    - Server → Client: { "type": "token", "data": "..." }
                       { "type": "tool_call", "data": {...} }
                       { "type": "tool_result", "data": {...} }
                       { "type": "done" }
                       { "type": "error", "data": "..." }
    """
    await websocket.accept()
    logger.info("WebSocket connected: session=%s", session_id)

    if session_id not in _sessions:
        await websocket.send_json({"type": "error", "data": "Session not found. Upload a screenshot first."})
        await websocket.close()
        return

    context, history = _sessions[session_id]

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": "Invalid JSON."})
                continue

            msg_type = msg.get("type")
            if msg_type == "feedback":
                feedback = msg.get("content", "").strip()
                if not feedback:
                    continue

                async for event in _agent.run(context, history, feedback):
                    await _emit_event(websocket, event)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({"type": "error", "data": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)


async def _emit_event(ws: WebSocket, event: AgentEvent) -> None:
    payload: dict = {"type": event.type}
    if event.data is not None:
        payload["data"] = event.data
    await ws.send_json(payload)


def register_session(
    session_id: str,
    context: AgentContext,
    history: ConversationHistory,
) -> None:
    """Register a session so the WebSocket handler can find it."""
    _sessions[session_id] = (context, history)


def unregister_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
