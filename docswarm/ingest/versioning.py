"""Content versioning — sha256 dedup + version chains.

Generic pattern: the same bytes never get re-ingested twice. A ``RawDocument``
is hashed; if its hash is already known, it is a duplicate (skip or link as a
new version). No database here — you pass in the set of known hashes.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

from docswarm.ingest.base import RawDocument


def content_hash(content: bytes) -> str:
    """Stable sha256 of the raw bytes."""
    return hashlib.sha256(content or b"").hexdigest()


def stamp(doc: RawDocument) -> RawDocument:
    """Fill ``doc.sha256`` in-place (and return it) if not already set."""
    if not doc.sha256:
        doc.sha256 = content_hash(doc.content)
    return doc


def is_duplicate(doc: RawDocument, known_hashes: Iterable[str]) -> bool:
    """True if this document's content hash is already in ``known_hashes``."""
    h = doc.sha256 or content_hash(doc.content)
    return h in set(known_hashes)


def dedupe(docs: Iterable[RawDocument]) -> list[RawDocument]:
    """Return the documents with unique content, first occurrence wins."""
    seen: set[str] = set()
    out: list[RawDocument] = []
    for d in docs:
        h = d.sha256 or content_hash(d.content)
        d.sha256 = h
        if h in seen:
            continue
        seen.add(h)
        out.append(d)
    return out
