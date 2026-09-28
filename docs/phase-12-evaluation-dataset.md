# SupportLens Phase 12 Evaluation Dataset

Status: Initial evaluation dataset and validation layer implemented.
Date: 2026-09-28

## Objective

Phase 12 creates the dataset used to evaluate retrieval quality in later phases.

This phase defines the questions and expected evidence. It does not calculate Recall@K, MRR, or other metrics yet.

## Completed

- Added `evaluation/dataset.json`.
- Added `backend/app/evaluation/dataset.py`.
- Added `EvaluationQuestion` records with:
  - question ID
  - question text
  - category
  - answerability flag
  - expected evidence
  - notes
- Added `ExpectedEvidence` records with:
  - expected document ID
  - optional expected section
  - optional required terms
- Added question categories for setup, troubleshooting, procedure, configuration, exact-term, multi-chunk, multi-document, unanswerable, and out-of-domain questions.
- Added dataset validation for:
  - empty datasets
  - duplicate question IDs
  - answerable questions without evidence
  - unanswerable questions with evidence
  - expected document IDs not present in `data/sources.csv`
- Added dataset summary counts.
- Added tests for the seed dataset and validation failures.

## Current Dataset

The current seed dataset contains 12 questions tied to the Stage A OpenWrt sources.

It includes:

- answerable support questions
- setup questions
- troubleshooting questions
- procedure questions
- configuration questions
- exact-term questions
- multi-chunk questions
- multi-document questions
- unanswerable questions
- out-of-domain questions

## Current Limits

The final project target is 100-150 evaluation questions.

This phase starts with a small validated seed dataset because the current source registry is still the Stage A smoke-test set. The dataset should expand as the knowledge base grows.

Metrics belong to Phase 13.
