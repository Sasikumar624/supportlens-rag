from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    product: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=100)
    source_type: str | None = Field(default=None, max_length=50)
    document_id: str | None = Field(default=None, max_length=100)
    conversation_context: list["ConversationContextTurn"] = Field(
        default_factory=list,
        max_length=6,
    )


class ConversationContextTurn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=1500)


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
    document_id: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=2000)
    product: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    source_type: str | None = Field(default=None, max_length=50)


class DocumentCreateResponse(BaseModel):
    status: str
    message: str
    document_id: str | None = None


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
    message: str


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=8000)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    feedback_id: int
    status: str
