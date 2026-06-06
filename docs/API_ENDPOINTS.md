# API endpoints — docswarm B2B

> Generado desde OpenAPI. Specs completas (request/response, schemas):
> - Core: [openapi.core.json](openapi.core.json) · Swagger UI `http://localhost:8008/docs`
> - Notifier (M2M, X-API-Key): [openapi.notifier.json](openapi.notifier.json) · `http://localhost:8010/docs`
>
> **Para el agente que conecta el front:** lo más cómodo es generar el cliente/tipos
> desde `openapi.core.json` (TS: `openapi-typescript` u `orval`). El front solo usa
> el Core API; el Notifier es máquina-a-máquina (no lo llama el navegador).
> Firma y avisos funcionan **dentro de la página** vía Core API:
> `POST /api/v1/firmas/afectado/{id}`, `POST /api/v1/firmas/contrato/{id}`,
> `GET /api/v1/notificaciones?canal=SISTEMA&no_leidas=true`,
> `GET /api/v1/notificaciones/no_leidas/conteo`, `POST /api/v1/notificaciones/{id}/leida`.


## Core API (`http://localhost:8008`) — JWT `Authorization: Bearer <token>`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/usuarios` | Crear Usuario |
| GET | `/api/v1/buscar/contenido` | Buscar Contenido |
| GET | `/api/v1/buscar/contratos` | Buscar Contratos |
| GET | `/api/v1/buscar/empresas` | Buscar Empresas |
| GET | `/api/v1/cambios` | Listar Cambios |
| POST | `/api/v1/cambios/afectados/{afectado_id}/firma` | Firmar Afectado |
| POST | `/api/v1/cambios/clausula` | Cambiar Clausula |
| POST | `/api/v1/cambios/precio` | Cambiar Precio |
| GET | `/api/v1/cambios/{cambio_id}/afectados` | Detalle Afectados |
| GET | `/api/v1/catalogo/clausulas` | Buscar Clausulas |
| POST | `/api/v1/catalogo/clausulas` | Crear Clausula |
| GET | `/api/v1/catalogo/precios` | Buscar Precios |
| POST | `/api/v1/catalogo/precios` | Crear Precio |
| POST | `/api/v1/contratos` | Crear Contrato |
| GET | `/api/v1/contratos` | Listar Contratos |
| PATCH | `/api/v1/contratos/clausulas/{clausula_id}` | Actualizar Clausula |
| DELETE | `/api/v1/contratos/clausulas/{clausula_id}` | Eliminar Clausula |
| POST | `/api/v1/contratos/generar` | Generar Contrato |
| GET | `/api/v1/contratos/{contrato_id}` | Obtener Contrato |
| PATCH | `/api/v1/contratos/{contrato_id}` | Actualizar Contrato |
| POST | `/api/v1/contratos/{contrato_id}/clausulas` | Agregar Clausula |
| POST | `/api/v1/contratos/{contrato_id}/firma` | Firmar Contrato |
| POST | `/api/v1/documentos` | Subir Documento |
| POST | `/api/v1/empresas` | Crear Empresa |
| GET | `/api/v1/empresas` | Listar Empresas |
| POST | `/api/v1/empresas/buscar` | Buscar Empresas |
| GET | `/api/v1/empresas/{empresa_id}` | Obtener Empresa |
| PATCH | `/api/v1/empresas/{empresa_id}` | Actualizar Empresa |
| GET | `/api/v1/firmas` | Listar Firmas |
| POST | `/api/v1/firmas/afectado/{afectado_id}` | Firmar Afectado |
| POST | `/api/v1/firmas/contrato/{contrato_id}` | Firmar Contrato |
| GET | `/api/v1/notificaciones` | Listar Notificaciones |
| GET | `/api/v1/notificaciones/no_leidas/conteo` | Conteo No Leidas |
| POST | `/api/v1/notificaciones/{notif_id}/leida` | Marcar Leida |
| GET | `/health` | Health |
| GET | `/health/db` | Health Db |

## Notifier (`http://localhost:8010`) — M2M `X-API-Key`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/dispatch` | Dispatch |
| POST | `/firmas` | Iniciar Firma |
| POST | `/firmas/{firma_id}/evento` | Evento Firma |
| GET | `/health` | Health |
| POST | `/notificaciones/{notif_id}/estado` | Actualizar Estado |
| GET | `/pendientes` | Pendientes |
