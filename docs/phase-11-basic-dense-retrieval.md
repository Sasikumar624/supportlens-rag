# SupportLens Phase 11 Basic Dense Retrieval

Status: Initial dense retrieval layer implemented.
Date: 2026-09-28

## Objective

Phase 11 retrieves the most relevant indexed chunks for a user question using dense vector search.

This phase does not generate answers with an LLM. The goal is to inspect retrieved chunks manually and verify that the indexed evidence is useful.

## Completed

- Added `backend/app/rag/retriever.py`.
- Added `DenseRetrievalConfig` for:
  - Qdrant collection config
  - top K result count
  - optional score threshold
- Added `DenseRetriever` for:
  - query embedding
  - Qdrant dense vector search
  - payload-backed retrieval results
- Added `RetrievalResult` with:
  - point ID
  - similarity score
  - chunk ID
  - document ID
  - title
  - source URL
  - page
  - section
  - text
  - citation label
- Added unit tests with fake embedders and fake Qdrant clients, so tests do not require Docker, network access, or a downloaded Hugging Face model.

## Current Strategy

The retrieval flow is:

```text
user question -> query embedding -> Qdrant query_points -> scored chunk results
```

The retriever asks Qdrant for payloads so the returned chunks include citation and debugging metadata.

## Current Limits

This is dense retrieval only.

It does not yet include:

- retrieval evaluation metrics
- metadata filtering
- keyword/BM25 retrieval
- hybrid retrieval
- reranking
- LLM answer generation
