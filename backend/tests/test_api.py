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


def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint_returns_app_status() -> None:
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "SupportLens"


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
    assert pipeline.calls == [
        (
            "How do I reset OpenWrt?",
            MetadataFilter(product="OpenWrt", category="troubleshooting"),
        )
    ]

    del app.state.query_pipeline


def test_query_endpoint_returns_service_unavailable_without_pipeline() -> None:
    if hasattr(app.state, "query_pipeline"):
        del app.state.query_pipeline

    response = client().post(
        "/api/query",
        json={"question": "How do I reset OpenWrt?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Query pipeline is not configured."


def test_documents_endpoint_lists_source_registry() -> None:
    response = client().get("/api/documents")

    assert response.status_code == 200
    documents = response.json()
    assert len(documents) >= 5
    assert documents[0]["document_id"] == "DOC001"
    assert documents[0]["source_type"] == "html"


def test_document_delete_endpoint_is_safe_registry_placeholder() -> None:
    response = client().delete("/api/documents/DOC001")

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "DOC001",
        "deleted": False,
        "message": "Document deletion is not enabled for the source registry yet.",
    }

    missing = client().delete("/api/documents/DOES_NOT_EXIST")
    assert missing.status_code == 404


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


def test_document_create_endpoint_is_reserved_for_ingestion() -> None:
    response = client().post("/api/documents")

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
