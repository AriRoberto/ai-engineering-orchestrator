from typing import Any

from pydantic import BaseModel, Field

from ai_engineering.domain.models import AgentKind


class EvidenceExecutionRequest(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    prompt: str = Field(min_length=3, max_length=10_000)
    demo: bool = False
    include_content: bool = False
    preferred_agents: list[AgentKind] = Field(default_factory=list, max_length=8)


class EvidenceFile(BaseModel):
    path: str
    sha: str
    size: int = Field(ge=0)
    source_url: str
    content: str | None = None
    content_sha256: str | None = None
    content_status: str = "metadata-only"


class EvidenceCollection(BaseModel):
    project_id: str
    repository: str
    ref: str
    revision: str
    files: list[EvidenceFile]
    total_bytes: int
    provider: str = "github"
    read_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceContextItem(BaseModel):
    citation: str
    path: str
    source_url: str
    content_sha256: str
    content: str
    truncated: bool = False
