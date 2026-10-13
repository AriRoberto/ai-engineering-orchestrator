from abc import ABC, abstractmethod

from ai_engineering.domain.models import AgentKind, AgentResult, TaskRequest


class EngineeringAgent(ABC):
    kind: AgentKind
    description: str

    @abstractmethod
    def execute(self, request: TaskRequest) -> AgentResult:
        """Perform a bounded, policy-compliant task."""
