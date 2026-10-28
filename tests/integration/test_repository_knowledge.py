import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete

from ai_engineering.infrastructure.migrations import apply_migrations
from ai_engineering.knowledge.database import DocumentRow, PostgresKnowledgeRepository
from ai_engineering.knowledge.models import KnowledgeDocumentCreate
from ai_engineering.knowledge.repository_ingestion import RepositoryScanner
from ai_engineering.knowledge.service import DeterministicEmbeddingProvider, KnowledgeService
from ai_engineering.security.content import KnowledgeContentGuard


def test_postgres_snapshot_is_atomic_idempotent_and_isolated(monkeypatch):
    database_url = os.environ.get("AIEO_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("AIEO_TEST_DATABASE_URL deve apontar para PostgreSQL descartável com pgvector")
    root = Path(__file__).resolve().parents[2]
    apply_migrations(database_url, root / "migrations")
    apply_migrations(database_url, root / "migrations")
    repository = PostgresKnowledgeRepository(database_url)
    project_id = f"test-{uuid4().hex}"
    other_project = f"test-{uuid4().hex}"
    snapshot = RepositoryScanner(root, project_id).scan()
    snapshot.entries = snapshot.entries[:2]
    other = RepositoryScanner(root, other_project).scan()
    other.entries = other.entries[:1]
    service = KnowledgeService(
        repository, DeterministicEmbeddingProvider(), KnowledgeContentGuard()
    )
    try:
        assert snapshot.publish(repository)["added"] == 2
        assert snapshot.publish(repository)["unchanged"] == 2
        other.publish(repository)
        manual = service.ingest(
            KnowledgeDocumentCreate(
                project_id=project_id,
                title="Manual",
                source="manual://test",
                content="Manual seguro",
            )
        )
        document, chunks = snapshot.entries[0]
        loaded = repository.get_document(document.id, project_id)
        assert loaded.provenance == document.provenance
        assert repository.get_document(document.id, other_project) is None
        restored = next(
            chunk
            for _doc, chunk in repository.chunks_for(project_id, False)
            if chunk.id == chunks[0].id
        )
        assert restored.start_line == chunks[0].start_line
        assert restored.content == chunks[0].content
        assert restored.embedding == pytest.approx(chunks[0].embedding)
        hits = service.search(project_id, "Manual seguro", 5, False)
        assert hits[0].document_id == manual.id
        assert all(hit.document_id != other.entries[0][0].id for hit in hits)
        alternate = snapshot.with_embeddings(DeterministicEmbeddingProvider(32))
        alternate.publish(repository)
        alternate_service = KnowledgeService(
            repository, DeterministicEmbeddingProvider(32), KnowledgeContentGuard()
        )
        alternate_hits = alternate_service.search(project_id, "arquitetura", 5, False)
        assert alternate_hits
        assert all(
            hit.document_id in {doc.id for doc, _chunks in alternate.entries}
            for hit in alternate_hits
        )
        assert all(
            hit.document_id not in {doc.id for doc, _chunks in alternate.entries}
            for hit in service.search(project_id, "arquitetura", 5, False)
        )
        existing_ids = {doc.id for doc, _chunk in repository.chunks_for(project_id, False)}
        changed = document.model_copy(update={"id": uuid4()}, deep=True)
        changed_chunks = [
            chunk.model_copy(update={"id": uuid4(), "document_id": changed.id}) for chunk in chunks
        ]
        original_add = repository._add

        def fail_add(*_arguments):
            raise RuntimeError("Falha de escrita simulada")

        monkeypatch.setattr(repository, "_add", fail_add)
        with pytest.raises(RuntimeError, match="simulada"):
            repository.sync_collection(project_id, "repository", [(changed, changed_chunks)])
        assert {doc.id for doc, _chunk in repository.chunks_for(project_id, False)} == existing_ids
        monkeypatch.setattr(repository, "_add", original_add)
        snapshot.entries = snapshot.entries[:1]
        assert snapshot.publish(repository)["removed"] == 1
        assert repository.get_document(manual.id, project_id) is not None
        assert repository.get_document(other.entries[0][0].id, other_project) is not None
    finally:
        with repository.engine.begin() as connection:
            connection.execute(
                delete(DocumentRow).where(DocumentRow.project_id.in_([project_id, other_project]))
            )
        repository.engine.dispose()
