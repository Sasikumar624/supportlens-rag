from fastapi import APIRouter, status

from app.api.dependencies import SOURCES_CSV
from app.api.errors import ApiErrorCode, conflict, not_found, service_unavailable
from app.api.schemas import (
    DocumentCreateRequest,
    DocumentCreateResponse,
    DocumentDeleteResponse,
    DocumentResponse,
)
from app.ingestion.loaders import load_sources_csv


router = APIRouter(prefix="/api/documents")


@router.get("", response_model=list[DocumentResponse])
def list_documents() -> list[DocumentResponse]:
    return [
        DocumentResponse(
            document_id=source.document_id,
            title=source.title,
            category=source.category,
            product=source.product,
            version=source.version,
            language=source.language,
            source_url=source.source_url,
            source_type=source.source_type,
            raw_storage_policy=source.raw_storage_policy,
        )
        for source in load_sources_csv(SOURCES_CSV)
    ]


@router.post(
    "",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_document(
    payload: DocumentCreateRequest | None = None,
) -> DocumentCreateResponse:
    if payload is not None and payload.document_id in _known_document_ids():
        raise conflict(
            ApiErrorCode.DUPLICATE_DOCUMENT,
            f"Document already exists: {payload.document_id}",
            field="document_id",
        )
    if payload is not None:
        raise service_unavailable(
            ApiErrorCode.DOCUMENT_INGESTION_NOT_CONFIGURED,
            "Document ingestion is not configured yet.",
        )
    return DocumentCreateResponse(
        status="accepted",
        message="Document ingestion endpoint is reserved for Phase 27 API wiring.",
        document_id=None,
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(document_id: str) -> DocumentDeleteResponse:
    if document_id not in _known_document_ids():
        raise not_found(
            ApiErrorCode.DOCUMENT_NOT_FOUND,
            f"Unknown document_id: {document_id}",
            field="document_id",
        )
    raise service_unavailable(
        ApiErrorCode.DOCUMENT_DELETION_NOT_CONFIGURED,
        "Document deletion is not enabled for the source registry yet.",
    )


def _known_document_ids() -> set[str]:
    return {source.document_id for source in load_sources_csv(SOURCES_CSV)}
