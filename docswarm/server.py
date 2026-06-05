"""Optional ACP server — expose the swarm agents over the ACP protocol.

The in-process ``SwarmRunner`` is all you need for a single service. This module
is for when you want agents to live in SEPARATE processes or languages and talk
over ACP (Agent Communication Protocol). It is OPTIONAL and EXPERIMENTAL:
``acp-sdk`` is imported lazily, so the rest of docswarm works without it.

    pip install docswarm[acp]

Each docswarm agent becomes an ACP agent that accepts an ``application/json``
payload ``{section_id, contract, facts, chunks, board_view, instructions}`` and
returns the generated section as ``text/markdown`` plus structured JSON.
"""

from __future__ import annotations

import json
from typing import Any

from docswarm.agents.base import BaseAgent, SectionRequest
from docswarm.orchestration.contracts import contract_from_dict
from docswarm.ports.llm import LLMPort


def _payload_to_request(payload: dict) -> SectionRequest:
    contract = contract_from_dict(payload.get("contract"))
    if contract is None:
        raise ValueError("payload.contract is required and must be a contract dict")
    return SectionRequest(
        section_id=payload.get("section_id") or contract.section_id,
        contract=contract,
        facts=payload.get("facts") or {},
        chunks=payload.get("chunks") or [],
        board_view=payload.get("board_view") or {},
        instructions=payload.get("instructions") or "",
    )


def build_acp_server(agents: dict[str, BaseAgent], llm: LLMPort) -> Any:
    """Build an ``acp_sdk`` Server with one ACP agent per docswarm agent.

    Returns the Server instance; call ``acp_sdk.server.create_app(*server.agents)``
    (or use ``serve``) to get an ASGI app. Raises ImportError if acp-sdk is
    missing — install with ``pip install docswarm[acp]``.
    """
    try:
        from acp_sdk.models import Message, MessagePart
        from acp_sdk.server import Server, agent as agent_decorator
    except ImportError as exc:  # noqa: BLE001
        raise ImportError(
            "acp-sdk not installed. Run: pip install docswarm[acp]") from exc

    server = Server()

    def _make_handler(name: str, ag: BaseAgent):
        def handler(input: list, context) -> Any:  # generator (sync)
            payload: dict = {}
            for msg in input:
                for part in getattr(msg, "parts", []):
                    if part.content and (part.content_type or "").startswith("application/json"):
                        try:
                            payload = json.loads(part.content)
                            break
                        except Exception:  # noqa: BLE001
                            continue
            req = _payload_to_request(payload)
            result = ag.generate(req, llm)
            yield MessagePart(content=result.content or "", content_type="text/markdown")
            yield MessagePart(
                content_type="application/json",
                content=json.dumps({
                    "section_id": result.section_id,
                    "content": result.content,
                    "error": result.error,
                    "latency_ms": result.latency_ms,
                }, ensure_ascii=False))
        handler.__name__ = name
        return handler

    for name, ag in agents.items():
        manifest = agent_decorator(
            name=name,
            description=f"docswarm section agent '{name}'",
            input_content_types=["application/json"],
            output_content_types=["text/markdown", "application/json"],
        )(_make_handler(name, ag))
        server.register(manifest)

    return server
