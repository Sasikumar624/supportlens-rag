# SupportLens Phase 20 Reranking

Status: Initial reranking layer implemented.
Date: 2026-09-28

## Objective

Phase 20 improves retrieval quality by retrieving a larger dense candidate set and reranking those chunks before they are sent to answer generation.

The target flow is:

```text
question -> Qdrant dense retrieval top 15
         -> CrossEncoder reranker
         -> best 4-6 chunks
         -> no-answer gate and LLM
```

## Completed

- Added `backend/app/rag/reranker.py`.
- Added `RerankingConfig` with:
  - `candidate_top_k`
  - `final_top_k`
  - validation that final results cannot exceed candidates
- Added `CrossEncoderRerankerConfig` using `cross-encoder/ms-marco-MiniLM-L6-v2` by default.
- Added `CrossEncoderReranker` behind a small testable interface.
- Added `RerankedRetriever`, which wraps an existing retriever and reranks its candidate chunks.
- Preserved original dense scores while adding `dense_score` and `rerank_score` to result payloads.
- Added `RetrievalResult.rerank_score`.
- Added environment settings:
  - `RERANKER_MODEL`
  - `RERANKER_CANDIDATE_TOP_K`
  - `RERANKER_FINAL_TOP_K`
- Added retrieval comparison reporting for dense-only versus dense-plus-reranking metrics with elapsed latency.
- Added unit tests using fake retrievers and fake reranker models, so tests do not require network access or model downloads.

## Current Strategy

The reranker does not replace dense retrieval. It sits after dense retrieval:

```text
DenseRetriever(top_k=15) -> CrossEncoderReranker -> top 5 reranked chunks
```

The dense retriever still owns candidate recall. The reranker owns ordering the candidate set by query-passage relevance.

The reranked result keeps the original dense score in `RetrievalResult.score` so existing no-answer thresholds and retrieval metadata do not suddenly change meaning. The cross-encoder score is stored separately as `rerank_score`.

## Role Responsibilities

The dense retriever role retrieves a broad candidate set from Qdrant. In Phase 20, it should usually fetch more chunks than the LLM will receive, such as top 15.

The reranker role scores each `(question, chunk text)` pair with a cross-encoder model. It reorders candidates by direct relevance to the question.

The final selector role keeps only the best reranked chunks, usually top 4-6, so the LLM receives focused evidence without unnecessary context noise.

The no-answer gate role still protects generation after reranking. It should refuse when the selected evidence is missing, too thin, or below the configured retrieval threshold.

The LLM role benefits from cleaner context. It should receive fewer irrelevant chunks and produce answers grounded in the reranked evidence.

The evaluator role compares dense-only retrieval against dense-plus-reranking using recall, MRR, and latency. Final answer quality should also be reviewed once answer evaluation is added in a later phase.

The product/API role can expose rerank scores in debug views later. Users do not need to see rerank internals, but developers should be able to inspect them during retrieval debugging.

## Current Limits

The reranker model is loaded only when `CrossEncoderReranker` is constructed. Tests use fake models.

Phase 20 does not yet add a CLI command or frontend debug view for reranking. It also does not automatically tune candidate or final top-k values. Those should be calibrated against the evaluation dataset and latency budget.
