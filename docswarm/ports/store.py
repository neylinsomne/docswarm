"""StorePort — persist a finished run (training data / audit), optional."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class RunRecord:
    """One agent (or whole-swarm) execution, ready to persist."""
    run_id: str
    agent_name: str
    status: str                          # "completed" | "failed"
    section_id: str = ""
    output: dict = field(default_factory=dict)
    trajectory: list = field(default_factory=list)
    error: Optional[dict] = None
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)


@runtime_checkable
class StorePort(Protocol):
    def persist(self, record: RunRecord) -> None:
        """Persist one run record. Implementations decide where (DB, file, ...)."""
        ...


class InMemoryStore:
    """Keeps runs in a list. Useful for tests/demos; swap for a DB in prod."""

    def __init__(self) -> None:
        self.records: list[RunRecord] = []

    def persist(self, record: RunRecord) -> None:
        self.records.append(record)

    def by_agent(self, agent_name: str) -> list[RunRecord]:
        return [r for r in self.records if r.agent_name == agent_name]
