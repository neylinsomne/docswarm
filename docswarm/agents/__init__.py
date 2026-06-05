"""Agents — the swarm members.

An agent is a small, stateless worker that writes ONE section, bounded by its
``SectionContract``. Agents never call each other; they coordinate through the
blackboard (anchors) and stay disjoint through their contracts.

  - ``BaseAgent``  : the interface (build a prompt, call the LLM, return result).
  - ``LLMAgent``   : a ready generic agent — system prompt + LLMPort → section.
  - ``JudgeAgent`` : a non-writing agent that scores a generated section.

Your domain subclasses or instantiates these with its own system prompts. None
of it is hardcoded to any business.
"""

from __future__ import annotations

from docswarm.agents.base import BaseAgent, LLMAgent, SectionRequest, SectionResult
from docswarm.agents.judge import JudgeAgent, JudgeReport

__all__ = [
    "BaseAgent", "LLMAgent", "SectionRequest", "SectionResult",
    "JudgeAgent", "JudgeReport",
]
