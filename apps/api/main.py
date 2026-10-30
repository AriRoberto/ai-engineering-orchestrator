import re
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ai_engineering.agents.specialists import default_agents
from ai_engineering.application.postgres_repository import PostgresExecutionRepository
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import Execution, ExecutionSummary, TaskRequest
from ai_engineering.evidence.audit import (
    EvidenceAccessAudit,
    EvidenceAuditRepository,
    PostgresEvidenceAuditRepository,
)
from ai_engineering.evidence.catalog import ProjectCatalog, ProjectSummary, PublicProjectCreate
from ai_engineering.evidence.context import EvidenceContextBuilder
from ai_engineering.evidence.github import (
    EvidenceCollectionError,
    GitHubEvidenceCollector,
    UrllibGitHubTreeTransport,
)
from ai_engineering.evidence.models import EvidenceExecutionRequest
from ai_engineering.evidence.service import EvidenceExecutionService
from ai_engineering.infrastructure.logging import configure_logging
from ai_engineering.infrastructure.settings import get_settings
from ai_engineering.infrastructure.telemetry import configure_telemetry, current_trace_id
from ai_engineering.integrations.llm.base import LLMRequest
from ai_engineering.integrations.llm.providers import build_llm_provider
from ai_engineering.integrations.mcp.client import SimulatedProjectMCPClient
from ai_engineering.integrations.mcp.models import (
    MCPApprovalRequest,
    MCPInvocation,
    MCPInvocationRequest,
    MCPToolDefinition,
)
from ai_engineering.integrations.mcp.policy import MCPPolicyStore
from ai_engineering.integrations.mcp.repository import (
    MCPAuditRepository,
    PostgresMCPAuditRepository,
)
from ai_engineering.integrations.mcp.service import MCPGateway
from ai_engineering.knowledge.database import PostgresKnowledgeRepository
from ai_engineering.knowledge.embeddings import build_embedding_provider
from ai_engineering.knowledge.ingestion_jobs import RepositoryIngestionJobs
from ai_engineering.knowledge.models import (
    FeedbackCreate,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeSearchRequest,
    KnowledgeStatus,
    RAGEvaluationRequest,
    RAGEvaluationResult,
    RAGFeedback,
    RAGFeedbackCreate,
    RAGMetrics,
    RepositoryIngestionJob,
    RepositoryIngestionRequest,
    SearchHit,
)
from ai_engineering.knowledge.service import (
    InMemoryKnowledgeRepository,
    KnowledgeService,
)
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator
from ai_engineering.security.api_access import APIAccessController
from ai_engineering.security.content import KnowledgeContentGuard
from ai_engineering.security.credentials import (
    FileGitHubTokenProvider,
    ScopedGitHubTokenProvider,
)
from ai_engineering.security.secrets import SecretRedactor

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()
access_controller = APIAccessController.build(
    settings.api_auth_enabled,
    settings.api_keys_file,
    auth_mode=settings.api_auth_mode,
    oidc_issuer=settings.oidc_issuer,
    oidc_audience=settings.oidc_audience,
    oidc_jwks_url=settings.oidc_jwks_url,
    oidc_role_claim=settings.oidc_role_claim,
    oidc_projects_claim=settings.oidc_projects_claim,
    oidc_quota_claim=settings.oidc_quota_claim,
    redis_url=(
        settings.api_quota_redis_url.get_secret_value()
        if settings.api_quota_redis_url
        else None
    ),
)
repository = (
    PostgresExecutionRepository(settings.database_url)
    if settings.database_url
    else InMemoryExecutionRepository()
)
knowledge_repository = (
    PostgresKnowledgeRepository(settings.database_url)
    if settings.database_url
    else InMemoryKnowledgeRepository()
)
knowledge_service = KnowledgeService(
    knowledge_repository,
    build_embedding_provider(settings),
    KnowledgeContentGuard(),
    settings.knowledge_chunk_size,
    settings.knowledge_chunk_overlap,
)
repository_ingestion_jobs = RepositoryIngestionJobs(
    knowledge_repository,
    knowledge_service.embeddings,
    settings.repository_ingestion_timeout_seconds,
)
llm_provider = build_llm_provider(
    settings.llm_provider,
    settings.llm_model,
    api_key=(
        settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    ),
    api_key_file=settings.openai_api_key_file,
    timeout_seconds=settings.llm_timeout_seconds,
    store_responses=settings.llm_store_responses,
    tracing_enabled=settings.llm_tracing_enabled,
)
mcp_audit_repository = (
    PostgresMCPAuditRepository(settings.database_url)
    if settings.database_url
    else MCPAuditRepository()
)
mcp_gateway = MCPGateway(
    [SimulatedProjectMCPClient()],
    MCPPolicyStore(settings.mcp_project_config_dir),
    mcp_audit_repository,
)
github_credential_provider = (
    FileGitHubTokenProvider(
        settings.github_private_read_token_file,
        settings.github_private_read_repository,
    )
    if settings.github_private_read_token_file
    else ScopedGitHubTokenProvider(
        (
            settings.github_private_read_token.get_secret_value()
            if settings.github_private_read_token
            else None
        ),
        settings.github_private_read_repository,
    )
)
evidence_audit_repository = (
    PostgresEvidenceAuditRepository(settings.database_url)
    if settings.database_url
    else EvidenceAuditRepository()
)
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
    max_rag_context_tokens=settings.max_rag_context_tokens,
)
evidence_execution_service = EvidenceExecutionService(
    settings.mcp_project_config_dir,
    GitHubEvidenceCollector(
        UrllibGitHubTreeTransport(
            settings.github_evidence_timeout_seconds,
            github_credential_provider,
        ),
        max_files=settings.evidence_max_files,
        max_file_bytes=settings.evidence_max_file_bytes,
        max_total_bytes=settings.evidence_max_total_bytes,
        max_content_files=settings.evidence_max_content_files,
        max_content_file_bytes=settings.evidence_max_content_file_bytes,
        max_content_total_bytes=settings.evidence_max_content_total_bytes,
        content_guard=KnowledgeContentGuard(),
        secret_redactor=SecretRedactor(),
    ),
    orchestrator,
    EvidenceContextBuilder(settings.evidence_context_max_chars),
    evidence_audit_repository,
)
project_catalog = ProjectCatalog(
    settings.mcp_project_config_dir,
    settings.github_evidence_timeout_seconds,
)


class LLMGenerateRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=10_000)
    instructions: str = Field(default="Responda como assistente de engenharia.", max_length=5_000)
    max_output_tokens: int = Field(default=1_000, ge=1, le=8_000)


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Fundação determinística e segura para fluxos multiagentes de engenharia.",
)
access_controller.install(app)
telemetry = configure_telemetry(
    app,
    enabled=settings.telemetry_enabled,
    metrics_enabled=settings.metrics_enabled,
    service_name=settings.otel_service_name,
    environment=settings.environment,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
)


def authorize_project(project_id: str) -> None:
    try:
        access_controller.authorize_project(project_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "ai-engineering-orchestrator"}


@app.get("/runtime", tags=["system"])
def runtime() -> dict[str, str | bool | int]:
    is_openai = settings.llm_provider == "openai-agents"
    uses_external_embeddings = settings.embedding_provider == "openai"
    return {
        "llm_mode": "openai" if is_openai else "simulated",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model if is_openai else "deterministic-demo",
        "external_api": is_openai,
        "usage_accounting": "measured" if is_openai else "estimated",
        "embedding_mode": "openai" if uses_external_embeddings else "local",
        "embedding_provider": settings.embedding_provider,
        "embedding_model": (
            settings.embedding_model if uses_external_embeddings else "deterministic-demo"
        ),
        "embedding_external_api": uses_external_embeddings,
        "max_rag_context_tokens": settings.max_rag_context_tokens,
        "project_registration_enabled": settings.project_registration_enabled,
    }


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    engine = getattr(repository, "engine", None)
    if engine is not None:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.warning("readiness_dependency_unavailable", dependency="database")
            raise HTTPException(status_code=503, detail="Banco de dados indisponível") from exc
    return {"status": "ready", "service": "ai-engineering-orchestrator"}


