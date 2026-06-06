"""Backend de gestión documental B2B (reference implementation de docswarm).

Estructura por capas (sin scripts sueltos; cada carpeta tiene una
responsabilidad y se comunica con las vecinas por interfaces claras):

    app/
      settings.py        configuración (env)
      db/                pool psycopg + RLS (GUC por tenant)
      storage/           cliente MinIO/S3
      embeddings/        motor BGE-M3 (real o stub)
      security/          contraseñas (bcrypt) + JWT + deps de FastAPI
      domain/            lógica de negocio: auth, companies, contracts, changes, search
      retrieval/         RetrievalPort sobre pgvector (engine docswarm)
      ingest/            ETL: subir/parsear/chunkear/vectorizar (engine docswarm)
      orchestration/     swarm de agentes (engine docswarm) + worker de cola
      api/               routers FastAPI (capa HTTP)
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
