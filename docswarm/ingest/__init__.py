"""Ingest — the document ETL layer (agnostic).

Pipeline: raw bytes → extract text/tables → version (sha256 dedup) → chunk.
Everything heavy (pymupdf, python-docx, openpyxl) is OPTIONAL and lazily
imported; the engine installs with zero deps and you add only the extractors
you need (``pip install docswarm[ingest]``).
"""

from __future__ import annotations

from docswarm.ingest.base import Chunk, RawDocument
from docswarm.ingest.chunking import chunk_text, default_chunker
from docswarm.ingest.extractors import ExtractResult, extract
from docswarm.ingest.versioning import content_hash, dedupe, is_duplicate

__all__ = [
    "RawDocument", "Chunk",
    "extract", "ExtractResult",
    "chunk_text", "default_chunker",
    "content_hash", "is_duplicate", "dedupe",
]
