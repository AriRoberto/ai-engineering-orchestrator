from threading import RLock
from typing import Protocol
from uuid import UUID

from ai_engineering.domain.models import Execution


class ExecutionRepository(Protocol):
    def save(self, execution: Execution) -> None: ...

    def get(self, execution_id: UUID, project_id: str) -> Execution | None: ...

    def list(self, project_id: str) -> list[Execution]: ...


class InMemoryExecutionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Execution] = {}
        self._lock = RLock()

    def save(self, execution: Execution) -> None:
        with self._lock:
            self._items[execution.id] = execution.model_copy(deep=True)

    def get(self, execution_id: UUID, project_id: str) -> Execution | None:
        with self._lock:
            item = self._items.get(execution_id)
            if not item or item.request.project_id != project_id:
                return None
            return item.model_copy(deep=True)

    def list(self, project_id: str) -> list[Execution]:
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in self._items.values()
                if item.request.project_id == project_id
            ]
