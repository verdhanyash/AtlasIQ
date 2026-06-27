-- AtlasIQ PostgreSQL Schema
-- This schema is executed on first startup via Docker entrypoint.
-- Tables are organized by domain: documents, queries, analytics, evaluation.

-- ═══════════════════════════════════════════════════════════════════════════
-- DOCUMENTS DOMAIN
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    title           TEXT,
    author          TEXT,
    page_count      INTEGER,
    word_count      INTEGER,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingested_at     TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

CREATE TABLE IF NOT EXISTS chunks (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    token_count     INTEGER,
    start_page      INTEGER,
    end_page        INTEGER,
    metadata_json   JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_chunk_per_doc UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- QUERY DOMAIN
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS query_history (
    id              TEXT PRIMARY KEY,
    question        TEXT NOT NULL,
    answer          TEXT,
    confidence      REAL,
    latency_ms      INTEGER,
    llm_provider    TEXT,
    llm_model       TEXT,
    chunks_retrieved INTEGER,
    chunks_after_rerank INTEGER,
    sources_json    JSONB DEFAULT '[]',
    cached          BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- EVALUATION DOMAIN
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS eval_results (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    metric_name     TEXT NOT NULL,
    metric_value    REAL NOT NULL,
    k_value         INTEGER,
    config_json     JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_results_run_id ON eval_results(run_id);
