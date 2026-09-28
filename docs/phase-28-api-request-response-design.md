# SupportLens Phase 28 API Request / Response Design

Status: Initial API contract schemas implemented.
Date: 2026-09-28

## Objective

Phase 28 makes the API request and response contracts explicit, reusable, and ready for frontend integration.

Phase 27 added endpoint behavior. Phase 28 separates and enriches the schema layer so clients have stable shapes for query, document, source, timing, and feedback data.

## Completed

- Added `backend/app/api/schemas.py`.
- Moved API request and response models out of individual routers into shared schema definitions.
- Updated query, document, and feedback routers to import shared schemas.
- Expanded `POST /api/query` response with:
  - `retrieval_time_ms`
  - `generation_time_ms`
  - `total_time_ms`
- Added `document` to source records so clients can display a simple document label without choosing between internal fields.
- Added `DocumentCreateRequest`.
- Added `DocumentCreateResponse`.
- Updated API tests to verify the enriched contract fields.
- Added the Phase 28 README roadmap entry.

## Query Request

```json
{
  "question": "How do I reset OpenWrt?",
  "product": "OpenWrt",
  "version": "current",
  "category": "troubleshooting",
  "language": "English",
  "source_type": "html",
  "document_id": "DOC003"
}
```

Only `question` is required. Metadata fields are optional filters.

## Query Response

```json
{
  "question": "How do I reset OpenWrt?",
  "answer": "Hold the reset button for ten seconds. [1]",
  "refused": false,
  "no_answer_reason": null,
  "sources": [
    {
      "source_id": 1,
      "chunk_id": "DOC003_C0001",
      "document_id": "DOC003",
      "document": "Failsafe mode, factory reset, and recovery mode",
      "title": "Failsafe mode, factory reset, and recovery mode",
      "category": "troubleshooting",
      "product": "OpenWrt",
      "version": "current",
      "page": null,
      "section": "Factory reset",
      "source_url": "https://openwrt.org/docs/guide-user/troubleshooting/failsafe_and_factory_reset",
      "score": 0.92
    }
  ],
  "retrieval_time_ms": null,
  "generation_time_ms": null,
  "total_time_ms": 12.4
}
```

`retrieval_time_ms` and `generation_time_ms` are nullable until the real pipeline exposes separate timings. `total_time_ms` is measured by the API endpoint now.

## Role Responsibilities

The schema role owns the public request and response models. It keeps API contracts stable and shared across routers.

The query request role captures the user question and optional metadata filters. It does not perform query processing itself.

The query response role returns the final answer, refusal state, citations, and timing fields.

The source response role exposes enough source metadata for a frontend to render citations, document labels, sections, URLs, and scores.

The document contract role defines how source registry records and future document-ingestion requests are represented over HTTP.

The feedback contract role defines how user ratings and comments are accepted and acknowledged.

The router role should stay thin. Routers validate inputs, call dependencies, and convert application objects into schema responses.

The frontend role can rely on stable field names instead of inspecting internal RAG objects.

## Current Limits

Separate retrieval and generation timings are not available from the RAG pipeline yet, so those fields are nullable.

Document creation is still a placeholder. The request contract exists, but storage and indexing behavior belong to later phases.

Error response contracts are still basic FastAPI errors. Detailed error handling belongs to Phase 29.