@app.get("/metrics", tags=["system"], include_in_schema=False)
def prometheus_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/agents", tags=["agents"])
def list_agents() -> list[dict[str, str]]:
    return [
        {"id": agent.kind.value, "description": agent.description}
        for agent in orchestrator.agents.values()
    ]


@app.get("/v1/projects", response_model=list[ProjectSummary], tags=["projects"])
def list_projects() -> list[ProjectSummary]:
    return project_catalog.list()


@app.post(
    "/v1/projects",
    response_model=ProjectSummary,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
def register_public_project(request: PublicProjectCreate) -> ProjectSummary:
    if not settings.project_registration_enabled:
        raise HTTPException(status_code=403, detail="Cadastro de projetos desabilitado")
    try:
        return project_catalog.register_public(request)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/v1/executions",
    response_model=Execution,
    status_code=status.HTTP_201_CREATED,
    tags=["executions"],
)
def create_execution(request: TaskRequest) -> Execution:
    authorize_project(request.project_id)
    execution = orchestrator.execute(request)
    span = trace.get_current_span()
    span.set_attribute("execution.id", str(execution.id))
    span.set_attribute("execution.project_id", execution.request.project_id)
    span.set_attribute("execution.status", execution.status.value)
    telemetry.record_execution(status=execution.status.value, source="direct")
    logger.info(
        "execution_processed",
        execution_id=str(execution.id),
        execution_status=execution.status.value,
        trace_id=current_trace_id(),
    )
    return execution


@app.get("/v1/executions", response_model=list[Execution], tags=["executions"])
def list_executions(project_id: str) -> list[Execution]:
    authorize_project(project_id)
    return repository.list(project_id)


@app.get(
    "/v1/executions/summaries",
    response_model=list[ExecutionSummary],
    tags=["executions"],
)
def list_execution_summaries(project_id: str) -> list[ExecutionSummary]:
    authorize_project(project_id)
    return [ExecutionSummary.from_execution(item) for item in repository.list(project_id)]


