import time

from ai_engineering.agents.base import EngineeringAgent
from ai_engineering.agents.specialists import default_agents
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import AgentKind, AgentResult, ExecutionStatus, TaskRequest
from ai_engineering.integrations.llm.providers import SimulatedLLMProvider
from ai_engineering.knowledge.models import KnowledgeDocumentCreate
from ai_engineering.knowledge.service import (
    DeterministicEmbeddingProvider,
    InMemoryKnowledgeRepository,
    KnowledgeService,
)
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator
from ai_engineering.security.content import KnowledgeContentGuard


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


def test_preferred_agents_override_automatic_routing_and_remove_duplicates() -> None:
    execution = make_orchestrator().execute(
        TaskRequest(
            project_id="demo-project",
            prompt="Analise código, Docker e Kubernetes",
            demo=True,
            preferred_agents=[AgentKind.QA, AgentKind.SECURITY, AgentKind.QA],
        )
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.selected_agents == [AgentKind.QA, AgentKind.SECURITY]
    assert [result.agent for result in execution.results] == [AgentKind.QA, AgentKind.SECURITY]


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
    assert "Stack detectada: Python" in findings
    assert "Stack detectada: JavaScript/TypeScript" in findings


def test_routes_all_phase3_specialists() -> None:
    selected = make_orchestrator().route(
        "Revise banco de dados, QA, segurança e documentação"
    )
    assert selected == [
        AgentKind.DATABASE,
        AgentKind.QA,
        AgentKind.SECURITY,
        AgentKind.DOCUMENTATION,
    ]


class FlakyAgent(EngineeringAgent):
    kind = AgentKind.SOFTWARE_ENGINEER
    description = "Test double"

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, request: TaskRequest) -> AgentResult:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient")
        return AgentResult(agent=self.kind, summary="Recovered")


class SlowAgent(EngineeringAgent):
    kind = AgentKind.SOFTWARE_ENGINEER
    description = "Test double"

    def execute(self, request: TaskRequest) -> AgentResult:
        time.sleep(0.05)
        return AgentResult(agent=self.kind, summary="Too late")


def test_transient_agent_failure_is_retried_once() -> None:
    agent = FlakyAgent()
    orchestrator = AIEngineeringOrchestrator(
        {AgentKind.SOFTWARE_ENGINEER: agent}, InMemoryExecutionRepository(), max_retries=1
    )
    execution = orchestrator.execute(TaskRequest(project_id="demo-project", prompt="Analyze code"))
    assert execution.status == ExecutionStatus.COMPLETED
    assert agent.calls == 2


def test_agent_timeout_fails_execution_without_exposing_details() -> None:
    orchestrator = AIEngineeringOrchestrator(
        {AgentKind.SOFTWARE_ENGINEER: SlowAgent()},
        InMemoryExecutionRepository(),
        agent_timeout_seconds=0.001,
        max_retries=0,
    )
    execution = orchestrator.execute(TaskRequest(project_id="demo-project", prompt="Analyze code"))
    assert execution.status == ExecutionStatus.FAILED
    assert execution.error == "AgentTimeout"


def test_rag_context_is_referenced_and_llm_consolidates_results() -> None:
    knowledge = KnowledgeService(
        InMemoryKnowledgeRepository(),
        DeterministicEmbeddingProvider(),
        KnowledgeContentGuard(),
    )
    knowledge.ingest(
        KnowledgeDocumentCreate(
            project_id="demo-project",
            title="Runbook",
            content="O pipeline fictício usa Docker e valida o health check.",
            source="demo://runbook",
        )
    )
    orchestrator = AIEngineeringOrchestrator(
        default_agents(),
        InMemoryExecutionRepository(),
        knowledge=knowledge,
        llm=SimulatedLLMProvider(),
    )

    execution = orchestrator.execute(
        TaskRequest(project_id="demo-project", prompt="Analise o pipeline Docker")
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.knowledge_sources == ["demo://runbook"]
    assert execution.consolidated_result is not None
    assert execution.llm_usage is not None
    assert execution.llm_usage.estimated is True


def test_llm_input_budget_fails_closed() -> None:
    orchestrator = AIEngineeringOrchestrator(
        default_agents(),
        InMemoryExecutionRepository(),
        llm=SimulatedLLMProvider(),
        max_llm_input_tokens=1,
    )
    execution = orchestrator.execute(
        TaskRequest(project_id="demo-project", prompt="Analise o código da aplicação")
    )
    assert execution.status == ExecutionStatus.FAILED
    assert execution.error == "ValueError"


def test_safe_evidence_context_is_cited_and_recorded() -> None:
    orchestrator = AIEngineeringOrchestrator(
        default_agents(),
        InMemoryExecutionRepository(),
        llm=SimulatedLLMProvider(),
    )
    source = "https://github.com/example/project/blob/abc/README.md"
    execution = orchestrator.execute(
        TaskRequest(
            project_id="demo-project",
            prompt="Revise a documentação",
            context={
                "files": ["README.md"],
                "evidence_context": [
                    {
                        "citation": "[evidence:README.md]",
                        "path": "README.md",
                        "source_url": source,
                        "content_sha256": "a" * 64,
                        "content": "Documentação pública aprovada.",
                        "truncated": False,
                    }
                ],
            },
        )
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.evidence_sources == [source]
    assert execution.plan[0] == "Analisar evidências textuais seguras com citações"
    assert execution.consolidated_result is not None
    assert "[evidence:README.md]" in execution.consolidated_result
