"""Orchestration core — the agnostic document engine.

Nothing here imports a database, a web framework, or any business domain. The
pieces:

  - ``blocks``      : ``blocks_v1`` typed AST + markdown→AST parser.
  - ``contracts``   : ``SectionContract`` (anti-overlap scope + produces/consumes).
  - ``blackboard``  : in-memory shared board (Hearsay-II pattern).
  - ``composer``    : deterministic assembly, late-bound numbering, ref resolution.
"""

from __future__ import annotations

from docswarm.orchestration import blackboard, blocks, composer, contracts

__all__ = ["blocks", "contracts", "blackboard", "composer"]
