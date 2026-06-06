-- =============================================================================
-- V3 · Contratos y sus cláusulas
-- -----------------------------------------------------------------------------
-- Un contrato vincula a Bayern (comprador) con un proveedor. Es la entidad
-- tenant-scoped por excelencia: un proveedor solo ve SUS contratos (RLS por
-- `empresa_proveedor_id`). Las cláusulas del contrato pueden derivar de una
-- cláusula/precio maestro de Bayern (ver V4); ese vínculo es lo que permite
-- propagar cambios y registrar qué documentos se ven afectados (V5).
-- =============================================================================

CREATE TABLE contratos (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- tenant: el proveedor dueño de la vista. Bayern (admin) ve todos.
    empresa_proveedor_id    BIGINT NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    empresa_compradora_id   BIGINT NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    numero                  TEXT,                 -- número/código de contrato
    titulo                  TEXT NOT NULL,
    objeto                  TEXT,                 -- objeto del contrato (texto libre)
    sector                  TEXT,                 -- 'agro', etc. (heredado/override)
    estado                  TEXT NOT NULL DEFAULT 'BORRADOR'
                                CHECK (estado IN ('BORRADOR','VIGENTE','SUSPENDIDO',
                                                  'VENCIDO','TERMINADO')),
    valor                   NUMERIC(18,2),
    moneda                  TEXT DEFAULT 'COP',
    fecha_inicio            DATE,
    fecha_fin               DATE,
    -- Estado de firma del contrato vigente por parte del proveedor.
    firmado_proveedor       BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_firma             TIMESTAMPTZ,
    metadata                JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Embedding del contenido del contrato para búsqueda semántica de alto nivel.
    -- (El detalle granular se vectoriza en document_chunks, V6.)
    contenido_vec           vector(1024),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_partes_distintas CHECK (empresa_proveedor_id <> empresa_compradora_id)
);

COMMENT ON TABLE  contratos IS 'Contrato Bayern↔proveedor. Tenant = empresa_proveedor_id.';
COMMENT ON COLUMN contratos.firmado_proveedor IS 'Si el proveedor firmó la versión vigente del contrato.';

CREATE INDEX idx_contratos_proveedor  ON contratos (empresa_proveedor_id);
CREATE INDEX idx_contratos_comprador  ON contratos (empresa_compradora_id);
CREATE INDEX idx_contratos_estado     ON contratos (estado);
CREATE INDEX idx_contratos_sector     ON contratos (sector);
CREATE INDEX idx_contratos_titulo_trgm ON contratos USING gin (titulo gin_trgm_ops);
CREATE INDEX idx_contratos_metadata   ON contratos USING gin (metadata jsonb_path_ops);
CREATE INDEX idx_contratos_vec        ON contratos
    USING ivfflat (contenido_vec vector_cosine_ops) WITH (lists = 100);

CREATE TRIGGER trg_contratos_touch
    BEFORE UPDATE ON contratos
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- -----------------------------------------------------------------------------
-- Cláusulas concretas dentro de un contrato.
-- `clausula_maestra_id` / `precio_maestro_id` (FK a V4) marcan de qué ítem
-- maestro de Bayern proviene la cláusula → permite detectar contratos afectados
-- cuando Bayern cambia ese ítem.
-- -----------------------------------------------------------------------------
CREATE TABLE contrato_clausulas (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contrato_id          BIGINT NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    tipo                 TEXT NOT NULL
                             CHECK (tipo IN ('PRECIO','ENTREGA','CALIDAD','PAGO',
                                             'PENALIZACION','CONFIDENCIALIDAD',
                                             'GENERAL')),
    titulo               TEXT,
    contenido            TEXT NOT NULL,
    orden                INTEGER NOT NULL DEFAULT 0,
    version              INTEGER NOT NULL DEFAULT 1,
    -- procedencia del ítem maestro (se rellenan en V4 con las FKs reales)
    clausula_maestra_id  BIGINT,
    precio_maestro_id    BIGINT,
    valor                NUMERIC(18,2),           -- para cláusulas de precio
    metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_clausulas_contrato  ON contrato_clausulas (contrato_id);
CREATE INDEX idx_clausulas_tipo      ON contrato_clausulas (tipo);
CREATE INDEX idx_clausulas_maestra   ON contrato_clausulas (clausula_maestra_id);
CREATE INDEX idx_clausulas_precio    ON contrato_clausulas (precio_maestro_id);
