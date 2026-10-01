from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.rag.retriever import DenseRetriever, MetadataFilter, RetrievalResult


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        ...


class Reranker(Protocol):
    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        ...


@dataclass(frozen=True)
class RerankingConfig:
    candidate_top_k: int = 15
    final_top_k: int = 5

    def __post_init__(self) -> None:
        if self.candidate_top_k <= 0:
            raise ValueError("candidate_top_k must be positive")
        if self.final_top_k <= 0:
            raise ValueError("final_top_k must be positive")
        if self.final_top_k > self.candidate_top_k:
            raise ValueError("final_top_k cannot exceed candidate_top_k")

    @classmethod
    def from_settings(cls) -> "RerankingConfig":
        settings = get_settings()
        return cls(
            candidate_top_k=settings.reranker_candidate_top_k,
            final_top_k=settings.reranker_final_top_k,
        )


@dataclass(frozen=True)
class CrossEncoderRerankerConfig:
    model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name cannot be empty")

    @classmethod
    def from_settings(cls) -> "CrossEncoderRerankerConfig":
        return cls(model_name=get_settings().reranker_model)


class CrossEncoderReranker:
    def __init__(
        self,
        config: CrossEncoderRerankerConfig | None = None,
        *,
        model=None,
    ) -> None:
        self.config = config or CrossEncoderRerankerConfig.from_settings()
        self._model = model or _load_cross_encoder(self.config.model_name)

    @classmethod
    def from_settings(cls) -> "CrossEncoderReranker":
        return cls(CrossEncoderRerankerConfig.from_settings())

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not results:
            return []

        pairs = [(query.strip(), result.text) for result in results]
        scores = [float(score) for score in self._model.predict(pairs)]
        reranked = [
            _with_rerank_score(result, rerank_score)
            for result, rerank_score in zip(results, scores, strict=True)
        ]
        return sorted(
            reranked,
            key=lambda result: result.rerank_score
            if result.rerank_score is not None
            else float("-inf"),
            reverse=True,
        )


class RerankedRetriever:
    def __init__(
        self,
        *,
        retriever: Retriever,
        reranker: Reranker,
        config: RerankingConfig | None = None,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self.config = config or RerankingConfig()

    @classmethod
    def from_settings(cls) -> "RerankedRetriever":
        config = RerankingConfig.from_settings()
        return cls(
            retriever=DenseRetriever.from_settings(top_k=config.candidate_top_k),
            reranker=CrossEncoderReranker.from_settings(),
            config=config,
        )

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")

        candidates = self._retriever.retrieve(
            query,
            metadata_filter=metadata_filter,
        )
        reranked = self._reranker.rerank(query, candidates)
        return reranked[: self.config.final_top_k]


def _load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def _with_rerank_score(
    result: RetrievalResult,
    rerank_score: float,
) -> RetrievalResult:
    payload = dict(result.payload)
    payload.setdefault("retrieval_score", result.score)
    payload.setdefault("dense_score", result.score)
    payload["rerank_score"] = rerank_score
    return RetrievalResult(
        point_id=result.point_id,
        score=result.score,
        payload=payload,
    )
