CREATE TABLE IF NOT EXISTS mcp_invocations (
    id UUID PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    status VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_mcp_invocations_project ON mcp_invocations (project_id);
CREATE INDEX IF NOT EXISTS ix_mcp_invocations_status ON mcp_invocations (status);
CREATE INDEX IF NOT EXISTS ix_mcp_invocations_created_at ON mcp_invocations (created_at);
