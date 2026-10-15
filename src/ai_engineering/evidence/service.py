from pathlib import Path

import yaml

from ai_engineering.domain.models import Execution, TaskRequest
from ai_engineering.evidence.context import EvidenceContextBuilder
from ai_engineering.evidence.github import GitHubEvidenceCollector, parse_public_github_project
from ai_engineering.evidence.models import EvidenceExecutionRequest
from ai_engineering.orchestrator.service import AIEngineeringOrchestrator


class EvidenceExecutionService:
    def __init__(
        self,
        config_dir: str,
        collector: GitHubEvidenceCollector,
        orchestrator: AIEngineeringOrchestrator,
        context_builder: EvidenceContextBuilder | None = None,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.collector = collector
        self.orchestrator = orchestrator
        self.context_builder = context_builder or EvidenceContextBuilder()

    def execute(self, request: EvidenceExecutionRequest) -> Execution:
        path = self.config_dir / f"{request.project_id}.yaml"
        if not path.is_file():
            raise PermissionError("Projeto não configurado para coleta")
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if config.get("id") != request.project_id:
            raise PermissionError("Configuração de projeto inconsistente")
        collection = self.collector.collect(
            parse_public_github_project(config), include_content=request.include_content
        )
        evidence_context = self.context_builder.build(collection)
        task = TaskRequest(
            project_id=request.project_id,
            prompt=request.prompt,
            demo=request.demo,
            read_only=True,
            context={
                "files": [item.path for item in collection.files],
                "evidence": collection.model_dump(mode="json"),
                "evidence_context": [item.model_dump(mode="json") for item in evidence_context],
            },
        )
        return self.orchestrator.execute(task)
