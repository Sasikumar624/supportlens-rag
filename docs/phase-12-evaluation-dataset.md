# SupportLens Phase 12 Evaluation Dataset

Status: Production-style evaluation dataset and validation layer implemented.
Date: 2026-09-29

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
  - expected answer guidance
  - user persona
  - notes
- Added `ExpectedEvidence` records with:
  - expected document ID
  - optional expected section
  - optional required terms
- Added question categories for setup, troubleshooting, procedure, configuration, exact-term, multi-chunk, multi-document, simple-factual, unanswerable, and out-of-domain questions.
- Added production-style end-user questions for OpenWrt, TP-Link, NETGEAR, and ASUS support scenarios.
- Added expected answer guidance so evaluation can check whether an answer reads like real support help, not only whether retrieval found a document.
- Added dataset validation for:
  - empty datasets
  - duplicate question IDs
  - answerable questions without evidence
  - unanswerable questions with evidence
  - expected document IDs not present in `data/sources.csv`
- Added dataset summary counts.
- Added tests for the seed dataset and validation failures.

## Current Dataset

The current dataset contains production-style questions tied to the Stage B multi-product source registry.

It includes:

- answerable support questions
- end-user phrasing such as "my router has no internet" and "I can't open routerlogin.net"
- setup questions
- troubleshooting questions
- procedure questions
- configuration questions
- firmware questions
- product overview / definition questions
- exact-term questions
- multi-chunk questions
- multi-document questions
- unanswerable questions
- out-of-domain questions
- expected answer guidance for user-facing answer quality
- user persona labels for realistic support context

Covered source families:

- OpenWrt
- TP-Link
- NETGEAR
- ASUS

## Current Limits

The final project target is 100-150 evaluation questions.

The current dataset is still below the final target, but it now reflects real user support wording and the Stage B multi-product source registry. The dataset should continue expanding as the knowledge base grows, especially for multi-document comparisons, warranty/support-policy questions, and ambiguous questions that require clarification.

Metrics belong to Phase 13.
