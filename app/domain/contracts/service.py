"""Contratos y sus cláusulas (RLS por proveedor)."""

from __future__ import annotations

import json
from typing import Any, Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.embeddings import embed_with_cache, to_pgvector
from app.domain.contracts import schemas


def crear_contrato(data: schemas.ContratoCreate) -> int:
    texto = " · ".join(filter(None, [data.titulo, data.objeto or "", data.sector or ""]))
    vec = to_pgvector(embed_with_cache(texto))
    with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO contratos (empresa_proveedor_id, empresa_compradora_id, numero,
                                   titulo, objeto, sector, valor, moneda, fecha_inicio,
                                   fecha_fin, metadata, contenido_vec)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
            RETURNING id
            """,
            (data.empresa_proveedor_id, data.empresa_compradora_id, data.numero,
             data.titulo, data.objeto, data.sector, data.valor, data.moneda,
             data.fecha_inicio, data.fecha_fin, json.dumps(data.metadata), vec),
        ).fetchone()
        contrato_id = row["id"]
        for cl in data.clausulas:
            conn.execute(
                """
                INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido,
                                                orden, clausula_maestra_id,
                                                precio_maestro_id, valor)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (contrato_id, cl.tipo, cl.titulo, cl.contenido, cl.orden,
                 cl.clausula_maestra_id, cl.precio_maestro_id, cl.valor),
            )
        # Materializar cláusulas/precios elegidos del catálogo maestro.
        _materializar_maestras(conn, contrato_id, data.clausulas_maestras_ids,
                               data.precios_maestros_ids)
    return contrato_id


def _materializar_maestras(conn, contrato_id: int, clausulas_ids: list[int],
                           precios_ids: list[int]) -> None:
    """Copia el contenido vigente de ítems maestros como cláusulas del contrato."""
    base = conn.execute(
        "SELECT COALESCE(MAX(orden), 0) AS m FROM contrato_clausulas WHERE contrato_id = %s",
        (contrato_id,),
    ).fetchone()
    orden = (base["m"] if isinstance(base, dict) else base[0]) or 0
    for cid in clausulas_ids:
        orden += 1
        conn.execute(
            """
            INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido,
                                            orden, clausula_maestra_id)
            SELECT %s, tipo, titulo, contenido_actual, %s, id
            FROM clausulas_maestras WHERE id = %s
            """,
            (contrato_id, orden, cid),
        )
    for pid in precios_ids:
        orden += 1
        conn.execute(
            """
            INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido,
                                            orden, precio_maestro_id, valor)
            SELECT %s, 'PRECIO', 'Precio ' || producto,
                   'Precio pactado: ' || precio || ' ' || moneda || '/' || COALESCE(unidad,'und'),
                   %s, id, precio
            FROM precios_maestros WHERE id = %s
            """,
            (contrato_id, orden, pid),
        )


def listar_contratos(estado: Optional[str] = None, limit: int = 50,
                     offset: int = 0) -> list[dict]:
    where: list[str] = ["TRUE"]
    params: list[Any] = []
    if estado:
        where.append("estado = %s")
        params.append(estado)
    params.extend([limit, offset])
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            f"""
            SELECT id, empresa_proveedor_id, empresa_compradora_id, numero, titulo,
                   estado, valor, moneda, firmado_proveedor, sector
            FROM contratos WHERE {' AND '.join(where)}
            ORDER BY created_at DESC LIMIT %s OFFSET %s
            """,
            params,
        ).fetchall()


def obtener_contrato(contrato_id: int) -> Optional[dict]:
    with db_conn() as conn:
        conn.row_factory = dict_row
        c = conn.execute(
            """
            SELECT c.id, c.empresa_proveedor_id, c.empresa_compradora_id, c.numero,
                   c.titulo, c.objeto, c.estado, c.valor, c.moneda, c.firmado_proveedor,
                   c.fecha_firma, c.sector, c.fecha_inicio, c.fecha_fin, c.metadata,
                   prov.nombre AS proveedor_nombre, comp.nombre AS comprador_nombre
            FROM contratos c
            LEFT JOIN empresas prov ON prov.id = c.empresa_proveedor_id
            LEFT JOIN empresas comp ON comp.id = c.empresa_compradora_id
            WHERE c.id = %s
            """,
            (contrato_id,),
        ).fetchone()
        if not c:
            return None
        c["clausulas"] = conn.execute(
            """
            SELECT id, tipo, titulo, contenido, orden, version, clausula_maestra_id,
                   precio_maestro_id, valor
            FROM contrato_clausulas WHERE contrato_id = %s ORDER BY orden
            """,
            (contrato_id,),
        ).fetchall()
        return c


def actualizar_contrato(contrato_id: int, data: schemas.ContratoUpdate) -> bool:
    sets: list[str] = []
    params: list[Any] = []
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "metadata":
            sets.append("metadata = %s"); params.append(json.dumps(value))
        else:
            sets.append(f"{field} = %s"); params.append(value)
    if not sets:
        return False
    params.append(contrato_id)
    with db_conn() as conn:
        cur = conn.execute(
            f"UPDATE contratos SET {', '.join(sets)} WHERE id = %s", params)
        return cur.rowcount > 0


def agregar_clausula(contrato_id: int, cl: schemas.ClausulaCreate) -> Optional[int]:
    """Agrega una cláusula a un contrato (manual o referenciando un ítem maestro)."""
    with db_conn() as conn:
        conn.row_factory = dict_row
        # Verifica visibilidad/propiedad del contrato bajo RLS.
        existe = conn.execute("SELECT 1 FROM contratos WHERE id = %s", (contrato_id,)).fetchone()
        if not existe:
            return None
        row = conn.execute(
            """
            INSERT INTO contrato_clausulas (contrato_id, tipo, titulo, contenido, orden,
                                            clausula_maestra_id, precio_maestro_id, valor)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (contrato_id, cl.tipo, cl.titulo, cl.contenido, cl.orden,
             cl.clausula_maestra_id, cl.precio_maestro_id, cl.valor),
        ).fetchone()
        return row["id"]


def actualizar_clausula(clausula_id: int, data: schemas.ClausulaUpdate) -> bool:
    sets: list[str] = []
    params: list[Any] = []
    for field, value in data.model_dump(exclude_none=True).items():
        sets.append(f"{field} = %s"); params.append(value)
    if not sets:
        return False
    sets.append("version = version + 1")
    params.append(clausula_id)
    with db_conn() as conn:
        cur = conn.execute(
            f"UPDATE contrato_clausulas SET {', '.join(sets)} WHERE id = %s", params)
        return cur.rowcount > 0


def eliminar_clausula(clausula_id: int) -> bool:
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM contrato_clausulas WHERE id = %s", (clausula_id,))
        return cur.rowcount > 0


def firmar_contrato(contrato_id: int, firmado: bool, usuario_id: int) -> bool:
    """El proveedor firma (o revierte) su contrato vigente."""
    with db_conn() as conn:
        cur = conn.execute(
            """
            UPDATE contratos
               SET firmado_proveedor = %s,
                   fecha_firma = CASE WHEN %s THEN now() ELSE NULL END
             WHERE id = %s
            """,
            (firmado, firmado, contrato_id),
        )
        return cur.rowcount > 0
