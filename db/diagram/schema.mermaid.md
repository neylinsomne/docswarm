# Diagrama ER — gestión documental B2B (vista inline)

> Render automático en GitHub/VSCode (Mermaid). Para la versión completa con todos
> los atributos usar [schema.dbml](schema.dbml) en dbdiagram.io.

```mermaid
erDiagram
    empresas ||--o{ empresa_caracteristicas : tiene
    empresas ||--o{ usuarios : "login por empresa"
    empresas ||--o{ contratos : "proveedor"
    empresas ||--o{ contratos : "comprador"
    contratos ||--o{ contrato_clausulas : contiene
    clausulas_maestras ||--o{ contrato_clausulas : "deriva (CL)"
    precios_maestros ||--o{ contrato_clausulas : "deriva (PR)"

    clausulas_maestras ||--o{ cambios_maestros : "cambia"
    precios_maestros ||--o{ cambios_maestros : "cambia"
    cambios_maestros ||--o{ cambios_documentos_afectados : "afecta"
    contratos ||--o{ cambios_documentos_afectados : "documento afectado"
    empresas ||--o{ cambios_documentos_afectados : "proveedor afectado"

    contratos ||--o{ raw_documents : "PDF/DOCX"
    empresas ||--o{ raw_documents : "tenant"
    raw_documents ||--o{ parsed_documents : "extrae"
    raw_documents ||--o{ document_chunks : "vectoriza"
    raw_documents ||--o{ document_links : "relaciona"

    kg_entidades ||--o{ kg_aristas : "source"
    kg_entidades ||--o{ kg_aristas : "target"
    empresas ||--o{ kg_validaciones : "valida"

    cambios_documentos_afectados ||--o{ notificaciones : "notifica"
    cambios_documentos_afectados ||--o{ firmas : "firma"
    usuarios ||--o{ notificaciones : "destinatario"
    notificaciones ||--o{ firmas : "origina"

    empresas {
        bigint id PK
        text tipo "COMPRADOR|PROVEEDOR"
        text nombre
        text sector
        text nicho
        jsonb metadata
        vector perfil_vec
    }
    contratos {
        bigint id PK
        bigint empresa_proveedor_id FK "tenant"
        bigint empresa_compradora_id FK
        text estado
        boolean firmado_proveedor
        vector contenido_vec
    }
    cambios_maestros {
        bigint id PK
        text tipo_objeto "CLAUSULA|PRECIO"
        jsonb valor_anterior
        jsonb valor_nuevo
    }
    cambios_documentos_afectados {
        bigint id PK
        bigint cambio_id FK
        bigint contrato_id FK
        boolean firmado_proveedor "★ ya firmó?"
        text estado_propagacion
    }
    document_chunks {
        bigint id PK
        bigint raw_document_id FK
        text contenido
        vector embedding_vec
    }
```

## Flujo de la feature central (cambio → afectados → firma)

```mermaid
flowchart LR
    A[Bayern edita cláusula/precio maestro] --> B[INSERT cambios_maestros<br/>antes/después + versión]
    B --> C{Buscar contratos<br/>con cláusula derivada}
    C --> D[INSERT cambios_documentos_afectados<br/>1 fila por contrato afectado]
    D --> E[firmado_proveedor = FALSE<br/>estado = NOTIFICADO]
    E --> F[Proveedor revisa y firma]
    F --> G[UPDATE firmado_proveedor = TRUE<br/>fecha_firma = now]
    D --> H[(vw_cambios_resumen<br/>afectados / firmados / pendientes)]
```

## Notificación + firma electrónica (microservicio notifier)

```mermaid
flowchart LR
    A[Cambio registrado<br/>core API] --> B[INSERT notificaciones<br/>PENDIENTE x usuario x canal]
    B --> C{{notifier · puerto propio}}
    C -->|GET /pendientes X-API-Key| D[Repo WhatsApp/Gmail<br/>o dispatcher interno]
    D -->|envía| E[WhatsApp / Gmail]
    D -->|POST /notificaciones/id/estado| F[estado=ENTREGADO<br/>→ afectado NOTIFICADO]
    E --> G[Proveedor responde / firma]
    G -->|POST /firmas| H[firma INICIADA + token]
    H -->|POST /firmas/id/evento FIRMADA| I[afectado.firmado_proveedor=TRUE<br/>contrato firmado]
```

