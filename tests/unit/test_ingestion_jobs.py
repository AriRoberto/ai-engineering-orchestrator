from types import SimpleNamespace

from ai_engineering.evidence.catalog import ProjectSummary
from ai_engineering.knowledge.embeddings import DeterministicEmbeddingProvider
from ai_engineering.knowledge.ingestion_jobs import RepositoryIngestionJobs
from ai_engineering.knowledge.models import IngestionStatus, RepositoryIngestionRequest
from ai_engineering.knowledge.service import InMemoryKnowledgeRepository


def project() -> ProjectSummary:
    return ProjectSummary(
        id="sample-project",
        owner="Example",
        repository="https://github.com/Example/sample-project",
        default_branch="main",
        visibility="public",
        mode="read-only",
    )


def test_ingestion_job_publishes_report(monkeypatch) -> None:
    manager = RepositoryIngestionJobs(
        InMemoryKnowledgeRepository(), DeterministicEmbeddingProvider(), 30
    )
    job = manager.create(RepositoryIngestionRequest(project_id="sample-project"), project())

    class FakeSnapshot:
        embedding_key = "deterministic:deterministic-demo:1:16"

        def report(self):
            return {
                "revision": "abc123",
                "documents": 2,
                "chunks": 4,
                "files": [
                    {"path": "src/app.py", "status": "accepted", "chunks": 2},
                    {
                        "path": "node_modules/pkg/index.js",
                        "status": "skipped",
                        "reason": "excluded_path",
                    },
                ],
            }

        def publish(self, _repository):
            return {"added": 2, "removed": 0, "unchanged": 0}

    class FakeScanner:
        def __init__(self, *_args, **_kwargs):
            pass

        def scan(self, revision):
            assert revision == "HEAD"
            return FakeSnapshot()

    monkeypatch.setattr("ai_engineering.knowledge.ingestion_jobs.shutil.which", lambda _: "git")
    monkeypatch.setattr(
        "ai_engineering.knowledge.ingestion_jobs.subprocess.run",
        lambda arguments, **_kwargs: (
            SimpleNamespace(returncode=0)
            if "--no-checkout" in arguments
            else SimpleNamespace(returncode=1)
        ),
    )
    monkeypatch.setattr(
        "ai_engineering.knowledge.ingestion_jobs.RepositoryScanner", FakeScanner
    )

    manager.run(job.id)

    completed = manager.get(job.id, "sample-project")
    assert completed.status == IngestionStatus.COMPLETED
    assert completed.report["sync"]["added"] == 2
    assert completed.report["total_files"] == 2
    assert completed.report["file_summary"]["skipped:excluded_path"] == 1
    assert completed.report["files"] == [
        {"path": "src/app.py", "status": "accepted", "chunks": 2}
    ]
    assert manager.get(job.id, "other-project") is None


def test_ingestion_job_reports_clone_failure_without_stderr(monkeypatch) -> None:
    manager = RepositoryIngestionJobs(
        InMemoryKnowledgeRepository(), DeterministicEmbeddingProvider(), 30
    )
    job = manager.create(RepositoryIngestionRequest(project_id="sample-project"), project())
    monkeypatch.setattr("ai_engineering.knowledge.ingestion_jobs.shutil.which", lambda _: "git")
    monkeypatch.setattr(
        "ai_engineering.knowledge.ingestion_jobs.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )

    manager.run(job.id)

    failed = manager.get(job.id, "sample-project")
    assert failed.status == IngestionStatus.FAILED
    assert failed.error == "Não foi possível clonar a branch solicitada"
