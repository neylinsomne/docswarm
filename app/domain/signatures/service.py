"""Servicio de firma electrónica ("firma inteligente").

El proceso de firma ocurre por el medio de comunicación (WhatsApp/Gmail). Aquí
solo se persiste su estado y, al quedar FIRMADA, se actualiza el booleano de
firma del documento afectado (y del contrato). Lógica de BD pura, reutilizable
por el core API y por el microservicio `notifier`.
"""

from __future__ import annotations

import secrets
from typing import Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.domain.signatures import schemas


def iniciar_firma(data: schemas.IniciarFirma) -> dict:
    """Crea un proceso de firma INICIADA y devuelve su token (para el medio externo)."""
    token = secrets.token_urlsafe(24)
    with db_conn(empresa_id=None) as conn:   # M2M / admin
        conn.row_factory = dict_row
        # Resolver empresa_id y contrato_id a partir de afectado_id si aplica.
        empresa_id: Optional[int] = None
        contrato_id = data.contrato_id
        if data.afectado_id:
            ref = conn.execute(
                """
                SELECT empresa_proveedor_id, contrato_id
                FROM cambios_documentos_afectados WHERE id = %s
                """,
                (data.afectado_id,),
            ).fetchone()
            if not ref:
                raise ValueError("documento afectado no encontrado")
            empresa_id = ref["empresa_proveedor_id"]
            contrato_id = contrato_id or ref["contrato_id"]
        elif contrato_id:
            ref = conn.execute(
                "SELECT empresa_proveedor_id FROM contratos WHERE id = %s",
                (contrato_id,),
            ).fetchone()
            if not ref:
                raise ValueError("contrato no encontrado")
            empresa_id = ref["empresa_proveedor_id"]

        row = conn.execute(
            """
            INSERT INTO firmas (empresa_id, contrato_id, afectado_id, usuario_id,
                                notificacion_id, canal, estado, token,
                                expira_at)
            VALUES (%s,%s,%s,%s,%s,%s,'INICIADA',%s, now() + interval '7 days')
            RETURNING id, token
            """,
            (empresa_id, contrato_id, data.afectado_id, data.usuario_id,
             data.notificacion_id, data.canal, token),
        ).fetchone()
        return {"firma_id": row["id"], "token": row["token"], "estado": "INICIADA"}


def registrar_evento(firma_id: int, evento: schemas.EventoFirma) -> bool:
    """Callback de firma. Al FIRMADA marca firmado_proveedor=TRUE en afectado/contrato."""
    if evento.estado not in ("EN_PROCESO", "FIRMADA", "RECHAZADA", "EXPIRADA"):
        raise ValueError(f"estado inválido: {evento.estado}")
    import json
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        firma = conn.execute(
            """
            UPDATE firmas
               SET estado = %s,
                   evidencia = evidencia || %s::jsonb,
                   referencia_externa = COALESCE(%s, referencia_externa),
                   firmado_at = CASE WHEN %s = 'FIRMADA' THEN now() ELSE firmado_at END
             WHERE id = %s
            RETURNING afectado_id, contrato_id, usuario_id, estado
            """,
            (evento.estado, json.dumps(evento.evidencia), evento.referencia_externa,
             evento.estado, firma_id),
        ).fetchone()
        if not firma:
            return False

        if evento.estado == "FIRMADA":
            # documento afectado por un cambio → firmado
            if firma["afectado_id"]:
                conn.execute(
                    """
                    UPDATE cambios_documentos_afectados
                       SET firmado_proveedor = TRUE, fecha_firma = now(),
                           firmado_por = %s, estado_propagacion = 'APLICADO'
                     WHERE id = %s
                    """,
                    (firma["usuario_id"], firma["afectado_id"]),
                )
            # contrato → firmado
            if firma["contrato_id"]:
                conn.execute(
                    """
                    UPDATE contratos
                       SET firmado_proveedor = TRUE, fecha_firma = now()
                     WHERE id = %s
                    """,
                    (firma["contrato_id"],),
                )
        return True


def firmar_en_pagina(*, usuario_id: int, afectado_id: Optional[int] = None,
                     contrato_id: Optional[int] = None,
                     evidencia: Optional[dict] = None) -> dict:
    """Firma electrónica simple DESDE la página (un solo click).

    Corre en el contexto del tenant (RLS asegura que el proveedor solo firma lo
    suyo). Crea la firma (canal WEB, FIRMADA) con evidencia y deja
    `firmado_proveedor=TRUE` en el documento afectado y/o el contrato.
    """
    import json
    import secrets
    if not afectado_id and not contrato_id:
        raise ValueError("indica afectado_id o contrato_id")
    token = secrets.token_urlsafe(16)
    with db_conn() as conn:                      # contexto del tenant (RLS)
        conn.row_factory = dict_row
        empresa_id: Optional[int] = None
        if afectado_id:
            ref = conn.execute(
                "SELECT empresa_proveedor_id, contrato_id FROM cambios_documentos_afectados WHERE id=%s",
                (afectado_id,),
            ).fetchone()
            if not ref:
                raise ValueError("documento afectado no encontrado")
            empresa_id = ref["empresa_proveedor_id"]
            contrato_id = contrato_id or ref["contrato_id"]
        else:
            ref = conn.execute(
                "SELECT empresa_proveedor_id FROM contratos WHERE id=%s", (contrato_id,)
            ).fetchone()
            if not ref:
                raise ValueError("contrato no encontrado")
            empresa_id = ref["empresa_proveedor_id"]

        ev = {"canal": "WEB", "usuario_id": usuario_id, **(evidencia or {})}
        firma = conn.execute(
            """
            INSERT INTO firmas (empresa_id, contrato_id, afectado_id, usuario_id,
                                canal, estado, token, evidencia, firmado_at)
            VALUES (%s,%s,%s,%s,'WEB','FIRMADA',%s,%s::jsonb, now())
            RETURNING id
            """,
            (empresa_id, contrato_id, afectado_id, usuario_id, token, json.dumps(ev)),
        ).fetchone()
        if afectado_id:
            conn.execute(
                """
                UPDATE cambios_documentos_afectados
                   SET firmado_proveedor=TRUE, fecha_firma=now(), firmado_por=%s,
                       estado_propagacion='APLICADO'
                 WHERE id=%s
                """,
                (usuario_id, afectado_id),
            )
        if contrato_id:
            conn.execute(
                "UPDATE contratos SET firmado_proveedor=TRUE, fecha_firma=now() WHERE id=%s",
                (contrato_id,),
            )
        return {"firma_id": firma["id"], "estado": "FIRMADA",
                "afectado_id": afectado_id, "contrato_id": contrato_id}


def listar_por_tenant(limit: int = 50, offset: int = 0) -> list[dict]:
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            """
            SELECT id, empresa_id, contrato_id, afectado_id, usuario_id, canal,
                   estado, token, referencia_externa, firmado_at, created_at
            FROM firmas ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
