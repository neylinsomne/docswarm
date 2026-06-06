"""Motor de embeddings (BGE-M3, 1024-dim) tras un singleton."""

from app.embeddings.engine import embed_with_cache, get_embedder, to_pgvector

__all__ = ["embed_with_cache", "get_embedder", "to_pgvector"]
