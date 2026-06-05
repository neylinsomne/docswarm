"""FactsPort — hard, case-specific facts shared by ALL agents.

Facts are the single source of truth that prevents cross-section
inconsistencies (same ids, names, dates everywhere). They seed the blackboard.
A fact set is just a dict; this port lets the domain compute it lazily (e.g.
from a database row) instead of passing a static dict.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FactsPort(Protocol):
    def facts(self, **context: Any) -> dict:
        """Return the hard-fact dict for one document run.

        ``context`` carries whatever identifies the case (ids, references...).
        """
        ...


class StaticFacts:
    """A FactsPort backed by a fixed dict. The simplest possible adapter."""

    def __init__(self, data: dict) -> None:
        self._data = dict(data or {})

    def facts(self, **context: Any) -> dict:
        return dict(self._data)
