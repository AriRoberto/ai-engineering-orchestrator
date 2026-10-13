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


class TaskRequest(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    prompt: str = Field(min_length=3, max_length=10_000)
    read_only: bool = True
    demo: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent: AgentKind
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    simulated: bool = False


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
    events: list[ExecutionEvent] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def transition(self, status: ExecutionStatus, detail: str) -> None:
        self.status = status
        self.updated_at = datetime.now(UTC)
        self.events.append(ExecutionEvent(status=status, detail=detail))
