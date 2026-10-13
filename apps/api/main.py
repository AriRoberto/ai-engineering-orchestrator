from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException, status

from ai_engineering.agents.specialists import default_agents
from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import Execution, TaskRequest
from ai_engineering.infrastructure.logging import configure_logging
from ai_engineering.infrastructure.settings import get_settings
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()
repository = InMemoryExecutionRepository()
orchestrator = AIEngineeringOrchestrator(default_agents(), repository, settings.max_steps)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Secure deterministic foundation for multi-agent engineering workflows.",
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
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@app.post("/v1/executions/{execution_id}/cancel", response_model=Execution, tags=["executions"])
def cancel_execution(execution_id: UUID) -> Execution:
    execution = orchestrator.cancel(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution
