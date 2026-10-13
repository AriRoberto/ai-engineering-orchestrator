from threading import RLock
from uuid import UUID

from ai_engineering.domain.models import Execution


class InMemoryExecutionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Execution] = {}
        self._lock = RLock()

    def save(self, execution: Execution) -> None:
        with self._lock:
            self._items[execution.id] = execution.model_copy(deep=True)

    def get(self, execution_id: UUID) -> Execution | None:
        with self._lock:
            item = self._items.get(execution_id)
            return item.model_copy(deep=True) if item else None

    def list(self) -> list[Execution]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._items.values()]
