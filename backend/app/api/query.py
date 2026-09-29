from time import perf_counter

from fastapi import APIRouter, Depends

from app.api.dependencies import QueryPipeline, query_pipeline
from app.api.errors import ApiErrorCode, bad_request, service_unavailable
from app.api.schemas import QueryRequest, QueryResponse, SourceResponse
from app.core.config import get_settings
from app.rag.generator import GeneratedAnswer
from app.rag.retriever import MetadataFilter


router = APIRouter(prefix="/api")
settings = get_settings()


@router.post("/query", response_model=QueryResponse)
def query_support(
    payload: QueryRequest,
    pipeline: QueryPipeline = Depends(query_pipeline),
) -> QueryResponse:
    _validate_query_request(payload)
    started_at = perf_counter()
    try:
        generated_answer = pipeline.answer(
            payload.question.strip(),
            metadata_filter=_metadata_filter_from_query(payload),
        )
    except ValueError as error:
        raise bad_request(
            ApiErrorCode.INVALID_METADATA,
            str(error),
        ) from error
    except RuntimeError as error:
        raise service_unavailable(
            ApiErrorCode.QUERY_PIPELINE_FAILED,
            str(error),
        ) from error
    total_time_ms = (perf_counter() - started_at) * 1000
    return _query_response(generated_answer, total_time_ms=total_time_ms)


def _validate_query_request(payload: QueryRequest) -> None:
    question = payload.question.strip()
    if not question:
        raise bad_request(
            ApiErrorCode.EMPTY_QUESTION,
            "Question cannot be empty.",
            field="question",
        )
    if len(question) > settings.api_max_question_chars:
        raise bad_request(
            ApiErrorCode.QUESTION_TOO_LONG,
            (
                "Question exceeds the maximum length of "
                f"{settings.api_max_question_chars} characters."
            ),
            field="question",
        )
    for field_name in [
        "product",
        "version",
        "category",
        "language",
        "source_type",
        "document_id",
    ]:
        value = getattr(payload, field_name)
        if value is not None and not value.strip():
            raise bad_request(
                ApiErrorCode.INVALID_METADATA,
                f"{field_name} cannot be blank.",
                field=field_name,
            )


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


def _query_response(
    generated_answer: GeneratedAnswer,
    *,
    total_time_ms: float,
) -> QueryResponse:
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
                document=source.title,
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
        retrieval_time_ms=_optional_float_attr(
            generated_answer,
            "retrieval_time_ms",
        ),
        generation_time_ms=_optional_float_attr(
            generated_answer,
            "generation_time_ms",
        ),
        total_time_ms=round(total_time_ms, 3),
    )


def _optional_float_attr(value: object, name: str) -> float | None:
    raw_value = getattr(value, name, None)
    if raw_value is None:
        return None
    return float(raw_value)
