from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from ai_engineering.application.postgres_repository import (
    ExecutionBase,
    PostgresExecutionRepository,
)
from ai_engineering.domain.models import Execution, ExecutionStatus, TaskRequest


def make_repository() -> PostgresExecutionRepository:
    repository = PostgresExecutionRepository.__new__(PostgresExecutionRepository)
    repository.engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ExecutionBase.metadata.create_all(repository.engine)
    return repository


def test_execution_round_trip_preserves_complete_audit_payload() -> None:
    repository = make_repository()
    execution = Execution(
        request=TaskRequest(project_id="project-one", prompt="Analise o código", demo=True)
    )
    execution.transition(ExecutionStatus.RUNNING, "Execução iniciada")
    repository.save(execution)

    loaded = repository.get(execution.id, "project-one")

    assert loaded == execution
    assert loaded is not None
    assert loaded.events[0].detail == "Execução iniciada"


def test_save_updates_existing_execution_and_list_is_newest_first() -> None:
    repository = make_repository()
    first = Execution(request=TaskRequest(project_id="project-one", prompt="Primeira tarefa"))
    second = Execution(request=TaskRequest(project_id="project-one", prompt="Segunda tarefa"))
    second.created_at = first.created_at.replace(microsecond=first.created_at.microsecond + 1)
    second.updated_at = second.created_at
    repository.save(first)
    repository.save(second)
    first.transition(ExecutionStatus.CANCELLED, "Cancelada")
    repository.save(first)

    assert repository.get(first.id, "project-one").status == ExecutionStatus.CANCELLED
    assert [item.id for item in repository.list("project-one")] == [second.id, first.id]


def test_queries_are_project_isolated() -> None:
    repository = make_repository()
    execution = Execution(request=TaskRequest(project_id="project-one", prompt="Tarefa privada"))
    repository.save(execution)

    assert repository.get(execution.id, "project-two") is None
    assert repository.list("project-two") == []
