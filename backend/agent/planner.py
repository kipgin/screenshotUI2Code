"""TaskPlanner — decomposes a design task into parallel sub-tasks.

When `enable_parallel=True` in the AgentContext, the planner sends the
design description to the LLM and asks it to break the work into
independent components (e.g. Navbar, Hero, Footer).

The output is a list of SubTask objects consumed by api/parallelism.py.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from prompts.parallelism import parallelism_prompt

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    """A single parallelisable code generation task."""

    id: str
    description: str
    output_file: str
    result: str = ""  # populated after generation


class TaskPlanner:
    """Breaks a design description into independent sub-tasks using the LLM."""

    def __init__(self) -> None:
        pass  # prompt is imported directly from prompts.parallelism

    async def plan(
        self,
        design_description: str,
        llm_client: Any,
    ) -> list[SubTask]:
        """Return a list of SubTask objects for parallel generation.

        Args:
            design_description: High-level design goal text.
            llm_client:         Any BaseLLMClient subclass.

        Returns:
            List of SubTask. Falls back to a single task if parsing fails.
        """
        prompt = parallelism_prompt(design_description)
        try:
            response = await llm_client.chat(
                [{"role": "user", "content": prompt}]
            )
            tasks = self._parse_response(response)
            logger.info("TaskPlanner: decomposed into %d sub-tasks.", len(tasks))
            return tasks
        except Exception as exc:
            logger.warning("TaskPlanner: planning failed (%s), falling back to single task.", exc)
            return [SubTask(id="main", description=design_description, output_file="index.html")]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _parse_response(self, response: str) -> list[SubTask]:
        from utils.code_parser import extract_json_block
        raw = extract_json_block(response)
        if not raw:
            raise ValueError("No JSON block found in planner response.")
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Expected a JSON array.")
        tasks = []
        for item in data:
            tasks.append(SubTask(
                id=item["id"],
                description=item["description"],
                output_file=item["output_file"],
            ))
        return tasks
