"""The swarm for the demo: three agents, zero business domain.

  - tabulator : writes the metrics section and PRODUCES the metrics table.
  - analyst   : writes the analysis and CITES that table (never reprints it).
  - judge     : scores each section (the swarm's quality vote).

They are plain ``LLMAgent`` instances differing only by their system prompt.
With ``StubLLM`` they run fully offline; with ``OllamaLLM`` they call a local
model. Nothing here is tied to any industry — swap the prompts and the plan and
the same swarm writes a different kind of document.
"""

from __future__ import annotations

from docswarm.agents import JudgeAgent, LLMAgent

TABULATOR_SYSTEM = (
    "You are a data tabulator. You turn shared facts into clean tables. "
    "Write a short lead sentence and then the required table. Use the exact "
    "columns from the contract. Do not interpret the numbers."
)

ANALYST_SYSTEM = (
    "You are an analyst. You interpret metrics produced by other sections. "
    "You must reference the metrics table using its [ref:...] marker and never "
    "reprint it. Be concise and factual."
)


def build_agents() -> dict[str, LLMAgent]:
    return {
        "tabulator": LLMAgent("tabulator", system_prompt=TABULATOR_SYSTEM,
                              temperature=0.2),
        "analyst": LLMAgent("analyst", system_prompt=ANALYST_SYSTEM,
                            temperature=0.4),
    }


def build_judge() -> JudgeAgent:
    return JudgeAgent(review_threshold=0.6)
