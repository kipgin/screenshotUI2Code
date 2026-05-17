# Architecture: AI Frontend Design Backend

## Overview

A production-grade backend that powers an AI agent to **design and generate frontend code from screenshots and multi-turn text feedback**. The local model server (OpenVINO / Qwen2.5 Coder) is treated as an OpenAI-compatible endpoint, and the backend wraps it with an agentic loop, tool execution, streaming API, and session management.

---

## System Design Philosophy

- **Agent-first**: The core is an agentic reasoning loop — not a simple request/response.
- **Tool-augmented**: The LLM can call structured tools to create/edit/delete files — all managed by the `tool` module.
- **Streaming-native**: All LLM responses are streamed token-by-token to the client via Server-Sent Events (SSE) or WebSocket.
- **Provider-agnostic LLM**: The `llm` module abstracts over OpenAI, Anthropic, Gemini, and any local OpenAI-compatible endpoint (e.g., the local OpenVINO server).
- **Parallelizable**: Code generation for independent UI modules can run in parallel when configured.
- **Testable**: Each submodule has co-located tests.

---

## Module Map

```text
backend/
├── agent/                   # 1. Core agentic loop
│   ├── __init__.py
│   ├── agent.py             # Main Agent class with the run loop
│   ├── history.py           # Conversation history + summarization
│   ├── context.py           # AgentContext: holds state for one design session
│   └── planner.py           # (Optional) High-level task planning / decomposition
│
├── api/                     # 2. FastAPI HTTP + WebSocket API
│   ├── __init__.py
│   ├── app.py               # FastAPI app factory with lifespan
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── design.py        # REST endpoints: /upload, /feedback, /session
│   │   └── health.py        # /health, /readiness
│   ├── ws/
│   │   ├── __init__.py
│   │   └── design_ws.py     # WebSocket endpoint for streaming agent output
│   ├── pipeline.py          # Main LLM call pipeline (streaming, retries, SSE emit)
│   └── parallelism.py       # Parallel code generation manager (asyncio TaskGroup)
│
├── tool/                    # 3. Agent tool execution
│   ├── __init__.py
│   ├── registry.py          # Tool registry — maps tool name -> handler
│   ├── schema.py            # Pydantic schemas for tool call inputs/outputs
│   ├── file_tools.py        # create_file, edit_file, delete_file, read_file
│   ├── folder_tools.py      # create_folder, delete_folder, list_folder
│   ├── diff_tools.py        # generate_diff, apply_diff, view_diff
│   ├── git_tools.py         # commit, create_branch, get_log
│   └── prompts/
│       ├── tool_system.md   # System prompt injected when tools are enabled
│       └── tool_format.md   # Format instructions for JSON tool call output
│
├── prompts/                 # 4. All prompt instruction files
│   ├── system_base.md       # Base system prompt for the design agent
│   ├── vision_analysis.md   # Prompt for first-pass screenshot analysis
│   ├── code_generation.md   # Prompt for generating initial HTML/CSS/JS/React
│   ├── refinement.md        # Prompt for applying user feedback to existing code
│   ├── summarization.md     # Prompt for summarizing old conversation history
│   └── parallelism.md       # Prompt for splitting design into parallel tasks
│
├── llm/                     # 5. LLM provider abstraction
│   ├── __init__.py
│   ├── base.py              # BaseLLMClient ABC (stream_chat, chat, count_tokens)
│   ├── config.py            # LLMConfig: model, temperature, max_tokens, provider, etc.
│   ├── openai_client.py     # OpenAI + local OpenVINO-compatible endpoint
│   ├── anthropic_client.py  # Anthropic Claude client
│   ├── gemini_client.py     # Google Gemini client
│   └── factory.py           # get_llm_client(config) factory function
│
├── utils/                   # 6. Parsing, fixing, helpers
│   ├── __init__.py
│   ├── code_parser.py       # Extract HTML/CSS/JS/TS/React from markdown
│   ├── text_utils.py        # Clean text, truncation, token estimation
│   ├── response_fixer.py    # Detect bad format → re-prompt → get corrected response
│   └── image_utils.py       # Encode image to base64 for vision API calls
│
└── tests/                   # 7. Test suite
    ├── __init__.py
    ├── test_agent.py
    ├── test_api.py
    ├── test_tools.py
    ├── test_llm.py
    ├── test_utils.py
    └── fixtures/
        ├── sample_screenshot.png
        └── sample_response.txt
```

