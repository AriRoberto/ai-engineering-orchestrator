from pathlib import Path

import yaml

from ai_engineering.domain.models import Execution, TaskRequest
from ai_engineering.evidence.audit import (
    EvidenceAccessAudit,
    EvidenceAccessStatus,
    EvidenceAuditRepository,
)
from ai_engineering.evidence.context import EvidenceContextBuilder
from ai_engineering.evidence.github import (
    EvidenceCollectionError,
    GitHubEvidenceCollector,
    parse_github_project,
)
from ai_engineering.evidence.models import EvidenceExecutionRequest
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator


class EvidenceExecutionService:
    def __init__(
        self,
        config_dir: str,
        collector: GitHubEvidenceCollector,
        orchestrator: AIEngineeringOrchestrator,
        context_builder: EvidenceContextBuilder | None = None,
        audit_repository=None,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.collector = collector
        self.orchestrator = orchestrator
        self.context_builder = context_builder or EvidenceContextBuilder()
        self.audit_repository = audit_repository or EvidenceAuditRepository()

    def execute(self, request: EvidenceExecutionRequest) -> Execution:
        visibility = "unknown"
        try:
            path = self.config_dir / f"{request.project_id}.yaml"
            if not path.is_file():
                raise PermissionError("Projeto não configurado para coleta")
            config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            visibility = str(config.get("visibility", "unknown"))
            if config.get("id") != request.project_id:
                raise PermissionError("Configuração de projeto inconsistente")
            collection = self.collector.collect(
                parse_github_project(config), include_content=request.include_content
            )
            evidence_context = self.context_builder.build(collection)
            task = TaskRequest(
                project_id=request.project_id,
                prompt=request.prompt,
                demo=request.demo,
                read_only=True,
                preferred_agents=request.preferred_agents,
                context={
                    "files": [item.path for item in collection.files],
                    "evidence": collection.model_dump(mode="json"),
                    "evidence_context": [
                        item.model_dump(mode="json") for item in evidence_context
                    ],
                },
            )
            execution = self.orchestrator.execute(task)
        except PermissionError as exc:
            self._record(
                request,
                EvidenceAccessStatus.DENIED,
                visibility,
                reason=str(exc),
            )
            raise
        except EvidenceCollectionError as exc:
            self._record(
                request,
                EvidenceAccessStatus.FAILED,
                visibility,
                reason=str(exc),
            )
            raise
        self._record(
            request,
            EvidenceAccessStatus.COMPLETED,
            visibility,
            authenticated=bool(collection.metadata.get("authenticated")),
            revision=collection.revision,
            execution_id=execution.id,
            reason="Coleta de evidências concluída",
        )
        return execution

    def _record(
        self,
        request: EvidenceExecutionRequest,
        status: EvidenceAccessStatus,
        visibility: str,
        *,
        authenticated: bool = False,
        revision: str | None = None,
        execution_id=None,
        reason: str,
    ) -> None:
        self.audit_repository.add(
            EvidenceAccessAudit(
                project_id=request.project_id,
                status=status,
                visibility=visibility,
                authenticated=authenticated,
                include_content=request.include_content,
                revision=revision,
                execution_id=execution_id,
                reason=reason,
            )
        )
