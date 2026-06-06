"""ETL de documentos: ingest version-aware (DB+MinIO) + reading (parse/chunk/embed)."""

from app.ingest.service import ingest_document, process_raw_document

__all__ = ["ingest_document", "process_raw_document"]
