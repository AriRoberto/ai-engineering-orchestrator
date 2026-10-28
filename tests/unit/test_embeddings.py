from types import SimpleNamespace

import pytest

from ai_engineering.knowledge.embeddings import (
    OpenAIEmbeddingProvider,
    validate_vectors,
)
from ai_engineering.knowledge.models import KnowledgeDocumentCreate
from ai_engineering.knowledge.service import (
    DeterministicEmbeddingProvider,
    InMemoryKnowledgeRepository,
    KnowledgeService,
)
from ai_engineering.security.content import KnowledgeContentGuard


class FakeClient:
    def __init__(self):
        self.embeddings = self
        self.calls = []

    def create(self, **arguments):
        self.calls.append(arguments)
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=index, embedding=[1.0] * arguments["dimensions"])
                for index in reversed(range(len(arguments["input"])))
            ]
        )


def test_openai_batches_validates_and_orders_response():
    client = FakeClient()
    provider = OpenAIEmbeddingProvider("text-embedding-3-small", 3, client=client, batch_size=2)
    assert provider.embed_many(["one", "two", "three"]) == [[1.0] * 3] * 3
    assert [call["input"] for call in client.calls] == [["one", "two"], ["three"]]
    assert client.calls[0]["encoding_format"] == "float"
    assert provider.key == "openai:text-embedding-3-small:1:3"
    with pytest.raises(ValueError):
        provider.embed("x" * 8001)
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    "vectors,count,dimensions",
    [
        ([[1.0]], 2, 1),
        ([[1.0]], 1, 2),
        ([[float("nan")]], 1, 1),
        ([[float("inf")]], 1, 1),
    ],
)
def test_invalid_embedding_response_is_rejected(vectors, count, dimensions):
    with pytest.raises(ValueError):
        validate_vectors(vectors, count, dimensions)


def test_embedding_failure_does_not_publish_document():
    class BrokenClient:
        embeddings = None

        def create(self, **_arguments):
            raise RuntimeError("sensitive provider detail")

    client = BrokenClient()
    client.embeddings = client
    repository = InMemoryKnowledgeRepository()
    service = KnowledgeService(
        repository,
        OpenAIEmbeddingProvider("text-embedding-3-small", 3, client=client),
        KnowledgeContentGuard(),
    )
    with pytest.raises(RuntimeError, match="^Falha no provedor de embeddings OpenAI$"):
        service.ingest(
            KnowledgeDocumentCreate(
                project_id="project-one",
                title="test",
                source="test://source",
                content="texto seguro",
            )
        )
    assert not repository.documents


def test_models_and_dimensions_are_never_mixed():
    repository = InMemoryKnowledgeRepository()
    demo = KnowledgeService(repository, DeterministicEmbeddingProvider(), KnowledgeContentGuard())
    semantic = KnowledgeService(
        repository,
        OpenAIEmbeddingProvider("text-embedding-3-small", 16, client=FakeClient()),
        KnowledgeContentGuard(),
    )
    request = KnowledgeDocumentCreate(
        project_id="project-one", title="test", source="test://source", content="postgres backup"
    )
    demo_document = demo.ingest(request)
    assert semantic.search("project-one", "postgres", 5, False) == []
    semantic_document = semantic.ingest(request)
    assert {hit.document_id for hit in semantic.search("project-one", "postgres", 5, False)} == {
        semantic_document.id
    }
    assert {hit.document_id for hit in demo.search("project-one", "postgres", 5, False)} == {
        demo_document.id
    }


def test_duplicate_response_indices_rejected():
    client = FakeClient()
    client.create = lambda **_arguments: SimpleNamespace(
        data=[SimpleNamespace(index=0, embedding=[1.0]), SimpleNamespace(index=0, embedding=[1.0])]
    )
    provider = OpenAIEmbeddingProvider("text-embedding-3-small", 1, client=client)
    with pytest.raises(ValueError, match="Índices"):
        provider.embed_many(["one", "two"])
