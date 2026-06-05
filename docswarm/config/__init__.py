"""Config — the plan that drives the swarm (what licitemos hardcoded, here CONFIG)."""

from __future__ import annotations

from docswarm.config.schema import (
    AnchorConfig,
    PlanConfig,
    SectionConfig,
    load_plan,
    plan_from_dict,
)

__all__ = ["PlanConfig", "SectionConfig", "AnchorConfig", "load_plan", "plan_from_dict"]
