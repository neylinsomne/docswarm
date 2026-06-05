"""Plain-text extractor (txt/md/csv/json/log) — stdlib only."""

from __future__ import annotations

from docswarm.ingest.extractors.base import ExtractResult


def extract_plain(content: bytes) -> ExtractResult:
    if not content:
        return ExtractResult(text="", method="plain")
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = content.decode(enc)
            return ExtractResult(text=text, method="plain", chars=len(text),
                                 meta={"encoding": enc})
        except UnicodeDecodeError:
            continue
    text = content.decode("utf-8", errors="replace")
    return ExtractResult(text=text, method="plain", chars=len(text),
                         meta={"encoding": "utf-8/replace"})
