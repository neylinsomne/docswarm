-- =============================================================================
-- V9 · Row-Level Security + GRANTs
-- -----------------------------------------------------------------------------
-- Patrón: la app fija `app.current_empresa_id` por sesión.
--   NULL  → Bayern/admin/background → ve todo.
--   valor → proveedor → solo lo suyo.
-- RLS solo surte efecto si la app conecta como docswarm_app (NOSUPERUSER
-- NOBYPASSRLS). Conectar como owner/superuser desactiva todo en silencio.
-- =============================================================================

-- --- empresas: el proveedor ve su propia ficha + la del comprador (Bayern) ----
ALTER TABLE empresas ENABLE ROW LEVEL SECURITY;
ALTER TABLE empresas FORCE ROW LEVEL SECURITY;
CREATE POLICY empresas_tenant ON empresas
    USING (app_current_empresa_id() IS NULL
           OR id = app_current_empresa_id()
           OR tipo = 'COMPRADOR')
    WITH CHECK (app_current_empresa_id() IS NULL
                OR id = app_current_empresa_id());

-- --- empresa_caracteristicas (child de empresas) ------------------------------
ALTER TABLE empresa_caracteristicas ENABLE ROW LEVEL SECURITY;
ALTER TABLE empresa_caracteristicas FORCE ROW LEVEL SECURITY;
CREATE POLICY empcar_tenant ON empresa_caracteristicas
    USING (app_current_empresa_id() IS NULL
           OR empresa_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL
                OR empresa_id = app_current_empresa_id());

-- --- usuarios -----------------------------------------------------------------
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios FORCE ROW LEVEL SECURITY;
CREATE POLICY usuarios_tenant ON usuarios
    USING (app_current_empresa_id() IS NULL
           OR empresa_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL
                OR empresa_id = app_current_empresa_id());

-- --- contratos: el proveedor ve los contratos donde es proveedor --------------
ALTER TABLE contratos ENABLE ROW LEVEL SECURITY;
ALTER TABLE contratos FORCE ROW LEVEL SECURITY;
CREATE POLICY contratos_tenant ON contratos
    USING (app_current_empresa_id() IS NULL
           OR empresa_proveedor_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL
                OR empresa_proveedor_id = app_current_empresa_id());

-- --- contrato_clausulas (child de contratos, join al padre) -------------------
ALTER TABLE contrato_clausulas ENABLE ROW LEVEL SECURITY;
ALTER TABLE contrato_clausulas FORCE ROW LEVEL SECURITY;
CREATE POLICY clausulas_tenant ON contrato_clausulas
    USING (app_current_empresa_id() IS NULL OR EXISTS (
        SELECT 1 FROM contratos c
        WHERE c.id = contrato_clausulas.contrato_id
          AND c.empresa_proveedor_id = app_current_empresa_id()))
    WITH CHECK (app_current_empresa_id() IS NULL OR EXISTS (
        SELECT 1 FROM contratos c
        WHERE c.id = contrato_clausulas.contrato_id
          AND c.empresa_proveedor_id = app_current_empresa_id()));

-- --- raw_documents: tenant propio o global (NULL) -----------------------------
ALTER TABLE raw_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_documents FORCE ROW LEVEL SECURITY;
CREATE POLICY rawdocs_tenant ON raw_documents
    USING (app_current_empresa_id() IS NULL
           OR tenant_id IS NULL
           OR tenant_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL
                OR tenant_id = app_current_empresa_id());

-- --- parsed_documents (child de raw_documents) --------------------------------
ALTER TABLE parsed_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE parsed_documents FORCE ROW LEVEL SECURITY;
CREATE POLICY parsed_tenant ON parsed_documents
    USING (app_current_empresa_id() IS NULL OR EXISTS (
        SELECT 1 FROM raw_documents r
        WHERE r.id = parsed_documents.raw_document_id
          AND (r.tenant_id IS NULL OR r.tenant_id = app_current_empresa_id())));

-- --- document_chunks: tenant propio o global ----------------------------------
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks FORCE ROW LEVEL SECURITY;
CREATE POLICY chunks_tenant ON document_chunks
    USING (app_current_empresa_id() IS NULL
           OR tenant_id IS NULL
           OR tenant_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL
                OR tenant_id = app_current_empresa_id());

-- --- cambios_documentos_afectados: el proveedor ve solo lo que le afecta ------
ALTER TABLE cambios_documentos_afectados ENABLE ROW LEVEL SECURITY;
ALTER TABLE cambios_documentos_afectados FORCE ROW LEVEL SECURITY;
CREATE POLICY cda_tenant ON cambios_documentos_afectados
    USING (app_current_empresa_id() IS NULL
           OR empresa_proveedor_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL
                OR empresa_proveedor_id = app_current_empresa_id());

-- --- kg_validaciones ----------------------------------------------------------
ALTER TABLE kg_validaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE kg_validaciones FORCE ROW LEVEL SECURITY;
CREATE POLICY kgval_tenant ON kg_validaciones
    USING (app_current_empresa_id() IS NULL
           OR empresa_id IS NULL
           OR empresa_id = app_current_empresa_id());

-- -----------------------------------------------------------------------------
-- Intencionalmente GLOBALES (sin RLS): clausulas_maestras, precios_maestros,
-- cambios_maestros, document_links, ingest_jobs, kg_entidades, kg_aristas,
-- acp_runs, scrape_jobs, service_heartbeats, audit_metrics.
-- (Bayern las posee; los proveedores solo ven sus efectos vía las tablas RLS.)
-- -----------------------------------------------------------------------------

-- --- GRANTs sobre las tablas ya existentes ------------------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO docswarm_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO docswarm_app;
GRANT EXECUTE ON FUNCTION app_current_empresa_id() TO docswarm_app;
