"""Generic section agent: contract + facts + chunks + board → section text.

This is the domain-agnostic counterpart of a "section writer". It builds a
canonical prompt from whatever context it is given and asks an ``LLMPort`` to
complete it. The contract block bounds the scope; the consumed-anchor summaries
let it cite other sections without seeing their content.
"""

from __future__ import annotations

import json as _json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from docswarm.orchestration.contracts import SectionContract
from docswarm.ports.llm import LLMPort


@dataclass
class SectionRequest:
    """Everything an agent needs to write its section."""
    section_id: str
    contract: SectionContract
    facts: dict = field(default_factory=dict)
    chunks: list[dict] = field(default_factory=list)     # retrieved context (RAG)
    board_view: dict = field(default_factory=dict)       # consumed anchors {id: {...}}
    instructions: str = ""                               # extra task instructions


@dataclass
class SectionResult:
    section_id: str
    content: str
    tokens_used: int = 0
    latency_ms: int = 0
    error: Optional[str] = None


def build_prompt(req: SectionRequest) -> str:
    """Assemble a canonical user prompt from the request context.

    Always the same blocks in the same order, so an agent's system prompt can
    rely on their presence. Nothing here is domain-specific.
    """
    c = req.contract
    parts: list[str] = [c.prompt_block()]

    if req.facts:
        parts.append("## FACTS (shared, authoritative — do not contradict)\n"
                     + _json.dumps(req.facts, ensure_ascii=False, indent=2))

    if req.board_view:
        refs = "\n".join(
            f"- {a.get('title') or aid} ({aid}): {a.get('summary') or 'no summary'}"
            for aid, a in req.board_view.items())
        parts.append("## ANCHORS FROM OTHER SECTIONS "
                     "(cite each with its [ref:<id>] marker, do NOT copy)\n" + refs)

    if req.chunks:
        serialized = []
        for i, ch in enumerate(req.chunks[:12], start=1):
            cid = ch.get("id") or ch.get("chunk_id") or i
            txt = ch.get("contenido") or ch.get("texto") or ch.get("content") or ""
            serialized.append(f"[FRAG #{cid}]\n{txt[:1200]}")
        parts.append("## KNOWLEDGE FRAGMENTS (cite as [FRAG #ID])\n"
                     + "\n---\n".join(serialized))

    if req.instructions:
        parts.append("## EXTRA INSTRUCTIONS\n" + req.instructions)

    parts.append(f"## TASK\nWrite the section **{c.title}**.")
    return "\n\n".join(parts)


class BaseAgent(ABC):
    """Interface for a swarm agent that writes one section."""

    name: str = "agent"

    @abstractmethod
    def generate(self, req: SectionRequest, llm: LLMPort) -> SectionResult:
        ...


class LLMAgent(BaseAgent):
    """A ready-to-use generic agent: a system prompt + an LLM.

    Instantiate one per role with the system prompt that defines its voice and
    expertise. The user prompt is built deterministically from the request.
    """

    def __init__(self, name: str, system_prompt: str = "",
                 temperature: float = 0.4, model: Optional[str] = None) -> None:
        self.name = name
        self.system_prompt = system_prompt or (
            "You are a precise technical writer. Write only the requested "
            "section. Do not invent data: if something is missing, write "
            "'[MISSING DATA]'. Respect the section contract exactly.")
        self.temperature = temperature
        self.model = model

    def generate(self, req: SectionRequest, llm: LLMPort) -> SectionResult:
        t0 = time.time()
        prompt = build_prompt(req)
        try:
            options = {"temperature": self.temperature}
            if self.model:
                options["model"] = self.model
            content = llm.complete(self.system_prompt, prompt, **options)
        except Exception as exc:  # noqa: BLE001
            return SectionResult(section_id=req.section_id, content="",
                                 error=f"llm_error: {exc}",
                                 latency_ms=int((time.time() - t0) * 1000))
        return SectionResult(
            section_id=req.section_id, content=(content or "").strip(),
            latency_ms=int((time.time() - t0) * 1000))
