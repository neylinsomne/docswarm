"""ETL de documentos de contrato.

Dos fases que comparten las tablas canónicas (V5):

  A. Ingest version-aware  → persist_versioned_raw_document
     sha256 dedup · cadena de versión (flip is_current, vN+1, supersedes) ·
     document_links (reemplaza_a / version_de). Bytes a MinIO; DB guarda la key.

  B. Reading (idempotente) → process_raw_document
     extract (docswarm) → chunk (docswarm) → embed → INSERT document_chunks +
     parsed_documents. Reprocesar borra antes chunks/parsed previos del raw_id.

Reusa el engine docswarm para extraer y chunkear (agnóstico de dominio).
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from typing import Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.embeddings import embed_with_cache, to_pgvector
from app.storage import get_storage
from docswarm.ingest.chunking import chunk_text
from docswarm.ingest.extractors import extract
from docswarm.ingest.versioning import content_hash


def normalize_filename(filename: str) -> str:
    """logical_key: identidad lógica estable entre re-cargas (sin acentos/ext/v2)."""
    base = os.path.splitext(filename or "")[0].lower()
    base = "".join(
        c for c in unicodedata.normalize("NFD", base)
        if unicodedata.category(c) != "Mn"
    )
    base = re.sub(r"[\s_]+v?\d+$", "", base)        # quita sufijos tipo "_v2"
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or "documento"


def _log_job(conn, raw_id: Optional[int], step: str, status: str,
             latency_ms: int = 0, error: Optional[str] = None) -> None:
    conn.execute(
        """
        INSERT INTO ingest_jobs (raw_document_id, step, status, latency_ms, error_message)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (raw_id, step, status, latency_ms, error),
    )


def ingest_document(*, content: bytes, filename: str, source: str = "upload",
                    tenant_id: Optional[int] = None, contrato_id: Optional[int] = None,
                    domain: str = "contratos", titulo: Optional[str] = None) -> dict:
    """Fase A: persiste el documento de forma version-aware. Devuelve metadata."""
    sha = content_hash(content)
    logical = normalize_filename(filename)
    ext = os.path.splitext(filename or "")[1].lstrip(".").lower()
    storage = get_storage()

    with db_conn() as conn:
        conn.row_factory = dict_row

        # 1) dedup exacto por contenido
        dup = conn.execute(
            "SELECT id, version FROM raw_documents WHERE sha256 = %s", (sha,)
        ).fetchone()
        if dup:
            return {"raw_document_id": dup["id"], "version": dup["version"],
                    "unchanged": True, "is_new_logical": False}

        # subir bytes a MinIO (key estable por sha para evitar colisiones)
        key = f"{tenant_id or 'global'}/{logical}/{sha}.{ext or 'bin'}"
        storage.put_object(key, content)

        # 2) versión vigente del mismo logical_key (mismo tenant)
        prev = conn.execute(
            """
            SELECT id, version FROM raw_documents
            WHERE logical_key = %s AND is_current
              AND tenant_id IS NOT DISTINCT FROM %s
            """,
            (logical, tenant_id),
        ).fetchone()

        version = (prev["version"] + 1) if prev else 1
        supersedes = prev["id"] if prev else None
        is_new_logical = prev is None

        # 3) flip de la versión anterior
        if prev:
            conn.execute(
                "UPDATE raw_documents SET is_current = FALSE WHERE id = %s", (prev["id"],)
            )

        # 4) insertar la nueva versión
        new = conn.execute(
            """
            INSERT INTO raw_documents
                (source, source_id, domain, titulo, minio_bucket, minio_key, extension,
                 bytes_len, tenant_id, contrato_id, sha256, logical_key, version,
                 supersedes_id, is_current, parse_status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,'PENDING')
            RETURNING id
            """,
            (source, sha[:32], domain, titulo or filename, storage.bucket, key, ext,
             len(content), tenant_id, contrato_id, sha, logical, version, supersedes),
        ).fetchone()
        raw_id = new["id"]

        # 5) cadena de auditoría
        if supersedes:
            for link in ("reemplaza_a", "version_de"):
                conn.execute(
                    """
                    INSERT INTO document_links (src_doc_id, dst_doc_id, link_type)
                    VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
                    """,
                    (raw_id, supersedes, link),
                )
        _log_job(conn, raw_id, "fetch", "ok")

    return {"raw_document_id": raw_id, "version": version,
            "unchanged": False, "is_new_logical": is_new_logical}


def process_raw_document(raw_id: int) -> dict:
    """Fase B (idempotente): parse → chunk → embed → index sobre un raw_document."""
    storage = get_storage()
    with db_conn() as conn:
        conn.row_factory = dict_row
        doc = conn.execute(
            """
            SELECT id, minio_key, extension, domain, tenant_id, titulo
            FROM raw_documents WHERE id = %s
            """,
            (raw_id,),
        ).fetchone()
        if not doc:
            raise ValueError(f"raw_document {raw_id} no existe")

        # idempotencia: borrar chunks/parsed previos
        conn.execute("DELETE FROM document_chunks WHERE raw_document_id = %s", (raw_id,))
        conn.execute("DELETE FROM parsed_documents WHERE raw_document_id = %s", (raw_id,))
        conn.execute(
            "UPDATE raw_documents SET parse_status = 'PARSING' WHERE id = %s", (raw_id,)
        )

        # parse
        t0 = time.time()
        content = storage.get_object(doc["minio_key"])
        result = extract(content, filename=f"x.{doc['extension']}")
        _log_job(conn, raw_id, "parse", "ok" if result.ok else "error",
                 int((time.time() - t0) * 1000), None if result.ok else result.error)

        if not result.ok:
            conn.execute(
                "UPDATE raw_documents SET parse_status = 'ERROR' WHERE id = %s", (raw_id,)
            )
            return {"raw_document_id": raw_id, "status": "ERROR", "chunks": 0}

        conn.execute(
            """
            INSERT INTO parsed_documents (raw_document_id, parser_name, parser_version,
                                          contenido_secciones, parser_confidence)
            VALUES (%s, %s, %s, %s::jsonb, %s)
            """,
            (raw_id, result.method, "1", _secciones_json(result), 1.0),
        )

        # chunk + embed + index
        chunks = chunk_text(result.text)
        for i, c in enumerate(chunks):
            vec = to_pgvector(embed_with_cache(c))
            conn.execute(
                """
                INSERT INTO document_chunks (raw_document_id, tenant_id, domain,
                                             chunk_index, contenido, embedding_vec)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
                """,
                (raw_id, doc["tenant_id"], doc["domain"], i, c, vec),
            )
        _log_job(conn, raw_id, "embed", "ok")
        _log_job(conn, raw_id, "index", "ok")
        conn.execute(
            "UPDATE raw_documents SET parse_status = 'INDEXED' WHERE id = %s", (raw_id,)
        )

    return {"raw_document_id": raw_id, "status": "INDEXED", "chunks": len(chunks)}


def _secciones_json(result) -> str:
    import json
    return json.dumps({
        "texto": result.text[:200000],
        "chars": result.chars,
        "method": result.method,
        "pages": result.pages,
        "ocr_pages": result.ocr_pages,
        "tablas": result.tables_markdown[:50],
    }, ensure_ascii=False)
