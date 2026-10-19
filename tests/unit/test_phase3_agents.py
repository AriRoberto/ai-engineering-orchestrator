from ai_engineering.agents.phase3 import (
    DatabaseAgent,
    DocumentationAgent,
    QAAgent,
    SecurityAgent,
)
from ai_engineering.domain.models import AgentKind, TaskRequest


def request(files: list[str]) -> TaskRequest:
    return TaskRequest(
        project_id="demo-project",
        prompt="Diagnóstico especializado",
        demo=True,
        context={"files": files},
    )


def test_database_agent_reports_migrations_and_sql_evidence() -> None:
    result = DatabaseAgent().execute(
        request(["migrations/001_schema.sql", "src/application.py"])
    )
    assert result.agent == AgentKind.DATABASE
    assert result.evidence == ["migrations/001_schema.sql"]
    assert "Migrações versionadas" in result.findings[1]


def test_qa_agent_correlates_tests_and_ci() -> None:
    result = QAAgent().execute(
        request(["tests/unit/test_service.py", ".github/workflows/ci.yml"])
    )
    assert result.agent == AgentKind.QA
    assert len(result.evidence) == 2
    assert "automação de CI" in result.findings[1]


def test_security_agent_flags_only_sensitive_file_names() -> None:
    result = SecurityAgent().execute(request(["SECURITY.md", ".gitignore", ".env"]))
    assert result.agent == AgentKind.SECURITY
    assert ".env" in result.evidence
    assert "Revisão necessária" in result.findings[1]


def test_documentation_agent_reports_missing_essential_documents() -> None:
    result = DocumentationAgent().execute(request(["README.md", "docs/architecture.md"]))
    assert result.agent == AgentKind.DOCUMENTATION
    assert "CHANGELOG.md" in result.findings[1]
    assert "SECURITY.md" in result.findings[1]
