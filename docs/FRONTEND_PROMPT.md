# Prompt de frontend — docswarm B2B (gestión documental de contratos)

> **Para Stitch / agentes de UI.** Este documento es un brief autocontenido para
> construir el frontend web del backend ya implementado. Incluye roles, vistas,
> endpoints, formas de datos y flujos. El backend NO se toca; el front solo
> consume la API REST (FastAPI). Idioma de UI: **español**.

---

## 1. Producto y contexto

SaaS B2B de **gestión documental de contratos**. La empresa compradora **Bayern**
(la "granbase") gestiona contratos con sus **proveedores**. Cuando Bayern cambia
una **cláusula o precio maestro**, el sistema detecta los **contratos afectados** y
lleva un **log** que muestra qué documentos cambiaron y un **booleano de si el
proveedor ya firmó**. La firma y las notificaciones ocurren también por
**WhatsApp/Gmail** (microservicio aparte). Hay **búsqueda vectorial** por contenido
de contrato y por nombre, y filtrado rico por metadata. Bayern puede **crear
contratos** eligiendo cláusulas del catálogo o **generándolos con un prompt** (ACP,
swarm de agentes).

### Roles
| Rol | Quién | Qué ve |
|---|---|---|
| **ADMIN/Bayern** (`tipo_empresa = COMPRADOR`) | empleados de Bayern | TODO: proveedores, todos los contratos, catálogo maestro, registrar cambios, generar contratos, notificaciones |
| **Proveedor** (`tipo_empresa = PROVEEDOR`) | cada empresa proveedora | SOLO lo suyo: sus contratos, los cambios que le afectan, sus notificaciones, firmar |

El JWT trae `tipo_empresa`, `empresa_id`, `rol`. La UI ramifica la navegación por
`tipo_empresa`. El aislamiento real lo hace el backend (RLS); el front solo
adapta el menú.

---

## 2. Técnico (cómo hablar con la API)

- **Base URL core API:** `http://localhost:8008` (prod: variable de entorno).
- **Auth:** `POST /api/v1/auth/login` (form `application/x-www-form-urlencoded`,
  campos `username`=email, `password`). Devuelve `{access_token, tipo_empresa,
  empresa_id, rol}`. Guardar el token y mandarlo en todas las llamadas:
  `Authorization: Bearer <token>`.
- **Errores:** 401 (token inválido) → volver a login; 403 (acción solo de Bayern);
  404 (no encontrado). Mostrar toasts.
- **Microservicio notifier** (`http://localhost:8010`, header `X-API-Key`) es
  **máquina-a-máquina** — NO lo llama el front; lo usa el repo de WhatsApp/Gmail.
  El front solo lee notificaciones por el core (`GET /api/v1/notificaciones`).

### Enums (para badges/estados)
- Contrato `estado`: `BORRADOR · VIGENTE · SUSPENDIDO · VENCIDO · TERMINADO`.
- Cambio `tipo_objeto`: `CLAUSULA · PRECIO`; `accion`: `CREACION · ACTUALIZACION · DEROGACION`.
- Afectado `estado_propagacion`: `PENDIENTE · NOTIFICADO · APLICADO · RECHAZADO`.
- Notificación `canal`: `WHATSAPP · GMAIL · SISTEMA`; `estado`: `PENDIENTE · ENVIADO · ENTREGADO · LEIDO · FALLIDO`.
- Cláusula `tipo`: `PRECIO · ENTREGA · CALIDAD · PAGO · PENALIZACION · CONFIDENCIALIDAD · GENERAL`.

---

## 3. Dirección de diseño

- App de dashboard B2B, limpia y densa en datos. Sidebar izquierdo + topbar con
  buscador global y avatar de empresa.
- Paleta: corporativa, acento verde/teal (agro), neutros grises; estados con
  semáforo (verde=firmado/ok, ámbar=pendiente/notificado, rojo=fallido/vencido).
- Componentes: tablas con filtros y paginación, tarjetas KPI, drawers de detalle,
  modales de formulario, badges de estado, line/area charts simples, file uploader.
- Responsive; foco en desktop. Accesible (labels, foco visible).

---

## 4. Navegación

**Topbar (siempre):** logo · buscador global · nombre de empresa + rol · logout.

**Sidebar Bayern (ADMIN):**
`Dashboard · Proveedores · Contratos · Catálogo maestro · Cambios · Notificaciones · Búsqueda`

**Sidebar Proveedor:**
`Dashboard · Mis contratos · Cambios que me afectan · Notificaciones · Mi empresa`

