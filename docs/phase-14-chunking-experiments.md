# SupportLens Phase 14 Chunking Experiments

Status: Initial chunking experiment framework implemented.
Date: 2026-09-28

## Objective

Phase 14 compares chunking strategies using retrieval metrics.

This phase creates the experiment runner. It does not invent benchmark numbers. Real results should be recorded only after indexing the dataset and running retrieval evaluation.

## Completed

- Added `backend/app/evaluation/chunking_experiments.py`.
- Added default chunking experiments for:
  - 300 target tokens, 0 overlap blocks
  - 500 target tokens, 1 overlap block
  - 800 target tokens, 1 overlap block
  - 500 target tokens, 2 overlap blocks
- Added `ChunkingExperiment` records with experiment IDs, descriptions, and chunking configs.
- Added `ChunkingExperimentResult` records combining:
  - experiment definition
  - indexing counts
  - retrieval metrics
- Added `run_chunking_experiments()` to:
  - reset the collection for each experiment
  - index with that experiment's chunking config
  - run retrieval evaluation
  - return comparable experiment results
- Added `select_best_experiment()` using:
  - Recall@5 first
  - MRR second
  - Recall@3 third
  - smaller chunk count as a tie-breaker
- Added tests for default variants, experiment execution, best-experiment selection, and validation failures.

## Current Strategy

Each experiment follows this flow:

```text
chunking config -> reset Qdrant collection -> re-index -> retrieve eval questions -> calculate metrics
```

The best strategy is selected only from measured retrieval metrics.

## Current Limits

No real benchmark numbers are recorded yet.

To produce real Phase 14 results, Qdrant must be running, documents must be indexable, and the Phase 12 dataset should be evaluated against each chunking configuration.
