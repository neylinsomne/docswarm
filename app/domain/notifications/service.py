"""Servicio de notificaciones (WhatsApp/Gmail).

Lógica de BD pura (sin dependencias pesadas) para que la importen tanto el core
API como el microservicio `notifier`. El microservicio externo consume las
PENDIENTES (cola pull) y reporta el estado de entrega por callback; al entregarse
una notificación de tipo CAMBIO, el documento afectado pasa a NOTIFICADO.
"""

from __future__ import annotations

from typing import Optional

from psycopg.rows import dict_row

from app.db import db_conn

CANALES_DEFECTO = ("WHATSAPP", "GMAIL")


def crear_notificaciones_para_cambio(conn, cambio_id: int,
                                     canales: tuple[str, ...] = CANALES_DEFECTO) -> int:
    """Inserta una notificación PENDIENTE por (documento afectado × usuario × canal).

    Usa la conexión `conn` recibida (corre dentro de la transacción del cambio).
    Conecta con la tabla de usuarios y, según su rol, resuelve el destino:
    email para GMAIL; teléfono (metadata) para WHATSAPP.
    """
    total = 0
    tiene_sistema = False
    for canal in canales:
        # SISTEMA = aviso in-page → ya "entregado"; el resto queda PENDIENTE para
        # que el microservicio externo (WhatsApp/Gmail) lo envíe.
        estado_inicial = "ENTREGADO" if canal == "SISTEMA" else "PENDIENTE"
        if canal == "SISTEMA":
            tiene_sistema = True
        cur = conn.execute(
            """
            INSERT INTO notificaciones
                (canal, tipo, empresa_id, usuario_id, afectado_id, contrato_id,
                 cambio_id, destino, asunto, mensaje, estado, entregado_at, metadata)
            SELECT
                %s, 'CAMBIO', cda.empresa_proveedor_id, u.id, cda.id, cda.contrato_id,
                cda.cambio_id,
                CASE WHEN %s = 'GMAIL' THEN u.email
                     WHEN %s = 'WHATSAPP' THEN e.metadata->>'telefono'
                     ELSE NULL END,
                'Cambio en su contrato ' || COALESCE(c.numero, c.titulo),
                'Bayern actualizó una cláusula/precio que afecta su contrato '
                    || COALESCE(c.numero, c.titulo)
                    || '. Por favor revise y firme la actualización.',
                %s,
                CASE WHEN %s = 'SISTEMA' THEN now() ELSE NULL END,
                jsonb_build_object('rol_destinatario', u.rol)
            FROM cambios_documentos_afectados cda
            JOIN contratos c ON c.id = cda.contrato_id
            JOIN empresas  e ON e.id = cda.empresa_proveedor_id
            JOIN usuarios  u ON u.empresa_id = cda.empresa_proveedor_id AND u.activo
            WHERE cda.cambio_id = %s
            """,
            (canal, canal, canal, estado_inicial, canal, cambio_id),
        )
        total += cur.rowcount
    # El aviso in-page (SISTEMA) marca los afectados como NOTIFICADO de inmediato.
    if tiene_sistema:
        conn.execute(
            """
            UPDATE cambios_documentos_afectados
               SET estado_propagacion = CASE WHEN estado_propagacion = 'PENDIENTE'
                                             THEN 'NOTIFICADO' ELSE estado_propagacion END,
                   notificado_at = COALESCE(notificado_at, now())
             WHERE cambio_id = %s
            """,
            (cambio_id,),
        )
    return total


def listar_pendientes(canal: Optional[str] = None, limit: int = 100) -> list[dict]:
    """Cola pull para el microservicio externo: notificaciones por enviar."""
    where = ["estado = 'PENDIENTE'"]
    params: list = []
    if canal:
        where.append("canal = %s")
        params.append(canal)
    params.append(limit)
    with db_conn(empresa_id=None) as conn:   # admin: ve todos los tenants
        conn.row_factory = dict_row
        return conn.execute(
            f"""
            SELECT id, canal, tipo, empresa_id, usuario_id, afectado_id, contrato_id,
                   destino, asunto, mensaje, metadata
            FROM notificaciones
            WHERE {' AND '.join(where)}
            ORDER BY created_at ASC
            LIMIT %s
            """,
            params,
        ).fetchall()


