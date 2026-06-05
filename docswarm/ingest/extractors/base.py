"""Extraction result DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractResult:
    text: str
    method: str
        # 'pdf_text' | 'pdf_ocr' | 'pdf_hybrid' | 'xlsx' | 'docx' | 'plain'
        # | 'unsupported' | 'error'
    pages: int = 0
    ocr_pages: int = 0
    tables_markdown: list[str] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
        # structured tables: [{page, markdown, rows: [[...]]}]
    chars: int = 0
    meta: dict = field(default_factory=dict)
    error: Optional[str] = None

    def __post_init__(self):
        if not self.chars:
            self.chars = len(self.text or "")

    @property
    def ok(self) -> bool:
        return self.method not in ("error", "unsupported") and bool((self.text or "").strip())
