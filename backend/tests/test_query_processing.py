from app.rag.query_processing import (
    QueryProcessingConfig,
    QueryProcessingRetriever,
    QueryProcessor,
    detect_identifiers,
    merge_metadata_filters,
    normalize_query,
)
from app.rag.retriever import MetadataFilter, RetrievalResult


class FakeRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, MetadataFilter | None]] = []

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        self.calls.append((query, metadata_filter))
        return [
            RetrievalResult(
                point_id="point-1",
                score=0.9,
                payload={
                    "chunk_id": "DOC001_C0001",
                    "document_id": "DOC001",
                    "text": "Retrieved text",
                },
            )
        ]


def test_normalize_query_collapses_whitespace_without_rewriting_identifiers() -> None:
    query = "  How   do I fix   ERR_105 on  FW_2.3.17?  "

    assert normalize_query(query) == "How do I fix ERR_105 on FW_2.3.17?"


def test_detect_identifiers_preserves_exact_technical_tokens() -> None:
    identifiers = detect_identifiers(
        "ERR_105 on AX4200 after FW_2.3.17 at 192.168.0.1"
    )

    assert identifiers.error_codes == ["ERR_105"]
    assert identifiers.model_numbers == ["AX4200"]
    assert identifiers.firmware_versions == ["FW_2.3.17"]
    assert identifiers.ip_addresses == ["192.168.0.1"]
    assert identifiers.all == ["ERR_105", "FW_2.3.17", "AX4200", "192.168.0.1"]


def test_query_processor_detects_product_version_and_category_filter() -> None:
    processor = QueryProcessor()

    processed = processor.process(
        "How do I upgrade OpenWrt current firmware using LuCI?"
    )

    assert processed.normalized_query == (
        "How do I upgrade OpenWrt current firmware using LuCI?"
    )
    assert processed.detected_product == "OpenWrt"
    assert processed.detected_version == "current"
    assert processed.detected_category == "firmware"
    assert processed.metadata_filter == MetadataFilter(
        product="OpenWrt",
        version="current",
        category="firmware",
    )


def test_query_processor_supports_custom_products_and_categories() -> None:
    processor = QueryProcessor(
        QueryProcessingConfig(
            known_products=("Router X",),
            known_versions=("v2",),
            category_aliases={"troubleshooting": ("error", "ERR_105")},
        )
    )

    processed = processor.process("Router X v2 shows ERR_105")

    assert processed.detected_product == "Router X"
    assert processed.detected_version == "v2"
    assert processed.detected_category == "troubleshooting"


def test_query_processing_retriever_uses_normalized_query_and_inferred_filter() -> None:
    base_retriever = FakeRetriever()
    retriever = QueryProcessingRetriever(base_retriever)

    results = retriever.retrieve("  OpenWrt   Wi-Fi configuration  ")

    assert results[0].chunk_id == "DOC001_C0001"
    assert base_retriever.calls == [
        (
            "OpenWrt Wi-Fi configuration",
            MetadataFilter(product="OpenWrt", category="configuration"),
        )
    ]
    assert retriever.last_processed_query is not None
    assert retriever.last_processed_query.detected_category == "configuration"


def test_explicit_metadata_filter_overrides_inferred_values() -> None:
    explicit = MetadataFilter(product="Router X", language="English")
    inferred = MetadataFilter(product="OpenWrt", category="firmware", version="current")

    merged = merge_metadata_filters(
        explicit_filter=explicit,
        inferred_filter=inferred,
    )

    assert merged == MetadataFilter(
        product="Router X",
        version="current",
        category="firmware",
        language="English",
    )


def test_query_processing_validates_inputs() -> None:
    processor = QueryProcessor()

    try:
        processor.process("  ")
    except ValueError as error:
        assert "query" in str(error)
    else:
        raise AssertionError("Expected query validation error")

    try:
        QueryProcessingConfig(known_products=("OpenWrt", " "))
    except ValueError as error:
        assert "known_products" in str(error)
    else:
        raise AssertionError("Expected known_products validation error")

    try:
        QueryProcessingConfig(category_aliases={"setup": (" ",)})
    except ValueError as error:
        assert "aliases" in str(error)
    else:
        raise AssertionError("Expected category alias validation error")
