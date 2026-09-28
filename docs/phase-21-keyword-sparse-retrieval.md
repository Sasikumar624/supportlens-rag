# SupportLens Phase 21 Keyword Sparse Retrieval

Status: Initial keyword retrieval layer implemented.
Date: 2026-09-28

## Objective

Dense embeddings can miss exact technical identifiers such as error codes, router models, firmware versions, and IP addresses. Phase 21 adds sparse keyword retrieval so SupportLens can match exact strings like:

- `ERR_105`
- `AX4200`
- `FW_2.3.17`
- `192.168.0.1`

This phase adds sparse retrieval only. Combining sparse retrieval with dense retrieval belongs to Phase 22.

## Completed

- Added `backend/app/rag/keyword_retriever.py`.
- Added `KeywordRetrievalConfig` with:
  - `top_k`
  - `min_score`
- Added `KeywordRetriever`, an in-memory BM25 retriever over chunk payloads.
- Added identifier-preserving tokenization for:
  - underscores
  - hyphens
  - dotted firmware versions
  - IP addresses
  - alphanumeric model numbers
- Added metadata-aware search text using:
  - title
  - product
  - version
  - category
  - section
  - chunk text
- Added metadata filtering support using the existing `MetadataFilter`.
- Added `RetrievalResult.keyword_score`.
- Added environment settings:
  - `KEYWORD_RETRIEVAL_TOP_K`
  - `KEYWORD_RETRIEVAL_MIN_SCORE`
- Added tests for exact identifier matching, metadata-field search, metadata filtering, top-k limiting, empty input handling, and config validation.

## Current Strategy

The sparse retrieval flow is:

```text
chunk payloads -> identifier-preserving tokenizer -> BM25 index
query -> same tokenizer -> BM25 scores + exact token overlap -> top keyword matches
```

BM25 remains the ranking base. A small exact-token overlap component is added because tiny corpora or terms that appear in every document can otherwise receive zero or negative BM25 scores. That behavior is bad for Phase 21 because exact identifiers should stay retrievable even in small local test indexes.

The keyword retriever returns normal `RetrievalResult` objects, so evaluation code can treat it like dense retrieval. The sparse score is stored as both `score` and `keyword_score`.

## Role Responsibilities

The ingestion role still prepares chunk payloads with complete metadata and text. Keyword retrieval depends on those payloads containing the exact identifiers users may search for.

The sparse retriever role builds a BM25 index from chunk payloads and ranks chunks by lexical relevance. It is strongest for exact terms, IDs, error codes, firmware versions, model numbers, command names, and IP addresses.

The dense retriever role remains responsible for semantic matching when the user describes a problem without exact vocabulary.

The metadata filter role limits sparse results by fields such as product, version, category, language, source type, or document ID.

The evaluator role can now measure sparse retrieval separately from dense retrieval. Phase 22 should compare dense only, sparse only, hybrid, and hybrid plus reranking.

The product/API role should not expose sparse retrieval as a separate user-facing mode yet. It can later expose keyword scores in retrieval debug views.

## Current Limits

The current keyword retriever is in-memory and expects payloads to be supplied by the caller. It does not yet load all payloads directly from Qdrant.

Phase 21 does not combine sparse and dense candidates. That fusion belongs to Phase 22.

The tokenizer is intentionally simple. Phase 23 can add query processing for detecting product names, firmware versions, categories, and exact identifiers more explicitly.
