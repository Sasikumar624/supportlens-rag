from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import SOURCES_CSV
from app.ingestion.loaders import load_sources_csv


router = APIRouter(prefix="/api/documents")


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    category: str
    product: str
    version: str
    language: str
    source_url: str
    source_type: str
    raw_storage_policy: str


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
    message: str


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


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_document() -> dict[str, str]:
    return {
        "status": "accepted",
        "message": "Document ingestion endpoint is reserved for Phase 27 API wiring.",
    }


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
