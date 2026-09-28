# SupportLens Phase 22 Hybrid Retrieval

Status: Initial hybrid retrieval layer implemented.
Date: 2026-09-28

## Objective

Phase 22 combines dense semantic retrieval with keyword sparse retrieval so SupportLens can handle both natural-language support questions and exact technical identifiers.

The target flow is:

```text
question -> dense retriever
         -> keyword retriever
         -> reciprocal rank fusion
         -> candidate set
         -> optional reranker
         -> no-answer gate and LLM
```

## Completed

- Added `backend/app/rag/hybrid_retriever.py`.
- Added `HybridRetrievalConfig` with:
  - `top_k`
  - `rrf_k`
  - `dense_weight`
  - `keyword_weight`
- Added `HybridRetriever`, which calls dense and keyword retrievers using the same query and metadata filter.
- Added `reciprocal_rank_fusion` for rank-based dense/sparse fusion.
- Added deduplication by `chunk_id` with `point_id` fallback.
- Added hybrid debug metadata:
  - `hybrid_score`
  - `dense_score`
  - `keyword_score`
  - `dense_rank`
  - `keyword_rank`
  - `retrieval_sources`
- Added `RetrievalResult.dense_score` and `RetrievalResult.hybrid_score`.
- Added environment settings:
  - `HYBRID_RETRIEVAL_TOP_K`
  - `HYBRID_RRF_K`
- Added tests for RRF ordering, deduplication, top-k limiting, metadata filter forwarding, keyword-only matches, and config validation.

## Current Strategy

The hybrid retriever is intentionally separate from the reranker:

```text
DenseRetriever + KeywordRetriever -> HybridRetriever -> RerankedRetriever
```

Phase 22 produces a fused candidate set. Phase 20 reranking can then be applied on top of that fused set because `HybridRetriever` exposes the same `retrieve()` interface as the other retrievers.

The fusion strategy is Reciprocal Rank Fusion. It uses rank position instead of raw score magnitude, because dense similarity scores and BM25 keyword scores are not directly comparable.

## Role Responsibilities

The dense retriever role finds semantically similar support chunks. It helps when the user describes an issue without using the exact documentation terms.

The keyword retriever role finds exact lexical matches. It is strongest for error codes, model numbers, firmware versions, IP addresses, command names, and precise settings.

The fusion role combines dense and sparse ranked lists into one candidate set. It deduplicates repeated chunks and records which retrievers found each chunk.

The reranker role remains optional after fusion. It can reorder the fused candidate set using a cross-encoder before generation.

The no-answer gate role still decides whether the final selected evidence is strong enough to answer.

The LLM role receives better evidence because hybrid retrieval can include both semantic context and exact identifier matches.

The evaluator role should compare dense only, sparse only, hybrid, and hybrid plus reranking using recall, MRR, final answer quality, and latency.

The product/API role can expose hybrid debug fields later in a retrieval debug view. Normal users should see the final answer and citations, not fusion internals.

## Current Limits

The current hybrid layer requires both retrievers to be provided by the caller. Loading keyword payloads from Qdrant is still outside this phase.

Hybrid retrieval does not yet perform query processing. Phase 23 can add query normalization and identifier detection.

The default RRF settings are starting points. They should be tuned against the evaluation dataset once dense, sparse, hybrid, and hybrid-plus-reranking runs are compared.
