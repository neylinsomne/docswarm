"""PlanConfig — the document plan, loaded from YAML or a dict.

A plan declares the document's sections: which agent writes each, in what order,
the anti-overlap scope (must_cover / must_not_cover), and the anchors each one
produces/consumes. This is the ONE place a domain is expressed; the engine reads
it, it does not own it. See ``examples/informe_demo/plan.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AnchorConfig:
    anchor_id: str
    type: str = "table"
    title: str = ""
    schema: list[str] = field(default_factory=list)


@dataclass
class SectionConfig:
    id: str
    agent: str
    order: int = 0
    title: str = ""
    must_cover: list[str] = field(default_factory=list)
    must_not_cover: list[str] = field(default_factory=list)
    max_words: Optional[int] = None
    produces: list[AnchorConfig] = field(default_factory=list)
    consumes: list[str] = field(default_factory=list)
    tone: str = "technical, formal"


@dataclass
class PlanConfig:
    title: str
    sections: list[SectionConfig] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _anchor_from(data: dict) -> AnchorConfig:
    return AnchorConfig(
        anchor_id=data["anchor_id"],
        type=data.get("type", "table"),
        title=data.get("title", ""),
        schema=list(data.get("schema") or []),
    )


def _section_from(data: dict) -> SectionConfig:
    return SectionConfig(
        id=data["id"],
        agent=data.get("agent", "general"),
        order=int(data.get("order", 0)),
        title=data.get("title", ""),
        must_cover=list(data.get("must_cover") or []),
        must_not_cover=list(data.get("must_not_cover") or []),
        max_words=data.get("max_words"),
        produces=[_anchor_from(a) for a in (data.get("produces") or [])],
        consumes=list(data.get("consumes") or []),
        tone=data.get("tone", "technical, formal"),
    )


def plan_from_dict(data: dict) -> PlanConfig:
    """Build a PlanConfig from a plain dict (already parsed YAML/JSON)."""
    if not isinstance(data, dict):
        raise TypeError("plan must be a mapping")
    sections = [_section_from(s) for s in (data.get("sections") or [])]
    if not sections:
        raise ValueError("plan has no sections")
    return PlanConfig(
        title=data.get("title", "Document"),
        sections=sections,
        meta=dict(data.get("meta") or {}),
    )


def load_plan(path: str) -> PlanConfig:
    """Load a plan from a YAML (preferred) or JSON file.

    YAML needs PyYAML (``pip install docswarm[yaml]``). JSON works with stdlib.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    data: Any
    if path.lower().endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError(
                "PyYAML required for YAML plans. Run: pip install docswarm[yaml]"
            ) from exc
        data = yaml.safe_load(raw)
    else:
        import json
        data = json.loads(raw)
    return plan_from_dict(data)
