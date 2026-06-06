# Imagen del microservicio notifier (WhatsApp/Gmail + firma). Imagen propia y
# liviana (sin extractores pesados del ETL) para aislar fallos del core.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY docswarm ./docswarm
COPY app ./app
COPY services ./services

# Solo el extra `backend` (FastAPI, psycopg, pydantic...). Nada de ingest/embeddings.
RUN pip install --no-cache-dir -e ".[backend]"

COPY . .

EXPOSE 8010

CMD ["uvicorn", "services.notifier.main:app", "--host", "0.0.0.0", "--port", "8010"]
