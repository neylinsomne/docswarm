# `db/` — Base de datos (Flyway)

Todo lo relativo a la base de datos vive aquí: **migraciones versionadas**,
**diagrama** y configuración. No hay scripts SQL sueltos fuera de este árbol; el
orden de aplicación lo dicta Flyway por el prefijo `V<n>__` (versionadas) y
`R__` (repetibles, se re-aplican al cambiar su contenido).

```
db/
├── flyway.conf              # conexión + opciones (sobreescrito por env en compose)
├── migrations/             # ← única fuente de verdad del esquema
│   ├── V1__extensions_and_roles.sql   extensiones (vector, pg_trgm) + rol app RLS
│   ├── V2__tenant_core.sql            empresas, características, usuarios, helper RLS
│   ├── V3__contracts.sql              contratos + contrato_clausulas
│   ├── V4__master_catalog.sql         clausulas_maestras + precios_maestros (Bayern)
│   ├── V5__data_platform.sql          raw_documents, parsed, chunks(pgvector), links, jobs
│   ├── V6__change_log.sql             ★ cambios_maestros + cambios_documentos_afectados
│   ├── V7__knowledge_graph.sql        kg_entidades / kg_aristas / kg_validaciones
│   ├── V8__orchestration_ops.sql      acp_runs, scrape_jobs (cola), heartbeats, métricas
│   ├── V9__rls_policies.sql           RLS por tenant + GRANTs
│   ├── V10__seed_demo.sql             semilla agro (Bayern + 2 proveedores + 1 cambio)
│   └── R__views.sql                   vistas de tablero (resumen de cambios)
└── diagram/
    ├── schema.dbml                    diagrama completo (dbdiagram.io)
    └── schema.mermaid.md              diagrama ER + flujo (inline en GitHub/VSCode)
```

## Modelo de dominio (B2B)

- **Bayern** es la única empresa `tipo='COMPRADOR'` (la *granbase*). Sus usuarios
  actúan como **admin**: la app conecta con `app.current_empresa_id = NULL` y ven
  todo.
- Cada **proveedor** es `tipo='PROVEEDOR'`, tiene su propio usuario/contraseña y
  está **aislado por RLS**: solo ve sus contratos, documentos y los cambios que le
  afectan.
- **Contrato** = relación Bayern↔proveedor; sus cláusulas pueden **derivar** de un
  ítem del **catálogo maestro** de Bayern (`clausulas_maestras` / `precios_maestros`).

## Feature central — log de cambios

Cuando Bayern cambia una cláusula o precio maestro:

1. Se inserta en **`cambios_maestros`** (qué, antes/después, versión, quién).
2. Se calculan los **contratos afectados** (los que tienen una cláusula derivada de
   ese ítem) y se inserta una fila por cada uno en
   **`cambios_documentos_afectados`**, con el booleano **`firmado_proveedor`** que
   rectifica si esa empresa proveedora **ya firmó**.
3. La vista **`vw_cambios_resumen`** entrega `docs_afectados / docs_firmados /
   docs_pendientes` por cambio (tablero).

## Aplicar las migraciones

Con el stack de `docker-compose.yml` en la raíz:

```bash
docker compose up -d postgres           # levanta pgvector
docker compose run --rm flyway migrate  # aplica V1..V10 + R__
docker compose run --rm flyway info     # estado de migraciones
```

> **RLS (lo más importante):** la app debe conectarse con el rol
> `docswarm_app` (NOSUPERUSER NOBYPASSRLS). Conectarse como `postgres`/owner
> **desactiva en silencio** todas las políticas. Flyway sí usa el rol owner para
> poder crear objetos; la **aplicación** usa `docswarm_app`.

## Búsqueda

- **Por nombre** (empresa/contrato): índices GIN trigram (`pg_trgm`).
- **Por contenido del contrato**: `document_chunks.embedding_vec` (pgvector
  ivfflat, coseno `<=>`). La consulta canónica usa el vector dos veces:
  `1 - (embedding_vec <=> %s::vector)` como score y `ORDER BY embedding_vec <=>
  %s::vector` para que el índice dirija el orden.
- **Por características/metadata**: `empresa_caracteristicas` (facetas) +
  `metadata` JSONB (GIN).
