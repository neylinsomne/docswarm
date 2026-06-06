-- =============================================================================
-- V4 · Catálogo maestro de Bayern (la "granbase")
-- -----------------------------------------------------------------------------
-- Bayern mantiene cláusulas y precios maestros versionados. Cuando cambian, el
-- cambio se registra (V5) y se calcula qué contratos de proveedores quedan
-- afectados. Estas tablas son GLOBALES (propiedad de Bayern, sin RLS por
-- tenant); los proveedores solo las ven indirectamente a través de los
-- documentos afectados (V5).
-- =============================================================================

CREATE TABLE clausulas_maestras (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo            TEXT NOT NULL UNIQUE,        -- 'CL-CALIDAD-001'
    tipo              TEXT NOT NULL
                          CHECK (tipo IN ('ENTREGA','CALIDAD','PAGO','PENALIZACION',
                                          'CONFIDENCIALIDAD','GENERAL')),
    titulo            TEXT NOT NULL,
    contenido_actual  TEXT NOT NULL,
    version           INTEGER NOT NULL DEFAULT 1,
    sector            TEXT,                        -- alcance opcional por sector
    nicho             TEXT,
    vigente           BOOLEAN NOT NULL DEFAULT TRUE,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE clausulas_maestras IS 'Cláusulas maestras versionadas de Bayern (global, sin RLS).';
CREATE INDEX idx_clmaestra_tipo   ON clausulas_maestras (tipo);
CREATE INDEX idx_clmaestra_sector ON clausulas_maestras (sector, nicho);

CREATE TRIGGER trg_clmaestra_touch
    BEFORE UPDATE ON clausulas_maestras
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- -----------------------------------------------------------------------------
-- Precios maestros (lista de precios por producto/categoría).
-- -----------------------------------------------------------------------------
CREATE TABLE precios_maestros (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo            TEXT NOT NULL UNIQUE,        -- 'PR-MAIZ-AMARILLO'
    producto          TEXT NOT NULL,
    categoria         TEXT,                        -- p.ej. UNSPSC / familia
    precio            NUMERIC(18,4) NOT NULL,
    moneda            TEXT NOT NULL DEFAULT 'COP',
    unidad            TEXT,                        -- 'ton', 'kg', 'unidad'
    version           INTEGER NOT NULL DEFAULT 1,
    vigente_desde     DATE NOT NULL DEFAULT CURRENT_DATE,
    vigente           BOOLEAN NOT NULL DEFAULT TRUE,
    sector            TEXT,
    nicho             TEXT,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE precios_maestros IS 'Lista de precios maestra de Bayern (global, sin RLS).';
CREATE INDEX idx_prmaestro_producto ON precios_maestros (producto);
CREATE INDEX idx_prmaestro_categoria ON precios_maestros (categoria);

CREATE TRIGGER trg_prmaestro_touch
    BEFORE UPDATE ON precios_maestros
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- -----------------------------------------------------------------------------
-- Ahora sí, enlazar contrato_clausulas (V3) con los ítems maestros (FKs).
-- -----------------------------------------------------------------------------
ALTER TABLE contrato_clausulas
    ADD CONSTRAINT fk_clausula_maestra
        FOREIGN KEY (clausula_maestra_id) REFERENCES clausulas_maestras(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_precio_maestro
        FOREIGN KEY (precio_maestro_id)   REFERENCES precios_maestros(id)   ON DELETE SET NULL;
