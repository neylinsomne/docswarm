# `docs/mocks/` — Datos de ejemplo para el front

Mocks en JSON con **las mismas formas que devuelve la API real**, para que el
front (Stitch/agente) renderice ya, sin backend, y luego cambie mock↔API sin
tocar la UI. Dominio: nicho **agro** (Bayern + proveedores).

| Archivo | Endpoint que imita | Para qué vista |
|---|---|---|
| [auth.json](auth.json) | `POST /api/v1/auth/login` | Login (usuarios demo) |
| [empresas.json](empresas.json) | `GET /api/v1/empresas` (+ detalle con `caracteristicas`) | Proveedores: lista, detalle, filtros |
| [clausulas_maestras.json](clausulas_maestras.json) | `GET /api/v1/catalogo/clausulas` | Catálogo · "buscar y poner cláusulas" |
| [precios_maestros.json](precios_maestros.json) | `GET /api/v1/catalogo/precios` | Catálogo de precios |
| [contratos.json](contratos.json) | `GET /api/v1/contratos` (+ detalle con `clausulas`) | Contratos: lista y detalle |
| [cambios.json](cambios.json) | `GET /api/v1/cambios` y `/{id}/afectados` | Tablero de cambios + drill-down |
| [notificaciones.json](notificaciones.json) | `GET /api/v1/notificaciones`, `/firmas` | Avisos in-page + firmas |
| [generacion_acp.json](generacion_acp.json) | `POST /api/v1/contratos/generar` | Preview del wizard ACP |

## Notas
- Los `id` son consistentes entre archivos (p.ej. `empresa_proveedor_id: 2` =
  "AgroSemillas del Valle" en `empresas.json`; `clausula_maestra_id: 1` =
  `CL-CALIDAD-001`).
- Cada archivo trae un bloque `_meta` (no es parte de la respuesta real; ignóralo
  al mapear). Las claves de datos sí coinciden con la API.
- Estados para badges: ver enums en [../FRONTEND_PROMPT.md](../FRONTEND_PROMPT.md) §2.
- Para datos vivos equivalentes, la semilla `db/migrations/V10__seed_demo.sql` ya
  carga Bayern + 2 proveedores + 1 cambio; estos mocks amplían el set para diseño.
