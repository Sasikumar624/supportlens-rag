from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import SOURCES_CSV
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
    return DocumentCreateResponse(
        status="accepted",
        message="Document ingestion endpoint is reserved for Phase 27 API wiring.",
        document_id=payload.document_id if payload is not None else None,
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(document_id: str) -> DocumentDeleteResponse:
    known_document_ids = {
        source.document_id for source in load_sources_csv(SOURCES_CSV)
    }
    if document_id not in known_document_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document_id: {document_id}",
        )
    return DocumentDeleteResponse(
        document_id=document_id,
        deleted=False,
        message="Document deletion is not enabled for the source registry yet.",
    )
