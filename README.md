# 🐝 docswarm

**A domain-agnostic engine to ingest documents and *generate* documents with a swarm of cooperating agents that never overlap.**

[🇪🇸 Léeme en español](README.es.md) · [Architecture](docs/ARCHITECTURE.md) · License: PolyForm Noncommercial 1.0.0 (non-commercial use)

---

docswarm is the reusable core extracted from a real proposal-writing system. It does two things, both **agnostic of any business domain**:

1. **Ingest** raw documents (PDF / DOCX / XLSX / text) → clean text, tables, chunks, dedup.
2. **Generate** one coherent document by orchestrating a **swarm of agents** that:
   - each write a single section, bounded by a **contract** (disjoint scope — they can't step on each other),
   - coordinate through a **blackboard** (they publish/consume *anchors*, never talk directly),
   - and are scored by a **judge** agent,
   - then assembled by a **deterministic composer** that numbers tables/figures and resolves cross-references *late* — so `[ref:tbl-metrics]` becomes "Table 1" no matter the order agents ran in.

The domain (what the documents are *about*) is injected through **ports** (LLM, retrieval, store, facts) and your own agents. The engine never touches a database or hardcodes a use case.

> **Why "swarm"?** The agents don't form a chat. They're a *stigmergic* swarm: complementarity through a shared board + disjoint contracts, plus an independent judge that votes on quality. No agent sees another's text — only the symbols it's allowed to.

---

## Install

```bash
pip install -e .                 # engine core — ZERO third-party deps
pip install -e ".[yaml,dev]"     # + YAML plans and the test suite
pip install -e ".[ingest]"       # + PDF/DOCX/XLSX extraction (pymupdf, python-docx, openpyxl)
pip install -e ".[acp]"          # + optional ACP protocol server (multi-process agents)
```

Python ≥ 3.10. The core installs with **no dependencies**; everything heavy is optional and lazily imported.

## 60-second demo (runs offline, no model needed)

```bash
python -m examples.informe_demo.run            # deterministic StubLLM — works with nothing installed
python -m examples.informe_demo.run --ollama   # use a local Ollama model instead (ollama pull qwen3:8b)
```

You'll see a two-section report where a **tabulator** agent produces a metrics table, an **analyst** agent cites it as **Table 1** (without reprinting it), and a **judge** scores both — three agents that never talked to each other:

```
This section on period metrics addresses a table of the period's key metrics.

**Table 1. Period metrics**
| Metric   | Value |
| ---      | ---   |
| Metric 1 | 11    |
...

As shown in Table 1, the figures above support the analysis presented in this section.

JUDGE:
  - metrics:  score=0.75 ready=True
  - analysis: score=0.85 ready=True
SELF-CHECK: PASS — cross-reference resolved to a numbered table
```

## Use it in your code

```python
from docswarm.adapters import OllamaLLM, StubLLM
from docswarm.agents import LLMAgent, JudgeAgent
from docswarm.config import plan_from_dict
from docswarm.runner import SwarmRunner

plan = plan_from_dict({
    "title": "Activity Report",
    "sections": [
        {"id": "metrics", "agent": "tabulator", "order": 1,
         "must_cover": ["a table of the period's metrics"],
         "produces": [{"anchor_id": "tbl", "type": "table",
                       "title": "Metrics", "schema": ["Metric", "Value"]}]},
        {"id": "analysis", "agent": "analyst", "order": 2,
         "must_cover": ["interpretation"], "consumes": ["tbl"]},
    ],
})

agents = {
    "tabulator": LLMAgent("tabulator", "You build clean tables from facts."),
    "analyst":   LLMAgent("analyst",   "You interpret metrics and cite tables by ref."),
}

runner = SwarmRunner(llm=StubLLM(), agents=agents, judge=JudgeAgent())  # swap StubLLM → OllamaLLM
result = runner.run(plan, facts={"company": "ACME"})

print(result.markdown)        # assembled document, "Table 1" resolved
print(result.html)            # editor-ready HTML
print(result.reports)         # judge scores per section
```

## Ingest documents

```python
from docswarm.ingest import extract, chunk_text, dedupe

res = extract(open("brief.pdf", "rb").read(), filename="brief.pdf")
print(res.text, res.tables_markdown)
chunks = chunk_text(res.text, max_chars=1500, overlap=150)
```

## How it fits together

```
          ┌──────────── ingest ────────────┐      ┌────────────── orchestration ──────────────┐
bytes ──▶ extract ──▶ version ──▶ chunk ──▶ │      │  contracts  ·  blackboard  ·  composer    │
          (pdf/docx/xlsx/txt)               │      │  (scope)       (anchors)      (assemble)   │
                                            ▼      ▲                                            │
                                       ports (LLM, retrieval, store, facts) ── injected by YOU  │
                                            │      │                                            │
                                            ▼      │     agents (swarm) + judge ────────────────┘
                                       SwarmRunner ─────────────────────────────▶ document_v1 (md + html)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and [docs/CONCEPTS.md](docs/CONCEPTS.md) for the vocabulary (contract, anchor, blackboard, late binding).

## Bring your own everything

| Port | What you implement | Example adapter shipped |
|------|--------------------|-------------------------|
| `LLMPort` | `complete(system, prompt)` | `OllamaLLM`, `StubLLM` |
| `RetrievalPort` | `retrieve(query)` → chunks | `NullRetrieval` |
| `StorePort` | `persist(run)` | `InMemoryStore` |
| `FactsPort` | `facts()` → dict | `StaticFacts` |

Implement `LLMPort` to use OpenAI, Anthropic, vLLM, etc. The engine doesn't care.

## Tests

```bash
pip install -e ".[dev]"
pytest -q          # 20 tests, all run offline with StubLLM
```

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free for personal, research, educational, and other **non-commercial** use; commercial use requires a separate license. This is a *source-available* license, not OSI open-source. For commercial licensing, contact the copyright holder.

## Acknowledgements

Born from a production document-generation pipeline; the orchestration core (blocks AST, contracts, blackboard, composer) is the part that turned out to be universal.