---

## Data Flow

### Turn 1 — Screenshot Upload
```
Client
  │─ POST /api/upload (multipart: image + framework) ──────────────────────────────►
  │                                                                              API Layer
  │                                                                          (api/routes/design.py)
  │                                                              Save image → Create AgentContext
  │                                                                                │
  │                                                              Image encoded as base64 (utils/image_utils.py)
  │                                                                                │
  │                                                              Agent.run(context) ──► LLM Vision call (streaming)
  │                                                                                │
  │◄─ SSE stream: token-by-token code ──────────────────────────────────────────────
  │
  │  [tool call detected in stream]
  │                                                              tool/registry.py dispatches → file_tools.py
  │                                                              Files written to workspace/session_id/
  │                                                              git_tools.py: auto-commit "Initial generation"
  │◄─ SSE: tool_result event ───────────────────────────────────────────────────────
```

### Turn N — Multi-turn Feedback
```
Client
  │─ WS /ws/design/{session_id} ────────────────────────────────────────────────────►
  │                                                              ws/design_ws.py
  │─ send: { "feedback": "Make the button blue" } ──────────────────────────────────►
  │                                                              history.py: append message
  │                                                              history.py: check if summarize needed
  │                                                              Agent.run(context, feedback)
  │                                                              pipeline.py: stream LLM call
  │◄─ WS stream: { type: "token", content: "..." } ────────────────────────────────
  │◄─ WS stream: { type: "tool_call", tool: "edit_file", ... } ─────────────────────
  │◄─ WS stream: { type: "tool_result", ... } ─────────────────────────────────────
  │◄─ WS stream: { type: "done" } ─────────────────────────────────────────────────
```

---

## Module Details

### 1. `agent/` — Agentic Loop

**`agent.py`** — `Agent` class
- `async def run(context, user_message) → AsyncGenerator[AgentEvent]`
- Inner loop:
  1. Build prompt from context (history, system prompt, tool schema)
  2. Call `pipeline.stream_llm()`
  3. If tool call detected: dispatch to `tool/registry.py`, inject result into history
  4. If no tool call: finalize, emit `done` event
  5. Repeat (agentic loop) until stop condition

**`history.py`** — `ConversationHistory`
- Stores messages as a list of `Message` objects
- `add_message(role, content)`
- `should_summarize() → bool` (configurable token threshold)
- `summarize(llm_client) → None` — replaces old turns with a summary using `prompts/summarization.md`
- `get_messages() → list[Message]`

**`context.py`** — `AgentContext`
- Holds `session_id`, `workspace_dir`, `history`, `framework`, current `LLMConfig`

**`planner.py`** — `TaskPlanner` (optional)
- Breaks a complex design task into sub-tasks (e.g., header, hero, footer) to feed `api/parallelism.py`

---

### 2. `api/` — HTTP + WebSocket

**`pipeline.py`** — `LLMPipeline`
- `async def stream_chat(messages, llm_client) → AsyncGenerator[str]`
- Handles retries, error recovery, and token accumulation
- Detects tool calls in the streamed output (by matching a JSON block pattern)
- Invokes `utils/response_fixer.py` if format is invalid

**`parallelism.py`** — `ParallelCodeGenerator`
- `async def generate_parallel(tasks: list[SubTask], llm_client) → list[CodeResult]`
- Uses `asyncio.TaskGroup` to run independent code generation calls concurrently
- Controlled by `ENABLE_PARALLEL_GENERATION` config flag

**`ws/design_ws.py`** — WebSocket handler
- Accepts WebSocket connection keyed to `session_id`
- Streams `AgentEvent` objects as JSON frames to the client
- Handles client disconnection gracefully

---

### 3. `tool/` — Tool Execution

**`registry.py`** — `ToolRegistry`
- `register(name, handler, schema)` — decorates tool handler functions
- `dispatch(tool_call: ToolCall) → ToolResult` — routes parsed tool calls to the right handler
- Generates the JSON schema injected into the LLM system prompt

**Tool Definitions (all return `ToolResult`):**

| File | Tools |
|------|-------|
| `file_tools.py` | `create_file`, `read_file`, `edit_file`, `delete_file` |
| `folder_tools.py` | `create_folder`, `list_folder`, `delete_folder` |
| `diff_tools.py` | `generate_diff`, `apply_diff`, `preview_diff` |
| `git_tools.py` | `git_commit`, `git_create_branch`, `git_log`, `git_status` |

