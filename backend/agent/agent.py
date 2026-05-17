"""Agent — the core agentic run loop.

The Agent class orchestrates:
  1. Building the prompt from context (system prompt, tool schema, history)
  2. Calling the LLM pipeline (streaming)
  3. Detecting and dispatching tool calls
  4. Re-entering the loop after each tool result (agentic iteration)
  5. Auto-committing to git after a successful generation turn
  6. Emitting structured AgentEvent objects to the caller

Usage:
    agent = Agent()
    context = AgentContext(framework="react", ...)
    history = ConversationHistory(system_prompt=...)

    async for event in agent.run(context, history, user_message="Make it dark mode"):
        if event.type == "token":
            print(event.data, end="", flush=True)
        elif event.type == "tool_call":
            print(f"\n[calling tool: {event.data['name']}]")
        elif event.type == "done":
            break
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Literal

from agent.context import AgentContext
from agent.history import ConversationHistory
from llm.factory import get_llm_client
from tool import registry
from tool.schema import ToolCall
from utils.response_fixer import ResponseFixer, requires_non_empty

logger = logging.getLogger(__name__)

# Pattern that detects a tool call fence in the accumulated stream text
_TOOL_CALL_RE = re.compile(
    r"```tool_call\s*\n(?P<json>[\s\S]*?)(?:\n```|$)",
    re.DOTALL,
)


@dataclass
class AgentEvent:
    """A single event emitted by the agent run loop."""

    type: Literal["token", "tool_call", "tool_result", "error", "done"]
    data: Any = None


class Agent:
    """The main agent class.

    One Agent instance can handle multiple sessions concurrently — it is
    stateless; all session state lives in AgentContext and ConversationHistory.
    """

    def __init__(self) -> None:
        self._fixer = ResponseFixer(max_retries=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        context: AgentContext,
        history: ConversationHistory,
        user_message: Any,           # str or vision content list
        image_path: Path | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run one agent turn and yield AgentEvent objects.

        Args:
            context:      Session state.
            history:      Mutable conversation history.
            user_message: The new user input (text or vision content list).
            image_path:   Optional image for vision turn (overrides user_message build).

        Yields:
            AgentEvent objects: tokens, tool calls, tool results, done.
        """
        llm_client = get_llm_client(context.llm_config)

        # Build the user message (possibly vision)
        if image_path:
            from utils.image_utils import encode_image_base64, get_image_media_type
            b64 = encode_image_base64(image_path)
            media_type = get_image_media_type(image_path) or "image/png"
            msg_content = llm_client.build_vision_message(
                "user", str(user_message), b64, media_type
            )["content"]
            history.add_user(msg_content)
        else:
            # Look for index.html in the workspace to supply as current_code for refinement
            current_code = ""
            if context.workspace_dir:
                index_path = Path(context.workspace_dir) / "index.html"
                if index_path.exists():
                    try:
                        current_code = index_path.read_text(encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Failed to read index.html: {e}")
            
            if current_code:
                from prompts.refinement import refinement_prompt
                reinforced_message = refinement_prompt(current_code, str(user_message))
            else:
                reinforced_message = str(user_message)
                
            # Append a highly detailed workspace file map with sizes
            ws_map = ""
            if context.workspace_dir:
                ws_path = Path(context.workspace_dir)
                tree = _get_workspace_tree_summary(ws_path)
                if tree:
                    ws_map = f"\n\n[Current Workspace Files & Sizes]:\n{tree}\n(Note: If any file like styles.css is 0 bytes, it is empty. You must populate it using write_file/create_file.)"

            # Always reinforce the tool call formatting requirements
            if "[System Reminder:" not in reinforced_message:
                reinforced_message += (
                    ws_map +
                    "\n\n[System Reminder: You are in an agentic loop. "
                    "To create, edit, or delete files, you MUST use `create_file` or other tools by outputting a valid JSON block "
                    "wrapped in a ```tool_call code fence. Do NOT output raw code fences like ```html or ```css directly in your text "
                    "without calling a tool. Always invoke tools to save your code!]"
                )
            history.add_user(reinforced_message)

        # Strip old base64 images to free up token context and bandwidth
        history.strip_old_base64_images()

        # Proactive summarisation
        if history.should_summarise():
            logger.info("Agent: summarising history (tokens=%d).", history.token_count())
            await history.summarise(llm_client)

        # Agentic loop
        for iteration in range(context.max_iterations):
            accumulated = ""
            messages = history.get_messages()

            # Stream from LLM
            async for token in llm_client.stream_chat(messages):
                accumulated += token
                yield AgentEvent(type="token", data=token)

            # Validate non-empty response
            accumulated = await self._fixer.fix(
                response=accumulated,
                check_fn=requires_non_empty,
                correction_prompt="Your response was empty. Please provide a valid response.",
                llm_client=llm_client,
                messages=messages,
            )

            # Check for tool call in the accumulated response
            tool_match = _TOOL_CALL_RE.search(accumulated)

            if tool_match:
                # Add the full response including the tool call to history so the LLM remembers what it wrote!
                history.add_assistant(accumulated)

                # Parse and dispatch tool call
                tc_dict = None
                raw_json = tool_match.group("json")
                try:
                    tc_dict = json.loads(raw_json)
                except (json.JSONDecodeError, KeyError):
                    # Fallback to our custom robust malformed JSON parser
                    from utils.json_repair import try_parse_malformed_tool_call
                    tc_dict = try_parse_malformed_tool_call(raw_json)

                if tc_dict:
                    try:
                        tool_call = ToolCall(
                            name=tc_dict.get("name", ""),
                            arguments=tc_dict.get("arguments", {}),
                        )
                    except Exception as exc:
                        yield AgentEvent(type="error", data=f"Failed to instantiate tool call: {exc}")
                        break
                else:
                    yield AgentEvent(type="error", data="Failed to parse malformed tool call JSON.")
                    break

                yield AgentEvent(type="tool_call", data=tc_dict)
                tool_result = await registry.dispatch(tool_call, context.workspace_str)
                yield AgentEvent(type="tool_result", data=tool_result.model_dump())

                # Inject tool result into history and loop again
                history.add_tool_result(tool_call.name, tool_result.to_message())
                continue  # next iteration

            else:
                # No tool call — final response for this turn
                history.add_assistant(accumulated)

                # Auto git commit after each successful turn
                await self._auto_commit(context, iteration)

                yield AgentEvent(type="done", data=None)
                return

        # Exceeded max iterations
        yield AgentEvent(
            type="error",
            data=f"Agent exceeded max iterations ({context.max_iterations}).",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _auto_commit(self, context: AgentContext, iteration: int) -> None:
        """Commit generated files to the workspace git repo using a premium LLM-generated commit message."""
        from tool.git_tools import git_commit, _get_repo
        
        commit_msg = f"AI generation — turn {iteration + 1}"
        try:
            repo = _get_repo(context.workspace_str)
            # Check if we have untracked changes or modified changes
            untracked = repo.untracked_files
            diff_index = repo.index.diff("HEAD") if repo.head.is_valid() else []
            modified = [item.a_path for item in diff_index]
            
            changed_files = list(set(untracked + modified))
            if not changed_files:
                logger.info("Agent: no changes detected to commit.")
                return

            # Extract a brief git diff
            diff_text = ""
            if repo.head.is_valid():
                diff_text = repo.git.diff("HEAD")
            else:
                # First commit has no HEAD, use diff of index
                diff_text = repo.git.diff()
                
            if len(diff_text) > 2000:
                diff_text = diff_text[:2000] + "\n... (truncated)"
                
            # Perform out-of-band LLM query (completely independent of history)
            llm_client = get_llm_client(context.llm_config)
            sys_msg = (
                "You are an expert developer. Generate a very concise, professional Git commit message "
                "in English (maximum 50 characters, one line, e.g., 'Update login form styling') describing the changes "
                "shown in the diff/status. Return ONLY the commit message text, with no markdown, no quotes, and no intro."
            )
            user_msg = f"Changed files: {', '.join(changed_files)}\n\nDiff:\n{diff_text}"
            
            response = await llm_client.chat([
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg}
            ])
            
            clean_msg = response.strip().replace('"', '').replace("'", "")
            if clean_msg and len(clean_msg) < 120:
                commit_msg = clean_msg
            else:
                commit_msg = f"Update files: {', '.join(changed_files[:3])}"
        except Exception as e:
            logger.warning(f"Failed to generate custom commit message with LLM: {e}")

        result = await git_commit(message=commit_msg, workspace=context.workspace_str)
        if result.success:
            logger.info("Agent: auto-committed with message '%s': %s", commit_msg, result.output)
        else:
            logger.warning("Agent: auto-commit failed: %s", result.error)


def _get_workspace_tree_summary(base_dir: Path, current_dir: Path = None, indent: str = "") -> str:
    """Recursively builds a clean ASCII directory/file tree of the workspace with file sizes."""
    if current_dir is None:
        current_dir = base_dir
    lines = []
    try:
        entries = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for entry in entries:
            if entry.name in (".git", "__pycache__", ".gemini", "node_modules"):
                continue
            if entry.is_dir():
                lines.append(f"{indent}📁 {entry.name}/")
                sub = _get_workspace_tree_summary(base_dir, entry, indent + "  ")
                if sub:
                    lines.append(sub)
            else:
                size = entry.stat().st_size
                lines.append(f"{indent}📄 {entry.name} ({size} bytes)")
    except Exception:
        pass
    return "\n".join(lines)


