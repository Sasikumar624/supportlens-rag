# SupportLens Phase 27 FastAPI Backend

Status: Initial API endpoint layer implemented.
Date: 2026-09-28

## Objective

Phase 27 exposes the first SupportLens backend API surface with health, query, document, and feedback endpoints.

This phase creates stable request and response contracts without forcing the local retriever, Qdrant index, or LLM to load during app import.

## Completed

- Kept `backend/app/main.py` focused on app setup, middleware, and router registration.
- Added separate API router modules under `backend/app/api/`:
  - `health.py`
  - `query.py`
  - `documents.py`
  - `feedback.py`
  - `dependencies.py`
- Added CORS middleware using `API_CORS_ORIGINS`.
- Kept `GET /health`.
- Added `POST /api/query`.
- Added `GET /api/documents`.
- Added `POST /api/documents`.
- Added `DELETE /api/documents/{document_id}`.
- Added `POST /api/feedback`.
- Added API tests in `backend/tests/test_api.py`.

## Endpoint Behavior

`GET /health` returns service status, app name, and environment.

`POST /api/query` accepts a support question plus optional metadata filters:

```json
{
  "question": "How do I reset OpenWrt?",
  "product": "OpenWrt",
  "category": "troubleshooting"
}
```

The endpoint calls `app.state.query_pipeline.answer(...)` when a pipeline is configured. If no query pipeline is attached yet, it returns `503 Service Unavailable` instead of loading models implicitly.

`GET /api/documents` reads `data/sources.csv` and returns the current source registry.

`POST /api/documents` returns `202 Accepted` as a reserved ingestion hook. Full upload, validation, indexing, and reindexing behavior belong to later phases.

`DELETE /api/documents/{document_id}` validates the document ID against the source registry. It returns a safe placeholder response because deleting from the registry and vector index is not enabled yet.

`POST /api/feedback` accepts a question, answer, rating, and optional comment. Feedback is stored in app memory for this phase.

## Role Responsibilities

The API role owns HTTP contracts, request validation, response shapes, status codes, and dependency boundaries. Endpoint groups live in separate router modules so query, document, feedback, and health behavior can evolve independently.

The query pipeline role owns retrieval, no-answer handling, prompt construction, LLM generation, and citations. The API calls it but does not perform RAG logic itself.

The metadata filter role converts optional API fields into `MetadataFilter` so product, version, category, language, source type, and document ID can constrain retrieval.

The document registry role exposes source metadata from `data/sources.csv`. It does not modify the registry in this phase.

The ingestion role is reserved behind `POST /api/documents`. It will later validate uploads or source records and trigger indexing.

The deletion role is intentionally conservative. It confirms known document IDs but does not remove registry entries or vector payloads until persistence and reindexing flows exist.

The feedback role captures user ratings and comments. In this phase it uses in-memory storage only, but the response contract is ready for persistent storage later.

The frontend/product role can now call stable endpoints for health, queries, source listing, document actions, and feedback.

## Current Limits

The query pipeline is not auto-wired at app startup yet. A caller must attach a compatible object to `app.state.query_pipeline`.

Feedback is not persisted across process restarts.

Document creation and deletion are API placeholders. Full document management should be implemented with storage, index updates, audit logging, and failure handling in later phases.
