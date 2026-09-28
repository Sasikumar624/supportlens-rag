# SupportLens Phase 26 Baseline vs Improved System

Status: Initial measurable comparison layer implemented.
Date: 2026-09-28

## Objective

Phase 26 compares a simple baseline RAG system against the improved SupportLens pipeline using real retrieval and generation metrics.

The phase does not invent benchmark numbers. It provides the comparison structure so actual runs can measure whether the improved system is better than the baseline.

## Completed

- Added `backend/app/evaluation/system_comparison.py`.
- Added reusable system profiles:
  - `BASELINE_PROFILE`
  - `IMPROVED_PROFILE`
- Defined the baseline profile as:
  - basic chunking
  - dense retrieval
  - top 5 context
  - LLM generation
- Defined the improved profile as:
  - structure-aware chunking
  - metadata filtering
  - dense retrieval
  - keyword sparse retrieval
  - hybrid fusion
  - reranking
  - grounded prompt
  - no-answer handling
  - citations
- Added `SystemUnderEvaluation` to pair a profile with a retriever and answering pipeline.
- Added `compare_systems()` to run:
  - retrieval evaluation for baseline and improved retrievers
  - generation evaluation for baseline and improved answering pipelines
  - numeric metric deltas between the two systems
- Added tests for:
  - baseline and improved report generation
  - retrieval metric deltas
  - generation metric deltas
  - profile feature definitions
  - invalid inputs

## Current Strategy

The comparison flow is:

```text
evaluation questions
        |
        |-> baseline retriever -> retrieval metrics
        |-> baseline pipeline  -> generation metrics
        |
        |-> improved retriever -> retrieval metrics
        |-> improved pipeline  -> generation metrics
        |
        |-> metric deltas
```

Metric deltas are reported as:

```text
improved value - baseline value
```

Positive deltas are better for the current metrics because they are all score-style metrics where higher is better.

## Role Responsibilities

The baseline system role provides the simple reference system. It represents the minimum RAG path: basic chunks, dense retrieval, top 5 context, and LLM generation.

The improved system role provides the candidate SupportLens pipeline. It includes the accumulated improvements from previous phases: structure-aware chunks, metadata filtering, hybrid retrieval, reranking, grounded prompts, no-answer handling, and citations.

The retriever role is measured separately for each system. It determines recall, ranking quality, and whether expected documents are present in context.

The answering pipeline role is measured separately for each system. It determines whether final answers are grounded, relevant, correctly refused, and correctly cited.

The evaluator role runs the same questions through both systems and produces comparable retrieval and generation reports.

The delta role converts baseline and improved metrics into direct numeric differences so regressions and improvements are visible.

The reviewer role interprets the results. The comparison layer shows what changed, but a human still decides whether metric movement reflects better technical-support behavior.

## Current Limits

This phase creates the comparison framework, not a persisted benchmark report or CLI command.

The current profiles describe intended capabilities. The caller still supplies the actual baseline and improved retrievers and answering pipelines.

Full benchmark quality depends on a larger evaluation dataset, a populated Qdrant collection, stable local LLM behavior, and manual review of edge cases.
