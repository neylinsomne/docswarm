# Imagen del backend B2B (API + worker). El engine docswarm se instala junto.
FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema mínimas (psycopg binary trae libpq; curl para healthcheck).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Metadata primero para cachear la capa de dependencias.
COPY pyproject.toml README.md ./
COPY docswarm ./docswarm
COPY app ./app

# Instala el engine + extras del backend (FastAPI, psycopg, minio, ...).
RUN pip install --no-cache-dir -e ".[backend,yaml,ingest]"

COPY . .

EXPOSE 8000

# Por defecto levanta la API; el worker se arranca con otro `command` en compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
