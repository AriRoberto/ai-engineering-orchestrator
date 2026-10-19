from pathlib import Path

from ai_engineering.integrations.mcp.client import SimulatedProjectMCPClient
from ai_engineering.integrations.mcp.models import MCPInvocationRequest, MCPInvocationStatus
from ai_engineering.integrations.mcp.policy import MCPPolicyStore
from ai_engineering.integrations.mcp.repository import MCPAuditRepository
from ai_engineering.integrations.mcp.service import MCPGateway


def make_gateway(tmp_path: Path, mode: str = "read-write-demo") -> MCPGateway:
    (tmp_path / "project-one.yaml").write_text(
        "\n".join(
            [
                "id: project-one",
                f"mode: {mode}",
                "mcp:",
                "  allowed_tools:",
                "    - project-catalog:project_summary",
                "    - project-catalog:publish_change",
            ]
        ),
        encoding="utf-8",
    )
    return MCPGateway(
        [SimulatedProjectMCPClient()], MCPPolicyStore(str(tmp_path)), MCPAuditRepository()
    )


def test_catalog_only_exposes_allowlisted_tools(tmp_path: Path) -> None:
    gateway = make_gateway(tmp_path)
    assert {tool.name for tool in gateway.list_tools("project-one")} == {
        "project_summary",
        "publish_change",
    }
    assert gateway.list_tools("unknown-project") == []
    assert gateway.list_tools("../../etc/passwd") == []


def test_read_tool_validates_schema_and_records_audit(tmp_path: Path) -> None:
    gateway = make_gateway(tmp_path)
    invocation = gateway.invoke(
        MCPInvocationRequest(
            project_id="project-one",
            server="project-catalog",
            tool="project_summary",
            arguments={},
        )
    )
    assert invocation.status == MCPInvocationStatus.COMPLETED
    assert invocation.result["simulated"] is True
    assert gateway.audit.list("project-one") == [invocation]


def test_invalid_arguments_fail_closed(tmp_path: Path) -> None:
    gateway = make_gateway(tmp_path)
    invocation = gateway.invoke(
        MCPInvocationRequest(
            project_id="project-one",
            server="project-catalog",
            tool="project_summary",
            arguments={"unexpected": True},
        )
    )
    assert invocation.status == MCPInvocationStatus.FAILED
    assert invocation.result is None


def test_write_waits_for_approval_and_read_only_project_denies_it(tmp_path: Path) -> None:
    gateway = make_gateway(tmp_path)
    request = MCPInvocationRequest(
        project_id="project-one",
        server="project-catalog",
        tool="publish_change",
        arguments={"branch": "agents/devops/feat-demo-001"},
    )
    assert gateway.invoke(request).status == MCPInvocationStatus.WAITING_APPROVAL

    read_only_gateway = make_gateway(tmp_path, mode="read-only")
    approved = request.model_copy(update={"approved": True, "approved_by": "human@example.test"})
    assert read_only_gateway.invoke(approved).status == MCPInvocationStatus.DENIED


def test_non_allowlisted_tool_is_denied_and_audited(tmp_path: Path) -> None:
    gateway = make_gateway(tmp_path)
    invocation = gateway.invoke(
        MCPInvocationRequest(
            project_id="project-one",
            server="unknown-server",
            tool="delete_everything",
        )
    )
    assert invocation.status == MCPInvocationStatus.DENIED
    assert len(gateway.audit.list("project-one")) == 1
