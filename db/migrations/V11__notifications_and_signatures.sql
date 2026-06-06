-- =============================================================================
-- V11 · Notificaciones (WhatsApp/Gmail) + firma electrónica
-- -----------------------------------------------------------------------------
-- Subsistema de comunicación del flujo cambio → notifica → firma:
--   · `notificaciones`: un mensaje por canal (WhatsApp/Gmail) dirigido a un
--      usuario de la empresa proveedora. Estado de entrega (PENDIENTE→ENVIADO→
--      ENTREGADO→LEIDO/FALLIDO). El microservicio externo (otro repo) consume las
--      pendientes y reporta el estado por callback; al entregarse marca el
--      documento afectado como NOTIFICADO.
--   · `firmas`: proceso de firma electrónica ("firma inteligente"), que ocurre
--      por el mismo medio de comunicación. Al quedar FIRMADA marca el booleano
--      `firmado_proveedor` del documento afectado (y del contrato).
-- Ambas son tenant-scoped por `empresa_id` (RLS).
-- =============================================================================

CREATE TABLE notificaciones (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canal               TEXT NOT NULL CHECK (canal IN ('WHATSAPP','GMAIL','SISTEMA')),
    tipo                TEXT NOT NULL DEFAULT 'CAMBIO'
                            CHECK (tipo IN ('CAMBIO','RECORDATORIO','FIRMA','GENERAL')),
    -- destino del mensaje: empresa (tenant) + usuario concreto (admin o normal)
    empresa_id          BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    usuario_id          BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    -- a qué se refiere: documento afectado por un cambio + su contrato/cambio
    afectado_id         BIGINT REFERENCES cambios_documentos_afectados(id) ON DELETE CASCADE,
    contrato_id         BIGINT REFERENCES contratos(id) ON DELETE CASCADE,
    cambio_id           BIGINT REFERENCES cambios_maestros(id) ON DELETE SET NULL,
    -- dirección concreta (teléfono/email) denormalizada para el sender externo
    destino             TEXT,
    asunto              TEXT,
    mensaje             TEXT,
    estado              TEXT NOT NULL DEFAULT 'PENDIENTE'
                            CHECK (estado IN ('PENDIENTE','ENVIADO','ENTREGADO',
                                              'LEIDO','FALLIDO')),
    referencia_externa  TEXT,                    -- id del mensaje en WhatsApp/Gmail
    intentos            INTEGER NOT NULL DEFAULT 0,
    enviado_at          TIMESTAMPTZ,
    entregado_at        TIMESTAMPTZ,
    leido_at            TIMESTAMPTZ,
    error               TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE notificaciones IS
    'Mensajes por WhatsApp/Gmail (cola pull para el microservicio externo + estado de entrega).';
CREATE INDEX idx_notif_empresa   ON notificaciones (empresa_id);
CREATE INDEX idx_notif_afectado  ON notificaciones (afectado_id);
CREATE INDEX idx_notif_contrato  ON notificaciones (contrato_id);
CREATE INDEX idx_notif_estado    ON notificaciones (estado);
-- cola: el sender externo reclama las pendientes por canal
CREATE INDEX idx_notif_pendientes ON notificaciones (canal, created_at)
    WHERE estado = 'PENDIENTE';

CREATE TRIGGER trg_notif_touch
    BEFORE UPDATE ON notificaciones
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- -----------------------------------------------------------------------------
-- Firma electrónica (firma inteligente) por el medio de comunicación.
-- -----------------------------------------------------------------------------
CREATE TABLE firmas (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    empresa_id          BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    contrato_id         BIGINT REFERENCES contratos(id) ON DELETE CASCADE,
    afectado_id         BIGINT REFERENCES cambios_documentos_afectados(id) ON DELETE CASCADE,
    usuario_id          BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,   -- quien firma
    notificacion_id     BIGINT REFERENCES notificaciones(id) ON DELETE SET NULL,
    canal               TEXT NOT NULL DEFAULT 'WHATSAPP'
                            CHECK (canal IN ('WHATSAPP','GMAIL','WEB')),
    estado              TEXT NOT NULL DEFAULT 'INICIADA'
                            CHECK (estado IN ('INICIADA','EN_PROCESO','FIRMADA',
                                              'RECHAZADA','EXPIRADA')),
    token               TEXT UNIQUE,             -- token del proceso de firma
    referencia_externa  TEXT,
    evidencia           JSONB NOT NULL DEFAULT '{}'::jsonb,  -- OTP, hash, IP, ts...
    firmado_at          TIMESTAMPTZ,
    expira_at           TIMESTAMPTZ,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE firmas IS
    'Proceso de firma electrónica (firma inteligente) ligado a un documento afectado/contrato.';
CREATE INDEX idx_firmas_empresa  ON firmas (empresa_id);
CREATE INDEX idx_firmas_afectado ON firmas (afectado_id);
CREATE INDEX idx_firmas_contrato ON firmas (contrato_id);
CREATE INDEX idx_firmas_estado   ON firmas (estado);

CREATE TRIGGER trg_firmas_touch
    BEFORE UPDATE ON firmas
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- -----------------------------------------------------------------------------
-- RLS: el proveedor ve solo sus notificaciones/firmas; Bayern (admin) ve todo.
-- -----------------------------------------------------------------------------
ALTER TABLE notificaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE notificaciones FORCE ROW LEVEL SECURITY;
CREATE POLICY notif_tenant ON notificaciones
    USING (app_current_empresa_id() IS NULL OR empresa_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL OR empresa_id = app_current_empresa_id());

ALTER TABLE firmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE firmas FORCE ROW LEVEL SECURITY;
CREATE POLICY firmas_tenant ON firmas
    USING (app_current_empresa_id() IS NULL OR empresa_id = app_current_empresa_id())
    WITH CHECK (app_current_empresa_id() IS NULL OR empresa_id = app_current_empresa_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON notificaciones, firmas TO docswarm_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO docswarm_app;
