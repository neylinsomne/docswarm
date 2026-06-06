"""Embeddings BGE-M3 (1024-dim) con caché por sha256.

Dos backends, seleccionados por ``EMBEDDINGS_REAL``:
  · real  → FlagEmbedding / sentence-transformers (pesado; modelo BAAI/bge-m3).
  · stub  → vector determinista por hash (sin dependencias; dev/CI/tests).

Ambos devuelven listas de ``EMBEDDINGS_DIM`` floats. ``to_pgvector`` las formatea
como literal pgvector ``'[v1,v2,...]'`` para castear con ``::vector`` en SQL.
"""

from __future__ import annotations

import hashlib
import math
import struct
from functools import lru_cache
from typing import List, Protocol

from app.settings import settings


class Embedder(Protocol):
    def encode(self, text: str) -> List[float]: ...


class _StubEmbedder:
    """Embedder determinista: misma entrada → mismo vector. Útil sin GPU/modelo."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def encode(self, text: str) -> List[float]:
        # Expande sha256 con contadores hasta cubrir `dim` floats, luego normaliza.
        out: List[float] = []
        counter = 0
        base = (text or "").encode("utf-8")
        while len(out) < self.dim:
            h = hashlib.sha256(base + struct.pack(">I", counter)).digest()
            for i in range(0, len(h), 4):
                if len(out) >= self.dim:
                    break
                val = struct.unpack(">I", h[i : i + 4])[0]
                out.append((val / 2**32) * 2.0 - 1.0)  # → [-1, 1)
            counter += 1
        norm = math.sqrt(sum(v * v for v in out)) or 1.0
        return [v / norm for v in out]


class _RealEmbedder:
    """BGE-M3 vía FlagEmbedding (lazy import; solo si EMBEDDINGS_REAL=1)."""

    def __init__(self, model_id: str, dim: int) -> None:
        from FlagEmbedding import BGEM3FlagModel  # type: ignore

        self._model = BGEM3FlagModel(model_id, use_fp16=False)
        self.dim = dim

    def encode(self, text: str) -> List[float]:
        vec = self._model.encode([text or ""])["dense_vecs"][0]
        return [float(x) for x in vec]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.embeddings_real:
        return _RealEmbedder(settings.embeddings_model, settings.embeddings_dim)
    return _StubEmbedder(settings.embeddings_dim)


@lru_cache(maxsize=4096)
def _encode_cached(text_sha: str, text: str) -> tuple:
    return tuple(get_embedder().encode(text))


def embed_with_cache(text: str) -> List[float]:
    """Embeddea con caché por sha256 (los boilerplates legales se repiten)."""
    sha = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return list(_encode_cached(sha, text))


def to_pgvector(vec: List[float]) -> str:
    """Formatea un vector como literal pgvector: ``'[v1,v2,...]'``."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
