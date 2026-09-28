import math
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.core.config import get_settings
from app.ingestion.chunker import Chunk


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class TextEncoder(Protocol):
    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ):
        ...


@dataclass(frozen=True)
class EmbeddingConfig:
    model_name: str = DEFAULT_EMBEDDING_MODEL
    batch_size: int = 32
    normalize: bool = True
    query_instruction: str = DEFAULT_QUERY_INSTRUCTION

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name cannot be empty")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]

    @property
    def point_id(self) -> str:
        return self.chunk.chunk_id

    @property
    def payload(self) -> dict[str, str | int | list[str] | None]:
        return self.chunk.metadata


class EmbeddingModel:
    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        *,
        encoder: TextEncoder | None = None,
    ) -> None:
        self.config = config or EmbeddingConfig()
        self._encoder = encoder or _load_sentence_transformer(self.config.model_name)

    @classmethod
    def from_settings(cls) -> "EmbeddingModel":
        settings = get_settings()
        return cls(EmbeddingConfig(model_name=settings.embedding_model))

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        _validate_texts(texts)
        encoded = self._encoder.encode(
            list(texts),
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = [_as_float_list(vector) for vector in encoded]

        if self.config.normalize:
            return [normalize_vector(vector) for vector in vectors]
        return vectors

    def embed_query(self, query: str) -> list[float]:
        _validate_query(query)
        embedded_query = self.config.query_instruction + query.strip()
        return self.embed_texts([embedded_query])[0]

    def embed_chunks(self, chunks: Sequence[Chunk]) -> list[EmbeddedChunk]:
        texts = [chunk.text for chunk in chunks]
        vectors = self.embed_texts(texts)
        return [
            EmbeddedChunk(chunk=chunk, vector=vector)
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

    @property
    def dimension(self) -> int | None:
        get_dimension = getattr(self._encoder, "get_sentence_embedding_dimension", None)
        if get_dimension is None:
            return None
        dimension = get_dimension()
        return int(dimension) if dimension is not None else None


def normalize_vector(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("cannot normalize a zero vector")
    return [float(value / norm) for value in vector]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimension")
    left_normalized = normalize_vector(left)
    right_normalized = normalize_vector(right)
    return sum(a * b for a, b in zip(left_normalized, right_normalized, strict=True))


def _validate_texts(texts: Sequence[str]) -> None:
    for text in texts:
        if not text.strip():
            raise ValueError("embedding text cannot be empty")


def _validate_query(query: str) -> None:
    if not query.strip():
        raise ValueError("query cannot be empty")


def _as_float_list(vector) -> list[float]:
    return [float(value) for value in vector]


def _load_sentence_transformer(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "sentence-transformers is required for real embeddings. "
            "Install backend/requirements.txt before loading the embedding model."
        ) from error

    return SentenceTransformer(model_name)
