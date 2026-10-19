CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    status VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_executions_project ON executions (project_id);
CREATE INDEX IF NOT EXISTS ix_executions_status ON executions (status);
CREATE INDEX IF NOT EXISTS ix_executions_updated_at ON executions (updated_at);
