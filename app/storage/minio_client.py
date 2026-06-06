"""Cliente MinIO/S3: guarda y recupera los bytes crudos de los documentos.

La BD solo guarda ``minio_bucket``/``minio_key``; los bytes viven aquí.
"""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Optional

from app.settings import settings


class StorageClient:
    def __init__(self) -> None:
        from minio import Minio  # lazy import

        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self.bucket):
            self._client.make_bucket(self.bucket)

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Sube bytes a ``key`` y devuelve la key. Idempotente por key."""
        self._client.put_object(
            self.bucket, key, io.BytesIO(data), length=len(data),
            content_type=content_type,
        )
        return key

    def get_object(self, key: str) -> bytes:
        resp = self._client.get_object(self.bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def remove_object(self, key: str) -> None:
        self._client.remove_object(self.bucket, key)


@lru_cache(maxsize=1)
def get_storage() -> StorageClient:
    return StorageClient()
