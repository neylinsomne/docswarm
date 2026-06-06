"""Empresas: alta con metadata rica, características facetadas y filtrado."""

from __future__ import annotations

import json
from typing import Any, Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.embeddings import embed_with_cache, to_pgvector
from app.domain.companies import schemas


def _perfil_text(nombre: str, sector: Optional[str], nicho: Optional[str],
                 metadata: dict[str, Any]) -> str:
    """Texto base para el embedding del perfil (búsqueda de empresas por similitud)."""
    partes = [nombre, sector or "", nicho or "", json.dumps(metadata, ensure_ascii=False)]
    return " · ".join(p for p in partes if p)


def crear_empresa(data: schemas.EmpresaCreate) -> int:
    perfil = _perfil_text(data.nombre, data.sector, data.nicho, data.metadata)
    vec = to_pgvector(embed_with_cache(perfil))
    with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO empresas (tipo, nombre, nit, sector, nicho, pais, ciudad,
                                  metadata, perfil_vec)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
            RETURNING id
            """,
            (data.tipo, data.nombre, data.nit, data.sector, data.nicho, data.pais,
             data.ciudad, json.dumps(data.metadata), vec),
        ).fetchone()
        empresa_id = row["id"]
        for c in data.caracteristicas:
            conn.execute(
                """
                INSERT INTO empresa_caracteristicas (empresa_id, clave, valor, valor_num)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (empresa_id, clave, valor) DO NOTHING
                """,
                (empresa_id, c.clave, c.valor, c.valor_num),
            )
    return empresa_id


def obtener_empresa(empresa_id: int) -> Optional[dict]:
    with db_conn() as conn:
        conn.row_factory = dict_row
        emp = conn.execute(
            """
            SELECT id, tipo, nombre, nit, sector, nicho, pais, ciudad, metadata, activo
            FROM empresas WHERE id = %s
            """,
            (empresa_id,),
        ).fetchone()
        if not emp:
            return None
        cars = conn.execute(
            "SELECT clave, valor, valor_num FROM empresa_caracteristicas WHERE empresa_id = %s",
            (empresa_id,),
        ).fetchall()
        emp["caracteristicas"] = cars
        return emp


def listar_empresas(filtro: schemas.EmpresaFiltro) -> list[dict]:
    """Filtrado facetado: nombre (trigram), sector/nicho y características exactas."""
    where: list[str] = ["TRUE"]
    params: list[Any] = []

    if filtro.nombre:
        where.append("nombre ILIKE %s")
        params.append(f"%{filtro.nombre}%")
    if filtro.sector:
        where.append("sector = %s")
        params.append(filtro.sector)
    if filtro.nicho:
        where.append("nicho = %s")
        params.append(filtro.nicho)
    # Una subconsulta EXISTS por cada característica pedida (AND entre facetas).
    for clave, valor in filtro.caracteristicas.items():
        where.append(
            "EXISTS (SELECT 1 FROM empresa_caracteristicas ec "
            "WHERE ec.empresa_id = empresas.id AND ec.clave = %s AND ec.valor = %s)"
        )
        params.extend([clave, valor])

    params.extend([filtro.limit, filtro.offset])
    sql = f"""
        SELECT id, tipo, nombre, nit, sector, nicho, pais, ciudad, metadata, activo
        FROM empresas
        WHERE {' AND '.join(where)}
        ORDER BY nombre
        LIMIT %s OFFSET %s
    """
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(sql, params).fetchall()


def actualizar_empresa(empresa_id: int, data: schemas.EmpresaUpdate) -> bool:
    sets: list[str] = []
    params: list[Any] = []
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "metadata":
            sets.append("metadata = %s")
            params.append(json.dumps(value))
        else:
            sets.append(f"{field} = %s")
            params.append(value)
    if not sets:
        return False
    params.append(empresa_id)
    with db_conn() as conn:
        cur = conn.execute(
            f"UPDATE empresas SET {', '.join(sets)} WHERE id = %s", params
        )
        return cur.rowcount > 0
