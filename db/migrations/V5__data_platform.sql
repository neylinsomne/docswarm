-- =============================================================================
-- V5 · Data-platform canónica (ETL version-aware + pgvector)
-- -----------------------------------------------------------------------------
-- Las 5 tablas canónicas del ETL (la caja "data collection/verification" del
-- mapa de Sculley). Los bytes crudos viven en MinIO/S3; la BD guarda solo
-- minio_bucket/minio_key. `document_chunks` vectoriza el contenido para la
-- búsqueda por contenido del contrato. tenant_id (NULL=global) habilita RLS.
-- =============================================================================

CREATE TABLE raw_documents (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source          TEXT NOT NULL,                -- 'upload', 'whatsapp', 'api'
    source_id       TEXT,                         -- id en la fuente (único por versión)
    domain          TEXT NOT NULL DEFAULT 'contratos',
    titulo          TEXT,
    -- ubicación de los bytes crudos en object storage
    minio_bucket    TEXT,
    minio_key       TEXT,
    extension       TEXT,                         -- 'pdf','docx','xlsx',...
    bytes_len       BIGINT,
    -- tenant: el proveedor dueño del documento; NULL = global (Bayern/normas)
    tenant_id       BIGINT REFERENCES empresas(id) ON DELETE CASCADE,
    -- contrato asociado (un documento suele ser el PDF de un contrato)
    contrato_id     BIGINT REFERENCES contratos(id) ON DELETE SET NULL,
    -- version-awareness
    sha256          TEXT NOT NULL UNIQUE,         -- identidad de CONTENIDO
    logical_key     TEXT,                         -- identidad LÓGICA entre re-cargas
    version         INTEGER NOT NULL DEFAULT 1,
    supersedes_id   BIGINT REFERENCES raw_documents(id) ON DELETE SET NULL,
    is_current      BOOLEAN NOT NULL DEFAULT TRUE,
    lifecycle_stage TEXT DEFAULT 'vigente',
    parse_status    TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (parse_status IN ('PENDING','PARSING','INDEXED','ERROR')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE raw_documents IS 'Unidad mínima ingerida, version-aware. Bytes en MinIO; DB guarda keys.';
CREATE INDEX idx_rawdocs_tenant     ON raw_documents (tenant_id);
CREATE INDEX idx_rawdocs_contrato   ON raw_documents (contrato_id);
CREATE INDEX idx_rawdocs_logical    ON raw_documents (logical_key);
CREATE INDEX idx_rawdocs_status     ON raw_documents (parse_status) WHERE parse_status <> 'INDEXED';
CREATE INDEX idx_rawdocs_current    ON raw_documents (logical_key) WHERE is_current;

-- estructura extraída del documento
CREATE TABLE parsed_documents (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_document_id      BIGINT NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
    parser_name          TEXT,
    parser_version       TEXT,
    contenido_secciones  JSONB,                   -- {texto,chars,method,pages,tablas}
    entities_extracted   JSONB,
    parser_confidence    NUMERIC,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_parsed_raw       ON parsed_documents (raw_document_id);
CREATE INDEX idx_parsed_entities  ON parsed_documents USING gin (entities_extracted);

-- chunks vectorizados (búsqueda por contenido del contrato)
CREATE TABLE document_chunks (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_document_id  BIGINT NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
    tenant_id        BIGINT REFERENCES empresas(id) ON DELETE CASCADE,
    domain           TEXT NOT NULL DEFAULT 'contratos',
    seccion_hint     TEXT,                         -- p.ej. 'tabla'
    chunk_index      INTEGER NOT NULL,
    contenido        TEXT NOT NULL,
    embedding_vec    vector(1024),
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE document_chunks IS 'Chunks vectorizados del contenido; búsqueda semántica por contrato.';
CREATE INDEX idx_chunks_raw      ON document_chunks (raw_document_id);
CREATE INDEX idx_chunks_tenant   ON document_chunks (tenant_id);
CREATE INDEX idx_chunks_contenido_trgm ON document_chunks USING gin (contenido gin_trgm_ops);
CREATE INDEX idx_chunks_vec      ON document_chunks
    USING ivfflat (embedding_vec vector_cosine_ops) WITH (lists = 200);

-- relaciones inter-documento (cadenas de versión, adendas, etc.)
CREATE TABLE document_links (
    src_doc_id  BIGINT NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
    dst_doc_id  BIGINT NOT NULL REFERENCES raw_documents(id) ON DELETE CASCADE,
    link_type   TEXT NOT NULL
                    CHECK (link_type IN ('adenda_de','version_de','reemplaza_a',
                                         'similar_a','cita_norma','anexo_de')),
    score       NUMERIC,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (src_doc_id, dst_doc_id, link_type)
);

-- log auditable por paso del ETL (NO es la cola de trabajo, ver V8)
CREATE TABLE ingest_jobs (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_document_id  BIGINT REFERENCES raw_documents(id) ON DELETE CASCADE,
    step             TEXT NOT NULL
                         CHECK (step IN ('discover','fetch','parse','normalize',
                                         'embed','index','link','rescrape')),
    status           TEXT NOT NULL,
    attempt          INTEGER NOT NULL DEFAULT 1,
    latency_ms       INTEGER,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ingjobs_raw ON ingest_jobs (raw_document_id);