---

## 5. Vistas (pantallas)

### 5.1 Login  `[todos]`
- Form email + password → `POST /api/v1/auth/login`.
- Guardar token; redirigir a Dashboard según `tipo_empresa`.
- Demo: `bayern.demo@docswarm.local` / `Demo1234*` (Bayern);
  `semillas.demo@docswarm.local`, `campo.demo@docswarm.local` (proveedores).

### 5.2 Dashboard Bayern  `[ADMIN]`
- KPIs (tarjetas): nº proveedores, contratos vigentes, cambios último mes, % de
  documentos afectados pendientes de firma.
- Tabla "Cambios recientes" (de `GET /api/v1/cambios`): columnas objeto, tipo,
  afectados, firmados, pendientes, fecha. Click → detalle (5.6).
- Datos: `GET /api/v1/cambios`, `GET /api/v1/contratos`, `GET /api/v1/empresas`.

### 5.3 Proveedores (empresas)  `[ADMIN]`
- **Lista + filtros**: buscador por nombre, selects sector/nicho.
  - Simple: `GET /api/v1/empresas?nombre=&sector=&nicho=&limit=&offset=`
  - Facetas (características clave→valor): `POST /api/v1/empresas/buscar` body
    `{nombre, sector, nicho, caracteristicas:{certificacion:"ISO9001"}, limit, offset}`.
- **Crear proveedor** (modal, solo Bayern): `POST /api/v1/empresas` body
  `{nombre, nit, tipo:"PROVEEDOR", sector, nicho, ciudad, metadata:{...},
  caracteristicas:[{clave,valor,valor_num}]}`. La metadata es JSON libre (editor
  clave-valor) — "lo más rico posible" para búsqueda/filtrado.
- **Detalle** (drawer): `GET /api/v1/empresas/{id}` (incluye `caracteristicas`).
  Editar: `PATCH /api/v1/empresas/{id}` `{nombre?,sector?,nicho?,ciudad?,metadata?,activo?}`.

### 5.4 Contratos  `[ADMIN ve todos · Proveedor ve los suyos]`
- **Lista**: `GET /api/v1/contratos?estado=&limit=&offset=`. Badge de `estado` y de
  `firmado_proveedor`. Columnas: número, título, proveedor, estado, valor, firmado.
- **Detalle**: `GET /api/v1/contratos/{id}` → cabecera + lista de `clausulas`
  (tipo, título, contenido, orden, vínculo a maestro).
- **Proveedor: firmar** botón `POST /api/v1/contratos/{id}/firma` `{firmado:true}`.
- **Bayern: editar** `PATCH /api/v1/contratos/{id}`; cláusulas:
  `POST /api/v1/contratos/{id}/clausulas`, `PATCH /api/v1/contratos/clausulas/{cid}`,
  `DELETE /api/v1/contratos/clausulas/{cid}`.

#### 5.4.b Crear contrato — asistente (wizard)  `[ADMIN]`  ★ vista clave
Tres pasos:
1. **Datos**: proveedor (autocomplete sobre `GET /api/v1/empresas`), comprador
   (Bayern fijo), título, objeto, sector, valor, fechas.
2. **Cláusulas**: dos modos (tabs):
   - **Buscar y poner del catálogo**: buscador `GET /api/v1/catalogo/clausulas?q=&tipo=`
     y `GET /api/v1/catalogo/precios?q=`. El usuario selecciona ítems → se guardan
     sus ids. (También permite añadir cláusulas manuales libres.)
   - **Generar con prompt (ACP)**: textarea de instrucción + selección opcional de
     cláusulas/precios base → `POST /api/v1/contratos/generar` body
     `{prompt, empresa_proveedor_id, objeto, titulo, clausulas_maestras_ids:[],
     precios_maestros_ids:[], use_ollama:false}`. Respuesta `{titulo, markdown,
     html, secciones, warnings}` → **previsualizar** el documento (render markdown/html).
3. **Confirmar**: `POST /api/v1/contratos` body
   `{empresa_proveedor_id, empresa_compradora_id, titulo, numero, objeto, sector,
   valor, moneda, fecha_inicio, fecha_fin, metadata,
   clausulas:[{tipo,contenido,titulo,orden,valor}],
   clausulas_maestras_ids:[], precios_maestros_ids:[]}` (los ids del catálogo se
   materializan como cláusulas del contrato copiando su contenido vigente).

### 5.5 Catálogo maestro  `[ADMIN]`
- Dos tablas: **Cláusulas** (`GET /api/v1/catalogo/clausulas?q=&tipo=&sector=`) y
  **Precios** (`GET /api/v1/catalogo/precios?q=&categoria=`).
