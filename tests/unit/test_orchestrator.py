from ai_engineering.agents.specialists import default_agents
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import AgentKind, ExecutionStatus, TaskRequest
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator


def make_orchestrator() -> AIEngineeringOrchestrator:
    return AIEngineeringOrchestrator(default_agents(), InMemoryExecutionRepository())


def test_routes_multiple_specialists_and_assigns_unique_ids() -> None:
    orchestrator = make_orchestrator()
    request = TaskRequest(
        project_id="demo-project", prompt="Analise código, Docker e Kubernetes", demo=True
    )
    first = orchestrator.execute(request)
    second = orchestrator.execute(request)
    assert first.id != second.id
    assert first.status == ExecutionStatus.COMPLETED
    assert set(first.selected_agents) == {
        AgentKind.SOFTWARE_ENGINEER,
        AgentKind.DEVOPS,
        AgentKind.KUBERNETES,
    }


def test_write_request_waits_for_approval() -> None:
    execution = make_orchestrator().execute(
        TaskRequest(project_id="demo-project", prompt="Implemente uma feature", read_only=False)
    )
    assert execution.status == ExecutionStatus.WAITING_APPROVAL
    assert execution.results == []


def test_software_agent_detects_example_stack() -> None:
    execution = make_orchestrator().execute(
        TaskRequest(
            project_id="demo-project",
            prompt="Detecte a stack do código",
            context={"files": ["pyproject.toml", "package.json"]},
        )
    )
    findings = execution.results[0].findings
    assert "Detected stack: Python" in findings
    assert "Detected stack: JavaScript/TypeScript" in findings
