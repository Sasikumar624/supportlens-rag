import re
from dataclasses import dataclass
from typing import Iterable, Protocol

from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.db.qdrant import QdrantCollectionConfig, get_qdrant_client
from app.rag.retriever import MetadataFilter, RetrievalResult


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*")


class QdrantPayloadScroller(Protocol):
    def scroll(
        self,
        *,
        collection_name: str,
        limit: int,
        with_payload: bool,
        with_vectors: bool,
        offset=None,
        scroll_filter=None,
    ):
        ...


@dataclass(frozen=True)
class KeywordRetrievalConfig:
    top_k: int = 5
    min_score: float = 0.0

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.min_score < 0:
            raise ValueError("min_score cannot be negative")

    @classmethod
    def from_settings(cls) -> "KeywordRetrievalConfig":
        settings = get_settings()
        return cls(
            top_k=settings.keyword_retrieval_top_k,
            min_score=settings.keyword_retrieval_min_score,
        )


class KeywordRetriever:
    def __init__(
        self,
        payloads: Iterable[dict],
        config: KeywordRetrievalConfig | None = None,
    ) -> None:
        self.config = config or KeywordRetrievalConfig()
        self._results = [
            _payload_to_result(index, payload)
            for index, payload in enumerate(payloads, start=1)
        ]
        self._tokenized_corpus = [
            tokenize_for_keyword_search(_searchable_text(result.payload))
            for result in self._results
        ]
        self._bm25 = (
            BM25Okapi(self._tokenized_corpus)
            if any(self._tokenized_corpus)
            else None
        )

    @classmethod
    def from_results(
        cls,
        results: Iterable[RetrievalResult],
        config: KeywordRetrievalConfig | None = None,
    ) -> "KeywordRetriever":
        return cls((result.payload for result in results), config=config)

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if self._bm25 is None:
            return []

        query_tokens = tokenize_for_keyword_search(query)
        if not query_tokens:
            return []

        bm25_scores = self._bm25.get_scores(query_tokens)
        scored_results = []
        for result, bm25_score, document_tokens in zip(
            self._results,
            bm25_scores,
            self._tokenized_corpus,
            strict=True,
        ):
            keyword_score = _keyword_score(
                float(bm25_score),
                query_tokens,
                document_tokens,
            )
            if keyword_score <= self.config.min_score:
                continue
            if not _matches_metadata_filter(result, metadata_filter):
                continue
            scored_results.append(_with_keyword_score(result, keyword_score))
        return sorted(
            scored_results,
            key=lambda result: result.keyword_score
            if result.keyword_score is not None
            else float("-inf"),
            reverse=True,
        )[: self.config.top_k]


class QdrantKeywordRetriever:
    def __init__(
        self,
        collection: QdrantCollectionConfig,
        config: KeywordRetrievalConfig | None = None,
        *,
        client: QdrantPayloadScroller | None = None,
        scroll_batch_size: int = 256,
    ) -> None:
        if scroll_batch_size <= 0:
            raise ValueError("scroll_batch_size must be positive")
        self.collection = collection
        self.config = config or KeywordRetrievalConfig()
        self._client = client or get_qdrant_client(collection)
        self._scroll_batch_size = scroll_batch_size
        self._retriever: KeywordRetriever | None = None

    @classmethod
    def from_settings(cls) -> "QdrantKeywordRetriever":
        return cls(
            QdrantCollectionConfig.from_settings(),
            KeywordRetrievalConfig.from_settings(),
        )

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        if self._retriever is None:
            self._retriever = KeywordRetriever(
                self._load_payloads(),
                config=self.config,
            )
        return self._retriever.retrieve(query, metadata_filter=metadata_filter)

    def _load_payloads(self) -> list[dict]:
        payloads: list[dict] = []
        offset = None

        while True:
            response = self._client.scroll(
                collection_name=self.collection.collection_name,
                limit=self._scroll_batch_size,
                with_payload=True,
                with_vectors=False,
                offset=offset,
                scroll_filter=None,
            )
            points, offset = _scroll_response_parts(response)
            payloads.extend(
                dict(point.payload)
                for point in points
                if isinstance(getattr(point, "payload", None), dict)
            )
            if offset is None:
                break

        return payloads


def _scroll_response_parts(response) -> tuple[list, object | None]:
    if isinstance(response, tuple) and len(response) == 2:
        points, next_offset = response
        return list(points), next_offset
    if hasattr(response, "points"):
        return list(response.points), getattr(response, "next_page_offset", None)
    return list(response), None


def tokenize_for_keyword_search(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def _payload_to_result(index: int, payload: dict) -> RetrievalResult:
    point_id = str(payload.get("chunk_id") or f"keyword-{index}")
    return RetrievalResult(point_id=point_id, score=0.0, payload=dict(payload))


def _searchable_text(payload: dict) -> str:
    values = [
        payload.get("title"),
        payload.get("product"),
        payload.get("version"),
        payload.get("category"),
        payload.get("section"),
        payload.get("text"),
    ]
    return " ".join(value for value in values if isinstance(value, str))


def _with_keyword_score(
    result: RetrievalResult,
    keyword_score: float,
) -> RetrievalResult:
    payload = dict(result.payload)
    payload["keyword_score"] = keyword_score
    return RetrievalResult(
        point_id=result.point_id,
        score=keyword_score,
        payload=payload,
    )


def _keyword_score(
    bm25_score: float,
    query_tokens: list[str],
    document_tokens: list[str],
) -> float:
    document_token_set = set(document_tokens)
    exact_overlap = sum(1 for token in set(query_tokens) if token in document_token_set)
    return bm25_score + exact_overlap


def _matches_metadata_filter(
    result: RetrievalResult,
    metadata_filter: MetadataFilter | None,
) -> bool:
    if metadata_filter is None or metadata_filter.is_empty:
        return True

    expected_values = {
        "product": metadata_filter.product,
        "version": metadata_filter.version,
        "category": metadata_filter.category,
        "language": metadata_filter.language,
        "source_type": metadata_filter.source_type,
        "document_id": metadata_filter.document_id,
    }
    return all(
        expected is None or result.payload.get(field_name) == expected
        for field_name, expected in expected_values.items()
    )
