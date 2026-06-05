"""Chunking for the ingest pipeline.

Default strategy: split by paragraphs, accumulating up to ~max_chars, with an
overlap so border context is not lost. Good enough for most documents; a source
with its own structure can override it.
"""

from __future__ import annotations

import re

from docswarm.ingest.base import Chunk

MAX_CHARS = 1500
OVERLAP = 150
MIN_CHARS = 40


def chunk_text(text: str, max_chars: int = MAX_CHARS,
               overlap: int = OVERLAP) -> list[str]:
    """Split text into chunks by paragraph, accumulating up to max_chars."""
    if not text or not text.strip():
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= max_chars:
            buf = f"{buf}\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            if len(p) > max_chars:
                # giant paragraph: hard cut with overlap
                start = 0
                while start < len(p):
                    chunks.append(p[start:start + max_chars])
                    start += max_chars - overlap
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    # overlap between consecutive chunks (tail of previous → head of next)
    if overlap and len(chunks) > 1:
        out = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            out.append((tail + " " + chunks[i]).strip())
        chunks = out
    return [c for c in chunks if len(c) >= MIN_CHARS]


def default_chunker(text: str, raw_doc_id: str, domain: str = "general",
                    max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[Chunk]:
    """Chunk plain text into ``Chunk`` objects tied to a raw document."""
    out: list[Chunk] = []
    for i, c in enumerate(chunk_text(text, max_chars=max_chars, overlap=overlap)):
        out.append(Chunk(
            raw_document_id=raw_doc_id, domain=domain,
            seccion_hint=None, chunk_index=i, contenido=c,
            metadata={"chars": len(c)},
        ))
    return out
