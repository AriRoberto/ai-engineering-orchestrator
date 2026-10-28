ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS embedding_key VARCHAR(200)
    NOT NULL DEFAULT 'deterministic:deterministic-demo:1:16';

ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector USING embedding::vector;

CREATE INDEX IF NOT EXISTS ix_knowledge_documents_embedding
    ON knowledge_documents (project_id, embedding_key);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_code_text
    ON knowledge_chunks USING GIN (to_tsvector('simple', content));
