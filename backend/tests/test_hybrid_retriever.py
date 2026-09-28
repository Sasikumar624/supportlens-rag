from app.rag.hybrid_retriever import (
    HybridRetrievalConfig,
    HybridRetriever,
    reciprocal_rank_fusion,
)
from app.rag.retriever import MetadataFilter, RetrievalResult


class FakeRetriever:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, MetadataFilter | None]] = []

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append((query, metadata_filter))
        return self.results


def result(
    chunk_id: str,
    score: float,
    *,
    keyword_score: float | None = None,
    text: str = "Retrieved text",
) -> RetrievalResult:
    document_id = chunk_id.split("_C")[0]
    payload = {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "title": f"{document_id} Guide",
        "text": text,
    }
    if keyword_score is not None:
        payload["keyword_score"] = keyword_score
    return RetrievalResult(
        point_id=f"{chunk_id}_POINT",
        score=score,
        payload=payload,
    )


def test_reciprocal_rank_fusion_combines_dense_and_keyword_results() -> None:
    dense_results = [
        result("DOC001_C0001", 0.91),
        result("DOC002_C0001", 0.82),
    ]
    keyword_results = [
        result("DOC002_C0001", 4.2, keyword_score=4.2),
        result("DOC003_C0001", 3.1, keyword_score=3.1),
    ]

    fused = reciprocal_rank_fusion(
        dense_results=dense_results,
        keyword_results=keyword_results,
        config=HybridRetrievalConfig(top_k=10, rrf_k=0),
    )

    assert [item.chunk_id for item in fused] == [
        "DOC002_C0001",
        "DOC001_C0001",
        "DOC003_C0001",
    ]
    merged = fused[0]
    assert merged.hybrid_score == 1.5
    assert merged.dense_score == 0.82
    assert merged.keyword_score == 4.2
    assert merged.payload["dense_rank"] == 2
    assert merged.payload["keyword_rank"] == 1
    assert merged.payload["retrieval_sources"] == ["dense", "keyword"]


def test_hybrid_retriever_forwards_metadata_filter_and_limits_top_k() -> None:
    dense = FakeRetriever(
        [
            result("DOC001_C0001", 0.91),
            result("DOC002_C0001", 0.82),
        ]
    )
    keyword = FakeRetriever(
        [
            result("DOC003_C0001", 4.2, keyword_score=4.2),
            result("DOC002_C0001", 3.1, keyword_score=3.1),
        ]
    )
    retriever = HybridRetriever(
        dense_retriever=dense,
        keyword_retriever=keyword,
        config=HybridRetrievalConfig(top_k=2, rrf_k=60),
    )
    metadata_filter = MetadataFilter(product="Router X")

    results = retriever.retrieve("ERR_105 reset", metadata_filter=metadata_filter)

    assert dense.calls == [("ERR_105 reset", metadata_filter)]
    assert keyword.calls == [("ERR_105 reset", metadata_filter)]
    assert len(results) == 2
    assert results[0].hybrid_score is not None


def test_hybrid_retriever_returns_keyword_only_matches() -> None:
    retriever = HybridRetriever(
        dense_retriever=FakeRetriever([]),
        keyword_retriever=FakeRetriever(
            [result("DOC_KEYWORD_C0001", 5.0, keyword_score=5.0)]
        ),
    )

    results = retriever.retrieve("192.168.0.1")

    assert [item.chunk_id for item in results] == ["DOC_KEYWORD_C0001"]
    assert results[0].dense_score is None
    assert results[0].keyword_score == 5.0
    assert results[0].payload["retrieval_sources"] == ["keyword"]


def test_hybrid_retriever_rejects_invalid_inputs() -> None:
    retriever = HybridRetriever(
        dense_retriever=FakeRetriever([]),
        keyword_retriever=FakeRetriever([]),
    )

    try:
        retriever.retrieve(" ")
    except ValueError as error:
        assert "query" in str(error)
    else:
        raise AssertionError("Expected query validation error")

    try:
        HybridRetrievalConfig(top_k=0)
    except ValueError as error:
        assert "top_k" in str(error)
    else:
        raise AssertionError("Expected top_k validation error")

    try:
        HybridRetrievalConfig(rrf_k=-1)
    except ValueError as error:
        assert "rrf_k" in str(error)
    else:
        raise AssertionError("Expected rrf_k validation error")

    try:
        HybridRetrievalConfig(dense_weight=0.0, keyword_weight=0.0)
    except ValueError as error:
        assert "weight" in str(error)
    else:
        raise AssertionError("Expected retrieval weight validation error")
