from __future__ import annotations

from uuid import UUID

from ai_engineering.agents.base import EngineeringAgent
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import AgentKind, Execution, ExecutionStatus, TaskRequest


class AIEngineeringOrchestrator:
    def __init__(
        self,
        agents: dict[AgentKind, EngineeringAgent],
        repository: InMemoryExecutionRepository,
        max_steps: int = 8,
    ) -> None:
        self.agents = agents
        self.repository = repository
        self.max_steps = max_steps

    def route(self, prompt: str) -> list[AgentKind]:
        text = prompt.casefold()
        selected: list[AgentKind] = []
        rules = {
            AgentKind.KUBERNETES: ("kubernetes", "k8s", "helm", "deployment"),
            AgentKind.DEVOPS: ("pipeline", "ci/cd", "docker", "git", "release"),
            AgentKind.LINUX_SRE: ("linux", "incident", "log", "sre", "servidor"),
            AgentKind.SOFTWARE_ENGINEER: (
                "código",
                "code",
                "arquitetura",
                "stack",
                "software",
                "teste",
            ),
        }
        for kind, terms in rules.items():
            if any(term in text for term in terms):
                selected.append(kind)
        return selected or [AgentKind.SOFTWARE_ENGINEER]

    def execute(self, request: TaskRequest) -> Execution:
        execution = Execution(request=request)
        execution.transition(
            ExecutionStatus.PLANNING, "Request accepted for deterministic planning"
        )
        execution.selected_agents = self.route(request.prompt)
        execution.plan = [
            f"Run read-only diagnostic with {kind.value}" for kind in execution.selected_agents
        ]
        if len(execution.plan) > self.max_steps:
            execution.error = "Maximum step limit exceeded"
            execution.transition(ExecutionStatus.FAILED, execution.error)
            self.repository.save(execution)
            return execution
        if not request.read_only:
            execution.transition(
                ExecutionStatus.WAITING_APPROVAL, "Write-capable task requires human approval"
            )
            self.repository.save(execution)
            return execution
        execution.transition(ExecutionStatus.RUNNING, "Executing bounded agent plan")
        try:
            for kind in execution.selected_agents:
                execution.results.append(self.agents[kind].execute(request))
            execution.transition(ExecutionStatus.COMPLETED, "All planned diagnostics completed")
        except Exception as exc:  # defensive boundary; error detail is intentionally limited
            execution.error = type(exc).__name__
            execution.transition(ExecutionStatus.FAILED, "Agent execution failed")
        self.repository.save(execution)
        return execution

    def cancel(self, execution_id: UUID) -> Execution | None:
        execution = self.repository.get(execution_id)
        if execution and execution.status not in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
        }:
            execution.transition(ExecutionStatus.CANCELLED, "Cancellation requested")
            self.repository.save(execution)
        return execution
