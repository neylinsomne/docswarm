-- =============================================================================
-- V7 · Grafo de conocimiento (entidades + aristas + validaciones)
-- -----------------------------------------------------------------------------
-- Modela relaciones verificables entre entidades extraídas de contratos y del
-- catálogo maestro (p.ej. CONTRATO --INCLUYE--> CLAUSULA --DERIVA_DE-->
-- CLAUSULA_MAESTRA). Permite trazar cadenas de evidencia y, a futuro, que un
-- agente (p.ej. WhatsApp) responda "qué contratos referencian la cláusula X".
-- Tablas GLOBALES (sin RLS); el filtrado por tenant se hace en la consulta.
-- =============================================================================

CREATE TABLE kg_entidades (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo          TEXT NOT NULL
                      CHECK (tipo IN ('EMPRESA','CONTRATO','CLAUSULA','PRECIO',
                                      'PRODUCTO','NORMA_LEGAL','SECTOR','PERSONA')),
    nombre        TEXT NOT NULL,
    -- vínculo de regreso a la fila fuente
    source_type   TEXT,                            -- 'CONTRATO','CLAUSULA_MAESTRA',...
    source_id     BIGINT,                          -- PK en esa tabla
    embedding_vec vector(1024),
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_kgent_tipo       ON kg_entidades (tipo);
CREATE INDEX idx_kgent_source     ON kg_entidades (source_type, source_id);
CREATE INDEX idx_kgent_nombre_trgm ON kg_entidades USING gin (nombre gin_trgm_ops);
CREATE INDEX idx_kgent_vec        ON kg_entidades
    USING ivfflat (embedding_vec vector_cosine_ops) WITH (lists = 100);

CREATE TABLE kg_aristas (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id   BIGINT NOT NULL REFERENCES kg_entidades(id) ON DELETE CASCADE,
    target_id   BIGINT NOT NULL REFERENCES kg_entidades(id) ON DELETE CASCADE,
    relacion    TEXT NOT NULL
                    CHECK (relacion IN ('INCLUYE','DERIVA_DE','SUMINISTRA',
                                        'AFECTA','FUNDAMENTA','PERTENECE_A',
                                        'REFERENCIA')),
    peso        NUMERIC NOT NULL DEFAULT 1.0,      -- confianza de la relación
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, target_id, relacion)
);
CREATE INDEX idx_kgar_source ON kg_aristas (source_id, relacion);
CREATE INDEX idx_kgar_target ON kg_aristas (target_id, relacion);

-- cadenas de validación: una afirmación → ruta de evidencia → estado
CREATE TABLE kg_validaciones (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    afirmacion   TEXT NOT NULL,
    ruta         JSONB,                            -- secuencia de entidades/aristas
    confianza    NUMERIC,                          -- producto de pesos de la ruta
    estado       TEXT CHECK (estado IN ('VALIDADO','PARCIAL','INVALIDO')),
    empresa_id   BIGINT REFERENCES empresas(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_kgval_empresa ON kg_validaciones (empresa_id);
