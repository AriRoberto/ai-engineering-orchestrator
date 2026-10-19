from ai_engineering.evidence.audit import (
    EvidenceAccessAudit,
    EvidenceAccessStatus,
    EvidenceAuditRepository,
)


def test_in_memory_audit_is_isolated_by_project_and_newest_first() -> None:
    repository = EvidenceAuditRepository()
    first = EvidenceAccessAudit(
        project_id="project-a",
        status=EvidenceAccessStatus.DENIED,
        reason="Credencial indisponível",
    )
    second = EvidenceAccessAudit(
        project_id="project-a",
        status=EvidenceAccessStatus.COMPLETED,
        reason="Coleta concluída",
    )
    repository.add(first)
    repository.add(
        EvidenceAccessAudit(
            project_id="project-b",
            status=EvidenceAccessStatus.COMPLETED,
            reason="Outro projeto",
        )
    )
    repository.add(second)

    assert [item.id for item in repository.list("project-a")] == [second.id, first.id]
