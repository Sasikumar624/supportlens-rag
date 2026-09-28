# SupportLens Phase 9 Qdrant Local Setup

Status: Initial Qdrant setup adapter implemented.
Date: 2026-09-28

## Objective

Phase 9 prepares a local Qdrant vector database for SupportLens embeddings.

Phase 8 creates vectors. Phase 9 creates and validates the collection that will store those vectors. Full indexing belongs to Phase 10.

## Completed

- Added `backend/app/db/qdrant.py`.
- Added `QdrantCollectionConfig` with:
  - Qdrant URL
  - API key
  - collection name
  - vector size
  - distance metric
- Added Qdrant client creation from project settings.
- Added collection helpers for:
  - checking whether a collection exists
  - creating the collection if missing
  - resetting the collection for local development
- Added Qdrant point conversion for embedded chunks.
- Added deterministic UUID point IDs derived from logical chunk IDs.
- Added vector-size validation before point creation.
- Added unit tests with a fake Qdrant client, so tests do not require Docker or a running Qdrant server.

## Current Strategy

The local collection defaults to:

- collection: `supportlens_chunks`
- vector size: `384`
- distance: `Cosine`

The vector size matches the expected output dimension of `BAAI/bge-small-en-v1.5`.

Qdrant point IDs are deterministic UUIDs generated from chunk IDs. The original chunk ID remains in the payload as `chunk_id`.

## Running Qdrant Locally

Use Docker for local development:

```powershell
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Qdrant should then be available at:

```text
http://localhost:6333
```

The local dashboard is available at:

```text
http://localhost:6333/dashboard
```

## Current Limits

This phase does not yet upsert all chunks into Qdrant.

Phase 10 will build the repeatable indexing pipeline:

```text
documents -> load -> clean -> structure -> chunk -> embed -> store in Qdrant
```
