"""Configuración central del backend, leída del entorno (.env).

Una sola fuente de verdad para credenciales y flags. Se importa como
``from app.settings import settings``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- PostgreSQL (rol de aplicación, RLS) ---
    db_host: str = Field("localhost", alias="DB_HOST")
    db_port: int = Field(5432, alias="DB_PORT")
    db_name: str = Field("docswarm", alias="DB_NAME")
    db_user: str = Field("docswarm_app", alias="DB_USER")
    db_password: str = Field("change_me_in_env", alias="DB_PASSWORD")
    # Permitir conectar con un rol que ignora RLS (solo backfills/worker admin).
    db_allow_admin_role: bool = Field(False, alias="DB_ALLOW_ADMIN_ROLE")
    db_pool_min: int = Field(1, alias="DB_POOL_MIN")
    db_pool_max: int = Field(10, alias="DB_POOL_MAX")

    # --- MinIO / S3 ---
    minio_endpoint: str = Field("localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field("minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field("docswarm-docs", alias="MINIO_BUCKET")
    minio_secure: bool = Field(False, alias="MINIO_SECURE")

    # --- Ollama / LLM ---
    ollama_host: str = Field("http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field("qwen3:8b", alias="OLLAMA_MODEL")
    llm_timeout: float = Field(60.0, alias="LLM_TIMEOUT")
    # Preferencia de proveedor por defecto: auto|ollama|gemini|stub
    llm_prefer: str = Field("auto", alias="LLM_PREFER")

    # --- Gemini (fallback si Ollama se cuelga) ---
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.0-flash", alias="GEMINI_MODEL")

    # --- Embeddings (BGE-M3) ---
    embeddings_real: bool = Field(False, alias="EMBEDDINGS_REAL")
    embeddings_model: str = Field("BAAI/bge-m3", alias="EMBEDDINGS_MODEL")
    embeddings_dim: int = Field(1024, alias="EMBEDDINGS_DIM")

    # --- Auth ---
    jwt_secret: str = Field("dev-insecure-secret-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(480, alias="JWT_EXPIRE_MINUTES")

    # --- Integración M2M (microservicio notifier / repo WhatsApp+Gmail) ---
    # Clave de servicio en header X-API-Key para los endpoints máquina-a-máquina.
    service_api_key: str = Field("dev-service-key-change-me", alias="SERVICE_API_KEY")
    # Canales por defecto al notificar un cambio. SISTEMA = aviso visible DENTRO
    # de la página (entrega inmediata, sin depender de WhatsApp/Gmail).
    notif_canales: str = Field("SISTEMA,WHATSAPP,GMAIL", alias="NOTIF_CANALES")
    # Crear notificaciones automáticamente al registrar un cambio.
    notif_auto: bool = Field(True, alias="NOTIF_AUTO")

    @property
    def notif_canales_list(self) -> tuple[str, ...]:
        return tuple(c.strip().upper() for c in self.notif_canales.split(",") if c.strip())

    @property
    def db_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
