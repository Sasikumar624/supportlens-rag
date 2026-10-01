from fastapi.testclient import TestClient

from app.main import app
from app.rag.generator import GeneratedAnswer, SourceCitation
from app.rag.retriever import MetadataFilter


class FakeQueryPipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, MetadataFilter | None]] = []

    def answer(
        self,
        question: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> GeneratedAnswer:
        self.calls.append((question, metadata_filter))
        return GeneratedAnswer(
            question=question,
            answer="Hold the reset button for ten seconds. [1]",
            sources=[
                SourceCitation(
                    source_id=1,
                    chunk_id="DOC003_C0001",
                    document_id="DOC003",
                    title="Failsafe mode, factory reset, and recovery mode",
                    category="troubleshooting",
                    product="OpenWrt",
                    version="current",
                    page=None,
                    section="Factory reset",
                    source_url="https://openwrt.org/docs/guide-user/troubleshooting/failsafe_and_factory_reset",
                    score=0.92,
                )
            ],
            context_chunks=[],
        )


class FailingQueryPipeline:
    def answer(
        self,
        question: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> GeneratedAnswer:
        raise RuntimeError("LLM unavailable")


def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint_returns_app_status() -> None:
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "SupportLens"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-ID"]


def test_api_preserves_request_id_header() -> None:
    response = client().get(
        "/health",
        headers={"X-Request-ID": "test-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_query_endpoint_returns_generated_answer_and_sources() -> None:
    pipeline = FakeQueryPipeline()
    app.state.query_pipeline = pipeline

    response = client().post(
        "/api/query",
        json={
            "question": "How do I reset OpenWrt?",
            "product": "OpenWrt",
            "category": "troubleshooting",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Hold the reset button for ten seconds. [1]"
    assert body["refused"] is False
    assert body["sources"][0]["document_id"] == "DOC003"
    assert body["sources"][0]["document"] == (
        "Failsafe mode, factory reset, and recovery mode"
    )
    assert body["retrieval_time_ms"] is None
    assert body["generation_time_ms"] is None
    assert body["total_time_ms"] >= 0.0
    assert pipeline.calls == [
        (
            "How do I reset OpenWrt?",
            MetadataFilter(product="OpenWrt", category="troubleshooting"),
        )
    ]

    del app.state.query_pipeline


def test_query_endpoint_answers_product_inventory_from_source_registry() -> None:
    pipeline = FakeQueryPipeline()
    app.state.query_pipeline = pipeline

    response = client().post(
        "/api/query",
        json={"question": "List the products"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (
        "The indexed knowledge base currently includes these products:"
        in body["answer"]
    )
    assert "- OpenWrt [1]" in body["answer"]
    assert "- TP-Link Archer AX21 [2]" in body["answer"]
    assert "- TP-Link Archer AX55 [3]" in body["answer"]
    assert "- TP-Link Routers [4]" in body["answer"]
    assert "- NETGEAR Routers [5]" in body["answer"]
    assert "- ASUS Routers [6]" in body["answer"]
    assert "- ASUS RT-AX55 [7]" in body["answer"]
    assert body["refused"] is False
    assert [source["product"] for source in body["sources"]] == [
        "OpenWrt",
        "TP-Link Archer AX21",
        "TP-Link Archer AX55",
        "TP-Link Routers",
        "NETGEAR Routers",
        "ASUS Routers",
        "ASUS RT-AX55",
    ]
    assert pipeline.calls == []

    del app.state.query_pipeline


def test_query_endpoint_returns_service_unavailable_without_pipeline() -> None:
    if hasattr(app.state, "query_pipeline"):
        del app.state.query_pipeline

    response = client().post(
        "/api/query",
        json={"question": "How do I reset OpenWrt?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "query_pipeline_unavailable",
        "message": "Query pipeline is not configured.",
    }


def test_query_endpoint_returns_structured_validation_errors() -> None:
    app.state.query_pipeline = FakeQueryPipeline()

    empty_question = client().post(
        "/api/query",
        json={"question": "   "},
    )
    assert empty_question.status_code == 400
    assert empty_question.json()["detail"] == {
        "code": "empty_question",
        "message": "Question cannot be empty.",
        "field": "question",
    }

    long_question = client().post(
        "/api/query",
        json={"question": "x" * 2001},
    )
    assert long_question.status_code == 400
    assert long_question.json()["detail"]["code"] == "question_too_long"

    blank_metadata = client().post(
        "/api/query",
        json={"question": "How do I reset OpenWrt?", "product": "  "},
    )
    assert blank_metadata.status_code == 400
    assert blank_metadata.json()["detail"] == {
        "code": "invalid_metadata",
        "message": "product cannot be blank.",
        "field": "product",
    }

    del app.state.query_pipeline


def test_api_rejects_oversized_request_body() -> None:
    app.state.query_pipeline = FakeQueryPipeline()

    response = client().post(
        "/api/query",
        json={"question": "x" * 40000},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "request_too_large"

    del app.state.query_pipeline


def test_query_endpoint_maps_pipeline_failures_to_service_unavailable() -> None:
    app.state.query_pipeline = FailingQueryPipeline()

    response = client().post(
        "/api/query",
        json={"question": "How do I reset OpenWrt?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "query_pipeline_failed",
        "message": "LLM unavailable",
    }

    del app.state.query_pipeline


def test_documents_endpoint_lists_source_registry() -> None:
    response = client().get("/api/documents")

    assert response.status_code == 200
    documents = response.json()
    assert len(documents) >= 5
    assert documents[0]["document_id"] == "DOC001"
    assert documents[0]["source_type"] == "html"


def test_document_delete_endpoint_is_safe_registry_placeholder() -> None:
    response = client().delete("/api/documents/DOC001")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "document_deletion_not_configured",
        "message": "Document deletion is not enabled for the source registry yet.",
    }

    missing = client().delete("/api/documents/DOES_NOT_EXIST")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "document_not_found"


def test_feedback_endpoint_stores_in_memory_feedback() -> None:
    if hasattr(app.state, "feedback_items"):
        del app.state.feedback_items

    response = client().post(
        "/api/feedback",
        json={
            "question": "How do I reset OpenWrt?",
            "answer": "Hold the reset button.",
            "rating": 4,
            "comment": "Useful answer",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"feedback_id": 1, "status": "stored"}
    assert app.state.feedback_items[0]["rating"] == 4

    invalid_comment = client().post(
        "/api/feedback",
        json={
            "question": "How do I reset OpenWrt?",
            "answer": "Hold the reset button.",
            "rating": 4,
            "comment": "x" * 1001,
        },
    )
    assert invalid_comment.status_code == 422


def test_document_create_endpoint_is_reserved_for_ingestion() -> None:
    empty_response = client().post("/api/documents")
    assert empty_response.status_code == 202
    assert empty_response.json()["status"] == "accepted"

    duplicate = client().post(
        "/api/documents",
        json={
            "document_id": "DOC001",
            "title": "Existing guide",
            "source_url": "https://example.com/router",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_document"

    response = client().post(
        "/api/documents",
        json={
            "document_id": "DOC_NEW",
            "title": "New router guide",
            "source_url": "https://example.com/router",
            "product": "Router X",
            "version": "v1",
            "category": "setup",
            "source_type": "html",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "document_ingestion_not_configured",
        "message": "Document ingestion is not configured yet.",
    }
