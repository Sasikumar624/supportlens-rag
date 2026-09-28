from app.rag.reranker import (
    CrossEncoderReranker,
    CrossEncoderRerankerConfig,
    RerankedRetriever,
    RerankingConfig,
)
from app.rag.retriever import MetadataFilter, RetrievalResult


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.pairs = []

    def predict(self, pairs):
        self.pairs.append(list(pairs))
        return self.scores


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


def result(chunk_id: str, text: str, score: float = 0.8) -> RetrievalResult:
    return RetrievalResult(
        point_id=f"{chunk_id}_POINT",
        score=score,
        payload={
            "chunk_id": chunk_id,
            "document_id": chunk_id.split("_")[0],
            "text": text,
        },
    )


def test_cross_encoder_reranker_orders_results_by_rerank_score() -> None:
    model = FakeCrossEncoder(scores=[0.1, 0.9, 0.4])
    reranker = CrossEncoderReranker(
        CrossEncoderRerankerConfig(model_name="fake-model"),
        model=model,
    )
    results = [
        result("DOC001_C0001", "setup steps"),
        result("DOC002_C0001", "factory reset procedure"),
        result("DOC003_C0001", "firmware upgrade"),
    ]

    reranked = reranker.rerank("How do I reset the router?", results)

    assert [item.chunk_id for item in reranked] == [
        "DOC002_C0001",
        "DOC003_C0001",
        "DOC001_C0001",
    ]
    assert reranked[0].score == 0.8
    assert reranked[0].rerank_score == 0.9
    assert reranked[0].payload["dense_score"] == 0.8
    assert model.pairs == [
        [
            ("How do I reset the router?", "setup steps"),
            ("How do I reset the router?", "factory reset procedure"),
            ("How do I reset the router?", "firmware upgrade"),
        ]
    ]


def test_reranked_retriever_limits_results_and_forwards_metadata_filter() -> None:
    candidates = [
        result("DOC001_C0001", "setup"),
        result("DOC002_C0001", "reset"),
        result("DOC003_C0001", "upgrade"),
    ]
    base_retriever = FakeRetriever(candidates)
    reranker = CrossEncoderReranker(
        CrossEncoderRerankerConfig(model_name="fake-model"),
        model=FakeCrossEncoder(scores=[0.2, 0.8, 0.6]),
    )
    retriever = RerankedRetriever(
        retriever=base_retriever,
        reranker=reranker,
        config=RerankingConfig(candidate_top_k=3, final_top_k=2),
    )
    metadata_filter = MetadataFilter(product="Router X")

    results = retriever.retrieve("reset?", metadata_filter=metadata_filter)

    assert base_retriever.calls == [("reset?", metadata_filter)]
    assert [item.chunk_id for item in results] == ["DOC002_C0001", "DOC003_C0001"]


def test_reranker_handles_empty_candidates_without_model_call() -> None:
    model = FakeCrossEncoder(scores=[])
    reranker = CrossEncoderReranker(
        CrossEncoderRerankerConfig(model_name="fake-model"),
        model=model,
    )

    assert reranker.rerank("reset?", []) == []
    assert model.pairs == []


def test_reranking_config_validates_limits() -> None:
    try:
        RerankingConfig(candidate_top_k=0)
    except ValueError as error:
        assert "candidate_top_k" in str(error)
    else:
        raise AssertionError("Expected candidate_top_k validation error")

    try:
        RerankingConfig(final_top_k=0)
    except ValueError as error:
        assert "final_top_k" in str(error)
    else:
        raise AssertionError("Expected final_top_k validation error")

    try:
        RerankingConfig(candidate_top_k=3, final_top_k=4)
    except ValueError as error:
        assert "final_top_k" in str(error)
    else:
        raise AssertionError("Expected final_top_k validation error")

    try:
        CrossEncoderRerankerConfig(model_name=" ")
    except ValueError as error:
        assert "model_name" in str(error)
    else:
        raise AssertionError("Expected model_name validation error")
