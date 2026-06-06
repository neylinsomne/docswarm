"""Búsqueda: por contenido del contrato (pgvector) y por nombre (trigram).

Patrón canónico pgvector: el vector de consulta se usa DOS veces — como score
``1 - (embedding_vec <=> q)`` y en ``ORDER BY embedding_vec <=> q`` para que el
índice ivfflat dirija el orden. RLS aísla automáticamente por tenant.
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.db import db_conn
from app.embeddings import embed_with_cache, to_pgvector


def buscar_por_contenido(query: str, top_k: int = 10) -> list[dict]:
    """Búsqueda semántica sobre los chunks del contenido de los contratos."""
    q = to_pgvector(embed_with_cache(query))
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            """
            SELECT dc.id AS chunk_id, dc.raw_document_id, dc.contenido,
                   r.contrato_id, r.titulo AS documento_titulo,
                   1 - (dc.embedding_vec <=> %s::vector) AS similarity
            FROM document_chunks dc
            JOIN raw_documents r ON r.id = dc.raw_document_id
            WHERE dc.embedding_vec IS NOT NULL
            ORDER BY dc.embedding_vec <=> %s::vector
            LIMIT %s
            """,
            (q, q, top_k),
        ).fetchall()


def buscar_contratos_por_nombre(texto: str, limit: int = 20) -> list[dict]:
    """Búsqueda de contratos por nombre/título (trigram)."""
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            """
            SELECT id, numero, titulo, estado, empresa_proveedor_id,
                   similarity(titulo, %s) AS score
            FROM contratos
            WHERE titulo %% %s OR titulo ILIKE %s
            ORDER BY score DESC NULLS LAST
            LIMIT %s
            """,
            (texto, texto, f"%{texto}%", limit),
        ).fetchall()


def buscar_empresas_por_similitud(query: str, top_k: int = 10) -> list[dict]:
    """Búsqueda de empresas por similitud de perfil (vector)."""
    q = to_pgvector(embed_with_cache(query))
    with db_conn() as conn:
        conn.row_factory = dict_row
        return conn.execute(
            """
            SELECT id, nombre, sector, nicho,
                   1 - (perfil_vec <=> %s::vector) AS similarity
            FROM empresas
            WHERE perfil_vec IS NOT NULL
            ORDER BY perfil_vec <=> %s::vector
            LIMIT %s
            """,
            (q, q, top_k),
        ).fetchall()
