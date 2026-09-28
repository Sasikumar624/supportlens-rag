from app.rag.keyword_retriever import (
    KeywordRetrievalConfig,
    KeywordRetriever,
    tokenize_for_keyword_search,
)
from app.rag.retriever import MetadataFilter, RetrievalResult


def payload(
    chunk_id: str,
    text: str,
    *,
    product: str = "Router X",
    version: str = "FW_2.3.17",
    category: str = "troubleshooting",
) -> dict:
    document_id = chunk_id.split("_C")[0]
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "title": f"{product} Support Guide",
        "product": product,
        "version": version,
        "category": category,
        "language": "English",
        "source_type": "html",
        "section": "Errors",
        "text": text,
    }


def test_keyword_tokenizer_preserves_exact_identifier_tokens() -> None:
    tokens = tokenize_for_keyword_search(
        "ERR_105 on AX4200 after FW_2.3.17 at 192.168.0.1"
    )

    assert "err_105" in tokens
    assert "ax4200" in tokens
    assert "fw_2.3.17" in tokens
    assert "192.168.0.1" in tokens


def test_keyword_retriever_ranks_exact_identifier_matches_first() -> None:
    retriever = KeywordRetriever(
        [
            payload(
                "DOC001_C0001",
                "General router setup steps for connecting the WAN cable.",
            ),
            payload(
                "DOC002_C0001",
                "ERR_105 means the AX4200 cannot reach the configured gateway.",
            ),
            payload(
                "DOC003_C0001",
                "Factory reset steps for restoring default settings.",
            ),
        ]
    )

    results = retriever.retrieve("How do I fix ERR_105 on AX4200?")

    assert [result.chunk_id for result in results][:1] == ["DOC002_C0001"]
    assert results[0].score == results[0].keyword_score
    assert results[0].keyword_score is not None
    assert results[0].keyword_score > 0.0


def test_keyword_retriever_searches_metadata_fields() -> None:
    retriever = KeywordRetriever(
        [
            payload("DOC001_C0001", "Basic setup.", product="Router X"),
            payload("DOC002_C0001", "Setup for the gateway.", product="AX4200"),
            payload("DOC003_C0001", "Troubleshooting notes.", product="Router Z"),
        ]
    )

    results = retriever.retrieve("AX4200 setup")

    assert results[0].chunk_id == "DOC002_C0001"


def test_keyword_retriever_applies_metadata_filter_and_top_k() -> None:
    retriever = KeywordRetriever(
        [
            payload("DOC001_C0001", "ERR_105 reset procedure.", product="Router X"),
            payload("DOC002_C0001", "ERR_105 reset procedure.", product="Router Y"),
            payload("DOC003_C0001", "ERR_105 reset procedure.", product="Router X"),
        ],
        KeywordRetrievalConfig(top_k=1),
    )

    results = retriever.retrieve(
        "ERR_105 reset",
        metadata_filter=MetadataFilter(product="Router X"),
    )

    assert len(results) == 1
    assert results[0].product == "Router X"


def test_keyword_retriever_can_build_from_retrieval_results() -> None:
    dense_results = [
        RetrievalResult(
            point_id="point-1",
            score=0.4,
            payload=payload("DOC001_C0001", "Use 192.168.0.1 to open the admin UI."),
        )
    ]

    retriever = KeywordRetriever.from_results(dense_results)
    results = retriever.retrieve("192.168.0.1")

    assert results[0].chunk_id == "DOC001_C0001"


def test_keyword_retriever_rejects_invalid_inputs() -> None:
    retriever = KeywordRetriever([])

    assert retriever.retrieve("ERR_105") == []
    assert KeywordRetriever([{}]).retrieve("ERR_105") == []

    try:
        retriever.retrieve(" ")
    except ValueError as error:
        assert "query" in str(error)
    else:
        raise AssertionError("Expected query validation error")

    try:
        KeywordRetrievalConfig(top_k=0)
    except ValueError as error:
        assert "top_k" in str(error)
    else:
        raise AssertionError("Expected top_k validation error")

    try:
        KeywordRetrievalConfig(min_score=-0.1)
    except ValueError as error:
        assert "min_score" in str(error)
    else:
        raise AssertionError("Expected min_score validation error")
