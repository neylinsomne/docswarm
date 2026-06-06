-- =============================================================================
-- V6 · Log de cambios maestros + documentos afectados  ★ feature central ★
-- -----------------------------------------------------------------------------
-- Cuando Bayern cambia una cláusula o un precio maestro:
--   1. se inserta una fila en `cambios_maestros` (qué cambió, antes/después,
--      quién y cuándo, versiones).
--   2. se calcula qué contratos/documentos de proveedores quedan afectados y se
--      inserta una fila por cada uno en `cambios_documentos_afectados`, con un
--      BOOLEANO `firmado_proveedor` que rectifica si esa empresa proveedora ya
--      firmó la actualización.
-- Esto da el tablero "este cambio afectó N documentos; M ya firmados".
-- =============================================================================

CREATE TABLE cambios_maestros (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_objeto       TEXT NOT NULL CHECK (tipo_objeto IN ('CLAUSULA','PRECIO')),
    -- exactamente una de las dos FKs apunta al ítem maestro cambiado
    clausula_maestra_id BIGINT REFERENCES clausulas_maestras(id) ON DELETE CASCADE,
    precio_maestro_id   BIGINT REFERENCES precios_maestros(id)   ON DELETE CASCADE,
    accion            TEXT NOT NULL DEFAULT 'ACTUALIZACION'
                          CHECK (accion IN ('CREACION','ACTUALIZACION','DEROGACION')),
    descripcion       TEXT,
    version_anterior  INTEGER,
    version_nueva     INTEGER,
    valor_anterior    JSONB,                       -- snapshot previo (contenido/precio)
    valor_nuevo       JSONB,                       -- snapshot nuevo
    realizado_por     BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,  -- usuario Bayern
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- garantiza coherencia: el tipo casa con la FK rellenada
    CONSTRAINT chk_objeto_coherente CHECK (
        (tipo_objeto = 'CLAUSULA' AND clausula_maestra_id IS NOT NULL AND precio_maestro_id IS NULL)
     OR (tipo_objeto = 'PRECIO'   AND precio_maestro_id  IS NOT NULL AND clausula_maestra_id IS NULL)
    )
);
COMMENT ON TABLE cambios_maestros IS
    'Log: un cambio sobre una cláusula o precio maestro de Bayern (versionado, antes/después).';
CREATE INDEX idx_cambios_tipo     ON cambios_maestros (tipo_objeto);
CREATE INDEX idx_cambios_clausula ON cambios_maestros (clausula_maestra_id);
CREATE INDEX idx_cambios_precio   ON cambios_maestros (precio_maestro_id);
CREATE INDEX idx_cambios_fecha    ON cambios_maestros (created_at DESC);

-- -----------------------------------------------------------------------------
-- Documentos/contratos afectados por un cambio + estado de firma del proveedor.
-- Una fila por (cambio, contrato afectado). El booleano `firmado_proveedor`
-- responde literalmente "¿la empresa proveedora ya firmó?".
-- -----------------------------------------------------------------------------
CREATE TABLE cambios_documentos_afectados (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cambio_id            BIGINT NOT NULL REFERENCES cambios_maestros(id) ON DELETE CASCADE,
    contrato_id          BIGINT NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    -- tenant del proveedor afectado (denormalizado para RLS directo y dashboards)
    empresa_proveedor_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    clausula_contrato_id BIGINT REFERENCES contrato_clausulas(id) ON DELETE SET NULL,
    raw_document_id      BIGINT REFERENCES raw_documents(id) ON DELETE SET NULL,
    estado_propagacion   TEXT NOT NULL DEFAULT 'PENDIENTE'
                             CHECK (estado_propagacion IN ('PENDIENTE','NOTIFICADO',
                                                           'APLICADO','RECHAZADO')),
    -- ★ ¿el proveedor ya firmó la actualización derivada de este cambio?
    firmado_proveedor    BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_firma          TIMESTAMPTZ,
    firmado_por          BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    notificado_at        TIMESTAMPTZ,
    observaciones        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (cambio_id, contrato_id)
);
COMMENT ON TABLE cambios_documentos_afectados IS
    'Por cambio maestro: contratos/documentos afectados + si el proveedor ya firmó.';
COMMENT ON COLUMN cambios_documentos_afectados.firmado_proveedor IS
    'Rectifica si la empresa proveedora ya firmó la actualización de este cambio.';
CREATE INDEX idx_cda_cambio    ON cambios_documentos_afectados (cambio_id);
CREATE INDEX idx_cda_contrato  ON cambios_documentos_afectados (contrato_id);
CREATE INDEX idx_cda_proveedor ON cambios_documentos_afectados (empresa_proveedor_id);
CREATE INDEX idx_cda_estado    ON cambios_documentos_afectados (estado_propagacion);
CREATE INDEX idx_cda_pendiente_firma
    ON cambios_documentos_afectados (cambio_id) WHERE firmado_proveedor = FALSE;
