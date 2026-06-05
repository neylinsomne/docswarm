"""
SectionContract — the anti-overlap mechanism.

In the PLAN phase the orchestrator emits ONE contract per section and hands it
to each agent. The contract is the ANTI-OVERLAP (disjoint scope: must_cover /
must_not_cover) plus the COMPLEMENTARITY mechanism (produces/consumes anchors).

- ``produces``: anchors THIS section publishes (e.g. table "tbl-metrics").
- ``consumes``: anchors of OTHER sections this one cites (by anchor_id, it does
  NOT copy the content) → the agent is told to reference it with [ref:anchor_id],
  which the composer resolves to "Table N".

The orchestrator assigns the stable ``anchor_id`` in the PLAN, so A produces
"tbl-metrics" and B knows (from its contract) it must cite "tbl-metrics" —
without either talking to the other.

ZERO LLM in this module: it just builds structure. The plan that decides the
sections is CONFIG (``docswarm.config.PlanConfig``), not hardcoded domain rules.
That is the key difference from a domain-locked engine: ``build_contracts``
receives the plan, it does not own it.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AnchorSpec:
    """An anchor a section publishes (citable table/figure)."""
    anchor_id: str
    type: str            # "table" | "figure"
    title: str
    schema: list[str] = field(default_factory=list)   # columns, if a table


@dataclass
class SectionContract:
    """What the orchestrator assigns to EACH section/agent. Anti-overlap."""
    section_id: str
    title: str
    agent: str                                  # which agent handles it
    order_key: int                              # for assembly (composer)
    must_cover: list[str] = field(default_factory=list)
    must_not_cover: list[str] = field(default_factory=list)
    max_words: Optional[int] = None
    produces: list[AnchorSpec] = field(default_factory=list)
    consumes: list[str] = field(default_factory=list)   # anchor_ids it cites
    tone: str = "technical, formal"

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def prompt_block(self) -> str:
        """Render the contract as an instruction block for the LLM.

        Prepended to the agent prompt to BOUND its scope. It is text, not
        formatting — the agent keeps writing its normal content, but respecting
        the contract limits.
        """
        lines = [f"## CONTRACT FOR THIS SECTION ({self.section_id} - {self.title})"]
        if self.must_cover:
            lines.append("YOU MUST cover: " + "; ".join(self.must_cover) + ".")
        if self.must_not_cover:
            lines.append("DO NOT cover (it belongs to ANOTHER section): "
                         + "; ".join(self.must_not_cover) + ".")
        if self.max_words:
            lines.append(f"Target length: ~{self.max_words} words (do not exceed).")
        for a in self.produces:
            cols = (" with columns: " + ", ".join(a.schema)) if a.schema else ""
            lines.append(
                f"YOU MUST produce a {a.type} titled \"{a.title}\"{cols}. "
                f"It is the {a.type} {a.anchor_id}: the composer will number it.")
        for aid in self.consumes:
            lines.append(
                f"YOU MUST CITE (do not rewrite) anchor {aid} using exactly the "
                f"marker [ref:{aid}] where appropriate. DO NOT copy its content.")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# PLAN — build contracts from a plan (config), not hardcoded rules
# ---------------------------------------------------------------------------

def _section_attrs(section: Any) -> dict:
    """Normalize a plan section (a SectionConfig dataclass OR a plain dict)."""
    if dataclasses.is_dataclass(section):
        return dataclasses.asdict(section)
    if isinstance(section, dict):
        return dict(section)
    raise TypeError(f"unsupported section type: {type(section)!r}")


def build_contracts(plan: Any) -> dict[str, SectionContract]:
    """Build one SectionContract per section of the plan.

    ``plan`` may be a ``docswarm.config.PlanConfig`` or any object/dict exposing
    ``sections``: a list of section configs (dataclass or dict) with fields:
      id, agent, order?, title?, must_cover?, must_not_cover?, max_words?,
      produces? (list of {anchor_id,type,title,schema}), consumes? (list[str]),
      tone?

    ``order_key`` is derived from each section's ``order`` (or its position).
    A ``consumes`` anchor is only kept if SOME section in this plan ``produces``
    it (no point citing an anchor nobody creates).
    """
    sections = list(getattr(plan, "sections", None) or
                    (plan.get("sections") if isinstance(plan, dict) else []))
    norm = [_section_attrs(s) for s in sections]

    # 1st pass: which anchors are actually produced in this plan.
    produced_anchors: set[str] = set()
    for s in norm:
        for a in (s.get("produces") or []):
            aid = a.get("anchor_id") if isinstance(a, dict) else getattr(a, "anchor_id", None)
            if aid:
                produced_anchors.add(aid)

    contracts: dict[str, SectionContract] = {}
    for idx, s in enumerate(norm):
        sec_id = s.get("id") or s.get("section_id")
        if not sec_id:
            raise ValueError(f"plan section #{idx} has no 'id'")
        produces = []
        for a in (s.get("produces") or []):
            a = a if isinstance(a, dict) else dataclasses.asdict(a)
            produces.append(AnchorSpec(
                anchor_id=a["anchor_id"], type=a.get("type", "table"),
                title=a.get("title", ""), schema=list(a.get("schema") or [])))
        consumes = [aid for aid in (s.get("consumes") or [])
                    if aid in produced_anchors]
        order = s.get("order")
        order_key = int(order) * 100 if isinstance(order, (int, float)) else idx * 100
        contracts[sec_id] = SectionContract(
            section_id=sec_id,
            title=s.get("title") or sec_id.replace("_", " ").title(),
            agent=s.get("agent") or "general",
            order_key=order_key,
            must_cover=list(s.get("must_cover") or []),
            must_not_cover=list(s.get("must_not_cover") or []),
            max_words=s.get("max_words"),
            produces=produces,
            consumes=consumes,
            tone=s.get("tone") or "technical, formal",
        )
    return contracts


def contract_from_dict(data: Optional[dict]) -> Optional[SectionContract]:
    """Rebuild a SectionContract from a payload (agent side / over the wire)."""
    if not isinstance(data, dict):
        return None
    try:
        produces = [AnchorSpec(**a) for a in (data.get("produces") or [])]
        kwargs = {k: v for k, v in data.items()
                  if k in {f.name for f in dataclasses.fields(SectionContract)}}
        kwargs["produces"] = produces
        return SectionContract(**kwargs)
    except Exception:  # noqa: BLE001
        return None