def actualizar_estado(notif_id: int, estado: str, *,
                      referencia_externa: Optional[str] = None,
                      error: Optional[str] = None) -> bool:
    """Callback de entrega. Al ENTREGADO/LEIDO marca el doc afectado NOTIFICADO."""
    if estado not in ("ENVIADO", "ENTREGADO", "LEIDO", "FALLIDO"):
        raise ValueError(f"estado inválido: {estado}")
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            UPDATE notificaciones
               SET estado = %s,
                   referencia_externa = COALESCE(%s, referencia_externa),
                   error = %s,
                   intentos = intentos + 1,
                   enviado_at   = CASE WHEN %s IN ('ENVIADO','ENTREGADO','LEIDO')
                                       THEN COALESCE(enviado_at, now()) ELSE enviado_at END,
                   entregado_at = CASE WHEN %s IN ('ENTREGADO','LEIDO')
                                       THEN COALESCE(entregado_at, now()) ELSE entregado_at END,
                   leido_at     = CASE WHEN %s = 'LEIDO'
                                       THEN COALESCE(leido_at, now()) ELSE leido_at END
             WHERE id = %s
            RETURNING afectado_id, tipo, estado
            """,
            (estado, referencia_externa, error, estado, estado, estado, notif_id),
        ).fetchone()
        if not row:
            return False
        # Al entregarse una notificación de CAMBIO, el documento afectado queda NOTIFICADO.
        if row["afectado_id"] and estado in ("ENTREGADO", "LEIDO"):
            conn.execute(
                """
                UPDATE cambios_documentos_afectados
                   SET estado_propagacion = CASE WHEN estado_propagacion = 'PENDIENTE'
                                                 THEN 'NOTIFICADO' ELSE estado_propagacion END,
                       notificado_at = COALESCE(notificado_at, now())
                 WHERE id = %s
                """,
                (row["afectado_id"],),
            )
        return True


def listar_por_tenant(limit: int = 50, offset: int = 0, *,
                      solo_no_leidas: bool = False,
                      canal: Optional[str] = None) -> list[dict]:
    """Notificaciones visibles para el tenant en sesión (RLS aplica).

    `solo_no_leidas` y `canal` permiten al front mostrar el feed de avisos in-page
    (p.ej. canal=SISTEMA, no leídas).
    """
    where = ["TRUE"]
    params: list = []
    if solo_no_leidas:
        where.append("leido_at IS NULL")
    if canal:
        where.append("canal = %s")
        params.append(canal)
    params += [limit, offset]
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            f"""
            SELECT id, canal, tipo, empresa_id, usuario_id, afectado_id, contrato_id,
                   destino, asunto, mensaje, estado, referencia_externa,
                   enviado_at, entregado_at, leido_at, created_at
            FROM notificaciones
            WHERE {' AND '.join(where)}
            ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            params,
        ).fetchall()


def contar_no_leidas(canal: Optional[str] = "SISTEMA") -> int:
    """Badge de la campanita: avisos in-page no leídos del tenant.

    Por defecto cuenta solo el canal SISTEMA (lo que se ve DENTRO de la página);
    pasa `canal=None` para contar todos los canales.
    """
    where = ["leido_at IS NULL"]
    params: list = []
    if canal:
        where.append("canal = %s")
        params.append(canal)
    with db_conn() as conn:
        row = conn.execute(
            f"SELECT count(*) FROM notificaciones WHERE {' AND '.join(where)}", params
        ).fetchone()
        return int(row[0])


def marcar_leida(notif_id: int) -> bool:
    """Marca un aviso como leído DENTRO de la página (RLS: solo los del tenant).

    Si el aviso corresponde a un documento afectado, lo deja NOTIFICADO.
    """
    with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            UPDATE notificaciones
               SET estado = CASE WHEN estado IN ('PENDIENTE','ENVIADO','ENTREGADO')
                                 THEN 'LEIDO' ELSE estado END,
                   leido_at = COALESCE(leido_at, now())
             WHERE id = %s
            RETURNING afectado_id
            """,
            (notif_id,),
        ).fetchone()
        if not row:
            return False
        if row["afectado_id"]:
            conn.execute(
                """
                UPDATE cambios_documentos_afectados
                   SET estado_propagacion = CASE WHEN estado_propagacion = 'PENDIENTE'
                                                 THEN 'NOTIFICADO' ELSE estado_propagacion END,
                       notificado_at = COALESCE(notificado_at, now())
                 WHERE id = %s
                """,
                (row["afectado_id"],),
            )
        return True
