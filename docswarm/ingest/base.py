"""Core data carriers for the ingest layer (no third-party deps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawDocument:
    """A source document before reading: bytes + provenance metadata."""
    doc_id: str
    filename: str
    content: bytes = b""
    mime: str = ""
    domain: str = "general"
    source: str = ""                       # where it came from (url, system...)
    sha256: Optional[str] = None           # filled by versioning.content_hash
    meta: dict = field(default_factory=dict)


@dataclass
class Chunk:
    """A retrievable unit of text derived from a RawDocument."""
    raw_document_id: str
    domain: str
    chunk_index: int
    contenido: str                         # the chunk text (kept name-stable)
    seccion_hint: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.contenido
