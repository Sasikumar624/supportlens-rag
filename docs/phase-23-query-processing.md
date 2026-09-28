# SupportLens Phase 23 Query Processing

Status: Initial lightweight query processing layer implemented.
Date: 2026-09-28

## Objective

Phase 23 adds conservative query processing before retrieval. The goal is to clean up user input, preserve exact identifiers, and infer safe metadata filters without overcomplicated query rewriting.

Supported functions now include:

- normalize whitespace
- detect product names
- detect known versions
- detect firmware versions
- detect error codes
- detect model numbers
- detect IP addresses
- detect broad support category hints
- merge inferred filters with explicit caller filters

## Completed

- Added `backend/app/rag/query_processing.py`.
- Added `QueryProcessingConfig` for known products, known versions, and category aliases.
- Added `QueryIdentifiers` for:
  - error codes
  - firmware versions
  - model numbers
  - IP addresses
- Added `ProcessedQuery` with:
  - original query
  - normalized query
  - identifiers
  - detected product
  - detected version
  - detected category
  - optional `MetadataFilter`
- Added `QueryProcessor`.
- Added `QueryProcessingRetriever`, a wrapper that processes a query before calling an existing retriever.
- Added `merge_metadata_filters`, where explicit caller filters override inferred values.
- Added tests for normalization, identifier preservation, metadata inference, retriever wrapping, filter merging, custom configuration, and validation.

## Current Strategy

The query processor does not rewrite the user question semantically. It only normalizes spacing and extracts structured hints.

The default product/version hints match the current Stage A dataset:

```text
product: OpenWrt
version: current
```

Category detection uses simple aliases for setup, troubleshooting, configuration, and firmware. This is intentionally small so it can be audited and changed easily.

## Role Responsibilities

The query processor role normalizes the query and extracts identifiers and metadata hints. It must preserve exact technical tokens such as `ERR_105`, `AX4200`, `FW_2.3.17`, and `192.168.0.1`.

The metadata filter role turns safe product, version, and category detections into a `MetadataFilter`. Explicit filters from the caller take priority over inferred filters.

The dense retriever role benefits from normalized whitespace but still receives the natural-language question.

The keyword retriever role benefits from preserved exact identifiers.

The hybrid retriever role can use the same processed query and inferred filters for both dense and sparse retrieval.

The reranker role should receive the normalized query and the candidate set produced by retrieval.

The evaluator role should measure whether query processing improves recall and MRR, especially for category-specific and identifier-heavy questions.

The product/API role can later expose detected identifiers and inferred filters in a retrieval debug view.

## Current Limits

The processor does not yet infer arbitrary products or versions from the source registry automatically. It uses configured known values.

The processor does not rewrite intent, expand synonyms broadly, or add hidden query terms. Those behaviors can hurt grounding if added too early.

Phase 24 will improve prompt construction, not query processing.
