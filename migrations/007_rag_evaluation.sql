CREATE TABLE IF NOT EXISTS rag_evaluation_runs (
    id UUID PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_rag_evaluation_runs_project
    ON rag_evaluation_runs (project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS rag_retrieval_feedback (
    id UUID PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    evaluation_id UUID NOT NULL REFERENCES rag_evaluation_runs(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL,
    relevance VARCHAR(20) NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (evaluation_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS ix_rag_retrieval_feedback_project
    ON rag_retrieval_feedback (project_id, created_at DESC);
