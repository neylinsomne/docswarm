"""App FastAPI · backend de gestión documental B2B (Bayern + proveedores).

Arranque:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import TenantMiddleware
from app.api.v1 import api_router
from app.db import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Abre el pool (y valida que el rol respeta RLS) al arrancar.
    get_pool()
    yield
    close_pool()


app = FastAPI(
    title="docswarm B2B · gestión documental de contratos",
    description=(
        "Backend multi-tenant: Bayern (comprador/granbase) gestiona contratos con "
        "sus proveedores. Búsqueda vectorial por contenido + filtrado por metadata; "
        "log de cambios de cláusulas/precios con documentos afectados y firma."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Fija el tenant para RLS antes de cada endpoint (ver app/api/middleware.py).
app.add_middleware(TenantMiddleware)

app.include_router(api_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    from app.db import db_conn
    with db_conn(empresa_id=None) as conn:
        row = conn.execute("SELECT 1 AS ok").fetchone()
    return {"status": "ok", "db": row[0]}
