"""StubLLM — a deterministic, offline LLMPort.

It does not call any model. Instead it reads the structured hints the engine
already put into the prompt (the contract block: what to cover, which table to
produce, which anchor to cite) and emits markdown that satisfies them. That is
enough to exercise the WHOLE pipeline end-to-end — contracts, blackboard,
blocks parsing, anchor numbering, cross-reference resolution — with no model
installed. Used by the test suite and as the demo's offline fallback.

Output is fully determined by the prompt, so runs are reproducible.
"""

from __future__ import annotations

import re

_COVER_RE = re.compile(r"YOU MUST cover:\s*(.+?)\.\s*(?:\n|$)")
_PRODUCE_RE = re.compile(
    r'produce a (\w+) titled "([^"]+)"(?: with columns:\s*([^.]+?))?\.\s*'
    r'It is the \w+ ([A-Za-z0-9_\-]+):')
_CITE_RE = re.compile(r"\[ref:([A-Za-z0-9_\-]+)\]")
_TASK_RE = re.compile(r"## TASK\nWrite the section \*\*(.+?)\*\*")


def _sample_rows(columns: list[str], n: int = 3) -> list[list[str]]:
    rows: list[list[str]] = []
    for r in range(1, n + 1):
        row = []
        for c, col in enumerate(columns):
            # deterministic, readable cell values
            if c == 0:
                row.append(f"{col} {r}")
            else:
                row.append(str(r * (c + 10)))
        rows.append(row)
    return rows


class StubLLM:
    """Deterministic LLM stand-in driven by the contract hints in the prompt."""

    def complete(self, system: str, prompt: str, **options) -> str:
        title_m = _TASK_RE.search(prompt)
        title = title_m.group(1) if title_m else "Section"
        out: list[str] = []

        covers = _COVER_RE.search(prompt)
        if covers:
            items = [x.strip() for x in re.split(r";|,", covers.group(1)) if x.strip()]
            lead = ", ".join(items[:3]) if items else title.lower()
            out.append(f"This section on {title.lower()} addresses {lead}.")

        # Tables this section must produce.
        produced_any = False
        for _typ, tbl_title, cols_raw, _anchor in _PRODUCE_RE.findall(prompt):
            produced_any = True
            cols = [c.strip() for c in (cols_raw or "").split(",") if c.strip()] \
                or ["Item", "Value"]
            out.append(f"The {tbl_title.lower()} is summarized below.")
            # The table must be ONE contiguous block (header, separator, rows on
            # consecutive lines) so the markdown→blocks parser detects it.
            table_lines = ["| " + " | ".join(cols) + " |",
                           "| " + " | ".join("---" for _ in cols) + " |"]
            for row in _sample_rows(cols):
                table_lines.append("| " + " | ".join(row) + " |")
            out.append("\n".join(table_lines))

        # Anchors this section must cite.
        cited = []
        for aid in _CITE_RE.findall(prompt):
            if aid not in cited:
                cited.append(aid)
        for aid in cited:
            out.append(
                f"As shown in [ref:{aid}], the figures above support the "
                f"analysis presented in this section.")

        if not out:
            out.append(f"This is the **{title}** section, written deterministically "
                       f"for offline testing.")
        elif not produced_any and not cited:
            out.append("The points above are consistent with the shared facts.")

        return "\n\n".join(out)
