# Architecture

docswarm is a **hexagonal (ports & adapters)** engine. The core is pure logic
with zero I/O; the outside world (LLMs, databases, vector stores) plugs in
through ports. This is what makes it reusable across domains.

```
┌──────────────────────────── docswarm (the engine) ────────────────────────────┐
│                                                                                │
│  ingest/                          orchestration/                               │
│  ┌────────────────────┐           ┌──────────────────────────────────────┐    │
│  │ extractors (pdf,    │           │ blocks      typed AST (blocks_v1)     │    │
│  │   docx, xlsx, txt)  │           │ contracts   disjoint scope per section│    │
│  │ chunking            │           │ blackboard  shared anchors (no chat)  │    │
│  │ versioning (sha256) │           │ composer    deterministic assembly    │    │
│  └────────────────────┘           └──────────────────────────────────────┘    │
│                                                                                │
│  agents/            runner.py (SwarmRunner)              ports/                 │
│  ┌──────────────┐   orchestrates the swarm in-process   ┌───────────────────┐  │
│  │ BaseAgent    │ ◀───────────────────────────────────▶ │ LLMPort           │  │
│  │ LLMAgent     │                                        │ RetrievalPort     │  │
│  │ JudgeAgent   │                                        │ StorePort         │  │
│  └──────────────┘                                        │ FactsPort         │  │
│                                                          └───────────────────┘  │
└───────────────────────────────────────────▲────────────────────────────────────┘
                                             │ implemented by
                              adapters/ (OllamaLLM, StubLLM, InMemoryStore, …)
                                       + YOUR domain (prompts, retrieval, facts)
```

## The two layers

### 1. Ingest (`docswarm.ingest`) — the document ETL

`bytes → extract → version → chunk`. Agnostic and dependency-light:

- **extractors** dispatch by extension/MIME. Each heavy dependency (pymupdf,
  python-docx, openpyxl) is *lazily imported*; a missing one yields a clear
  `ExtractResult(method="unsupported")` instead of a crash.
- **versioning** is sha256 content-hash dedup — the same bytes never ingest twice.
- **chunking** splits by paragraph with overlap; override per source if needed.

### 2. Orchestration (`docswarm.orchestration`) — the document engine

This is the crown jewel and it has **zero domain knowledge**:

- **`blocks.py`** — `blocks_v1`, a typed document AST. An agent emits *structure*
  (headings, paragraphs, tables, runs with semantic marks), not formatting
  syntax. Bold is an attribute, never a `**` in the text. A deterministic parser
  turns the LLM's markdown into this AST.
- **`contracts.py`** — a `SectionContract` per section: `must_cover` /
  `must_not_cover` (disjoint scope = anti-overlap) and `produces` / `consumes`
  anchors (complementarity). Built from your **plan** (config), not hardcoded.
- **`blackboard.py`** — a shared board (Hearsay-II pattern). Agents publish and
  consume *anchors* (symbols with a short summary); they never exchange text. A
  consumer cites a producer's table meaningfully without ever seeing its content.
- **`composer.py`** — deterministic assembly. Concatenates sections in order,
  then does **late binding**: numbers tables/figures and resolves `[ref:anchor]`
  → "Table N" *after* everything is placed. So agents can run in any order (even
  in parallel) and the cross-references still come out right.

## The swarm (`docswarm.agents` + `docswarm.runner`)

An **agent** is a stateless worker that writes one section. The **SwarmRunner**:

1. `build_contracts(plan)` — one contract per section.
2. `create_board(facts)` — seed the blackboard with shared, authoritative facts.
3. For each section *in plan order*: build the prompt (contract block + facts +
   retrieved chunks + summaries of consumed anchors), call the agent's `LLMPort`,
   parse to `blocks_v1`, bind produced anchors, publish them to the board.
4. Optionally a **judge** scores each section (heuristic + optional LLM) and
   publishes a `judge_score` anchor — the swarm's quality vote.
5. `compose_document(...)` — one final `document_v1` (markdown + HTML).

No agent calls another. Coordination is *stigmergic*: through the board and the
contracts. That is what keeps them from overlapping and lets them complement
each other.

## Ports (`docswarm.ports`)

| Port | Method | Default adapter |
|------|--------|-----------------|
| `LLMPort` | `complete(system, prompt, **opts) -> str` | `OllamaLLM`, `StubLLM` |
| `RetrievalPort` | `retrieve(query, ...) -> list[chunk]` | `NullRetrieval` |
| `StorePort` | `persist(RunRecord)` | `InMemoryStore` |
| `FactsPort` | `facts(**ctx) -> dict` | `StaticFacts` |

The engine depends only on these interfaces. Your domain supplies the rest.

## Optional ACP server (`docswarm.server`)

For when agents must live in separate processes or languages, `build_acp_server`
exposes each agent over the [ACP](https://agentcommunicationprotocol.dev)
protocol (lazy `acp-sdk` import; `pip install docswarm[acp]`). For a single
service, the in-process `SwarmRunner` is all you need.

## Design rules

- **The engine never touches a database.** Everything by injection (ports).
- **The composer is deterministic.** No LLM in assembly, numbering, or refs.
- **Marks are attributes, not characters.** Formatting lives in the AST/renderer.
- **Domain is config + agents, never engine code.** Swap the plan and the
  prompts; the same machinery writes a different kind of document.
