from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExecutionStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentKind(StrEnum):
    SOFTWARE_ENGINEER = "software-engineer"
    DEVOPS = "devops"
    KUBERNETES = "kubernetes"
    LINUX_SRE = "linux-sre"
    DATABASE = "database"
    QA = "qa"
    SECURITY = "security"
    DOCUMENTATION = "documentation"


class TaskRequest(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    prompt: str = Field(min_length=3, max_length=10_000)
    read_only: bool = True
    demo: bool = False
    preferred_agents: list[AgentKind] = Field(default_factory=list, max_length=8)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent: AgentKind
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    simulated: bool = False


class LLMUsageRecord(BaseModel):
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated: bool = True
    estimated_cost_usd: float | None = None


class KnowledgeContextRecord(BaseModel):
    citation: str
    source: str
    title: str
    score: float
    content: str
    estimated_tokens: int
    start_line: int | None = None
    end_line: int | None = None


class ExecutionEvent(BaseModel):
    status: ExecutionStatus
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    detail: str


class Execution(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    request: TaskRequest
    status: ExecutionStatus = ExecutionStatus.PENDING
    selected_agents: list[AgentKind] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    knowledge_sources: list[str] = Field(default_factory=list)
    knowledge_context: list[KnowledgeContextRecord] = Field(default_factory=list)
    knowledge_input_tokens: int = 0
    evidence_sources: list[str] = Field(default_factory=list)
    consolidated_result: str | None = None
    llm_usage: LLMUsageRecord | None = None
    events: list[ExecutionEvent] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def transition(self, status: ExecutionStatus, detail: str) -> None:
        self.status = status
        self.updated_at = datetime.now(UTC)
        self.events.append(ExecutionEvent(status=status, detail=detail))


class ExecutionSummary(BaseModel):
    """Lightweight projection used by history screens and API clients."""

    id: UUID
    project_id: str
    prompt: str
    status: ExecutionStatus
    selected_agents: list[AgentKind] = Field(default_factory=list)
    evidence_source_count: int = 0
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_execution(cls, execution: Execution) -> ExecutionSummary:
        return cls(
            id=execution.id,
            project_id=execution.request.project_id,
            prompt=execution.request.prompt,
            status=execution.status,
            selected_agents=execution.selected_agents,
            evidence_source_count=len(execution.evidence_sources),
            created_at=execution.created_at,
            updated_at=execution.updated_at,
        )
