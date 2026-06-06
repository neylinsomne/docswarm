"""Worker de la cola durable `scrape_jobs` (Postgres-as-queue).

Patrón: claim atómico con ``FOR UPDATE SKIP LOCKED`` (N workers no colisionan),
ejecuta el handler inyectado por ``job_type``, hace ``complete``/``fail`` con
backoff exponencial. Liveness en ``service_heartbeats``. Corre como:

    python -m app.orchestration.worker
"""

from __future__ import annotations

import os
import socket
import time
from typing import Callable, Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.ingest import process_raw_document

POLL_INTERVAL_S = float(os.environ.get("WORKER_POLL_INTERVAL_S", "5"))
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

Handler = Callable[[dict], dict]


# --- Handlers por tipo de job ------------------------------------------------
def _handle_ingest_doc(payload: dict) -> dict:
    return process_raw_document(int(payload["raw_document_id"]))


HANDLERS: dict[str, Handler] = {
    "ingest_doc": _handle_ingest_doc,
}


# --- Cola --------------------------------------------------------------------
def claim_job() -> Optional[dict]:
    """Reclama un job de forma atómica (un solo row, sin colisiones)."""
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        job = conn.execute(
            """
            SELECT id, job_type, payload, attempts
            FROM scrape_jobs
            WHERE status IN ('queued','deferred') AND run_after <= now()
            ORDER BY priority ASC, run_after ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        ).fetchone()
        if not job:
            return None
        conn.execute(
            """
            UPDATE scrape_jobs
               SET status='running', locked_by=%s, heartbeat_at=now(),
                   attempts=attempts+1
             WHERE id=%s
            """,
            (WORKER_ID, job["id"]),
        )
        return job


def complete_job(job_id: int) -> None:
    with db_conn(empresa_id=None) as conn:
        conn.execute("UPDATE scrape_jobs SET status='done' WHERE id=%s", (job_id,))


def fail_job(job_id: int, attempts: int, error: str) -> None:
    """Backoff exponencial 60·2^(n-1) capado a 1h → deferred; si no, dead."""
    backoff = min(60 * (2 ** max(0, attempts - 1)), 3600)
    with db_conn(empresa_id=None) as conn:
        conn.execute(
            """
            UPDATE scrape_jobs
               SET status = CASE WHEN attempts >= 5 THEN 'dead' ELSE 'deferred' END,
                   run_after = now() + (%s || ' seconds')::interval,
                   last_error = %s
             WHERE id = %s
            """,
            (backoff, error[:1000], job_id),
        )


def heartbeat(status: str = "alive", detail: Optional[dict] = None) -> None:
    import json
    with db_conn(empresa_id=None) as conn:
        conn.execute(
            """
            INSERT INTO service_heartbeats (service, instance_id, status, detail, beat_at)
            VALUES ('worker', %s, %s, %s::jsonb, now())
            ON CONFLICT (service) DO UPDATE
               SET instance_id=EXCLUDED.instance_id, status=EXCLUDED.status,
                   detail=EXCLUDED.detail, beat_at=now()
            """,
            (WORKER_ID, status, json.dumps(detail or {})),
        )


def run_worker() -> None:
    print(f"[worker] iniciado {WORKER_ID}; handlers={list(HANDLERS)}", flush=True)
    while True:
        heartbeat()
        job = claim_job()
        if job is None:
            time.sleep(POLL_INTERVAL_S)
            continue
        handler = HANDLERS.get(job["job_type"])
        if handler is None:
            fail_job(job["id"], job["attempts"], f"sin handler para {job['job_type']}")
            continue
        try:
            handler(job["payload"] or {})
            complete_job(job["id"])
            print(f"[worker] job {job['id']} ({job['job_type']}) OK", flush=True)
        except Exception as exc:  # noqa: BLE001
            fail_job(job["id"], job["attempts"], str(exc))
            print(f"[worker] job {job['id']} FAIL: {exc}", flush=True)


def enqueue(job_type: str, payload: dict, *, dedup_key: Optional[str] = None,
            priority: int = 100) -> int:
    """Encola un job idempotentemente (ON CONFLICT por dedup_key)."""
    import json
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO scrape_jobs (job_type, payload, dedup_key, priority)
            VALUES (%s, %s::jsonb, %s, %s)
            ON CONFLICT (dedup_key) DO UPDATE
               SET status='queued', run_after=now()
            RETURNING id
            """,
            (job_type, json.dumps(payload), dedup_key, priority),
        ).fetchone()
        return row["id"]


if __name__ == "__main__":
    run_worker()
