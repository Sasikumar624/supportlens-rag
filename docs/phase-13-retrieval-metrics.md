# SupportLens Phase 13 Retrieval Metrics

Status: Initial retrieval metrics implemented.
Date: 2026-09-28

## Objective

Phase 13 measures whether dense retrieval returns the expected evidence for the evaluation questions.

This phase calculates retrieval metrics only. It does not evaluate generated answers or LLM behavior.

## Completed

- Added `backend/app/evaluation/metrics.py`.
- Added `backend/app/evaluation/retrieval_eval.py`.
- Added per-question retrieval evaluations with:
  - question ID
  - answerability flag
  - expected document IDs
  - retrieved document IDs
  - first relevant rank
  - reciprocal rank
- Added aggregate retrieval metrics:
  - Hit Rate
  - Recall@1
  - Recall@3
  - Recall@5
  - MRR
- Added a retrieval evaluation runner that executes a retriever over evaluation questions.
- Added tests for per-question ranking, aggregate metrics, answerable-question filtering, evaluation runner behavior, and invalid inputs.

## Current Strategy

Metrics are based on whether retrieved chunk payloads contain an expected `document_id`.

Unanswerable and out-of-domain questions are preserved in the dataset, but current retrieval metrics are calculated over answerable questions only. No-answer correctness belongs to later generation/no-answer phases.

## Current Limits

This phase does not yet produce a persisted report file or CLI command.

It also does not judge section-level correctness or required-term coverage yet. Those can be added once the retrieval baseline is running against an indexed Qdrant collection.
