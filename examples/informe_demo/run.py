"""Run the demo swarm end-to-end.

    python -m examples.informe_demo.run            # offline (StubLLM)
    python -m examples.informe_demo.run --ollama   # use local Ollama (qwen3:8b)

Success criterion (the proof the engine is functional and domain-free): the
output document has a numbered "Table 1" and the analysis section's cross
reference resolves to "Table 1" — produced by two agents that never talked to
each other, coordinated only through the blackboard and their contracts.
"""

from __future__ import annotations

import argparse
import json
import os

from docswarm.adapters import OllamaLLM, StubLLM
from docswarm.config import load_plan
from docswarm.ports.store import InMemoryStore
from docswarm.runner import SwarmRunner

from examples.informe_demo.agents import build_agents, build_judge

_HERE = os.path.dirname(__file__)


def main() -> int:
    parser = argparse.ArgumentParser(description="docswarm demo swarm")
    parser.add_argument("--ollama", action="store_true",
                        help="use a local Ollama server instead of the offline stub")
    parser.add_argument("--model", default="qwen3:8b", help="Ollama model name")
    args = parser.parse_args()

    plan = load_plan(os.path.join(_HERE, "plan.yaml"))
    with open(os.path.join(_HERE, "facts.json"), encoding="utf-8") as f:
        facts = json.load(f)

    llm = OllamaLLM(model=args.model) if args.ollama else StubLLM()
    store = InMemoryStore()
    runner = SwarmRunner(
        llm=llm, agents=build_agents(), judge=build_judge(),
        store=store, judge_uses_llm=args.ollama)

    result = runner.run(plan, facts)

    print("=" * 70)
    print(f"DOCUMENT: {plan.title}    (engine: {'ollama' if args.ollama else 'stub'})")
    print("=" * 70)
    print(result.markdown)
    print("\n" + "-" * 70)
    print("ANCHORS:", json.dumps(result.document.get("anchors", {}), indent=2))
    print("JUDGE:")
    for sid, rep in result.reports.items():
        print(f"  - {sid}: score={rep.overall_score:.2f} "
              f"ready={rep.ready_to_show} review={len(rep.paragraphs_needing_review())}")
    if result.warnings:
        print("WARNINGS:", result.warnings)
    print(f"RUNS PERSISTED: {len(store.records)}")

    # Self-check: the cross reference must have resolved to a numbered table.
    ok = "Table 1" in result.markdown and "[pending reference]" not in result.markdown
    print("\nSELF-CHECK:", "PASS — cross-reference resolved to a numbered table"
          if ok else "FAIL — reference did not resolve")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
