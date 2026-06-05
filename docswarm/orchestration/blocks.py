"""
blocks_v1 — structured-document AST for agent output.

The idea: an agent emits semantic STRUCTURE (typed blocks with intent marks),
not formatting syntax. Rendering (bold, tables, spacing) and assembly are
deterministic, outside the LLM → it kills the classic ``**bold**Name**`` mess.

Typical flow: the LLM keeps producing markdown/HTML; we PARSE it to blocks_v1
deterministically here. Later steps can force the LLM to emit blocks_v1 directly
(JSON Schema / grammar) and feed the deterministic composer.

blocks_v1 format (aligned to ProseMirror/TipTap):
  document = { "format": "blocks_v1", "blocks": [ <block>, ... ] }
  block:
    { "type": "heading", "level": 1..6, "runs": [<run>] }
    { "type": "paragraph", "runs": [<run>] }
    { "type": "bullet_list" | "ordered_list", "items": [ [<run>], ... ] }
    { "type": "table", "anchor_id": str|None, "columns": [str], "rows": [[str]] }
    { "type": "code", "text": str }
  run (text with SEMANTIC marks, not syntax):
    { "text": str, "marks": ["bold"|"italic"] }                  # emphasis
    { "type": "ref", "anchor_id": str }                          # internal cite
    { "type": "citation", "source": "FRAG #id", "url": str|None } # cite to KB

Bold/italic are ATTRIBUTES of the run, never ``**`` characters in the text.
"""

from __future__ import annotations

import re
from typing import Any

BLOCKS_FORMAT = "blocks_v1"

# Inline marks: **bold**, __bold__, *italic*, _italic_  (standard markdown).
# Order matters: bold (double) before italic (single).
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_ITALIC_RE = re.compile(r"\*(.+?)\*|_(.+?)_")
# Cite to KB: [FRAG #42] or [FRAG #abc]
_FRAG_RE = re.compile(r"\[FRAG #([A-Za-z0-9_\-]+)\]")
# Internal ref to an anchor: [ref:tbl-metrics]
_REF_RE = re.compile(r"\[ref:([A-Za-z0-9_\-]+)\]")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


# ---------------------------------------------------------------------------
# Runs (inline) — text with semantic marks + refs/citations
# ---------------------------------------------------------------------------

def _parse_runs(text: str) -> list[dict]:
    """Convert a line with inline markdown into a list of typed runs.

    Resolves, in order: [FRAG #id] → citation, [ref:x] → ref, **/__ → bold,
    */_ → italic. The rest is plain text. Marks NEVER stay as characters in
    ``run.text``.
    """
    if not text:
        return []

    # 1) Slice by "special" tokens (FRAG / ref) preserving their position.
    tokens: list[dict] = []
    pos = 0
    # Combine FRAG and ref in a single positional pass.
    specials = []
    for m in _FRAG_RE.finditer(text):
        specials.append((m.start(), m.end(), {"type": "citation",
                                              "source": f"FRAG #{m.group(1)}"}))
    for m in _REF_RE.finditer(text):
        specials.append((m.start(), m.end(), {"type": "ref",
                                             "anchor_id": m.group(1)}))
    specials.sort(key=lambda x: x[0])

    for start, end, node in specials:
        if start > pos:
            tokens.extend(_parse_emphasis(text[pos:start]))
        tokens.append(node)
        pos = end
    if pos < len(text):
        tokens.extend(_parse_emphasis(text[pos:]))
    return tokens


def _parse_emphasis(text: str) -> list[dict]:
    """Turn **bold** / *italic* into runs with marks, dropping the asterisks."""
    if not text:
        return []
    runs: list[dict] = []

    # Bold first (consumes doubles), then italic over the plain segments.
    pos = 0
    for m in _BOLD_RE.finditer(text):
        if m.start() > pos:
            runs.extend(_italic_runs(text[pos:m.start()]))
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        # bold may contain nested italic
        for r in _italic_runs(inner):
            marks = sorted(set(r.get("marks", []) + ["bold"]))
            runs.append({"text": r["text"], "marks": marks})
        pos = m.end()
    if pos < len(text):
        runs.extend(_italic_runs(text[pos:]))
    return [r for r in runs if r.get("text")]


def _italic_runs(text: str) -> list[dict]:
    if not text:
        return []
    runs: list[dict] = []
    pos = 0
    for m in _ITALIC_RE.finditer(text):
        if m.start() > pos:
            runs.append({"text": text[pos:m.start()], "marks": []})
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        runs.append({"text": inner, "marks": ["italic"]})
        pos = m.end()
    if pos < len(text):
        runs.append({"text": text[pos:], "marks": []})
    return runs


# ---------------------------------------------------------------------------
# Markdown (pipe) tables
# ---------------------------------------------------------------------------

def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _looks_like_table(lines: list[str], i: int) -> bool:
    return (
        i + 1 < len(lines)
        and "|" in lines[i]
        and _TABLE_SEP_RE.match(lines[i + 1] or "")
    )


