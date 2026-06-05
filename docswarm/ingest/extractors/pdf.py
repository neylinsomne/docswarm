"""PDF extractor with pymupdf — text + structured tables, boilerplate removal.

Quality touches:
  - drops repeated boilerplate (footer/header repeated on most pages) that
    breaks text continuity → cleaner chunks.
  - extracts TABLES as structured units (markdown + rows), separated from prose,
    so downstream consumers treat them as table nodes, not diluted text.

pymupdf is OPTIONAL: if it is not installed, returns method="unsupported" with a
clear hint instead of raising. OCR for scanned pages is intentionally out of
scope here (bring your own via the ingest pipeline if you need it).
"""

from __future__ import annotations

import re

from docswarm.ingest.extractors.base import ExtractResult

MIN_CHARS_PER_PAGE = 20
BOILER_PAGE_FRACTION = 0.4   # a line is boilerplate if it appears in >= 40% of pages
_PAGE_RE = re.compile(r"^\s*(page|p[áa]gina)\s+\d+\s*(of|de\s+\d+)?\s*$", re.IGNORECASE)
_DIGITS = re.compile(r"\d+")


def _norm_line(s: str) -> str:
    return _DIGITS.sub("#", s.lower()).strip()


def _strip_boilerplate(pages_lines: list[list[str]]) -> list[list[str]]:
    from collections import Counter
    n = len(pages_lines)
    if n == 0:
        return pages_lines
    counter: Counter = Counter()
    for lines in pages_lines:
        for ln in {l.strip() for l in lines if l.strip()}:
            counter[_norm_line(ln)] += 1
    threshold = max(2, int(round(n * BOILER_PAGE_FRACTION)))
    boiler = {k for k, v in counter.items() if v >= threshold and len(k) >= 4}
    cleaned: list[list[str]] = []
    for lines in pages_lines:
        kept = []
        for l in lines:
            s = l.strip()
            if not s:
                kept.append(l)
                continue
            if _PAGE_RE.match(s):
                continue
            if _norm_line(s) in boiler:
                continue
            kept.append(l)
        cleaned.append(kept)
    return cleaned


def _extract_tables(page) -> list[dict]:
    out: list[dict] = []
    try:
        finder = page.find_tables()
        for t in getattr(finder, "tables", []) or []:
            try:
                rows = t.extract()
            except Exception:
                rows = []
            if not rows or sum(1 for r in rows for c in r if (c or "").strip()) < 2:
                continue
            try:
                md = t.to_markdown()
            except Exception:
                md = "\n".join(" | ".join((c or "").strip() for c in r) for r in rows)
            out.append({"markdown": md, "rows": rows})
    except Exception:
        pass
    return out


def extract_pdf(content: bytes, *, min_chars_per_page: int = MIN_CHARS_PER_PAGE,
                max_pages: int = 200) -> ExtractResult:
    try:
        import fitz  # pymupdf
    except ImportError:
        return ExtractResult(
            text="", method="unsupported",
            error="pymupdf not installed. Run: pip install docswarm[ingest]")

    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 — corrupt/empty/not-a-pdf
        return ExtractResult(text="", method="error",
                             error=f"could not open PDF: {exc}")
    total_pages = doc.page_count
    n = min(total_pages, max_pages)

    pages_lines: list[list[str]] = []
    tables: list[dict] = []

    for i in range(n):
        page = doc[i]
        txt = (page.get_text("text") or "").strip()
        for tb in _extract_tables(page):
            tb["page"] = i + 1
            tables.append(tb)
        pages_lines.append(txt.split("\n") if txt else [])

    doc.close()

    pages_lines = _strip_boilerplate(pages_lines)
    text = "\n\n".join("\n".join(l for l in lines).strip()
                       for lines in pages_lines if any(x.strip() for x in lines))

    meta = {"total_pages": total_pages, "n_tables": len(tables)}
    err = None
    method = "pdf_text"
    if not text.strip() and not tables:
        err = "PDF has no extractable text layer (likely scanned; OCR not enabled)"
        method = "error"

    return ExtractResult(
        text=text, method=method, pages=n,
        tables_markdown=[t["markdown"] for t in tables], tables=tables,
        chars=len(text), meta=meta, error=err,
    )
