# SupportLens Phase 25 Generation Evaluation

Status: Initial deterministic generation evaluator implemented.
Date: 2026-09-28

## Objective

Phase 25 measures whether generated RAG answers are grounded, relevant, correctly refused when unsupported, and correctly cited.

This phase adds custom checks that can run locally and deterministically. RAGAS and manual review can be layered on later once a larger indexed corpus and stable local model runs are available.

## Completed

- Added `backend/app/evaluation/generation.py`.
- Added per-question generation evaluations with:
  - question ID
  - answerability flag
  - refusal state
  - expected document IDs
  - retrieved context document IDs
  - cited source IDs
  - faithfulness score
  - answer relevance score
  - context precision score
  - context recall score
  - no-answer correctness score
  - citation correctness score
  - machine-readable issue labels
- Added aggregate generation metrics:
  - average faithfulness
  - average answer relevance
  - average context precision
  - average context recall
  - no-answer accuracy
  - average citation correctness
  - average overall score
- Added a generation evaluation runner that executes a RAG pipeline over evaluation questions.
- Added tests for grounded answers, incorrect refusals, correct refusals, invalid citation markers, aggregate metrics, runner behavior, and empty-input validation.

## Current Strategy

The evaluator uses transparent custom checks:

- Faithfulness checks answer token overlap against retrieved context text.
- Answer relevance checks required expected-evidence terms when the dataset provides them.
- Context precision checks how much retrieved context came from expected documents.
- Context recall checks whether expected documents appeared in the generated answer context.
- No-answer correctness checks that answerable questions are answered and unsupported questions are refused.
- Citation correctness checks that model-written bracketed citations point to real returned sources and cite expected documents.

These checks are intentionally conservative. They are useful for regression testing and baseline comparison, but they are not a replacement for semantic review.

## Role Responsibilities

The dataset role defines what should be answerable, what should be refused, and which documents or terms count as expected evidence.

The retriever role supplies the context that generation will use. Its output controls context precision and context recall.

The no-answer gate role decides whether weak or missing evidence should stop generation before the LLM is called. Its behavior is measured by no-answer correctness.

The LLM role writes the final answer from the grounded prompt. It is measured for faithfulness, answer relevance, and citation behavior.

The citation role connects bracketed source markers in the answer to structured `SourceCitation` records. It is responsible for making citations verifiable instead of decorative.

The evaluator role converts pipeline outputs into per-question scores and aggregate metrics. It does not change retrieval or generation behavior.

The manual reviewer role remains important for judging nuanced support quality, partial answers, confusing wording, and semantic faithfulness that simple token checks cannot fully measure.

## Current Limits

The current evaluator is deterministic and dependency-free. It does not call RAGAS yet.

Faithfulness and relevance are heuristic scores based on text overlap and required terms. They should be interpreted as early warning signals, not final product-quality judgments.

The next phase can use these metrics to compare a baseline system against the improved SupportLens pipeline.
