from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KnowledgeScope(StrEnum):
    PROJECT = "project"
    SHARED = "shared"
    EXECUTION = "execution"
    VALIDATED_SOLUTION = "validated-solution"


class KnowledgeProvenance(BaseModel):
    path: str
    revision: str
    content_sha256: str
    document_type: str
    embedding_model: str = "deterministic-demo"
    embedding_dimensions: int = 16
    embedding_version: str = "1"
    chunker_version: str = "lines-v1"
    chunk_size: int
    redactions: int = 0


class KnowledgeDocumentCreate(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=1_000_000)
    source: str = Field(min_length=1, max_length=2_000)
    scope: KnowledgeScope = KnowledgeScope.PROJECT
    sharing_authorized: bool = False


class KnowledgeChunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    project_id: str
    scope: KnowledgeScope
    content: str
    position: int
    embedding: list[float]
    start_line: int | None = None
    end_line: int | None = None


class KnowledgeDocument(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: str
    title: str
    source: str
    scope: KnowledgeScope
    sharing_authorized: bool
    chunks: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    collection: str | None = None
    provenance: KnowledgeProvenance | None = None


class SearchHit(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    source: str
    content: str
    score: float
    provenance: KnowledgeProvenance | None = None
    start_line: int | None = None
    end_line: int | None = None


class KnowledgeSearchRequest(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    query: str = Field(min_length=2, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)
    include_shared: bool = False


class FeedbackCreate(BaseModel):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    execution_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2_000)
    validated: bool = False
