"""StorePort → persiste cada ejecución de agente en `acp_runs` (dataset SFT/eval)."""

from __future__ import annotations

import json
from typing import Optional

from app.db import db_conn
from docswarm.ports.store import RunRecord


class AcpRunsStore:
    """Implementa docswarm.ports.StorePort escribiendo en acp_runs."""

    def __init__(self, empresa_id: Optional[int] = None,
                 contrato_id: Optional[int] = None) -> None:
        self.empresa_id = empresa_id
        self.contrato_id = contrato_id

    def persist(self, record: RunRecord) -> None:
        try:
            with db_conn(empresa_id=self.empresa_id) as conn:
                conn.execute(
                    """
                    INSERT INTO acp_runs (run_id, agent_name, section_id, status,
                                          empresa_id, contrato_id, output, trajectory,
                                          error, latency_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s)
                    """,
                    (record.run_id, record.agent_name, record.section_id, record.status,
                     self.empresa_id, self.contrato_id,
                     json.dumps(record.output, ensure_ascii=False),
                     json.dumps(record.trajectory, ensure_ascii=False),
                     json.dumps(record.error, ensure_ascii=False) if record.error else None,
                     record.latency_ms),
                )
        except Exception:  # noqa: BLE001 — la persistencia de runs nunca rompe el flujo
            pass
