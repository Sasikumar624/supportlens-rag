# SupportLens Phase 6 Chunking

Status: Initial structure-aware chunker implemented.
Date: 2026-09-25

## Objective

Phase 6 converts structured document blocks into metadata-rich chunks that can later be embedded and indexed.

The chunker should preserve meaning, avoid mixing unrelated sections when possible, keep procedures and warnings readable, and carry enough metadata for citations and evaluation.

## Completed

- Added `backend/app/ingestion/chunker.py`.
- Added a `Chunk` model with stable chunk IDs such as `DOC001_C0001`.
- Added `ChunkingConfig` with:
  - `target_tokens`
  - `overlap_blocks`
- Added `chunk_blocks()` for grouping structured blocks into chunks.
- Added chunk metadata for:
  - chunk ID
  - document ID
  - source URL
  - page
  - section
  - token count
  - source block IDs
  - source block types
- Added tests for metadata preservation, size splitting, heading-based section splits, overlap behavior, and config validation.

## Current Strategy

The current chunker uses simple token counting based on whitespace. It starts a new chunk when:

- adding a block would exceed the configured token target
- a new heading indicates a new section

Optional block overlap carries limited context from the previous chunk.

## Current Limits

This is the first chunking implementation. It does not yet perform tokenizer-specific counting, semantic compression, table reconstruction, or chunk-quality scoring.

Those improvements should be driven by retrieval metrics in later phases.