@app.get("/v1/executions/{execution_id}", response_model=Execution, tags=["executions"])
def get_execution(execution_id: UUID, project_id: str) -> Execution:
    authorize_project(project_id)
    execution = repository.get(execution_id, project_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution


@app.post("/v1/executions/{execution_id}/cancel", response_model=Execution, tags=["executions"])
def cancel_execution(execution_id: UUID, project_id: str) -> Execution:
    authorize_project(project_id)
    execution = orchestrator.cancel(execution_id, project_id)
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
    authorize_project(request.project_id)
    try:
        return knowledge_service.ingest(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/knowledge/search", response_model=list[SearchHit], tags=["knowledge"])
def search_knowledge(request: KnowledgeSearchRequest) -> list[SearchHit]:
    authorize_project(request.project_id)
    return knowledge_service.search(
        request.project_id, request.query, request.limit, request.include_shared
    )


@app.get("/v1/knowledge/status", response_model=KnowledgeStatus, tags=["knowledge"])
def get_knowledge_status(project_id: str) -> KnowledgeStatus:
    authorize_project(project_id)
    return knowledge_service.status(project_id)


@app.post(
    "/v1/knowledge/evaluations",
    response_model=RAGEvaluationResult,
    status_code=status.HTTP_201_CREATED,
    tags=["knowledge"],
)
def evaluate_rag(request: RAGEvaluationRequest) -> RAGEvaluationResult:
    authorize_project(request.project_id)
    try:
        return knowledge_service.evaluate(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/knowledge/evaluations/metrics", response_model=RAGMetrics, tags=["knowledge"])
def get_rag_evaluation_metrics(project_id: str) -> RAGMetrics:
    authorize_project(project_id)
    return knowledge_service.evaluation_metrics(project_id)


@app.post(
    "/v1/knowledge/evaluations/feedback",
    response_model=RAGFeedback,
    status_code=status.HTTP_201_CREATED,
    tags=["knowledge"],
)
def create_rag_feedback(request: RAGFeedbackCreate) -> RAGFeedback:
    authorize_project(request.project_id)
    try:
        return knowledge_service.add_retrieval_feedback(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/v1/knowledge/repositories/ingestions",
    response_model=RepositoryIngestionJob,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["knowledge"],
)
def start_repository_ingestion(
    request: RepositoryIngestionRequest, background_tasks: BackgroundTasks
) -> RepositoryIngestionJob:
    authorize_project(request.project_id)
    project = project_catalog.get(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado no catálogo")
    if project.visibility != "public" or project.mode != "read-only":
        raise HTTPException(
            status_code=403,
            detail="Ingestão pela interface exige repositório público em modo somente leitura",
        )
    if not re.fullmatch(
        r"https://github\.com/[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}",
        project.repository,
    ):
        raise HTTPException(status_code=422, detail="URL de repositório não autorizada")
    job = repository_ingestion_jobs.create(request, project)
    background_tasks.add_task(repository_ingestion_jobs.run, job.id)
    return job


@app.get(
    "/v1/knowledge/repositories/ingestions",
    response_model=list[RepositoryIngestionJob],
    tags=["knowledge"],
)
def list_repository_ingestions(project_id: str) -> list[RepositoryIngestionJob]:
    authorize_project(project_id)
    return repository_ingestion_jobs.list(project_id)


@app.get(
    "/v1/knowledge/repositories/ingestions/{job_id}",
    response_model=RepositoryIngestionJob,
    tags=["knowledge"],
)
def get_repository_ingestion(job_id: UUID, project_id: str) -> RepositoryIngestionJob:
    authorize_project(project_id)
    job = repository_ingestion_jobs.get(job_id, project_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestão não encontrada")
    return job


@app.delete("/v1/knowledge/documents/{document_id}", status_code=204, tags=["knowledge"])
def delete_document(document_id: UUID, project_id: str) -> None:
    authorize_project(project_id)
    if not knowledge_repository.delete(document_id, project_id):
        raise HTTPException(status_code=404, detail="Documento não encontrado no projeto")


@app.post("/v1/feedback", status_code=202, tags=["knowledge"])
def create_feedback(request: FeedbackCreate) -> dict[str, str]:
    authorize_project(request.project_id)
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


@app.get("/v1/mcp/tools", response_model=list[MCPToolDefinition], tags=["mcp"])
def list_mcp_tools(project_id: str) -> list[MCPToolDefinition]:
    authorize_project(project_id)
    return mcp_gateway.list_tools(project_id)


@app.post("/v1/mcp/invocations", response_model=MCPInvocation, tags=["mcp"])
def invoke_mcp_tool(request: MCPInvocationRequest) -> MCPInvocation:
    authorize_project(request.project_id)
    return mcp_gateway.invoke(request)


@app.get("/v1/mcp/invocations", response_model=list[MCPInvocation], tags=["mcp"])
def list_mcp_invocations(project_id: str) -> list[MCPInvocation]:
    authorize_project(project_id)
    return mcp_audit_repository.list(project_id)


@app.post(
    "/v1/mcp/invocations/{invocation_id}/approve",
    response_model=MCPInvocation,
    tags=["mcp"],
)
def approve_mcp_invocation(
    invocation_id: UUID,
    request: MCPApprovalRequest,
) -> MCPInvocation:
    authorize_project(request.project_id)
    try:
        return mcp_gateway.approve(invocation_id, request.project_id, request.approved_by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/v1/evidence/executions",
    response_model=Execution,
    status_code=status.HTTP_201_CREATED,
    tags=["evidence"],
)
def create_execution_from_evidence(request: EvidenceExecutionRequest) -> Execution:
    authorize_project(request.project_id)
    try:
        execution = evidence_execution_service.execute(request)
        telemetry.record_execution(status=execution.status.value, source="evidence")
        return execution
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EvidenceCollectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/evidence/audits", response_model=list[EvidenceAccessAudit], tags=["evidence"])
def list_evidence_audits(project_id: str) -> list[EvidenceAccessAudit]:
    authorize_project(project_id)
    return evidence_audit_repository.list(project_id)


web_directory = next(
    (path for path in (Path("web-dist"), Path("web/dist")) if path.is_dir()),
    None,
)
if web_directory:
    app.mount("/ui", StaticFiles(directory=web_directory, html=True), name="operations-ui")
