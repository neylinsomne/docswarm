"""Judge agent — scores a generated section instead of writing one.

The judge is what turns a set of writers into a *swarm*: an independent reviewer
that votes on quality and flags paragraphs needing human review. It works in two
modes:

  - heuristic (default, offline): cheap signals — length, missing-data markers,
    unresolved references, contract coverage — combined into a confidence score.
  - llm-assisted (optional): if you pass an ``LLMPort``, it additionally asks the
    model for a 0-1 confidence and merges it with the heuristic.

It never rewrites the section; it returns a ``JudgeReport``. The runner can
publish the report to the blackboard so other agents (or a human) react to it.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

from docswarm.orchestration.contracts import SectionContract
from docswarm.ports.llm import LLMPort

_MISSING_RE = re.compile(r"\[(MISSING DATA|DATO_PENDIENTE|TODO|TBD)\]", re.IGNORECASE)
_PENDING_REF_RE = re.compile(r"\[pending reference\]", re.IGNORECASE)


@dataclass
class ParagraphScore:
    index: int
    confidence: float
    flag: str                  # "ok" | "review" | "missing_data"
    needs_human: bool


@dataclass
class JudgeReport:
    section_id: str
    overall_score: float
    paragraphs: list[ParagraphScore] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    ready_to_show: bool = True

    def paragraphs_needing_review(self) -> list[ParagraphScore]:
        return [p for p in self.paragraphs if p.needs_human]

    def to_payload(self) -> dict:
        return {
            "section_id": self.section_id,
            "overall_score": round(self.overall_score, 3),
            "ready_to_show": self.ready_to_show,
            "flags": self.flags,
            "review_count": len(self.paragraphs_needing_review()),
            "paragraphs": [
                {"index": p.index, "confidence": round(p.confidence, 3),
                 "flag": p.flag, "needs_human": p.needs_human}
                for p in self.paragraphs
            ],
        }


class JudgeAgent:
    """Evaluates one section. Heuristic by default; LLM-assisted if given one."""

    name = "judge"

    def __init__(self, review_threshold: float = 0.6) -> None:
        self.review_threshold = review_threshold

    def evaluate(self, section_id: str, content: str, *,
                 contract: Optional[SectionContract] = None,
                 llm: Optional[LLMPort] = None) -> JudgeReport:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content or "") if p.strip()]
        flags: list[str] = []
        scores: list[ParagraphScore] = []

        for i, para in enumerate(paragraphs):
            conf = 0.85
            flag = "ok"
            if _MISSING_RE.search(para):
                conf, flag = 0.3, "missing_data"
                flags.append(f"paragraph {i}: missing-data marker")
            elif _PENDING_REF_RE.search(para):
                conf, flag = 0.45, "review"
                flags.append(f"paragraph {i}: unresolved reference")
            elif len(para) < 40:
                conf, flag = 0.55, "review"
            scores.append(ParagraphScore(
                index=i, confidence=conf, flag=flag,
                needs_human=conf < self.review_threshold))

        # Contract coverage: penalize if a must_cover keyword never appears.
        if contract and contract.must_cover:
            low = (content or "").lower()
            for kw in contract.must_cover:
                head = kw.lower().split()[0] if kw.split() else kw.lower()
                if head and head not in low:
                    flags.append(f"may not cover: {kw}")

        # Optional LLM second opinion (merged with the heuristic mean).
        heuristic = (sum(p.confidence for p in scores) / len(scores)) if scores else 0.0
        overall = heuristic
        if llm is not None and content.strip():
            try:
                raw = llm.complete(
                    "You are a strict reviewer. Reply with ONLY a number 0-1: how "
                    "confident are you this text is accurate, complete and "
                    "non-hallucinated?",
                    content[:4000])
                m = re.search(r"(0?\.\d+|0|1(?:\.0+)?)", raw or "")
                if m:
                    llm_score = max(0.0, min(1.0, float(m.group(1))))
                    overall = round(0.5 * heuristic + 0.5 * llm_score, 4)
            except Exception:  # noqa: BLE001
                pass

        if not scores:
            flags.append("empty section")

        return JudgeReport(
            section_id=section_id,
            overall_score=overall,
            paragraphs=scores,
            flags=flags,
            ready_to_show=overall >= self.review_threshold and bool(scores),
        )
