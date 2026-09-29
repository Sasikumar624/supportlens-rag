# SupportLens Phase 29 Backend Error Handling

Status: Initial structured API error handling implemented.
Date: 2026-09-28

## Objective

Phase 29 gives the backend predictable error responses for common API failures.

Earlier phases relied mostly on FastAPI defaults or plain `HTTPException` strings. This phase introduces application-level error codes so clients can handle failures consistently.

## Completed

- Added `backend/app/api/errors.py`.
- Added structured API error codes for:
  - empty questions
  - questions over the configured maximum length
  - invalid metadata filters
  - unavailable query pipeline
  - query pipeline runtime failures
  - duplicate documents
  - unknown documents
  - document ingestion not configured
  - document deletion not configured
- Added `API_MAX_QUESTION_CHARS` to settings and `.env.example`.
- Updated `POST /api/query` to:
  - trim questions before pipeline execution
  - reject whitespace-only questions
  - reject overlong questions
  - reject blank metadata fields
  - map `ValueError` to `400 Bad Request`
  - map `RuntimeError` to `503 Service Unavailable`
- Updated query-pipeline dependency errors to use structured responses.
- Updated document endpoints to:
  - return `409 Conflict` for duplicate document IDs
  - return `404 Not Found` for unknown document IDs
  - return `503 Service Unavailable` for ingestion/deletion behavior that is not configured yet
- Expanded API tests for structured error responses.

## Error Shape

Errors use FastAPI's `detail` field with a structured object:

```json
{
  "detail": {
    "code": "empty_question",
    "message": "Question cannot be empty.",
    "field": "question"
  }
}
```

`field` is included when the error maps to a specific request field.

## Current Error Codes

```text
empty_question
question_too_long
invalid_metadata
query_pipeline_unavailable
query_pipeline_failed
duplicate_document
document_not_found
document_ingestion_not_configured
document_deletion_not_configured
```

## Role Responsibilities

The error contract role owns stable machine-readable error codes and response shape.

The query validation role protects the pipeline from empty, oversized, or malformed query inputs.

The metadata validation role rejects blank metadata strings before they become invalid retriever filters.

The pipeline error role maps unavailable or failed RAG dependencies into clear service errors instead of raw stack traces.

The document error role distinguishes duplicate, missing, and not-yet-configured document operations.

The API router role stays responsible for translating request failures into HTTP status codes.

The frontend role can branch on `detail.code` instead of parsing human-readable messages.

## Current Limits

Unsupported file types, corrupted documents, Qdrant outages, embedding failures, LLM timeouts, and upload-size errors will need deeper ingestion, storage, and runtime wiring before they can be handled precisely.

FastAPI/Pydantic validation errors still use the default 422 response shape. Those can be normalized later if the frontend needs every error to share the same envelope.
