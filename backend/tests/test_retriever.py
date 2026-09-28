from dataclasses import dataclass

from app.db.qdrant import QdrantCollectionConfig
from app.rag.retriever import DenseRetrievalConfig, DenseRetriever


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return [0.1, 0.2, 0.3]


@dataclass(frozen=True)
class FakePoint:
    id: str
    score: float
    payload: dict


@dataclass(frozen=True)
class FakeQueryResponse:
    points: list[FakePoint]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def query_points(
        self,
        *,
        collection_name: str,
        query: list[float],
        limit: int,
        with_payload: bool,
        score_threshold: float | None = None,
    ) -> FakeQueryResponse:
        self.calls.append(
            {
                "collection_name": collection_name,
                "query": query,
                "limit": limit,
                "with_payload": with_payload,
                "score_threshold": score_threshold,
            }
        )
        return FakeQueryResponse(
            points=[
                FakePoint(
                    id="point-1",
                    score=0.91,
                    payload={
                        "chunk_id": "DOC_TEST_C0001",
                        "document_id": "DOC_TEST",
                        "title": "Router Guide",
                        "source_url": "https://example.com/router",
                        "page": 3,
                        "section": "Factory Reset",
                        "text": "Hold the reset button for ten seconds.",
                    },
                )
            ]
        )


def config(top_k: int = 5, score_threshold: float | None = None) -> DenseRetrievalConfig:
    return DenseRetrievalConfig(
        collection=QdrantCollectionConfig(
            url="http://localhost:6333",
            collection_name="supportlens_chunks",
            vector_size=3,
        ),
        top_k=top_k,
        score_threshold=score_threshold,
    )


def test_dense_retriever_embeds_query_and_searches_qdrant() -> None:
    client = FakeQdrantClient()
    embedder = FakeEmbedder()
    retriever = DenseRetriever(
        config(top_k=3, score_threshold=0.5),
        client=client,
        embedder=embedder,
    )

    results = retriever.retrieve("How do I factory reset the router?")

    assert embedder.queries == ["How do I factory reset the router?"]
    assert client.calls == [
        {
            "collection_name": "supportlens_chunks",
            "query": [0.1, 0.2, 0.3],
            "limit": 3,
            "with_payload": True,
            "score_threshold": 0.5,
        }
    ]
    assert len(results) == 1
    assert results[0].point_id == "point-1"
    assert results[0].score == 0.91
    assert results[0].chunk_id == "DOC_TEST_C0001"
    assert results[0].document_id == "DOC_TEST"
    assert results[0].text == "Hold the reset button for ten seconds."


def test_retrieval_result_builds_citation_label() -> None:
    result = DenseRetriever(
        config(),
        client=FakeQdrantClient(),
        embedder=FakeEmbedder(),
    ).retrieve("reset")[0]

    assert result.citation_label == "Router Guide - Page 3 - Factory Reset"


def test_dense_retriever_rejects_empty_queries() -> None:
    retriever = DenseRetriever(
        config(),
        client=FakeQdrantClient(),
        embedder=FakeEmbedder(),
    )

    try:
        retriever.retrieve("   ")
    except ValueError as error:
        assert "query" in str(error)
    else:
        raise AssertionError("Expected query validation error")


def test_dense_retrieval_config_validates_limits() -> None:
    try:
        config(top_k=0)
    except ValueError as error:
        assert "top_k" in str(error)
    else:
        raise AssertionError("Expected top_k validation error")

    try:
        config(score_threshold=-0.1)
    except ValueError as error:
        assert "score_threshold" in str(error)
    else:
        raise AssertionError("Expected score_threshold validation error")
