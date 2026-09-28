# SupportLens Phase 8 Embeddings

Status: Initial embedding layer implemented.
Date: 2026-09-28

## Objective

Phase 8 turns metadata-rich chunks into dense vectors that can later be stored in Qdrant and searched with query vectors.

The initial embedding model remains `BAAI/bge-small-en-v1.5`, matching the project plan and the existing `EMBEDDING_MODEL` setting.

## Completed

- Added `backend/app/rag/embeddings.py`.
- Added `EmbeddingConfig` for:
  - model name
  - batch size
  - normalization
  - BGE query instruction
- Added `EmbeddingModel` for:
  - batch document embeddings
  - query embeddings
  - chunk embeddings
  - lazy Sentence Transformers model loading
- Added `EmbeddedChunk` records with:
  - Qdrant-ready point ID
  - vector
  - chunk metadata payload
- Added vector helpers for:
  - normalization
  - cosine similarity
  - dimension validation
- Added tests using a fake encoder so unit tests do not download Hugging Face model weights.

## Current Strategy

Document chunks are embedded from raw chunk text.

Queries are embedded with the BGE search instruction:

`Represent this sentence for searching relevant passages: `

Vectors are normalized by default so cosine similarity and dot-product-style vector search stay consistent.

## Why This Matters

Embeddings are the bridge between SupportLens chunks and dense retrieval.

This phase makes it possible to:

- convert chunks into vectors
- inspect embedding dimensions
- embed user questions
- compare semantic similarity
- prepare Qdrant points in the next phase

## Current Limits

This phase does not yet create a Qdrant collection or persist vectors.

The real embedding model requires the dependencies in `backend/requirements.txt` and may download model weights the first time it is loaded. Unit tests avoid that network dependency by injecting a fake encoder.
