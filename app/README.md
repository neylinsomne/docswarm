# `app/` — Backend B2B (reference implementation de docswarm)

Implementación del producto que envuelve el **engine docswarm** (ingest +
orquestación + ports) en un backend multi-tenant para **gestión documental de
contratos**: **Bayern** (comprador / *granbase*) gestiona contratos con sus
**proveedores**; cada proveedor tiene su propio login y está aislado por RLS.

> El esquema de base de datos y sus migraciones viven en [`../db/`](../db/).
> Este árbol es el código de aplicación (API + servicios + cableado del engine).

## Mapa de carpetas (cada una con una responsabilidad)

```
app/
├── settings.py          configuración desde .env (una sola fuente de verdad)
├── main.py              app factory FastAPI (+ /health)
├── db/                  pool psycopg + RLS (GUC app.current_empresa_id por tenant)
├── storage/            cliente MinIO/S3 (bytes crudos de documentos)
├── embeddings/         BGE-M3 1024-dim (real o stub) + caché + to_pgvector
├── security/           bcrypt + JWT + deps de FastAPI (Principal, require_admin)
├── domain/             lógica de negocio (sin SQL en la API):
│   ├── auth/           login + alta de usuarios
│   ├── companies/      empresas, metadata rica y características facetadas
│   ├── contracts/      contratos + cláusulas (RLS por proveedor)
│   ├── changes/        ★ log de cambios maestros → documentos afectados → firma
│   └── search/         búsqueda por contenido (vector) y por nombre (trigram)
├── retrieval/          RetrievalPort sobre pgvector (puerto del engine)
├── ingest/             ETL: ingest version-aware (DB+MinIO) + reading (parse/chunk/embed)
├── orchestration/      SwarmRunner del engine + StorePort (acp_runs) + worker de cola
└── api/v1/             routers HTTP (auth, empresas, contratos, cambios, documentos, buscar)
```

**Regla de dependencias:** `api → domain → (db, storage, embeddings)`; el engine
se usa vía `retrieval`/`ingest`/`orchestration`. La API nunca contiene SQL; los
servicios de dominio nunca conocen HTTP.

## Multi-tenant y RLS (lo más importante)

- El JWT lleva `empresa_id` + `tipo_empresa`. En cada request,
  `get_current_principal` fija el tenant en un `ContextVar`:
  - **COMPRADOR (Bayern)** → tenant `None` = **admin**, ve todo.
  - **PROVEEDOR** → tenant = su `empresa_id`, RLS lo aísla.
- `db_conn()` aplica `SET LOCAL app.current_empresa_id` en cada transacción.
- La app conecta como `docswarm_app` (NOSUPERUSER NOBYPASSRLS); el pool **se
  niega a arrancar** con un rol que ignore RLS salvo `DB_ALLOW_ADMIN_ROLE=1`.

## Feature central — log de cambios

`POST /api/v1/cambios/precio` (o `/clausula`) — solo Bayern:
1. versiona el ítem maestro y registra el cambio (antes/después),
2. inserta un **documento afectado** por cada contrato con una cláusula derivada,
   con `firmado_proveedor = FALSE`.

`GET /api/v1/cambios` → tablero (afectados / firmados / pendientes).
`GET /api/v1/cambios/{id}/afectados` → drill-down por contrato.
`POST /api/v1/cambios/afectados/{id}/firma` → el proveedor firma (booleano → TRUE).

## Arranque local

```bash
cp .env.example .env                      # ajusta secretos
docker compose up -d postgres minio ollama
docker compose run --rm flyway migrate    # aplica el esquema + semilla agro
docker compose up -d api worker
# API:    http://localhost:8000/docs
# Login demo (Bayern): bayern.demo@docswarm.local / Demo1234*
```

Sin Docker (dev):

```bash
pip install -e ".[backend,yaml,ingest]"
uvicorn app.main:app --reload
```

## Búsqueda

- **Contenido del contrato** → `GET /api/v1/buscar/contenido?q=...` (pgvector coseno).
- **Nombre de contrato** → `GET /api/v1/buscar/contratos?q=...` (trigram).
- **Empresas por perfil** → `GET /api/v1/buscar/empresas?q=...` (vector).
- **Facetas/metadata** → `POST /api/v1/empresas/buscar` con `caracteristicas`.

## Extensión futura (agentes / WhatsApp)

El swarm (`app/orchestration`) ya está cableado con el engine y `acp_runs`. Un
canal como WhatsApp se añade como un nuevo `source` de ingest + un handler en el
worker; los agentes pueden recuperar contexto vía `PgVectorRetrieval` y responder
sobre los contratos del tenant respetando RLS.
