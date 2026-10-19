CREATE TABLE IF NOT EXISTS evidence_access_audits (
    id UUID PRIMARY KEY,
    project_id VARCHAR(63) NOT NULL,
    status VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_evidence_access_audits_project
    ON evidence_access_audits (project_id);
CREATE INDEX IF NOT EXISTS ix_evidence_access_audits_status
    ON evidence_access_audits (status);
CREATE INDEX IF NOT EXISTS ix_evidence_access_audits_created_at
    ON evidence_access_audits (created_at);
