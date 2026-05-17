"""ToolRegistry — registers, documents, and dispatches tool calls.

Tools are registered via the @registry.register() decorator. The registry
can generate a JSON schema description for injection into LLM prompts.

Example:
    registry = ToolRegistry()

    @registry.register(
        name="create_file",
        description="Create a new file with given content.",
        args_schema=CreateFileArgs,
    )
    async def create_file(path: str, content: str, workspace: str) -> ToolResult:
        ...
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

from .schema import ToolCall, ToolResult

logger = logging.getLogger(__name__)


class _RegisteredTool:
    def __init__(
        self,
        name: str,
        handler: Callable,
        description: str,
        args_schema: Optional[Type[BaseModel]],
    ) -> None:
        self.name = name
        self.handler = handler
        self.description = description
        self.args_schema = args_schema
        self.is_async = inspect.iscoroutinefunction(handler)

    def schema_dict(self) -> dict[str, Any]:
        """Produce an OpenAI-style function schema for LLM injection."""
        props: dict[str, Any] = {}
        required: list[str] = []
        if self.args_schema:
            for field_name, field_info in self.args_schema.model_fields.items():
                props[field_name] = {
                    "type": "string",
                    "description": field_info.description or "",
                }
                if field_info.is_required():
                    required.append(field_name)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        }


class ToolRegistry:
    """Central registry for agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, _RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        args_schema: Optional[Type[BaseModel]] = None,
    ) -> Callable:
        """Decorator factory. Usage:

            @registry.register("create_file", "Create a file.", CreateFileArgs)
            async def create_file(...): ...
        """
        def decorator(fn: Callable) -> Callable:
            self._tools[name] = _RegisteredTool(name, fn, description, args_schema)
            return fn
        return decorator

    async def dispatch(self, tool_call: ToolCall, workspace: str) -> ToolResult:
        """Route a tool call to the correct handler.

        Args:
            tool_call: Parsed ToolCall from the LLM response.
            workspace: Absolute path to the session workspace directory.

        Returns:
            ToolResult with success/failure info.
        """
        tool = self._tools.get(tool_call.name)
        if tool is None:
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                output="",
                error=f"Unknown tool: '{tool_call.name}'. Available: {list(self._tools)}",
            )

        try:
            args = {**tool_call.arguments, "workspace": workspace}
            if tool.is_async:
                result = await tool.handler(**args)
            else:
                result = tool.handler(**args)
            return result
        except TypeError as exc:
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                output="",
                error=f"Argument error: {exc}",
            )
        except Exception as exc:
            logger.exception("Tool '%s' raised an unexpected error.", tool_call.name)
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                output="",
                error=str(exc),
            )

    def get_schema_json(self) -> str:
        """Return a JSON string of all tool schemas for injection into a system prompt."""
        schemas = [t.schema_dict() for t in self._tools.values()]
        return json.dumps(schemas, indent=2)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


# ── Singleton registry used throughout the backend ────────────────────────────
registry = ToolRegistry()
