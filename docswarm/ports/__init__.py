"""Ports — the interfaces the domain implements (hexagonal / ports & adapters).

The engine NEVER touches a database, a vector index, or a specific LLM. It
declares *ports* and receives implementations by injection:

  - ``LLMPort``       : complete(system, prompt) -> str
  - ``RetrievalPort`` : retrieve(query, ...) -> list[chunk dict]
  - ``StorePort``     : persist a run / document
  - ``FactsPort``     : hard facts about the case (company, parties, dates...)

``docswarm.adapters`` ships ready-made implementations (Ollama LLM, an offline
stub LLM, an in-memory store). Your domain provides the rest.
"""

from __future__ import annotations

from docswarm.ports.facts import FactsPort
from docswarm.ports.llm import LLMPort
from docswarm.ports.retrieval import RetrievalPort
from docswarm.ports.store import RunRecord, StorePort

__all__ = ["LLMPort", "RetrievalPort", "StorePort", "FactsPort", "RunRecord"]
