from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.rag.retriever import MetadataFilter, RetrievalResult


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        ...


@dataclass(frozen=True)
class HybridRetrievalConfig:
    top_k: int = 10
    rrf_k: int = 60
    dense_weight: float = 1.0
    keyword_weight: float = 1.0

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.rrf_k < 0:
            raise ValueError("rrf_k cannot be negative")
        if self.dense_weight < 0:
            raise ValueError("dense_weight cannot be negative")
        if self.keyword_weight < 0:
            raise ValueError("keyword_weight cannot be negative")
        if self.dense_weight == 0 and self.keyword_weight == 0:
            raise ValueError("at least one retrieval weight must be positive")

    @classmethod
    def from_settings(cls) -> "HybridRetrievalConfig":
        settings = get_settings()
        return cls(
            top_k=settings.hybrid_retrieval_top_k,
            rrf_k=settings.hybrid_rrf_k,
        )


class HybridRetriever:
    def __init__(
        self,
        *,
        dense_retriever: Retriever,
        keyword_retriever: Retriever,
        config: HybridRetrievalConfig | None = None,
    ) -> None:
        self._dense_retriever = dense_retriever
        self._keyword_retriever = keyword_retriever
        self.config = config or HybridRetrievalConfig()

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")

        dense_results = self._dense_retriever.retrieve(
            query,
            metadata_filter=metadata_filter,
        )
        keyword_results = self._keyword_retriever.retrieve(
            query,
            metadata_filter=metadata_filter,
        )
        fused = reciprocal_rank_fusion(
            dense_results=dense_results,
            keyword_results=keyword_results,
            config=self.config,
        )
        return fused[: self.config.top_k]


def reciprocal_rank_fusion(
    *,
    dense_results: list[RetrievalResult],
    keyword_results: list[RetrievalResult],
    config: HybridRetrievalConfig | None = None,
) -> list[RetrievalResult]:
    config = config or HybridRetrievalConfig()
    fused: dict[str, dict] = {}

    _add_ranked_results(
        fused,
        results=dense_results,
        source_name="dense",
        weight=config.dense_weight,
        rrf_k=config.rrf_k,
    )
    _add_ranked_results(
        fused,
        results=keyword_results,
        source_name="keyword",
        weight=config.keyword_weight,
        rrf_k=config.rrf_k,
    )

    results = [
        _to_hybrid_result(key, entry)
        for key, entry in fused.items()
        if entry["hybrid_score"] > 0
    ]
    return sorted(
        results,
        key=lambda result: (
            result.hybrid_score if result.hybrid_score is not None else float("-inf"),
            result.dense_score if result.dense_score is not None else float("-inf"),
            result.keyword_score if result.keyword_score is not None else float("-inf"),
        ),
        reverse=True,
    )


def _add_ranked_results(
    fused: dict[str, dict],
    *,
    results: list[RetrievalResult],
    source_name: str,
    weight: float,
    rrf_k: int,
) -> None:
    if weight == 0:
        return

    for rank, result in enumerate(results, start=1):
        key = _fusion_key(result)
        entry = fused.setdefault(
            key,
            {
                "point_id": result.point_id,
                "payload": dict(result.payload),
                "hybrid_score": 0.0,
                "sources": set(),
            },
        )
        payload = entry["payload"]
        payload.update(
            {
                field_name: value
                for field_name, value in result.payload.items()
                if field_name not in payload or payload[field_name] in (None, "")
            }
        )
        score = weight / (rrf_k + rank)
        entry["hybrid_score"] += score
        entry["sources"].add(source_name)
        payload[f"{source_name}_rank"] = rank
        if source_name == "dense":
            payload["dense_score"] = result.score
        if source_name == "keyword":
            payload["keyword_score"] = result.keyword_score or result.score


def _to_hybrid_result(key: str, entry: dict) -> RetrievalResult:
    payload = dict(entry["payload"])
    payload["hybrid_score"] = entry["hybrid_score"]
    payload["retrieval_sources"] = sorted(entry["sources"])
    return RetrievalResult(
        point_id=str(payload.get("chunk_id") or entry["point_id"] or key),
        score=_best_relevance_score(payload, fallback=entry["hybrid_score"]),
        payload=payload,
    )


def _fusion_key(result: RetrievalResult) -> str:
    return result.chunk_id or result.point_id


def _best_relevance_score(payload: dict, *, fallback: float) -> float:
    for field_name in ["dense_score", "keyword_score", "hybrid_score"]:
        value = payload.get(field_name)
        if isinstance(value, int | float):
            return float(value)
    return fallback
