"""Design REST endpoints — upload, feedback (SSE), session info."""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from agent.agent import Agent, AgentEvent
from agent.context import AgentContext
from agent.history import ConversationHistory
from api.parallelism import ParallelCodeGenerator
from api.ws.design_ws import register_session, unregister_session
from llm.config import LLMConfig, small_model_config
from utils.text_utils import clean_llm_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/design", tags=["design"])

_agent = Agent()
_parallel_gen = ParallelCodeGenerator()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ── In-memory session store (replace with Redis/DB for production) ────────────

_sessions: dict[str, tuple[AgentContext, ConversationHistory]] = {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_screenshot(
    file: UploadFile = File(...),
    framework: str = Form("html/css"),
    enable_parallel: bool = Form(False),
):
    """Upload a screenshot and start initial code generation (SSE stream).

    Returns a streaming response of Server-Sent Events:
        data: {"type": "token", "data": "..."}
        data: {"type": "tool_call", "data": {...}}
        data: {"type": "tool_result", "data": {...}}
        data: {"type": "session_id", "data": "<id>"}
        data: {"type": "done"}
    """
    session_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix if file.filename else ".png"
    img_path = UPLOAD_DIR / f"{session_id}{ext}"
    img_path.write_bytes(await file.read())

    llm_config = small_model_config()
    context = AgentContext(
        session_id=session_id,
        workspace_dir=Path("workspaces") / session_id,
        framework=framework,
        llm_config=llm_config,
        screenshot_path=img_path,
        enable_parallel=enable_parallel,
    )

    from prompts.system_base import SYSTEM_BASE
    from prompts.vision_analysis import vision_analysis_prompt
    from prompts.code_generation import code_generation_prompt
    from tool.prompts import tool_system_prompt, TOOL_FORMAT
    from tool.registry import registry

    # Load and build the system prompt
    tool_schema_json = registry.get_schema_json()
    full_system_prompt = f"{SYSTEM_BASE}\n\n{tool_system_prompt(tool_schema_json)}\n\n{TOOL_FORMAT}"
    history = ConversationHistory(system_prompt=full_system_prompt)

    register_session(session_id, context, history)
    _sessions[session_id] = (context, history)

    # Build initial user message using vision + analysis prompt
    v_prompt = vision_analysis_prompt(framework)
    g_prompt = code_generation_prompt(framework)
    user_text = f"{v_prompt}\n\n---\n\n{g_prompt}"

    async def event_stream():
        # First emit session_id so client can connect WebSocket
        yield _sse({"type": "session_id", "data": session_id})

        if enable_parallel:
            # Parallel generation path
            completed_tasks = await _parallel_gen.generate(user_text, context)
            for task in completed_tasks:
                yield _sse({"type": "file_written", "data": task.output_file})
            yield _sse({"type": "done"})
        else:
            # Standard agentic path with streaming
            async for event in _agent.run(context, history, user_text, image_path=img_path):
                yield _sse(event_to_dict(event))
                if event.type == "done":
                    break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/feedback")
async def submit_feedback(
    session_id: str = Form(...),
    feedback: str = Form(...),
):
    """Submit multi-turn feedback as an SSE stream."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    context, history = _sessions[session_id]

    async def event_stream():
        async for event in _agent.run(context, history, feedback):
            yield _sse(event_to_dict(event))
            if event.type == "done":
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Return session metadata and conversation history."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    context, history = _sessions[session_id]
    return {
        "session_id": session_id,
        "framework": context.framework,
        "workspace": context.workspace_str,
        "message_count": len(history),
        "token_count": history.token_count(),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Remove a session from memory."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    _sessions.pop(session_id, None)
    unregister_session(session_id)
    return {"detail": "Session removed."}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def event_to_dict(event: AgentEvent) -> dict:
    d: dict = {"type": event.type}
    if event.data is not None:
        d["data"] = event.data
    return d
