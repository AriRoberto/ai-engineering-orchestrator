from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from uuid import UUID

from ai_engineering.agents.base import EngineeringAgent
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import (
    AgentKind,
    Execution,
    ExecutionStatus,
    LLMUsageRecord,
    TaskRequest,
)
from ai_engineering.integrations.llm.base import LLMProvider, LLMRequest
from ai_engineering.integrations.llm.providers import estimate_tokens
from ai_engineering.knowledge.service import KnowledgeService


class AIEngineeringOrchestrator:
    def __init__(
        self,
        agents: dict[AgentKind, EngineeringAgent],
        repository: InMemoryExecutionRepository,
        max_steps: int = 8,
        agent_timeout_seconds: float = 5.0,
        max_retries: int = 1,
        knowledge: KnowledgeService | None = None,
        llm: LLMProvider | None = None,
        max_llm_input_tokens: int = 4_000,
        max_llm_output_tokens: int = 1_000,
    ) -> None:
        self.agents = agents
        self.repository = repository
        self.max_steps = max_steps
        self.agent_timeout_seconds = agent_timeout_seconds
        self.max_retries = max_retries
        self.knowledge = knowledge
        self.llm = llm
        self.max_llm_input_tokens = max_llm_input_tokens
        self.max_llm_output_tokens = max_llm_output_tokens

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
            ExecutionStatus.PLANNING, "Solicitação aceita para planejamento determinístico"
        )
        execution.selected_agents = self.route(request.prompt)
        knowledge_context = self._retrieve_knowledge(execution)
        execution.plan = [
            f"Executar diagnóstico somente leitura com {kind.value}"
            for kind in execution.selected_agents
        ]
        if knowledge_context:
            execution.plan.insert(0, "Consultar conhecimento isolado e referenciado do projeto")
        if len(execution.plan) > self.max_steps:
            execution.error = "Limite máximo de etapas excedido"
            execution.transition(ExecutionStatus.FAILED, execution.error)
            self.repository.save(execution)
            return execution
        if not request.read_only:
            execution.transition(
                ExecutionStatus.WAITING_APPROVAL,
                "Tarefa com capacidade de escrita requer aprovação humana",
            )
            self.repository.save(execution)
            return execution
        execution.transition(ExecutionStatus.RUNNING, "Executando plano limitado de agentes")
        try:
            for kind in execution.selected_agents:
                execution.results.append(self._execute_agent(kind, request))
            self._consolidate(execution, knowledge_context)
            execution.transition(
                ExecutionStatus.COMPLETED, "Todos os diagnósticos planejados foram concluídos"
            )
        except TimeoutError:
            execution.error = "AgentTimeout"
            execution.transition(
                ExecutionStatus.FAILED, "A execução do agente excedeu o tempo limite"
            )
        except Exception as exc:  # defensive boundary; error detail is intentionally limited
            execution.error = type(exc).__name__
            execution.transition(ExecutionStatus.FAILED, "Falha na execução do agente")
        self.repository.save(execution)
        return execution

    def _retrieve_knowledge(self, execution: Execution) -> str:
        if not self.knowledge:
            return ""
        hits = self.knowledge.search(
            execution.request.project_id,
            execution.request.prompt,
            limit=3,
            include_shared=True,
        )
        execution.knowledge_sources = list(dict.fromkeys(hit.source for hit in hits))
        return "\n\n".join(f"Fonte: {hit.source}\nTrecho: {hit.content}" for hit in hits)

    def _consolidate(self, execution: Execution, knowledge_context: str) -> None:
        if not self.llm:
            return
        findings = "\n".join(
            f"- {result.agent.value}: {result.summary}" for result in execution.results
        )
        prompt = (
            f"Solicitação: {execution.request.prompt}\n\n"
            f"Conhecimento recuperado:\n{knowledge_context or 'Nenhum.'}\n\n"
            f"Resultados dos agentes:\n{findings}"
        )
        if estimate_tokens(prompt) > self.max_llm_input_tokens:
            raise ValueError("LLMInputTokenBudgetExceeded")
        response = self.llm.generate(
            LLMRequest(
                instructions=(
                    "Consolide somente as evidências fornecidas, cite as fontes disponíveis e "
                    "não conceda permissões nem invente resultados."
                ),
                prompt=prompt,
                max_output_tokens=self.max_llm_output_tokens,
            )
        )
        if response.usage.output_tokens > self.max_llm_output_tokens:
            raise ValueError("LLMOutputTokenBudgetExceeded")
        execution.consolidated_result = response.text
        execution.llm_usage = LLMUsageRecord(
            provider=response.provider,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            estimated=response.usage.estimated,
            estimated_cost_usd=response.usage.estimated_cost_usd,
        )

    def _execute_agent(self, kind: AgentKind, request: TaskRequest):
        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"agent-{kind.value}")
            future = executor.submit(self.agents[kind].execute, request)
            try:
                result = future.result(timeout=self.agent_timeout_seconds)
                executor.shutdown(wait=True)
                return result
            except TimeoutError:
                future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception as exc:
                last_error = exc
                executor.shutdown(wait=True)
        assert last_error is not None
        raise last_error

    def cancel(self, execution_id: UUID) -> Execution | None:
        execution = self.repository.get(execution_id)
        if execution and execution.status not in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
        }:
            execution.transition(ExecutionStatus.CANCELLED, "Cancelamento solicitado")
            self.repository.save(execution)
        return execution
