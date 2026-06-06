"""Catálogo maestro de Bayern: cláusulas y precios (buscar/listar/crear).

Tablas globales (sin RLS). La búsqueda por texto usa trigram sobre título/código.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.domain.catalog import schemas


def buscar_clausulas(texto: Optional[str] = None, tipo: Optional[str] = None,
                     sector: Optional[str] = None, solo_vigentes: bool = True,
                     limit: int = 50) -> list[dict]:
    where: list[str] = ["TRUE"]
    params: list[Any] = []
    if solo_vigentes:
        where.append("vigente = TRUE")
    if tipo:
        where.append("tipo = %s"); params.append(tipo)
    if sector:
        where.append("sector = %s"); params.append(sector)
    if texto:
        where.append("(titulo ILIKE %s OR codigo ILIKE %s OR contenido_actual ILIKE %s)")
        params += [f"%{texto}%", f"%{texto}%", f"%{texto}%"]
    params.append(limit)
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        return conn.execute(
            f"""
            SELECT id, codigo, tipo, titulo, contenido_actual, version, sector, nicho, vigente
            FROM clausulas_maestras WHERE {' AND '.join(where)}
            ORDER BY tipo, titulo LIMIT %s
            """,
            params,
        ).fetchall()


def buscar_precios(texto: Optional[str] = None, categoria: Optional[str] = None,
                   solo_vigentes: bool = True, limit: int = 50) -> list[dict]:
    where: list[str] = ["TRUE"]
    params: list[Any] = []
    if solo_vigentes:
        where.append("vigente = TRUE")
    if categoria:
        where.append("categoria = %s"); params.append(categoria)
    if texto:
        where.append("(producto ILIKE %s OR codigo ILIKE %s)")
        params += [f"%{texto}%", f"%{texto}%"]
    params.append(limit)
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        return conn.execute(
            f"""
            SELECT id, codigo, producto, categoria, precio, moneda, unidad, version, vigente
            FROM precios_maestros WHERE {' AND '.join(where)}
            ORDER BY producto LIMIT %s
            """,
            params,
        ).fetchall()


def crear_clausula(data: schemas.ClausulaMaestraCreate) -> int:
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO clausulas_maestras (codigo, tipo, titulo, contenido_actual,
                                            sector, nicho, metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (data.codigo, data.tipo, data.titulo, data.contenido_actual,
             data.sector, data.nicho, json.dumps(data.metadata)),
        ).fetchone()
        return row["id"]


def crear_precio(data: schemas.PrecioMaestroCreate) -> int:
    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO precios_maestros (codigo, producto, categoria, precio, moneda,
                                          unidad, sector, nicho, metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (data.codigo, data.producto, data.categoria, data.precio, data.moneda,
             data.unidad, data.sector, data.nicho, json.dumps(data.metadata)),
        ).fetchone()
        return row["id"]
