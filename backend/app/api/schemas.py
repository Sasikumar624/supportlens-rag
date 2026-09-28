from pydantic import BaseModel, Field


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
    document: str | None
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
    retrieval_time_ms: float | None
    generation_time_ms: float | None
    total_time_ms: float


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


class DocumentCreateRequest(BaseModel):
    document_id: str | None = None
    title: str | None = None
    source_url: str | None = None
    product: str | None = None
    version: str | None = None
    category: str | None = None
    source_type: str | None = None


class DocumentCreateResponse(BaseModel):
    status: str
    message: str
    document_id: str | None = None


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
    message: str


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    status: str