- Crear: `POST /api/v1/catalogo/clausulas` `{codigo,tipo,titulo,contenido_actual,
  sector,nicho,metadata}`; `POST /api/v1/catalogo/precios` `{codigo,producto,precio,
  categoria,moneda,unidad,sector,nicho}`.
- Cada fila muestra `version` y `vigente`.

### 5.6 Cambios (log)  `[ADMIN registra · todos consultan lo suyo]`  ★ feature central
- **Tablero**: `GET /api/v1/cambios` → tarjetas/tabla con `objeto_codigo`,
  `objeto_titulo`, `tipo_objeto`, `docs_afectados`, `docs_firmados`,
  `docs_pendientes`, fecha. Barra de progreso firmados/afectados.
- **Registrar cambio (Bayern)**: modal con tabs Cláusula/Precio.
  - Cláusula: `POST /api/v1/cambios/clausula` `{clausula_maestra_id, nuevo_contenido,
    descripcion}`.
  - Precio: `POST /api/v1/cambios/precio` `{precio_maestro_id, nuevo_precio,
    descripcion}`.
  - Respuesta `{cambio_id, docs_afectados, notificaciones}` → toast "N contratos
    afectados, M notificaciones enviadas".
- **Detalle / drill-down**: `GET /api/v1/cambios/{id}/afectados` → tabla de
  contratos afectados: proveedor, contrato, `estado_propagacion`,
  **`firmado_proveedor`** (badge sí/no), fecha_firma, notificado_at.
- **Proveedor: firmar la actualización**:
  `POST /api/v1/cambios/afectados/{afectado_id}/firma` `{observaciones?}`.

### 5.7 Notificaciones  `[todos, RLS]`
- Lista `GET /api/v1/notificaciones` → canal (icono WhatsApp/Gmail), asunto,
  estado de entrega (badge), destino, fecha. Solo lectura (el envío lo hace el
  microservicio). Mostrar timeline enviado/entregado/leído.
- Firmas (opcional): `GET /api/v1/firmas` → estado del proceso de firma.

### 5.8 Búsqueda global  `[todos, RLS]`
- Caja única con tabs de resultados:
  - **Contenido de contratos** (semántica): `GET /api/v1/buscar/contenido?q=&top_k=`
    → fragmentos con `similarity`, link al contrato.
  - **Contratos por nombre**: `GET /api/v1/buscar/contratos?q=`.
  - **Empresas por perfil**: `GET /api/v1/buscar/empresas?q=` (solo Bayern útil).

### 5.9 Documentos (subida)  `[todos, RLS]`
- Uploader `POST /api/v1/documentos` (multipart: `archivo`, `contrato_id?`,
  `titulo?`). Tras subir, el documento se versiona y se procesa en background
  (parse/chunk/embed) para que aparezca en la búsqueda por contenido.

### 5.10 Dashboard Proveedor  `[PROVEEDOR]`
- KPIs: mis contratos, pendientes de firma, notificaciones sin leer.
- Lista "Cambios que me afectan" con acción rápida de firma (usa 5.6 drill-down +
  firma de afectado).

---

## 6. Flujos clave (para conectar pantallas)

**A. Bayern crea un contrato con ACP**
Login → Contratos → "Crear" → wizard (datos → tab "Generar con prompt" →
`/contratos/generar` → preview → confirmar `/contratos`).

**B. Cambio maestro → notificación → firma**
Bayern: Cambios → "Registrar" (`/cambios/precio`) → tablero muestra afectados.
(El microservicio notifica por WhatsApp/Gmail.)
Proveedor: Dashboard/Notificaciones → "Cambios que me afectan" →
`/cambios/{id}/afectados` → firmar `/cambios/afectados/{id}/firma` → el tablero de
Bayern pasa el contador a "firmado".

**C. Proveedor revisa y firma su contrato**
Login proveedor → Mis contratos → detalle → `POST /contratos/{id}/firma`.

---

## 7. Arquitectura (vista opcional "Sistema")

Pipeline real del backend (para un diagrama informativo en la UI de admin):

```
Subida/WhatsApp/Gmail ─▶ Ingesta version-aware (MinIO + Postgres)
   ─▶ Parse/Chunk/Embed (BGE-M3) ─▶ pgvector (búsqueda por contenido)
Catálogo maestro (Bayern) ─▶ Cambios ─▶ Documentos afectados ─▶ Notificaciones
   ─▶ Firma electrónica (WhatsApp/Gmail)
Generación de contratos ─▶ Swarm de agentes (ACP): legal · comercial · técnico · general ─▶ Documento
```

