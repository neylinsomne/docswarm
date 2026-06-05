# 🐝 docswarm

**Un motor agnóstico de dominio para ingerir documentos y *generar* documentos con un enjambre de agentes que cooperan sin pisarse.**

[🇬🇧 Read me in English](README.md) · [Arquitectura](docs/ARCHITECTURE.md) · Licencia: PolyForm Noncommercial 1.0.0 (uso no comercial)

---

docswarm es el núcleo reutilizable extraído de un sistema real de generación de propuestas. Hace dos cosas, ambas **independientes de cualquier dominio de negocio**:

1. **Ingesta** de documentos crudos (PDF / DOCX / XLSX / texto) → texto limpio, tablas, chunks, deduplicación.
2. **Generación** de un documento coherente orquestando un **enjambre de agentes** que:
   - cada uno escribe una sola sección, acotada por un **contrato** (alcance disjunto — no se pueden pisar),
   - coordinan a través de un **blackboard** (publican/consumen *anclas*, nunca hablan directamente),
   - son evaluados por un agente **juez**,
   - y luego un **compositor determinístico** los ensambla: numera tablas/figuras y resuelve referencias cruzadas *al final* — así `[ref:tbl-metrics]` se convierte en "Table 1" sin importar el orden en que corrieron los agentes.

El dominio (de qué *tratan* los documentos) se inyecta mediante **ports** (LLM, retrieval, store, facts) y tus propios agentes. El motor nunca toca una base de datos ni hardcodea un caso de uso.

> **¿Por qué "enjambre"?** Los agentes no forman un chat. Son un enjambre *estigmérgico*: complementariedad vía un tablero compartido + contratos disjuntos, más un juez independiente que vota la calidad. Ningún agente ve el texto de otro — solo los símbolos que tiene permitido.

---

## Instalación

```bash
pip install -e .                 # núcleo del motor — CERO dependencias externas
pip install -e ".[yaml,dev]"     # + planes en YAML y la suite de tests
pip install -e ".[ingest]"       # + extracción PDF/DOCX/XLSX (pymupdf, python-docx, openpyxl)
pip install -e ".[acp]"          # + servidor opcional del protocolo ACP (agentes multi-proceso)
```

Python ≥ 3.10. El núcleo se instala **sin dependencias**; todo lo pesado es opcional y se importa de forma perezosa.

## Demo en 60 segundos (corre offline, sin modelo)

```bash
python -m examples.informe_demo.run            # StubLLM determinístico — funciona sin instalar nada
python -m examples.informe_demo.run --ollama   # usa un modelo Ollama local (ollama pull qwen3:8b)
```

Verás un informe de dos secciones donde un agente **tabulador** produce una tabla de métricas, un agente **analista** la cita como **Table 1** (sin reimprimirla) y un **juez** evalúa ambas — tres agentes que nunca hablaron entre sí:

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

## Úsalo en tu código

```python
from docswarm.adapters import OllamaLLM, StubLLM
from docswarm.agents import LLMAgent, JudgeAgent
from docswarm.config import plan_from_dict
from docswarm.runner import SwarmRunner

plan = plan_from_dict({
    "title": "Informe de actividad",
    "sections": [
        {"id": "metricas", "agent": "tabulador", "order": 1,
         "must_cover": ["una tabla de métricas del período"],
         "produces": [{"anchor_id": "tbl", "type": "table",
                       "title": "Métricas", "schema": ["Métrica", "Valor"]}]},
        {"id": "analisis", "agent": "analista", "order": 2,
         "must_cover": ["interpretación"], "consumes": ["tbl"]},
    ],
})

agents = {
    "tabulador": LLMAgent("tabulador", "Construyes tablas limpias a partir de los facts."),
    "analista":  LLMAgent("analista",  "Interpretas métricas y citas tablas por su ref."),
}

runner = SwarmRunner(llm=StubLLM(), agents=agents, judge=JudgeAgent())  # cambia StubLLM → OllamaLLM
result = runner.run(plan, facts={"empresa": "ACME"})

print(result.markdown)        # documento ensamblado, "Table 1" resuelto
print(result.html)            # HTML listo para el editor
print(result.reports)         # scores del juez por sección
```

## Ingesta de documentos

```python
from docswarm.ingest import extract, chunk_text, dedupe

res = extract(open("pliego.pdf", "rb").read(), filename="pliego.pdf")
print(res.text, res.tables_markdown)
chunks = chunk_text(res.text, max_chars=1500, overlap=150)
```

## Cómo encaja todo

```
          ┌──────────── ingest ────────────┐      ┌────────────── orchestration ──────────────┐
bytes ──▶ extract ──▶ version ──▶ chunk ──▶ │      │  contracts  ·  blackboard  ·  composer    │
          (pdf/docx/xlsx/txt)               │      │  (alcance)     (anclas)       (ensambla)   │
                                            ▼      ▲                                            │
                                       ports (LLM, retrieval, store, facts) ── inyectados por TI│
                                            │      │                                            │
                                            ▼      │     agents (enjambre) + juez ──────────────┘
                                       SwarmRunner ─────────────────────────────▶ document_v1 (md + html)
```

Mira [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para el diseño completo y [docs/CONCEPTS.md](docs/CONCEPTS.md) para el vocabulario (contrato, ancla, blackboard, late binding).

## Trae tu propia implementación de todo

| Port | Lo que implementas | Adapter de ejemplo incluido |
|------|--------------------|-----------------------------|
| `LLMPort` | `complete(system, prompt)` | `OllamaLLM`, `StubLLM` |
| `RetrievalPort` | `retrieve(query)` → chunks | `NullRetrieval` |
| `StorePort` | `persist(run)` | `InMemoryStore` |
| `FactsPort` | `facts()` → dict | `StaticFacts` |

Implementa `LLMPort` para usar OpenAI, Anthropic, vLLM, etc. Al motor le da igual.

## Tests

```bash
pip install -e ".[dev]"
pytest -q          # 20 tests, todos corren offline con StubLLM
```

## Licencia

[PolyForm Noncommercial 1.0.0](LICENSE) — libre para uso personal, de investigación, educativo y otros usos **no comerciales**; el uso comercial requiere una licencia aparte. Es una licencia *source-available*, no open-source OSI. Para licenciamiento comercial, contacta al titular del copyright.

## Agradecimientos

Nació de un pipeline de generación de documentos en producción; el núcleo de orquestación (AST de bloques, contratos, blackboard, compositor) resultó ser la parte universal.
