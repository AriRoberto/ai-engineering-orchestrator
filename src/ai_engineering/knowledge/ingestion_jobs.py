from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import UUID

from ai_engineering.evidence.catalog import ProjectSummary
from ai_engineering.knowledge.embeddings import EmbeddingProvider
from ai_engineering.knowledge.models import (
    IngestionStatus,
    RepositoryIngestionJob,
    RepositoryIngestionRequest,
)
from ai_engineering.knowledge.repository_ingestion import RepositoryScanner
from ai_engineering.knowledge.service import KnowledgeRepository


class RepositoryIngestionJobs:
    """In-process job registry for governed, read-only repository ingestion."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        embeddings: EmbeddingProvider,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.repository = repository
        self.embeddings = embeddings
        self.timeout_seconds = timeout_seconds
        self._jobs: dict[UUID, RepositoryIngestionJob] = {}
        self._lock = RLock()

    def create(
        self, request: RepositoryIngestionRequest, project: ProjectSummary
    ) -> RepositoryIngestionJob:
        branch = request.branch or project.default_branch
        job = RepositoryIngestionJob(
            project_id=request.project_id,
            repository=project.repository,
            branch=branch,
            collection=request.collection,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job.model_copy(deep=True)

    def get(self, job_id: UUID, project_id: str) -> RepositoryIngestionJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.project_id != project_id:
                return None
            return job.model_copy(deep=True)

    def list(self, project_id: str) -> list[RepositoryIngestionJob]:
        with self._lock:
            return sorted(
                (
                    job.model_copy(deep=True)
                    for job in self._jobs.values()
                    if job.project_id == project_id
                ),
                key=lambda job: job.created_at,
                reverse=True,
            )

    def run(self, job_id: UUID) -> None:
        job = self._update(job_id, status=IngestionStatus.RUNNING)
        if not job:
            return
        git = shutil.which("git")
        if not git:
            self._fail(job_id, "Git indisponível no serviço de ingestão")
            return
        try:
            with tempfile.TemporaryDirectory(prefix="aieo-rag-") as directory:
                root = Path(directory) / "repository"
                result = subprocess.run(  # noqa: S603 -- executable resolved locally; URL is catalog-governed.
                    [
                        git,
                        "clone",
                        "--quiet",
                        "--depth",
                        "1",
                        "--single-branch",
                        "--no-checkout",
                        "--branch",
                        job.branch,
                        "--",
                        job.repository,
                        str(root),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=self.timeout_seconds,
                )
                if result.returncode:
                    raise RuntimeError("Não foi possível clonar a branch solicitada")
                snapshot = RepositoryScanner(
                    root, job.project_id, collection=job.collection
                ).scan("HEAD")
                if self.embeddings.key != snapshot.embedding_key:
                    snapshot = snapshot.with_embeddings(self.embeddings)
                report = snapshot.report()
                files = report["files"]
                report["total_files"] = len(files)
                report["file_summary"] = dict(
                    Counter(
                        f"{item['status']}:{item.get('reason', 'eligible')}"
                        for item in files
                    )
                )
                report["files"] = [
                    item
                    for item in files
                    if item["status"] != "skipped"
                    or item.get("reason") not in {"excluded_path", "unsupported_type"}
                ][:500]
                # A clone temporária sem checkout representa somente o commit remoto.
                report["working_tree_dirty"] = False
                report["sync"] = snapshot.publish(self.repository)
                report["mode"] = "apply"
                self._update(job_id, status=IngestionStatus.COMPLETED, report=report)
        except subprocess.TimeoutExpired:
            self._fail(job_id, "Tempo limite excedido ao clonar o repositório")
        except Exception as exc:
            message = (
                str(exc)
                if isinstance(exc, (ValueError, RuntimeError))
                else "Falha na ingestão"
            )
            self._fail(job_id, message)

    def _fail(self, job_id: UUID, message: str) -> None:
        self._update(job_id, status=IngestionStatus.FAILED, error=message)

    def _update(self, job_id: UUID, **changes) -> RepositoryIngestionJob | None:
        with self._lock:
            current = self._jobs.get(job_id)
            if not current:
                return None
            current = current.model_copy(
                update={**changes, "updated_at": datetime.now(UTC)}, deep=True
            )
            self._jobs[job_id] = current
            return current.model_copy(deep=True)
