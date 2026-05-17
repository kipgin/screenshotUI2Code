"""Parallel code generation — runs independent sub-tasks concurrently.

When `enable_parallel=True` in the request, the agent first uses TaskPlanner
to decompose the design description into sub-tasks, then generates each
sub-task simultaneously using asyncio.TaskGroup.

The results are merged: each generated file is written to the workspace,
then a final assembly turn produces an index.html that imports everything.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from agent.context import AgentContext
from agent.planner import SubTask, TaskPlanner
from llm.factory import get_llm_client
from tool.file_tools import create_file

logger = logging.getLogger(__name__)


class ParallelCodeGenerator:
    """Runs sub-tasks in parallel and merges results into the workspace."""

    def __init__(self) -> None:
        self._planner = TaskPlanner()

    async def generate(
        self,
        design_description: str,
        context: AgentContext,
    ) -> list[SubTask]:
        """Decompose and generate all sub-tasks in parallel.

        Args:
            design_description: High-level design goal.
            context:            Session context (workspace, llm_config, framework).

        Returns:
            List of completed SubTask objects with `result` populated.
        """
        llm_client = get_llm_client(context.llm_config)
        tasks = await self._planner.plan(design_description, llm_client)
        logger.info("ParallelCodeGenerator: running %d sub-tasks.", len(tasks))

        # Python 3.11+ asyncio.TaskGroup for structured concurrency
        async with asyncio.TaskGroup() as tg:
            coros = [
                tg.create_task(self._generate_one(task, context, llm_client))
                for task in tasks
            ]

        # coros are done at this point; results stored in task.result
        completed = [t.result() for t in coros]

        # Write files to workspace
        for sub_task, code in zip(tasks, completed):
            sub_task.result = code
            await create_file(
                path=sub_task.output_file,
                content=code,
                workspace=context.workspace_str,
            )
            logger.info("ParallelCodeGenerator: wrote %s", sub_task.output_file)

        return tasks

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _generate_one(
        self,
        sub_task: SubTask,
        context: AgentContext,
        llm_client: Any,
    ) -> str:
        """Generate code for a single sub-task."""
        from prompts.code_generation import code_generation_prompt
        prompt = code_generation_prompt(context.framework)

        full_prompt = (
            f"{prompt}\n\n"
            f"## Your specific task\n{sub_task.description}\n\n"
            f"Output file: `{sub_task.output_file}`"
        )

        messages = [{"role": "user", "content": full_prompt}]
        try:
            result = await llm_client.chat(messages)
            return result
        except Exception as exc:
            logger.error("Sub-task '%s' failed: %s", sub_task.id, exc)
            return f"/* Generation failed: {exc} */"
