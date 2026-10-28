import hashlib
import math
import re
from typing import Protocol

from ai_engineering.security.credentials import read_secret_file


class EmbeddingProvider(Protocol):
    dimensions: int
    model: str
    version: str
    key: str

    def embed(self, text: str) -> list[float]: ...
    def embed_many(self, texts: list[str]) -> list[list[float]]: ...


def validate_vectors(vectors: list[list[float]], count: int, dimensions: int) -> None:
    if len(vectors) != count or any(
        len(vector) != dimensions or not all(math.isfinite(value) for value in vector)
        for vector in vectors
    ):
        raise ValueError("Resposta de embeddings com quantidade, dimensão ou valores inválidos")


class DeterministicEmbeddingProvider:
    """Embedding local de demonstração; não representa um modelo semântico."""

    model = "deterministic-demo"
    version = "1"

    def __init__(self, dimensions: int = 16) -> None:
        if dimensions < 1:
            raise ValueError("Dimensão deve ser positiva")
        self.dimensions = dimensions
        self.key = f"deterministic:{self.model}:{self.version}:{dimensions}"

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"\w+", text.casefold()):
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:2], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class OpenAIEmbeddingProvider:
    version = "1"

    def __init__(
        self,
        model: str,
        dimensions: int,
        api_key: str | None = None,
        api_key_file: str | None = None,
        timeout_seconds: float = 30.0,
        batch_size: int = 32,
        client=None,
    ) -> None:
        maxima = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}
        if model not in maxima or not 1 <= dimensions <= maxima[model]:
            raise ValueError("Modelo ou dimensão de embeddings não suportado")
        if not 1 <= batch_size <= 32 or timeout_seconds <= 0:
            raise ValueError("Lote ou timeout de embeddings inválido")
        self.model = model
        self.dimensions = dimensions
        self.key = f"openai:{model}:{self.version}:{dimensions}"
        self.batch_size = batch_size
        if client is None:
            from openai import OpenAI

            key = read_secret_file(api_key_file) if api_key_file else (api_key or "").strip()
            if not key:
                raise ValueError("Embeddings OpenAI exigem chave de API ou arquivo de chave")
            client = OpenAI(api_key=key, timeout=timeout_seconds, max_retries=2)
        self.client = client

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if any(not text.strip() or len(text.encode("utf-8")) > 8000 for text in texts):
            raise ValueError("Trecho vazio ou acima do limite conservador de 8000 bytes")
        vectors = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                    encoding_format="float",
                )
            except Exception:
                raise RuntimeError("Falha no provedor de embeddings OpenAI") from None
            ordered = sorted(response.data, key=lambda item: item.index)
            if [item.index for item in ordered] != list(range(len(batch))):
                raise ValueError("Índices de embeddings inválidos")
            values = [item.embedding for item in ordered]
            validate_vectors(values, len(batch), self.dimensions)
            if any(not any(vector) for vector in values):
                raise ValueError("Embedding semântico nulo")
            vectors.extend(values)
        return vectors


def build_embedding_provider(settings) -> EmbeddingProvider:
    if settings.embedding_provider == "deterministic":
        return DeterministicEmbeddingProvider(settings.embedding_dimensions)
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            api_key=settings.openai_api_key.get_secret_value() if settings.openai_api_key else None,
            api_key_file=settings.openai_api_key_file,
            timeout_seconds=settings.embedding_timeout_seconds,
            batch_size=settings.embedding_batch_size,
        )
    raise ValueError("Provedor de embeddings não suportado")
