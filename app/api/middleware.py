"""Middleware ASGI que fija el tenant (RLS) por request.

Por qué ASGI puro y no una dependency: una dependency *sync* de FastAPI corre en
un hilo del threadpool con una copia del contexto; el ContextVar que fije ahí NO
se propaga al endpoint (otra copia de contexto) → el endpoint correría como admin
y RLS no aislaría. Un middleware ASGI puro corre en el MISMO contexto async desde
el que Starlette luego copia el contexto hacia el threadpool del endpoint, así que
el ContextVar sí llega.

Decodifica el JWT (si viene) y fija:
  · COMPRADOR (Bayern) → tenant None (admin, ve todo)
  · PROVEEDOR          → tenant = empresa_id (RLS lo aísla)
  · sin/JWT inválido   → tenant None (los endpoints exigen auth aparte)
"""

from __future__ import annotations

from typing import Optional

from app.db import set_request_empresa
from app.security.tokens import decode_token


class TenantMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tenant: Optional[int] = None
        for k, v in scope.get("headers") or []:
            if k == b"authorization":
                try:
                    token = v.decode().split(" ", 1)[1]
                    payload = decode_token(token)
                    tenant = (None if payload.get("tipo_empresa") == "COMPRADOR"
                              else int(payload["empresa_id"]))
                except Exception:  # noqa: BLE001 — sin auth válida → admin/None
                    tenant = None
                break

        set_request_empresa(tenant)
        await self.app(scope, receive, send)
