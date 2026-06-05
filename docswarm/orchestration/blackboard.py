"""
Shared blackboard between agents (Hearsay-II pattern).

Agents do NOT talk to each other directly; they publish and consume SYMBOLS on a
shared board. This is complementarity without overlap: agent A publishes the
anchor ``tbl-metrics`` (with a ``summary``); agent B, if its contract
``consumes`` it, reads that summary + id and cites the table MEANINGFULLY —
without receiving A's full text.

DESIGN: in-memory store per process, indexed by ``board_id``. Valid when all
agents run in-process. Persisting to a database for HA/distributed is a later
step; this module's API does not change when migrating.

GENERIC FOR ALL AGENTS: not exclusive to section agents.
  - section agents → publish tables/figures (anchors), consume others'.
  - judge          → may publish a per-section score summary (anchor type
                     "judge_score") for others to read.
  - reviewer       → may read the WHOLE board to audit consistency.
Each agent decides what it publishes/consumes; the board is type-agnostic.

Thread-safe: accesses go under a lock.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Board structure
#   facts:   hard data shared by EVERYONE → zero inconsistencies (same ids,
#            names, dates across all sections).
#   anchors: symbols published by sections (tables, figures, scores...).
#            { anchor_id: {type, section_id, title, summary, status, payload} }
# ---------------------------------------------------------------------------

_boards: dict[str, dict[str, Any]] = {}
_lock = threading.RLock()

# Defensive TTL so we don't accumulate boards from old runs in memory.
_TTL_SECONDS = 3600


def _now() -> float:
    return time.monotonic()


def _gc_locked() -> None:
    """Remove expired boards. Must be called with the lock held."""
    dead = [bid for bid, b in _boards.items()
            if _now() - b.get("_touched", 0) > _TTL_SECONDS]
    for bid in dead:
        _boards.pop(bid, None)


# ---------------------------------------------------------------------------
# Board lifecycle
# ---------------------------------------------------------------------------

def create_board(facts: Optional[dict] = None, board_id: Optional[str] = None) -> str:
    """Create a board for one document run and seed it with facts.

    Returns the ``board_id`` the orchestrator passes to each agent.
    """
    bid = board_id or str(uuid.uuid4())
    with _lock:
        _gc_locked()
        _boards[bid] = {
            "facts": dict(facts or {}),
            "anchors": {},
            "_touched": _now(),
        }
    return bid


def clear_board(board_id: str) -> None:
    with _lock:
        _boards.pop(board_id, None)


def _touch(board_id: str) -> Optional[dict]:
    b = _boards.get(board_id)
    if b is not None:
        b["_touched"] = _now()
    return b


# ---------------------------------------------------------------------------
# Facts (shared hard data)
# ---------------------------------------------------------------------------

def set_facts(board_id: str, facts: dict) -> None:
    with _lock:
        b = _touch(board_id)
        if b is not None:
            b["facts"].update(facts or {})


def get_facts(board_id: str) -> dict:
    with _lock:
        b = _touch(board_id)
        return dict(b["facts"]) if b else {}


# ---------------------------------------------------------------------------
# Anchors (symbols one agent publishes for another to consume)
# ---------------------------------------------------------------------------

def publish_anchor(board_id: str, anchor_id: str, *, type: str,
                   section_id: str, title: str = "", summary: str = "",
                   status: str = "ready", payload: Optional[dict] = None) -> None:
    """Publish (or update) an anchor on the board.

    ``summary``: short description so the consumer cites meaningfully (e.g.
    "5 contracts, total $2.3M"). The full content is NOT published.
    ``type``: "table" | "figure" | "judge_score" | ... (free, agnostic).
    """
    with _lock:
        b = _touch(board_id)
        if b is None:
            return
        b["anchors"][anchor_id] = {
            "anchor_id": anchor_id, "type": type, "section_id": section_id,
            "title": title, "summary": summary, "status": status,
            "payload": payload or {},
        }


def get_view(board_id: str, anchor_ids: Optional[list[str]] = None) -> dict[str, dict]:
    """Board view filtered to the requested anchors (the ones a contract
    ``consumes``). Without ``anchor_ids`` → returns ALL (useful for a reviewer)."""
    with _lock:
        b = _touch(board_id)
        if b is None:
            return {}
        anchors = b["anchors"]
        if anchor_ids is None:
            return {k: dict(v) for k, v in anchors.items()}
        return {aid: dict(anchors[aid]) for aid in anchor_ids if aid in anchors}


def snapshot(board_id: str) -> dict:
    """Full copy of the board (for persistence/telemetry/debug)."""
    with _lock:
        b = _touch(board_id)
        if b is None:
            return {}
        return {
            "facts": dict(b["facts"]),
            "anchors": {k: dict(v) for k, v in b["anchors"].items()},
        }
