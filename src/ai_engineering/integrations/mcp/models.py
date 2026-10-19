from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class MCPToolRisk(StrEnum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


class MCPInvocationStatus(StrEnum):
    COMPLETED = "COMPLETED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DENIED = "DENIED"
    FAILED = "FAILED"


class MCPToolDefinition(BaseModel):
    server: str
    name: str
    description: str
    risk: MCPToolRisk
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]

    @property
    def qualified_name(self) -> str:
        return f"{self.server}:{self.name}"


class MCPInvocationRequest(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    server: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    tool: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{1,99}$")
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    approved_by: str | None = Field(default=None, min_length=2, max_length=200)

    @model_validator(mode="after")
    def approval_has_reviewer(self):
        if self.approved and not self.approved_by:
            raise ValueError("approved_by é obrigatório quando approved=true")
        return self


class MCPApprovalRequest(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    approved_by: str = Field(min_length=2, max_length=200)


class MCPInvocation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: str
    server: str
    tool: str
    risk: MCPToolRisk
    status: MCPInvocationStatus
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    reason: str
    approved_by: str | None = None
    approval_of: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
