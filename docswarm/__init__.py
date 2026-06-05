"""docswarm — a domain-agnostic engine for ingesting and generating documents
with a swarm of cooperating agents.

Two layers, both agnostic of any business domain:

  - ``docswarm.ingest``        — extract + chunk + version raw documents.
  - ``docswarm.orchestration`` — turn agent output into ONE coherent document:
      blocks (typed AST), contracts (anti-overlap scope), blackboard (shared
      symbols), composer (deterministic assembly with late-bound numbering).

The domain (what the documents are *about*) is injected through ``docswarm.ports``
(LLM, retrieval, store, facts) and through your own agents — never hardcoded.

See ``examples/informe_demo`` for a runnable, zero-domain example.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
