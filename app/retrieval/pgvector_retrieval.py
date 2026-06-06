"""Implementación de ``docswarm.ports.RetrievalPort`` con pgvector.

El engine docswarm recibe chunks y los puede citar como ``[FRAG #id]``; *cómo* se
obtienen (esta consulta) es la implementación detrás del puerto. RLS aísla por
tenant automáticamente (la conexión ya trae el GUC de la request).
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.db import db_conn
from app.embeddings import embed_with_cache, to_pgvector


class PgVectorRetrieval:
    """RetrievalPort: búsqueda coseno sobre document_chunks."""

    def retrieve(self, query: str, *, domain: str = "", top_k: int = 8,
                 **filters: Any) -> list[dict]:
        q = to_pgvector(embed_with_cache(query))
        where = ["dc.embedding_vec IS NOT NULL"]
        params: list[Any] = [q]
        if domain:
            where.append("dc.domain = %s")
            params.append(domain)
        params += [q, top_k]
        sql = f"""
            SELECT dc.id, dc.contenido, dc.raw_document_id,
                   1 - (dc.embedding_vec <=> %s::vector) AS score
            FROM document_chunks dc
            WHERE {' AND '.join(where)}
            ORDER BY dc.embedding_vec <=> %s::vector
            LIMIT %s
        """
        with db_conn() as conn:
            conn.row_factory = dict_row
            rows = conn.execute(sql, params).fetchall()
        # El puerto pide al menos `id` y uno de contenido/texto/content.
        return rows
