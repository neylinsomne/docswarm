"""
Deterministic document composer.

Takes the blocks_v1 ASTs of several sections (what each agent emits, see
``docswarm.orchestration.blocks``) and produces ONE final document:
  1. orders sections by ``order_key`` (or the given plan),
  2. concatenates their blocks → "B follows right after A" is automatic,
  3. LATE numbering (late binding): numbers tables/figures and headings by the
     final order,
  4. RESOLVES cross refs: { type:"ref", anchor_id } → "Table 3",
  5. applies spacing/style with FIXED rules,
  6. serializes to HTML (editor) and markdown (export/debug).

ZERO LLM. It is a transformation service (golden rule: deterministic). It does
not depend on sections having run in order — late binding ties refs at the end,
so A and B can be generated in parallel.

Input: list of "composed sections":
  { "section_id": "2.3", "order_key": 230, "title": "...", "document": <blocks_v1> }

Output (compose_document):
  { "format": "document_v1", "blocks": [...], "anchors": {...},
    "html": "...", "markdown": "...", "warnings": [...] }
"""

from __future__ import annotations

import html as _html

DOCUMENT_FORMAT = "document_v1"


# ---------------------------------------------------------------------------
# 1-2. Collect + order + concatenate blocks
# ---------------------------------------------------------------------------

def _ordered_sections(sections: list[dict]) -> list[dict]:
    """Order by order_key; sections without order_key go last, stable."""
    def key(s: dict, idx: int):
        ok = s.get("order_key")
        return (0, ok, idx) if isinstance(ok, (int, float)) else (1, 0, idx)
    return [s for _, s in sorted(
        ((key(s, i), s) for i, s in enumerate(sections)))]


# ---------------------------------------------------------------------------
# 3-4. Late binding: number anchors + headings, resolve refs
# ---------------------------------------------------------------------------

def _collect_anchors(blocks: list[dict]) -> dict[str, dict]:
    """Number tables with anchor_id, in appearance order.

    Returns { anchor_id: {"kind":"table","number":N,"label":"Table N"} }.
    (Figures will be added once the AST has 'figure' blocks.)
    """
    anchors: dict[str, dict] = {}
    table_n = 0
    for b in blocks:
        if b.get("type") == "table" and b.get("anchor_id"):
            table_n += 1
            anchors[b["anchor_id"]] = {
                "kind": "table", "number": table_n, "label": f"Table {table_n}"}
    return anchors


def _resolve_runs(runs: list[dict], anchors: dict[str, dict],
                  warnings: list[str]) -> list[dict]:
    """Replace {type:ref} nodes with text "Table N" (or placeholder if missing)."""
    out: list[dict] = []
    for r in runs or []:
        if r.get("type") == "ref":
            aid = r.get("anchor_id")
            anc = anchors.get(aid)
            if anc:
                out.append({"text": anc["label"], "marks": []})
            else:
                warnings.append(f"ref to missing anchor: {aid}")
                out.append({"text": "[pending reference]", "marks": []})
        else:
            out.append(r)
    return out


def _number_headings(blocks: list[dict]) -> None:
    """Number headings hierarchically (1, 1.1, 1.1.1) in-place.

    Only if the heading's first run does NOT already carry a number (e.g.
    "2.3 ..."). Conservative heuristic to avoid duplicating LLM numbering.
    """
    counters = [0, 0, 0, 0, 0, 0]
    for b in blocks:
        if b.get("type") != "heading":
            continue
        lvl = max(1, min(6, b.get("level", 1)))
        first = (b.get("runs") or [{}])[0].get("text", "").lstrip()
        # already numbered by the LLM? (e.g. "2.3 Analysis")
        already = bool(first[:1].isdigit() and "." in first[:6])
        counters[lvl - 1] += 1
        for k in range(lvl, 6):
            counters[k] = 0
        if not already:
            num = ".".join(str(counters[i]) for i in range(lvl) if counters[i])
            b["_number"] = num


# ---------------------------------------------------------------------------
# 6. Serialization
# ---------------------------------------------------------------------------

def _runs_to_html(runs: list[dict]) -> str:
    parts: list[str] = []
    for r in runs or []:
        if r.get("type") == "citation":
            src = _html.escape(r.get("source") or "source")
            url = r.get("url")
            sup = f'<sup class="cite" title="{src}">[{src}]</sup>'
            parts.append(f'<a href="{_html.escape(url)}">{sup}</a>' if url else sup)
            continue
        txt = _html.escape(r.get("text", ""))
        for m in r.get("marks", []):
            if m == "bold":
                txt = f"<strong>{txt}</strong>"
            elif m == "italic":
                txt = f"<em>{txt}</em>"
        parts.append(txt)
    return "".join(parts)


def _runs_to_md(runs: list[dict]) -> str:
    parts: list[str] = []
    for r in runs or []:
        if r.get("type") == "citation":
            parts.append(f"[{r.get('source','source')}]")
            continue
        txt = r.get("text", "")
        marks = r.get("marks", [])
        if "bold" in marks:
            txt = f"**{txt}**"
        if "italic" in marks:
            txt = f"*{txt}*"
        parts.append(txt)
    return "".join(parts)


