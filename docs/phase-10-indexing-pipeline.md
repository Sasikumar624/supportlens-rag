# SupportLens Phase 10 Indexing Pipeline

Status: Initial repeatable indexing pipeline implemented.
Date: 2026-09-28

## Objective

Phase 10 connects the completed ingestion, embedding, and Qdrant setup layers into one repeatable indexing pipeline.

The pipeline turns source records into Qdrant points:

```text
sources -> load -> detect structure -> chunk -> embed -> upsert to Qdrant
```

## Completed

- Added `backend/app/ingestion/indexer.py`.
- Added `IndexingConfig` for:
  - Qdrant collection config
  - chunking config
  - optional collection reset
  - upsert batch size
- Added `build_index_from_sources_csv()` to index a source registry.
- Added `build_index()` to index an in-memory list of source records.
- Added document-level indexing results with counts for:
  - loaded parts
  - detected blocks
  - generated chunks
- Added aggregate indexing results with counts for:
  - documents seen
  - documents indexed
  - total parts
  - total blocks
  - total chunks
  - total Qdrant points upserted
- Added batched Qdrant upserts.
- Added dependency injection for:
  - Qdrant client
  - embedding model
  - document loader
  - local path resolver
- Added unit tests that run without Docker, network access, or Hugging Face downloads.

## Current Strategy

The pipeline is intentionally explicit instead of hidden inside a framework:

1. Read `sources.csv`.
2. Load each document.
3. Detect structure.
4. Create chunks.
5. Generate embeddings.
6. Convert embedded chunks into Qdrant points.
7. Upsert points into the configured collection.
8. Return indexing counts for verification.

The default path uses the real loaders, real embedding model, and real Qdrant client. Tests inject fakes so pipeline behavior stays deterministic.

## Current Limits

The pipeline can index, but it does not yet retrieve from Qdrant.

Dense retrieval begins in Phase 11. Phase 10 only stores indexed vectors and payloads.
