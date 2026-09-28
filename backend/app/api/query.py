from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import QueryPipeline, query_pipeline
from app.rag.generator import GeneratedAnswer
from app.rag.retriever import MetadataFilter


router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    product: str | None = None
    version: str | None = None
    category: str | None = None
    language: str | None = None
    source_type: str | None = None
    document_id: str | None = None


class SourceResponse(BaseModel):
    source_id: int
    chunk_id: str | None
    document_id: str | None
    title: str | None
    category: str | None
    product: str | None
    version: str | None
    page: int | None
    section: str | None
    source_url: str | None
    score: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    refused: bool
    no_answer_reason: str | None
    sources: list[SourceResponse]


@router.post("/query", response_model=QueryResponse)
def query_support(
    payload: QueryRequest,
    pipeline: QueryPipeline = Depends(query_pipeline),
) -> QueryResponse:
    generated_answer = pipeline.answer(
        payload.question,
        metadata_filter=_metadata_filter_from_query(payload),
    )
    return _query_response(generated_answer)


def _metadata_filter_from_query(payload: QueryRequest) -> MetadataFilter | None:
    metadata_filter = MetadataFilter(
        product=payload.product,
        version=payload.version,
        category=payload.category,
        language=payload.language,
        source_type=payload.source_type,
        document_id=payload.document_id,
    )
    return None if metadata_filter.is_empty else metadata_filter


def _query_response(generated_answer: GeneratedAnswer) -> QueryResponse:
    return QueryResponse(
        question=generated_answer.question,
        answer=generated_answer.answer,
        refused=generated_answer.refused,
        no_answer_reason=generated_answer.no_answer_reason,
        sources=[
            SourceResponse(
                source_id=source.source_id,
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                title=source.title,
                category=source.category,
                product=source.product,
                version=source.version,
                page=source.page,
                section=source.section,
                source_url=source.source_url,
                score=source.score,
            )
            for source in generated_answer.sources
        ],
    )
