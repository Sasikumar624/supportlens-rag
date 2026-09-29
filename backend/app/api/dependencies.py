from pathlib import Path
from typing import Any, Protocol

from fastapi import Request

from app.api.errors import ApiErrorCode, service_unavailable
from app.rag.generator import GeneratedAnswer
from app.rag.retriever import MetadataFilter


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_CSV = REPO_ROOT / "data" / "sources.csv"


class QueryPipeline(Protocol):
    def answer(
        self,
        question: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> GeneratedAnswer:
        ...


def query_pipeline(request: Request) -> QueryPipeline:
    pipeline = getattr(request.app.state, "query_pipeline", None)
    if pipeline is None:
        raise service_unavailable(
            ApiErrorCode.QUERY_PIPELINE_UNAVAILABLE,
            "Query pipeline is not configured.",
        )
    return pipeline


def feedback_store(request: Request) -> list[dict[str, Any]]:
    feedback_items = getattr(request.app.state, "feedback_items", None)
    if feedback_items is None:
        feedback_items = []
        request.app.state.feedback_items = feedback_items
    return feedback_items
