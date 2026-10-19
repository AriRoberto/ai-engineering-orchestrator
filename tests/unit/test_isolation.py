from ai_engineering.application.repository import InMemoryExecutionRepository
from ai_engineering.domain.models import Execution, TaskRequest


def test_repository_returns_defensive_copies() -> None:
    repository = InMemoryExecutionRepository()
    execution = Execution(request=TaskRequest(project_id="project-one", prompt="Analyze code"))
    repository.save(execution)
    loaded = repository.get(execution.id, "project-one")
    assert loaded is not None
    loaded.request.context["mutation_probe"] = "isolated-value"
    assert repository.get(execution.id, "project-one").request.context == {}


def test_execution_repository_is_project_isolated() -> None:
    repository = InMemoryExecutionRepository()
    execution = Execution(request=TaskRequest(project_id="project-one", prompt="Analyze code"))
    repository.save(execution)

    assert repository.get(execution.id, "project-two") is None
    assert repository.list("project-two") == []
