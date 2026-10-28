ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS collection VARCHAR(63);
ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS provenance JSONB;
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS start_line INTEGER;
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS end_line INTEGER;

CREATE INDEX IF NOT EXISTS ix_knowledge_documents_collection
    ON knowledge_documents (project_id, collection);