**`prompts/tool_system.md`** — injected as system context to make the LLM aware of available tools and their call format (JSON block).

---

### 4. `prompts/` — Prompt Files

All prompts are plain Markdown/text files loaded at runtime, keeping logic separate from text.

| File | Purpose |
|------|---------|
| `system_base.md` | Core agent identity and behavior rules |
| `vision_analysis.md` | Instructions to analyze a screenshot layout |
| `code_generation.md` | Instructions to generate initial frontend code |
| `refinement.md` | Instructions to apply iterative user feedback |
| `summarization.md` | Instructions to compress long conversation history |
| `parallelism.md` | Instructions to split design into independent modules |

---

### 5. `llm/` — Provider Abstraction

**`base.py`** — `BaseLLMClient` ABC
```python
class BaseLLMClient(ABC):
    async def stream_chat(self, messages, **kwargs) -> AsyncGenerator[str]: ...
    async def chat(self, messages, **kwargs) -> str: ...
    def count_tokens(self, text: str) -> int: ...
```

**`openai_client.py`** — Works with OpenAI AND the local OpenVINO server (`base_url` configurable)
- Implements streaming via `openai` package's `stream=True`

**`config.py`** — `LLMConfig`
- `provider`: `openai | anthropic | gemini`
- `model`: e.g., `gpt-4o`, `qwen2.5-coder-ov`
- `base_url`: for local server override
- `api_key`, `temperature`, `max_tokens`, `stream`

---

### 6. `utils/` — Helpers

**`code_parser.py`**
- `extract_code_blocks(text) → dict[lang, code]` — extracts all fenced code blocks by language
- `reconstruct_html(html, css, js) → str` — assembles a full HTML document
- Supports: `html`, `css`, `js`, `jsx`, `tsx`, `python`, `json`, etc.

**`response_fixer.py`** — `ResponseFixer`
- `check_format(response, expected_format) → bool`
- `fix(response, llm_client, context) → str` — sends a correction prompt and re-generates; adds to history only after passing format check

**`text_utils.py`**
- `estimate_tokens(text) → int`
- `truncate_to_token_limit(text, limit) → str`

**`image_utils.py`**
- `encode_image_base64(path) → str`
- `get_image_media_type(path) → str`

---

### 7. `tests/`

Each submodule has a corresponding test file using `pytest` + `pytest-asyncio`:

| Test File | Covers |
|-----------|--------|
| `test_agent.py` | Agent run loop, tool call detection, history summarization |
| `test_api.py` | FastAPI endpoints, WebSocket frames, SSE output |
| `test_tools.py` | File CRUD, git commit, diff generation |
| `test_llm.py` | Mock streaming responses, token counting |
| `test_utils.py` | Code parsing, response fixing, image encoding |

---

## Configuration

```env
# LLM Provider
LLM_PROVIDER=openai
LLM_MODEL=qwen2.5-coder-ov
LLM_BASE_URL=http://localhost:8000/v1
LLM_API_KEY=local-gpu

# Agent
AGENT_MAX_ITERATIONS=10
HISTORY_SUMMARIZE_THRESHOLD=8000   # tokens
ENABLE_PARALLEL_GENERATION=false

# Git
GIT_AUTO_COMMIT=true
GIT_WORKSPACE_ROOT=./workspaces

# Uploads
UPLOAD_DIR=./uploads
```

---

## Key Design Decisions

1. **Streaming is mandatory**: Every LLM response is streamed. The `pipeline.py` accumulates tokens in parallel to detect tool calls without blocking the stream to the client.
2. **Tool calls are JSON blocks**: The LLM is instructed (via prompts) to output tool calls as a special JSON block within its text stream. The pipeline scans for these blocks as tokens arrive.
3. **Workspaces are git repos**: Each session has its own folder initialized as a git repo. Every successful agent response auto-commits, giving the user a full history they can roll back.
4. **History summarization is proactive**: When the estimated token count of history exceeds `HISTORY_SUMMARIZE_THRESHOLD`, the oldest non-system messages are replaced by a one-paragraph summary.
5. **Local OpenVINO server is treated as an OpenAI endpoint**: The `openai_client.py` just needs `base_url=http://localhost:8000/v1`, making it transparent.
