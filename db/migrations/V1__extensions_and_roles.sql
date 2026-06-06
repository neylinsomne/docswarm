-- =============================================================================
-- V1 · Extensiones + rol de aplicación
-- -----------------------------------------------------------------------------
-- Base de datos: gestión documental B2B de contratos.
--   · Comprador / "granbase":  Bayern  (tenant administrador, ve todo)
--   · Proveedores:             empresas que suplen servicios/productos a Bayern,
--                              cada una con su propio usuario y aislada por RLS.
--
-- Toda columna vectorial es vector(1024) (BGE-M3) con ivfflat + vector_cosine_ops
-- (distancia coseno, operador <=>). pg_trgm habilita búsqueda por nombre (trigram).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector: búsqueda semántica
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- búsqueda por nombre (GIN trigram)

-- -----------------------------------------------------------------------------
-- Rol de aplicación (load-bearing para RLS).
--
-- RLS SOLO surte efecto si el rol con el que conecta la app es
-- NOSUPERUSER NOBYPASSRLS. Conectar como superusuario/owner DESACTIVA en
-- silencio todas las políticas. Este bloque crea el rol de forma idempotente;
-- la contraseña real se asigna fuera de la migración (variable de entorno).
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'docswarm_app') THEN
        CREATE ROLE docswarm_app LOGIN
            NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE
            PASSWORD 'change_me_in_env';
    END IF;
END
$$;

-- Permisos mínimos sobre el esquema público (las tablas se crean en migraciones
-- siguientes; los GRANT por tabla viven al final, en V11).
GRANT USAGE ON SCHEMA public TO docswarm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO docswarm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO docswarm_app;
