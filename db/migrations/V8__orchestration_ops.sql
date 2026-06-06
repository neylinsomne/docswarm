-- =============================================================================
-- V8 · Orquestación / operaciones
-- -----------------------------------------------------------------------------
--  · acp_runs            → dataset (no log) de cada ejecución de agente (SFT/eval)
--  · scrape_jobs         → cola durable Postgres (FOR UPDATE SKIP LOCKED)
--  · service_heartbeats  → liveness por servicio (worker/scheduler/api)
--  · audit_metrics       → resultados de auditorías → dashboards
-- =============================================================================

CREATE TABLE acp_runs (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        UUID NOT NULL DEFAULT uuid_generate_v4(),
    agent_name    TEXT NOT NULL,
    section_id    TEXT,
    status        TEXT NOT NULL,                   -- 'completed'|'failed'
    empresa_id    BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    contrato_id   BIGINT REFERENCES contratos(id) ON DELETE SET NULL,
    input         JSONB,                           -- NO truncado (es dataset)
    output        JSONB,
    trajectory    JSONB,
    citations     JSONB,
    error         JSONB,
    latency_ms    INTEGER,
    cache_key     TEXT,                            -- SHA-256 (reuso de resultados)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE acp_runs IS 'Dataset de ejecuciones de agentes (SFT+eval), no un log; sin truncar.';
CREATE INDEX idx_acpruns_agent  ON acp_runs (agent_name);
CREATE INDEX idx_acpruns_cache  ON acp_runs (cache_key);
CREATE INDEX idx_acpruns_empresa ON acp_runs (empresa_id);

-- cola durable: FOR UPDATE SKIP LOCKED
CREATE TABLE scrape_jobs (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_type      TEXT NOT NULL,                   -- 'ingest_doc','propagar_cambio',...
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    dedup_key     TEXT UNIQUE,                     -- idempotencia global
    status        TEXT NOT NULL DEFAULT 'queued'
                      CHECK (status IN ('queued','running','deferred','done','dead')),
    priority      INTEGER NOT NULL DEFAULT 100,
    attempts      INTEGER NOT NULL DEFAULT 0,
    run_after     TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_by     TEXT,
    heartbeat_at  TIMESTAMPTZ,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- índice parcial que dirige el claim de la cola
CREATE INDEX idx_jobs_claim ON scrape_jobs (priority, run_after)
    WHERE status IN ('queued','deferred');
CREATE TRIGGER trg_jobs_touch
    BEFORE UPDATE ON scrape_jobs
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE TABLE service_heartbeats (
    service     TEXT PRIMARY KEY,                  -- 'worker','scheduler','api'
    instance_id TEXT,
    status      TEXT,
    detail      JSONB,
    beat_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_metrics (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric      TEXT NOT NULL,
    valor       NUMERIC,
    labels      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_metric ON audit_metrics (metric, created_at DESC);
