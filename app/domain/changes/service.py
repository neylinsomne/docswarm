"""Feature central · log de cambios maestros y propagación a documentos afectados.

Flujo (ver db/diagram/schema.mermaid.md):
  1. Bayern cambia una cláusula/precio maestro  → se versiona el ítem.
  2. Se registra el cambio en `cambios_maestros` (antes/después).
  3. Se detectan los contratos con una cláusula DERIVADA de ese ítem y se inserta
     una fila por contrato en `cambios_documentos_afectados` con
     `firmado_proveedor = FALSE` (estado NOTIFICADO).
  4. El proveedor firma → `firmar_documento_afectado` pone el booleano en TRUE.
"""

from __future__ import annotations

import json
from typing import Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.domain.changes import schemas
from app.domain.notifications import service as notif_service
from app.settings import settings


def _propagar_afectados(conn, cambio_id: int, columna: str, objeto_id: int) -> int:
    """Inserta un afectado por cada contrato cuya cláusula deriva del ítem maestro.

    `columna` ∈ {'clausula_maestra_id','precio_maestro_id'}. Devuelve el conteo.
    """
    cur = conn.execute(
        f"""
        INSERT INTO cambios_documentos_afectados
            (cambio_id, contrato_id, empresa_proveedor_id, clausula_contrato_id,
             raw_document_id, estado_propagacion, firmado_proveedor, notificado_at)
        SELECT %s, c.id, c.empresa_proveedor_id, cc.id,
               (SELECT r.id FROM raw_documents r
                 WHERE r.contrato_id = c.id AND r.is_current
                 ORDER BY r.version DESC LIMIT 1),
               'NOTIFICADO', FALSE, now()
        FROM contrato_clausulas cc
        JOIN contratos c ON c.id = cc.contrato_id
        WHERE cc.{columna} = %s
        ON CONFLICT (cambio_id, contrato_id) DO NOTHING
        """,
        (cambio_id, objeto_id),
    )
    return cur.rowcount


def _notificar(conn, cambio_id: int, afectados: int) -> int:
    """Crea notificaciones PENDIENTES (WhatsApp/Gmail) si hay afectados y está activo."""
    if not (settings.notif_auto and afectados):
        return 0
    return notif_service.crear_notificaciones_para_cambio(
        conn, cambio_id, settings.notif_canales_list)


def registrar_cambio_clausula(req: schemas.CambioClausulaRequest,
                              usuario_id: int) -> dict:
    """Admin (Bayern): cambia una cláusula maestra y propaga a contratos."""
    with db_conn(empresa_id=None) as conn:   # admin: ve todos los contratos
        conn.row_factory = dict_row
        prev = conn.execute(
            "SELECT contenido_actual, version FROM clausulas_maestras WHERE id = %s",
            (req.clausula_maestra_id,),
        ).fetchone()
        if not prev:
            raise ValueError("cláusula maestra no encontrada")

        nueva_version = prev["version"] + 1
        conn.execute(
            "UPDATE clausulas_maestras SET contenido_actual = %s, version = %s WHERE id = %s",
            (req.nuevo_contenido, nueva_version, req.clausula_maestra_id),
        )
        cambio = conn.execute(
            """
            INSERT INTO cambios_maestros (tipo_objeto, clausula_maestra_id, accion,
                                          descripcion, version_anterior, version_nueva,
                                          valor_anterior, valor_nuevo, realizado_por)
            VALUES ('CLAUSULA', %s, 'ACTUALIZACION', %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (req.clausula_maestra_id, req.descripcion, prev["version"], nueva_version,
             json.dumps({"contenido": prev["contenido_actual"]}),
             json.dumps({"contenido": req.nuevo_contenido}), usuario_id),
        ).fetchone()
        afectados = _propagar_afectados(
            conn, cambio["id"], "clausula_maestra_id", req.clausula_maestra_id)
        notifs = _notificar(conn, cambio["id"], afectados)
    return {"cambio_id": cambio["id"], "docs_afectados": afectados,
            "notificaciones": notifs}


def registrar_cambio_precio(req: schemas.CambioPrecioRequest, usuario_id: int) -> dict:
    """Admin (Bayern): cambia un precio maestro y propaga a contratos."""
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        prev = conn.execute(
            "SELECT precio, version FROM precios_maestros WHERE id = %s",
            (req.precio_maestro_id,),
        ).fetchone()
        if not prev:
            raise ValueError("precio maestro no encontrado")

        nueva_version = prev["version"] + 1
        conn.execute(
            "UPDATE precios_maestros SET precio = %s, version = %s WHERE id = %s",
            (req.nuevo_precio, nueva_version, req.precio_maestro_id),
        )
        cambio = conn.execute(
            """
            INSERT INTO cambios_maestros (tipo_objeto, precio_maestro_id, accion,
                                          descripcion, version_anterior, version_nueva,
                                          valor_anterior, valor_nuevo, realizado_por)
            VALUES ('PRECIO', %s, 'ACTUALIZACION', %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (req.precio_maestro_id, req.descripcion, prev["version"], nueva_version,
             json.dumps({"precio": float(prev["precio"])}),
             json.dumps({"precio": req.nuevo_precio}), usuario_id),
        ).fetchone()
        afectados = _propagar_afectados(
            conn, cambio["id"], "precio_maestro_id", req.precio_maestro_id)
        notifs = _notificar(conn, cambio["id"], afectados)
    return {"cambio_id": cambio["id"], "docs_afectados": afectados,
            "notificaciones": notifs}


def listar_cambios(limit: int = 50, offset: int = 0) -> list[dict]:
    """Tablero: resumen de cambios con conteo de afectados/firmados/pendientes."""
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            """
            SELECT cambio_id, tipo_objeto, accion, descripcion, objeto_codigo,
                   objeto_titulo, version_anterior, version_nueva, created_at,
                   docs_afectados, docs_firmados, docs_pendientes
            FROM vw_cambios_resumen
            ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()


def detalle_cambio(cambio_id: int) -> list[dict]:
    """Drill-down: documentos/contratos afectados por un cambio + estado de firma."""
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            """
            SELECT afectado_id, contrato_id, contrato_numero, contrato_titulo,
                   empresa_proveedor_id, empresa_proveedor, estado_propagacion,
                   firmado_proveedor, fecha_firma, notificado_at, raw_document_id
            FROM vw_cambios_afectados_detalle
            WHERE cambio_id = %s
            ORDER BY empresa_proveedor
            """,
            (cambio_id,),
        ).fetchall()


def firmar_documento_afectado(afectado_id: int, usuario_id: int,
                              observaciones: Optional[str] = None) -> bool:
    """El proveedor firma la actualización derivada de un cambio (booleano → TRUE).

    RLS garantiza que solo puede firmar afectados de SUS contratos.
    """
    with db_conn() as conn:
        cur = conn.execute(
            """
            UPDATE cambios_documentos_afectados
               SET firmado_proveedor = TRUE, fecha_firma = now(),
                   firmado_por = %s, estado_propagacion = 'APLICADO',
                   observaciones = COALESCE(%s, observaciones)
             WHERE id = %s AND firmado_proveedor = FALSE
            """,
            (usuario_id, observaciones, afectado_id),
        )
        return cur.rowcount > 0