---

## 8. Apéndice — referencia rápida de endpoints

| Método | Ruta | Rol | Uso |
|---|---|---|---|
| POST | `/api/v1/auth/login` | público | login (form) |
| POST | `/api/v1/auth/usuarios` | ADMIN | alta usuario |
| GET  | `/api/v1/empresas` | auth | listar/filtrar empresas |
| POST | `/api/v1/empresas/buscar` | auth | filtrado facetado |
| POST | `/api/v1/empresas` | ADMIN | crear empresa |
| GET  | `/api/v1/empresas/{id}` | auth | detalle |
| PATCH| `/api/v1/empresas/{id}` | auth | editar |
| GET  | `/api/v1/catalogo/clausulas` | auth | buscar cláusulas maestras |
| GET  | `/api/v1/catalogo/precios` | auth | buscar precios maestros |
| POST | `/api/v1/catalogo/clausulas` | ADMIN | crear cláusula maestra |
| POST | `/api/v1/catalogo/precios` | ADMIN | crear precio maestro |
| GET  | `/api/v1/contratos` | auth (RLS) | listar contratos |
| POST | `/api/v1/contratos` | ADMIN | crear contrato (+ ids maestros) |
| POST | `/api/v1/contratos/generar` | ADMIN | **ACP: prompt → documento** |
| GET  | `/api/v1/contratos/{id}` | auth (RLS) | detalle + cláusulas |
| PATCH| `/api/v1/contratos/{id}` | ADMIN | editar contrato |
| POST | `/api/v1/contratos/{id}/clausulas` | ADMIN | agregar cláusula |
| PATCH| `/api/v1/contratos/clausulas/{cid}` | ADMIN | editar cláusula |
| DELETE| `/api/v1/contratos/clausulas/{cid}` | ADMIN | borrar cláusula |
| POST | `/api/v1/contratos/{id}/firma` | proveedor | firmar contrato |
| POST | `/api/v1/cambios/clausula` | ADMIN | registrar cambio de cláusula |
| POST | `/api/v1/cambios/precio` | ADMIN | registrar cambio de precio |
| GET  | `/api/v1/cambios` | auth (RLS) | tablero de cambios |
| GET  | `/api/v1/cambios/{id}/afectados` | auth (RLS) | docs afectados + firma |
| POST | `/api/v1/cambios/afectados/{id}/firma` | proveedor | firmar actualización |
| GET  | `/api/v1/notificaciones` | auth (RLS) | mis avisos (`?canal=SISTEMA&no_leidas=true`) |
| GET  | `/api/v1/notificaciones/no_leidas/conteo` | auth (RLS) | badge campanita |
| POST | `/api/v1/notificaciones/{id}/leida` | auth (RLS) | marcar aviso leído (in-page) |
| GET  | `/api/v1/firmas` | auth (RLS) | procesos de firma |
| POST | `/api/v1/firmas/afectado/{id}` | proveedor | **firma electrónica in-page** del afectado |
| POST | `/api/v1/firmas/contrato/{id}` | proveedor | **firma electrónica in-page** del contrato |
| POST | `/api/v1/documentos` | auth (RLS) | subir documento (multipart) |
| GET  | `/api/v1/buscar/contenido` | auth (RLS) | búsqueda semántica |
| GET  | `/api/v1/buscar/contratos` | auth (RLS) | búsqueda por nombre |
| GET  | `/api/v1/buscar/empresas` | auth | búsqueda por perfil |
| GET  | `/health`, `/health/db` | público | salud |

> OpenAPI interactivo: `http://localhost:8008/docs` (úsalo para ver request/response
> exactos al maquetar). Genera tipos del front desde `http://localhost:8008/openapi.json`.
> Specs exportadas en el repo: [openapi.core.json](openapi.core.json),
> [openapi.notifier.json](openapi.notifier.json); lista compacta en
> [API_ENDPOINTS.md](API_ENDPOINTS.md).
>
> **Firma electrónica y avisos = dentro de la página** (no requieren WhatsApp):
> el proveedor firma con `POST /api/v1/firmas/afectado/{id}` (o `/contrato/{id}`) y ve
> los avisos con `GET /api/v1/notificaciones?canal=SISTEMA&no_leidas=true` + el badge
> `GET /api/v1/notificaciones/no_leidas/conteo`. WhatsApp/Gmail son un extra opcional
> del microservicio notifier.
