"""Document extractors — bytes → text (+ tables), dispatched by type.

Each extractor lazily imports its heavy dependency, so importing this package
costs nothing. Missing a dependency yields an ``ExtractResult`` with
``method="unsupported"`` and a helpful error, never a crash.

  pdf   → pymupdf            (pip install docswarm[ingest])
  docx  → python-docx
  xlsx  → openpyxl
  txt/md/csv/json → stdlib
"""

from __future__ import annotations

import os

from docswarm.ingest.extractors.base import ExtractResult

_BY_EXT = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx", ".xlsm": "xlsx",
    ".txt": "plain", ".md": "plain", ".markdown": "plain",
    ".csv": "plain", ".json": "plain", ".log": "plain",
}


def _kind(filename: str, mime: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in _BY_EXT:
        return _BY_EXT[ext]
    m = (mime or "").lower()
    if "pdf" in m:
        return "pdf"
    if "word" in m or "officedocument.wordprocessing" in m:
        return "docx"
    if "sheet" in m or "excel" in m:
        return "xlsx"
    if m.startswith("text/") or "json" in m:
        return "plain"
    return "unknown"


def extract(content: bytes, *, filename: str = "", mime: str = "",
            **options) -> ExtractResult:
    """Extract text (and tables when available) from raw bytes.

    Routing is by file extension, then MIME type. Unknown types fall back to a
    best-effort UTF-8 decode.
    """
    kind = _kind(filename, mime)
    if kind == "pdf":
        from docswarm.ingest.extractors.pdf import extract_pdf
        return extract_pdf(content, **options)
    if kind == "docx":
        from docswarm.ingest.extractors.docx_ import extract_docx
        return extract_docx(content)
    if kind == "xlsx":
        from docswarm.ingest.extractors.excel import extract_xlsx
        return extract_xlsx(content)
    if kind in ("plain", "unknown"):
        from docswarm.ingest.extractors.plain import extract_plain
        return extract_plain(content)
    return ExtractResult(text="", method="unsupported",
                         error=f"no extractor for kind={kind!r}")


__all__ = ["extract", "ExtractResult"]
