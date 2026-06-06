-- =============================================================================
-- V2 · Núcleo multi-tenant: empresas + usuarios + helper RLS
-- -----------------------------------------------------------------------------
-- `empresas` es la raíz tenant: su `id` es el `empresa_id` que circula por todo
-- el sistema. Bayern es la única empresa tipo COMPRADOR (admin); el resto son
-- PROVEEDOR. La función app_current_empresa_id() lee el GUC de sesión que la
-- app fija en cada conexión (ver V10 para las políticas RLS que la usan).
-- =============================================================================

CREATE TABLE empresas (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo            TEXT NOT NULL DEFAULT 'PROVEEDOR'
                        CHECK (tipo IN ('COMPRADOR', 'PROVEEDOR')),
    nombre          TEXT NOT NULL,
    nit             TEXT UNIQUE,                  -- identificación tributaria
    -- Metadata de negocio para búsqueda y filtrado (nicho agro, sector, etc.).
    -- Los campos "duros" más consultados se materializan como columnas (L1),
    -- el resto vive en JSONB (con índice GIN) para filtrado flexible y rico.
    sector          TEXT,                         -- p.ej. 'agro', 'logistica'
    nicho           TEXT,                         -- p.ej. 'alimentos', 'semillas'
    pais            TEXT DEFAULT 'CO',
    ciudad          TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,  -- atributos flexibles
    perfil_vec      vector(1024),                 -- embedding del perfil (búsqueda por similitud)
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  empresas IS 'Raíz tenant. Bayern=COMPRADOR (admin), resto=PROVEEDOR.';
COMMENT ON COLUMN empresas.metadata IS 'Atributos de negocio flexibles para filtrado facetado.';
COMMENT ON COLUMN empresas.perfil_vec IS 'Embedding BGE-M3 del perfil; búsqueda de empresas por similitud.';

CREATE INDEX idx_empresas_tipo        ON empresas (tipo);
CREATE INDEX idx_empresas_sector      ON empresas (sector);
CREATE INDEX idx_empresas_nicho       ON empresas (nicho);
CREATE INDEX idx_empresas_nombre_trgm ON empresas USING gin (nombre gin_trgm_ops);
CREATE INDEX idx_empresas_metadata    ON empresas USING gin (metadata jsonb_path_ops);
-- Índice vectorial: se reconstruye tras carga masiva + ANALYZE (entrena centroides).
CREATE INDEX idx_empresas_perfil_vec  ON empresas
    USING ivfflat (perfil_vec vector_cosine_ops) WITH (lists = 50);

-- -----------------------------------------------------------------------------
-- Características facetadas de la empresa (filtrado tipo facetas / sidebar).
-- Una fila por (empresa, clave) permite consultas como
--   "proveedores con certificacion=ISO9001 AND capacidad>=1000ton".
-- -----------------------------------------------------------------------------
CREATE TABLE empresa_caracteristicas (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    empresa_id  BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    clave       TEXT NOT NULL,                    -- 'certificacion', 'capacidad_ton'
    valor       TEXT NOT NULL,                    -- 'ISO9001', '1500'
    valor_num   NUMERIC,                          -- forma numérica (rangos), opcional
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, clave, valor)
);
CREATE INDEX idx_empcar_empresa ON empresa_caracteristicas (empresa_id);
CREATE INDEX idx_empcar_clave   ON empresa_caracteristicas (clave, valor);

-- -----------------------------------------------------------------------------
-- Usuarios: cada empresa (proveedor o Bayern) tiene su propio login.
-- -----------------------------------------------------------------------------
CREATE TABLE usuarios (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    empresa_id      BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    nombre          TEXT,
    rol             TEXT NOT NULL DEFAULT 'MIEMBRO'
                        CHECK (rol IN ('ADMIN', 'GESTOR', 'MIEMBRO')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_login    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_usuarios_empresa ON usuarios (empresa_id);

-- -----------------------------------------------------------------------------
-- Helper RLS: lee el GUC de sesión `app.current_empresa_id`.
--   NULL  → admin / proceso de fondo (ve todo)
--   valor → tenant proveedor (solo lo suyo)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION app_current_empresa_id()
RETURNS BIGINT
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
    SELECT NULLIF(current_setting('app.current_empresa_id', true), '')::bigint;
$$;

COMMENT ON FUNCTION app_current_empresa_id() IS
    'Tenant de la sesión (GUC app.current_empresa_id). NULL = admin/Bayern = ve todo.';

-- trigger genérico para updated_at
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END
$$;

CREATE TRIGGER trg_empresas_touch
    BEFORE UPDATE ON empresas
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
