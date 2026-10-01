import re
from dataclasses import replace
from time import perf_counter

from fastapi import APIRouter, Depends

from app.api.dependencies import QueryPipeline, SOURCES_CSV, query_pipeline
from app.api.errors import ApiErrorCode, bad_request, service_unavailable
from app.api.schemas import QueryRequest, QueryResponse, SourceResponse
from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.loaders import load_sources_csv
from app.rag.generator import GeneratedAnswer, SourceCitation
from app.rag.retriever import MetadataFilter


router = APIRouter(prefix="/api")
settings = get_settings()
logger = get_logger(__name__)

PRODUCT_INVENTORY_PATTERNS = (
    re.compile(r"\b(?:list|show)\s+(?:the\s+)?products\b", re.IGNORECASE),
    re.compile(
        r"\bwhat\s+products\s+(?:are\s+)?(?:available|indexed|included)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhich\s+products\s+(?:are\s+)?(?:available|indexed|included)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bproducts\s+(?:in|inside)\s+(?:the\s+)?(?:knowledge\s+base|corpus)\b",
        re.IGNORECASE,
    ),
)


@router.post("/query", response_model=QueryResponse)
def query_support(
    payload: QueryRequest,
    pipeline: QueryPipeline = Depends(query_pipeline),
) -> QueryResponse:
    _validate_query_request(payload)
    started_at = perf_counter()
    try:
        question = payload.question.strip()
        retrieval_question = _question_with_conversation_context(payload)
        metadata_filter = _metadata_filter_from_query(payload)
        if metadata_filter is None and _is_product_inventory_question(question):
            generated_answer = _answer_product_inventory(question)
        else:
            generated_answer = pipeline.answer(
                retrieval_question,
                metadata_filter=metadata_filter,
            )
            if generated_answer.question != question:
                generated_answer = replace(generated_answer, question=question)
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
    logger.info(
        "query_completed refused=%s source_count=%s total_time_ms=%.3f",
        generated_answer.refused,
        len(generated_answer.sources),
        total_time_ms,
    )
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


def _question_with_conversation_context(payload: QueryRequest) -> str:
    question = payload.question.strip()
    context_turns = [
        turn
        for turn in payload.conversation_context[-3:]
        if turn.question.strip() and turn.answer.strip()
    ]
    if not context_turns:
        return question

    context_lines = []
    for index, turn in enumerate(context_turns, start=1):
        context_lines.extend(
            [
                f"Previous question {index}: {_compact_context_value(turn.question)}",
                f"Previous answer {index}: {_compact_context_value(turn.answer)}",
            ]
        )
    return "\n".join(
        [
            "Use this recent conversation only to resolve follow-up references.",
            *context_lines,
            f"Current question: {question}",
        ]
    )


def _compact_context_value(value: str, *, max_chars: int = 500) -> str:
    compacted = " ".join(value.strip().split())
    if len(compacted) <= max_chars:
        return compacted
    return compacted[:max_chars].rsplit(" ", 1)[0].rstrip(" .,;:") + "."


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


def _is_product_inventory_question(question: str) -> bool:
    normalized = " ".join(question.strip().split())
    if normalized.lower().strip("?.!") == "products":
        return True
    return any(pattern.search(normalized) for pattern in PRODUCT_INVENTORY_PATTERNS)


def _answer_product_inventory(question: str) -> GeneratedAnswer:
    sources = load_sources_csv(SOURCES_CSV)
    product_sources = {}
    for source in sources:
        product_sources.setdefault(source.product, source)

    citations = [
        SourceCitation(
            source_id=index,
            chunk_id=None,
            document_id=source.document_id,
            title=source.title,
            category=source.category,
            product=source.product,
            version=source.version,
            page=None,
            section="Product inventory",
            source_url=source.source_url,
            score=1.0,
        )
        for index, source in enumerate(product_sources.values(), start=1)
    ]
    answer_lines = [
        "The indexed knowledge base currently includes these products:",
        "",
        *[
            f"- {citation.product} [{citation.source_id}]"
            for citation in citations
            if citation.product
        ],
    ]
    return GeneratedAnswer(
        question=question,
        answer="\n".join(answer_lines),
        sources=citations,
        context_chunks=[],
    )


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