def _blocks_to_html(blocks: list[dict]) -> str:
    out: list[str] = []
    for b in blocks:
        t = b.get("type")
        if t == "heading":
            lvl = max(1, min(6, b.get("level", 1)))
            num = (b.get("_number") + " ") if b.get("_number") else ""
            out.append(f"<h{lvl}>{_html.escape(num)}{_runs_to_html(b.get('runs'))}</h{lvl}>")
        elif t == "paragraph":
            out.append(f"<p>{_runs_to_html(b.get('runs'))}</p>")
        elif t in ("bullet_list", "ordered_list"):
            tag = "ul" if t == "bullet_list" else "ol"
            items = "".join(f"<li>{_runs_to_html(it)}</li>" for it in b.get("items", []))
            out.append(f"<{tag}>{items}</{tag}>")
        elif t == "table":
            cap = ""
            if b.get("_label") and b.get("title"):
                cap = f"<caption>{_html.escape(b['_label'])}. {_html.escape(b['title'])}</caption>"
            thead = "".join(f"<th>{_html.escape(c)}</th>" for c in b.get("columns", []))
            rows = "".join(
                "<tr>" + "".join(f"<td>{_html.escape(str(c))}</td>" for c in row) + "</tr>"
                for row in b.get("rows", []))
            out.append(f"<table>{cap}<thead><tr>{thead}</tr></thead><tbody>{rows}</tbody></table>")
        elif t == "code":
            out.append(f"<pre><code>{_html.escape(b.get('text',''))}</code></pre>")
    return "\n".join(out)


def _blocks_to_md(blocks: list[dict]) -> str:
    out: list[str] = []
    for b in blocks:
        t = b.get("type")
        if t == "heading":
            lvl = max(1, min(6, b.get("level", 1)))
            num = (b.get("_number") + " ") if b.get("_number") else ""
            out.append(f"{'#' * lvl} {num}{_runs_to_md(b.get('runs'))}")
        elif t == "paragraph":
            out.append(_runs_to_md(b.get("runs")))
        elif t == "bullet_list":
            out.append("\n".join(f"- {_runs_to_md(it)}" for it in b.get("items", [])))
        elif t == "ordered_list":
            out.append("\n".join(f"{i+1}. {_runs_to_md(it)}"
                                 for i, it in enumerate(b.get("items", []))))
        elif t == "table":
            if b.get("_label") and b.get("title"):
                out.append(f"**{b['_label']}. {b['title']}**")
            cols = b.get("columns", [])
            # Render the whole table as ONE block so rows stay on consecutive
            # lines (blank lines between rows would break the markdown table).
            tbl = ["| " + " | ".join(cols) + " |",
                   "| " + " | ".join("---" for _ in cols) + " |"]
            for row in b.get("rows", []):
                tbl.append("| " + " | ".join(str(c) for c in row) + " |")
            out.append("\n".join(tbl))
        elif t == "code":
            out.append(f"```\n{b.get('text','')}\n```")
    # Fixed spacing: one blank line between blocks.
    return "\n\n".join(x for x in out if x)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_document(sections: list[dict]) -> dict:
    """Assemble the sections (each with its blocks_v1 AST) into one document.

    ``sections``: [{ "section_id", "order_key", "title"?, "document": blocks_v1 }]
    Sections without ``document`` (an agent that emitted no AST) are ignored for
    the AST but a warning is recorded (the caller can fall back to that
    section's text/html separately).
    """
    warnings: list[str] = []
    ordered = _ordered_sections(sections)

    # 2. Concatenate all blocks in order. Annotate each table with its section
    #    title (for the caption) when the section provided one.
    all_blocks: list[dict] = []
    for s in ordered:
        doc = s.get("document")
        if not isinstance(doc, dict) or not doc.get("blocks"):
            warnings.append(f"section without blocks_v1: {s.get('section_id')}")
            continue
        sec_title = s.get("title")
        for b in doc["blocks"]:
            if b.get("type") == "table" and sec_title and not b.get("title"):
                b["title"] = sec_title
            all_blocks.append(b)

    # 3. Number anchors (tables) and headings.
    anchors = _collect_anchors(all_blocks)
    for b in all_blocks:
        if b.get("type") == "table" and b.get("anchor_id") in anchors:
            b["_label"] = anchors[b["anchor_id"]]["label"]
    _number_headings(all_blocks)

    # 4. Resolve cross refs (late binding).
    for b in all_blocks:
        if b.get("type") in ("heading", "paragraph"):
            b["runs"] = _resolve_runs(b.get("runs"), anchors, warnings)
        elif b.get("type") in ("bullet_list", "ordered_list"):
            b["items"] = [_resolve_runs(it, anchors, warnings)
                          for it in b.get("items", [])]

    return {
        "format": DOCUMENT_FORMAT,
        "blocks": all_blocks,
        "anchors": anchors,
        "html": _blocks_to_html(all_blocks),
        "markdown": _blocks_to_md(all_blocks),
        "warnings": warnings,
        "section_order": [s.get("section_id") for s in ordered],
    }
