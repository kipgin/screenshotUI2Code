"""Prompts package — all LLM instruction strings in one place.

Import examples:
    from prompts.system_base import SYSTEM_BASE
    from prompts.vision_analysis import vision_analysis_prompt
    from prompts.code_generation import code_generation_prompt
    from prompts.refinement import refinement_prompt
    from prompts.summarization import summarization_prompt
    from prompts.parallelism import parallelism_prompt
"""

from .system_base import SYSTEM_BASE
from .vision_analysis import vision_analysis_prompt
from .code_generation import code_generation_prompt
from .refinement import refinement_prompt
from .summarization import summarization_prompt
from .parallelism import parallelism_prompt

__all__ = [
    "SYSTEM_BASE",
    "vision_analysis_prompt",
    "code_generation_prompt",
    "refinement_prompt",
    "summarization_prompt",
    "parallelism_prompt",
]
