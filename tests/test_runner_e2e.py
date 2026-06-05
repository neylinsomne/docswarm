"""End-to-end: the whole swarm with the offline StubLLM.

Proves the engine is functional and domain-free: two agents that never talk
produce one document where the analysis cites a numbered table created by the
tabulator, and the judge scores both sections.
"""

from docswarm.adapters import StubLLM
from docswarm.agents import JudgeAgent, LLMAgent
from docswarm.config import plan_from_dict
from docswarm.ports.store import InMemoryStore
from docswarm.runner import SwarmRunner

PLAN = {
    "title": "Activity Report",
    "sections": [
        {"id": "metrics", "agent": "tabulator", "order": 1, "title": "Period metrics",
         "must_cover": ["a table of metrics"],
         "produces": [{"anchor_id": "tbl-metrics", "type": "table",
                       "title": "Period metrics", "schema": ["Metric", "Value"]}]},
        {"id": "analysis", "agent": "analyst", "order": 2, "title": "Analysis",
         "must_cover": ["interpretation"], "consumes": ["tbl-metrics"]},
    ],
}


def _runner():
    agents = {
        "tabulator": LLMAgent("tabulator", "tabulate"),
        "analyst": LLMAgent("analyst", "analyze"),
    }
    return SwarmRunner(StubLLM(), agents, judge=JudgeAgent(), store=InMemoryStore())


def test_e2e_table_numbered_and_reference_resolved():
    result = _runner().run(plan_from_dict(PLAN), {"company": "ACME"})
    md = result.markdown
    assert "Table 1" in md
    assert "[pending reference]" not in md
    assert result.document["anchors"]["tbl-metrics"]["label"] == "Table 1"


def test_e2e_judge_scored_every_section():
    result = _runner().run(plan_from_dict(PLAN), {})
    assert set(result.reports) == {"metrics", "analysis"}
    assert all(0.0 <= r.overall_score <= 1.0 for r in result.reports.values())


def test_e2e_runs_persisted():
    store = InMemoryStore()
    agents = {"tabulator": LLMAgent("tabulator", "t"),
              "analyst": LLMAgent("analyst", "a")}
    SwarmRunner(StubLLM(), agents, judge=JudgeAgent(), store=store).run(
        plan_from_dict(PLAN), {})
    assert len(store.records) == 2


def test_e2e_no_overlap_table_only_in_producer():
    result = _runner().run(plan_from_dict(PLAN), {})
    # exactly ONE table block in the whole document (no reprint by the analyst)
    tables = [b for b in result.document["blocks"] if b["type"] == "table"]
    assert len(tables) == 1
