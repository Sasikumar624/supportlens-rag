from dataclasses import dataclass
from typing import Protocol

from app.core.logging import get_logger
from app.db.qdrant import QdrantCollectionConfig, get_qdrant_client
from app.rag.embeddings import EmbeddingModel


logger = get_logger(__name__)


class QueryEmbedder(Protocol):
    def embed_query(self, query: str) -> list[float]:
        ...


class QdrantSearcher(Protocol):
    def query_points(
        self,
        *,
        collection_name: str,
        query: list[float],
        limit: int,
        with_payload: bool,
        score_threshold: float | None = None,
    ):
        ...


@dataclass(frozen=True)
class DenseRetrievalConfig:
    collection: QdrantCollectionConfig
    top_k: int = 5
    score_threshold: float | None = None

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.score_threshold is not None and self.score_threshold < 0:
            raise ValueError("score_threshold cannot be negative")


@dataclass(frozen=True)
class RetrievalResult:
    point_id: str
    score: float
    payload: dict

    @property
    def chunk_id(self) -> str | None:
        return _payload_string(self.payload, "chunk_id")

    @property
    def document_id(self) -> str | None:
        return _payload_string(self.payload, "document_id")

    @property
    def title(self) -> str | None:
        return _payload_string(self.payload, "title")

    @property
    def source_url(self) -> str | None:
        return _payload_string(self.payload, "source_url")

    @property
    def page(self) -> int | None:
        page = self.payload.get("page")
        return page if isinstance(page, int) else None

    @property
    def section(self) -> str | None:
        return _payload_string(self.payload, "section")

    @property
    def text(self) -> str:
        return _payload_string(self.payload, "text") or ""

    @property
    def citation_label(self) -> str:
        parts = [
            value
            for value in [
                self.title,
                f"Page {self.page}" if self.page is not None else None,
                self.section,
            ]
            if value
        ]
        return " - ".join(parts) if parts else self.point_id


class DenseRetriever:
    def __init__(
        self,
        config: DenseRetrievalConfig,
        *,
        client: QdrantSearcher | None = None,
        embedder: QueryEmbedder | None = None,
    ) -> None:
        self.config = config
        self._client = client or get_qdrant_client(config.collection)
        self._embedder = embedder or EmbeddingModel.from_settings()

    @classmethod
    def from_settings(
        cls,
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> "DenseRetriever":
        collection = QdrantCollectionConfig.from_settings()
        return cls(
            DenseRetrievalConfig(
                collection=collection,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        )

    def retrieve(self, query: str) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")

        query_vector = self._embedder.embed_query(query)
        logger.info(
            "Running dense retrieval against %s with top_k=%s",
            self.config.collection.collection_name,
            self.config.top_k,
        )
        response = self._client.query_points(
            collection_name=self.config.collection.collection_name,
            query=query_vector,
            limit=self.config.top_k,
            with_payload=True,
            score_threshold=self.config.score_threshold,
        )
        return [_to_retrieval_result(point) for point in _response_points(response)]


def _response_points(response) -> list:
    if hasattr(response, "points"):
        return list(response.points)
    return list(response)


def _to_retrieval_result(point) -> RetrievalResult:
    payload = point.payload or {}
    return RetrievalResult(
        point_id=str(point.id),
        score=float(point.score),
        payload=dict(payload),
    )


def _payload_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None
