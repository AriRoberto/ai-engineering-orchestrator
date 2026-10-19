CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    title VARCHAR(300) NOT NULL,
    source VARCHAR(2000) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    sharing_authorized BOOLEAN NOT NULL DEFAULT FALSE,
    chunk_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_knowledge_documents_project
    ON knowledge_documents (project_id);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    project_id VARCHAR(63) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    position INTEGER NOT NULL,
    embedding vector(16) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_project ON knowledge_chunks (project_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_document ON knowledge_chunks (document_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_text
    ON knowledge_chunks USING GIN (to_tsvector('portuguese', content));

CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    execution_id UUID NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL DEFAULT '',
    validated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_feedback_project ON feedback (project_id);
