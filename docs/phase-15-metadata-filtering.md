# SupportLens Phase 15 Metadata Filtering

Status: Initial retrieval metadata filtering implemented.
Date: 2026-09-28

## Objective

Phase 15 lets dense retrieval limit results by chunk metadata such as product, version, category, language, source type, or document ID.

This helps queries like "How do I reset Router X?" retrieve evidence from the relevant product instead of similar but wrong documents.

## Completed

- Added `MetadataFilter` to `backend/app/rag/retriever.py`.
- Added supported filters for:
  - product
  - version
  - category
  - language
  - source type
  - document ID
- Added conversion from `MetadataFilter` to Qdrant `Filter` conditions.
- Wired metadata filters into `DenseRetriever.retrieve()`.
- Preserved unfiltered retrieval behavior when no filter is provided.
- Added tests for:
  - passing filters into Qdrant search
  - empty filters
  - invalid blank filter values

## Current Strategy

Callers can pass filters explicitly:

```python
retriever.retrieve(
    "How do I reset Router X?",
    metadata_filter=MetadataFilter(product="Router X", category="troubleshooting"),
)
```

The retriever converts that into a Qdrant payload filter before running dense vector search.

## Current Limits

Filters are not inferred automatically from the question yet.

Automatic product, version, error-code, and category detection belongs to the later query-processing phase.
