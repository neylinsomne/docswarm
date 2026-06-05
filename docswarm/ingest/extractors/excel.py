"""XLSX extractor with openpyxl — each sheet as a markdown table (optional dep)."""

from __future__ import annotations

import io

from docswarm.ingest.extractors.base import ExtractResult


def _rows_to_markdown(rows: list[list[str]]) -> str:
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        return ""
    header, *body = rows
    width = len(header)
    md = ["| " + " | ".join(header) + " |",
          "| " + " | ".join("---" for _ in header) + " |"]
    for r in body:
        r = (r + [""] * width)[:width]
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


def extract_xlsx(content: bytes, *, max_rows: int = 1000) -> ExtractResult:
    try:
        import openpyxl
    except ImportError:
        return ExtractResult(
            text="", method="unsupported",
            error="openpyxl not installed. Run: pip install docswarm[ingest]")

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    tables: list[dict] = []
    text_parts: list[str] = []
    for ws in wb.worksheets:
        rows: list[list[str]] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= max_rows:
                break
            rows.append(["" if v is None else str(v) for v in row])
        md = _rows_to_markdown(rows)
        if md:
            tables.append({"markdown": md, "rows": rows, "sheet": ws.title})
            text_parts.append(f"# {ws.title}\n{md}")
    wb.close()

    text = "\n\n".join(text_parts)
    return ExtractResult(
        text=text, method="xlsx",
        tables_markdown=[t["markdown"] for t in tables], tables=tables,
        chars=len(text), meta={"n_sheets": len(tables)},
    )
