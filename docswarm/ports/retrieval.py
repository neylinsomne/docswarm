"""RetrievalPort — pluggable context retrieval (RAG), optional.

The engine does NOT load embeddings, torch, or a vector DB. If you want your
agents to ground their writing in a knowledge base, implement this port (with
pgvector, FAISS, Elastic, or anything) and pass it to the runner. Agents receive
the returned chunks and may cite them with ``[FRAG #id]``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RetrievalPort(Protocol):
    def retrieve(self, query: str, *, domain: str = "", top_k: int = 8,
                 **filters: Any) -> list[dict]:
        """Return up to ``top_k`` chunk dicts relevant to ``query``.

        Each chunk SHOULD carry at least ``id`` and one of
        ``contenido`` / ``texto`` / ``content``. Optional: ``url``, ``score``.
        Returning ``[]`` (no retrieval) is always valid.
        """
        ...


class NullRetrieval:
    """A retrieval port that returns nothing. The default when none is given."""

    def retrieve(self, query: str, *, domain: str = "", top_k: int = 8,
                 **filters: Any) -> list[dict]:
        return []
