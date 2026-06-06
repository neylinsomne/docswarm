"""Cliente de object storage (MinIO/S3) para los bytes crudos de documentos."""

from app.storage.minio_client import get_storage, StorageClient

__all__ = ["get_storage", "StorageClient"]
