"""SwarmRunner — orchestrates the swarm in-process.

This is the conductor. Given a plan, a fact set, an LLM and a map of agents, it:

  1. builds one ``SectionContract`` per section (anti-overlap scope),
  2. creates a blackboard seeded with the shared facts,
  3. runs each section's agent IN PLAN ORDER, so a producer publishes its anchor
     before a consumer needs it,
  4. parses each agent's markdown into the blocks_v1 AST, binds the produced
     anchors, and publishes them (with a summary) to the blackboard,
  5. optionally has a judge score each section (the swarm's quality vote),
  6. composes ONE final document with deterministic numbering and resolved
     cross-references.

Everything domain-specific arrives by injection (agents, facts, LLM, retrieval,
store). The runner itself knows nothing about any business.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from docswarm.agents.base import BaseAgent, SectionRequest, SectionResult
from docswarm.agents.judge import JudgeAgent, JudgeReport
from docswarm.orchestration import blackboard, composer
from docswarm.orchestration.blocks import (
    anchor_summary,
    assign_anchor,
    build_document,
)
from docswarm.orchestration.contracts import build_contracts
from docswarm.ports.llm import LLMPort
from docswarm.ports.retrieval import NullRetrieval, RetrievalPort
from docswarm.ports.store import RunRecord, StorePort


@dataclass
class SwarmResult:
    document: dict                                   # composer output (document_v1)
    sections: list[SectionResult] = field(default_factory=list)
    reports: dict[str, JudgeReport] = field(default_factory=dict)
    board: dict = field(default_factory=dict)        # blackboard snapshot
    warnings: list[str] = field(default_factory=list)

    @property
    def markdown(self) -> str:
        return self.document.get("markdown", "")

    @property
    def html(self) -> str:
        return self.document.get("html", "")


class SwarmRunner:
    def __init__(self, llm: LLMPort, agents: dict[str, BaseAgent], *,
                 judge: Optional[JudgeAgent] = None,
                 retrieval: Optional[RetrievalPort] = None,
                 store: Optional[StorePort] = None,
                 judge_uses_llm: bool = False) -> None:
        self.llm = llm
        self.agents = agents
        self.judge = judge
        self.retrieval = retrieval or NullRetrieval()
        self.store = store
        self.judge_uses_llm = judge_uses_llm

    def run(self, plan, facts: Optional[dict] = None) -> SwarmResult:
        contracts = build_contracts(plan)
        # Plan order = the order the author declared (order_key).
        ordered = sorted(contracts.values(), key=lambda c: c.order_key)
        board_id = blackboard.create_board(facts or {})

        composed_sections: list[dict] = []
        results: list[SectionResult] = []
        reports: dict[str, JudgeReport] = {}
        warnings: list[str] = []

        for contract in ordered:
            agent = self.agents.get(contract.agent)
            if agent is None:
                warnings.append(
                    f"section '{contract.section_id}': no agent named "
                    f"'{contract.agent}', skipped")
                continue

            # Context: retrieved chunks + the summaries of consumed anchors.
            chunks = self.retrieval.retrieve(
                contract.title, domain=contract.agent,
                top_k=8) if contract else []
            board_view = blackboard.get_view(board_id, contract.consumes) \
                if contract.consumes else {}

            req = SectionRequest(
                section_id=contract.section_id, contract=contract,
                facts=blackboard.get_facts(board_id), chunks=chunks,
                board_view=board_view)

            result = agent.generate(req, self.llm)
            results.append(result)

            if result.error:
                warnings.append(f"section '{contract.section_id}': {result.error}")
                self._persist(contract, result, status="failed")
                continue

            # Parse to blocks_v1, bind produced anchors, publish to the board.
            doc = build_document(contract.section_id, contract.agent, result.content)
            if contract.produces:
                table_anchors = [a.anchor_id for a in contract.produces
                                 if a.type == "table"]
                assign_anchor(doc, table_anchors)
                for a in contract.produces:
                    blackboard.publish_anchor(
                        board_id, a.anchor_id, type=a.type,
                        section_id=contract.section_id, title=a.title,
                        summary=anchor_summary(doc, a.anchor_id))

            composed_sections.append({
                "section_id": contract.section_id,
                "order_key": contract.order_key,
                "title": contract.title,
                "document": doc,
            })

            # Judge vote (optional).
            if self.judge is not None:
                report = self.judge.evaluate(
                    contract.section_id, result.content, contract=contract,
                    llm=self.llm if self.judge_uses_llm else None)
                reports[contract.section_id] = report
                blackboard.publish_anchor(
                    board_id, f"judge::{contract.section_id}", type="judge_score",
                    section_id=contract.section_id, title=f"Judge: {contract.title}",
                    summary=f"score={report.overall_score:.2f} "
                            f"review={len(report.paragraphs_needing_review())}",
                    payload=report.to_payload())

            self._persist(contract, result, status="completed")

        document = composer.compose_document(composed_sections)
        warnings.extend(document.get("warnings", []))
        snap = blackboard.snapshot(board_id)
        blackboard.clear_board(board_id)

        return SwarmResult(
            document=document, sections=results, reports=reports,
            board=snap, warnings=warnings)

    def _persist(self, contract, result: SectionResult, *, status: str) -> None:
        if self.store is None:
            return
        try:
            self.store.persist(RunRecord(
                run_id=str(uuid.uuid4()), agent_name=contract.agent,
                status=status, section_id=contract.section_id,
                output={"content": result.content, "error": result.error},
                latency_ms=result.latency_ms))
        except Exception:  # noqa: BLE001
            pass
