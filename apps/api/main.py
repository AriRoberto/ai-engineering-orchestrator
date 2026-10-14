from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from ai_engineering.agents.specialists import default_agents
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import Execution, TaskRequest
from ai_engineering.infrastructure.logging import configure_logging
from ai_engineering.infrastructure.settings import get_settings
from ai_engineering.integrations.llm.base import LLMRequest
from ai_engineering.integrations.llm.providers import build_llm_provider
from ai_engineering.knowledge.database import PostgresKnowledgeRepository
from ai_engineering.knowledge.models import (
    FeedbackCreate,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeSearchRequest,
    SearchHit,
)
from ai_engineering.knowledge.service import (
    DeterministicEmbeddingProvider,
    InMemoryKnowledgeRepository,
    KnowledgeService,
)
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator
from ai_engineering.security.content import KnowledgeContentGuard

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()
repository = InMemoryExecutionRepository()
knowledge_repository = (
    PostgresKnowledgeRepository(settings.database_url)
    if settings.database_url
    else InMemoryKnowledgeRepository()
)
knowledge_service = KnowledgeService(
    knowledge_repository,
    DeterministicEmbeddingProvider(settings.embedding_dimensions),
    KnowledgeContentGuard(),
    settings.knowledge_chunk_size,
    settings.knowledge_chunk_overlap,
)
llm_provider = build_llm_provider(settings.llm_provider, settings.llm_model)
orchestrator = AIEngineeringOrchestrator(
    default_agents(),
    repository,
    settings.max_steps,
    settings.agent_timeout_seconds,
    settings.max_retries,
    knowledge=knowledge_service,
    llm=llm_provider if settings.llm_planning_enabled else None,
    max_llm_input_tokens=settings.max_llm_input_tokens,
    max_llm_output_tokens=settings.max_llm_output_tokens,
)


class LLMGenerateRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=10_000)
    instructions: str = Field(default="Responda como assistente de engenharia.", max_length=5_000)
    max_output_tokens: int = Field(default=1_000, ge=1, le=8_000)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Fundação determinística e segura para fluxos multiagentes de engenharia.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "ai-engineering-orchestrator"}


@app.get("/v1/agents", tags=["agents"])
def list_agents() -> list[dict[str, str]]:
    return [
        {"id": agent.kind.value, "description": agent.description}
        for agent in orchestrator.agents.values()
    ]


@app.post(
    "/v1/executions",
    response_model=Execution,
    status_code=status.HTTP_201_CREATED,
    tags=["executions"],
)
def create_execution(request: TaskRequest) -> Execution:
    execution = orchestrator.execute(request)
    logger.info(
        "execution_processed",
        execution_id=str(execution.id),
        execution_status=execution.status.value,
    )
    return execution


@app.get("/v1/executions", response_model=list[Execution], tags=["executions"])
def list_executions() -> list[Execution]:
    return repository.list()


@app.get("/v1/executions/{execution_id}", response_model=Execution, tags=["executions"])
def get_execution(execution_id: UUID) -> Execution:
    execution = repository.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution


@app.post("/v1/executions/{execution_id}/cancel", response_model=Execution, tags=["executions"])
def cancel_execution(execution_id: UUID) -> Execution:
    execution = orchestrator.cancel(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution


@app.post(
    "/v1/knowledge/documents",
    response_model=KnowledgeDocument,
    status_code=status.HTTP_201_CREATED,
    tags=["knowledge"],
)
def ingest_document(request: KnowledgeDocumentCreate) -> KnowledgeDocument:
    try:
        return knowledge_service.ingest(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/knowledge/search", response_model=list[SearchHit], tags=["knowledge"])
def search_knowledge(request: KnowledgeSearchRequest) -> list[SearchHit]:
    return knowledge_service.search(
        request.project_id, request.query, request.limit, request.include_shared
    )


@app.delete("/v1/knowledge/documents/{document_id}", status_code=204, tags=["knowledge"])
def delete_document(document_id: UUID, project_id: str) -> None:
    if not knowledge_repository.delete(document_id, project_id):
        raise HTTPException(status_code=404, detail="Documento não encontrado no projeto")


@app.post("/v1/feedback", status_code=202, tags=["knowledge"])
def create_feedback(request: FeedbackCreate) -> dict[str, str]:
    knowledge_repository.add_feedback(request)
    return {"status": "accepted"}


@app.post("/v1/llm/generate", tags=["llm"])
def generate_with_llm(request: LLMGenerateRequest) -> dict[str, object]:
    response = llm_provider.generate(
        LLMRequest(
            instructions=request.instructions,
            prompt=request.prompt,
            max_output_tokens=request.max_output_tokens,
        )
    )
    return {
        "text": response.text,
        "provider": response.provider,
        "model": response.model,
        "simulated": response.simulated,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "estimated": response.usage.estimated,
            "estimated_cost_usd": response.usage.estimated_cost_usd,
        },
    }