# ---------------------------------------------------------------------------
# Main parser: markdown → blocks_v1
# ---------------------------------------------------------------------------

def markdown_to_blocks(text: str) -> list[dict]:
    """Convert the markdown an LLM produces into a list of blocks_v1.

    Deterministic, best-effort: any line that does not match a known structure
    falls back to a paragraph. Never raises (returns what it parsed).
    """
    if not text or not text.strip():
        return []

    # Normalize basic HTML an agent might emit (<b>, <br>).
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")

    lines = text.split("\n")
    blocks: list[dict] = []
    i = 0
    n = len(lines)
    para_buf: list[str] = []
    list_buf: list[list[dict]] = []
    list_kind: str | None = None

    def flush_para():
        nonlocal para_buf
        if para_buf:
            joined = " ".join(s.strip() for s in para_buf if s.strip())
            if joined:
                blocks.append({"type": "paragraph", "runs": _parse_runs(joined)})
            para_buf = []

    def flush_list():
        nonlocal list_buf, list_kind
        if list_buf:
            blocks.append({"type": list_kind or "bullet_list", "items": list_buf})
            list_buf = []
            list_kind = None

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_para(); flush_list()
            i += 1
            continue

        # Table
        if _looks_like_table(lines, i):
            flush_para(); flush_list()
            columns = _split_row(lines[i])
            rows: list[list[str]] = []
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip():
                rows.append(_split_row(lines[j]))
                j += 1
            blocks.append({"type": "table", "anchor_id": None,
                           "columns": columns, "rows": rows})
            i = j
            continue

        # Heading
        m = _HEADING_RE.match(stripped)
        if m:
            flush_para(); flush_list()
            blocks.append({"type": "heading", "level": len(m.group(1)),
                           "runs": _parse_runs(m.group(2).strip())})
            i += 1
            continue

        # Lists
        mb = _BULLET_RE.match(line)
        mo = _ORDERED_RE.match(line)
        if mb:
            flush_para()
            if list_kind not in (None, "bullet_list"):
                flush_list()
            list_kind = "bullet_list"
            list_buf.append(_parse_runs(mb.group(1).strip()))
            i += 1
            continue
        if mo:
            flush_para()
            if list_kind not in (None, "ordered_list"):
                flush_list()
            list_kind = "ordered_list"
            list_buf.append(_parse_runs(mo.group(1).strip()))
            i += 1
            continue

        # Paragraph (accumulate contiguous lines)
        flush_list()
        para_buf.append(stripped)
        i += 1

    flush_para(); flush_list()
    return blocks


def build_document(section: str, domain: str, content: str,
                   anchors_produced: list[dict] | None = None) -> dict:
    """Wrap the parsed blocks into the blocks_v1 document of one section.

    ``anchors_produced`` (optional): anchors this section publishes to the
    blackboard. Usually empty here; ``assign_anchor`` binds anchor_ids later.
    """
    blocks = markdown_to_blocks(content)
    return {
        "format": BLOCKS_FORMAT,
        "section_id": section,
        "domain": domain,
        "blocks": blocks,
        "anchors": anchors_produced or [],
    }


def assign_anchor(doc: dict, anchor_ids: list[str]) -> dict:
    """Assign anchor_ids to the document's UN-anchored tables, in order.

    The contract declares that this section ``produces`` certain tables; here we
    bind them to their stable anchor_id so other sections can cite them with
    [ref:anchor_id] (the composer resolves it to "Table N"). Best-effort: if
    there are fewer tables than anchor_ids (or more), bind what it can.
    """
    if not anchor_ids:
        return doc
    pending = list(anchor_ids)
    for b in doc.get("blocks", []):
        if not pending:
            break
        if b.get("type") == "table" and not b.get("anchor_id"):
            b["anchor_id"] = pending.pop(0)
    return doc


def anchor_summary(doc: dict, anchor_id: str) -> str:
    """Short summary of an anchor (table) to publish to the blackboard.

    E.g. "table 5 rows x 4 cols (Contract, Entity, Value, Year)". So the
    consuming section can cite it meaningfully without seeing its content.
    """
    for b in doc.get("blocks", []):
        if b.get("type") == "table" and b.get("anchor_id") == anchor_id:
            cols = b.get("columns", [])
            return (f"table {len(b.get('rows', []))} rows x {len(cols)} cols"
                    + (f" ({', '.join(cols)})" if cols else ""))
    return ""


def blocks_stats(doc: dict) -> dict[str, Any]:
    """Quick metrics of the AST (for trajectory/telemetry)."""
    blocks = doc.get("blocks", [])
    by_type: dict[str, int] = {}
    for b in blocks:
        by_type[b["type"]] = by_type.get(b["type"], 0) + 1
    return {"total_blocks": len(blocks), "by_type": by_type}
