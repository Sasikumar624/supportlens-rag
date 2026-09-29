# SupportLens Phase 32 Automated Tests

Status: Root-level automated test workflow established.
Date: 2026-09-29

## Objective

Phase 32 makes the test suite easier to run consistently from the project root.

Earlier tests existed across the backend, but the command depended on running pytest from the `backend/` directory so Python could import the `app` package. This phase adds a root pytest configuration so the expected test command works from the repository root and can later be reused by CI.

## Completed

- Added root-level `pytest.ini`.
- Configured pytest to discover tests under `backend/tests`.
- Configured `backend` as the Python import path for tests.
- Added a project-owned `test_workspace` fixture for tests that need scratch files.
- Disabled pytest's local cache provider for cleaner Windows workspace runs.
- Enabled strict marker validation.
- Defined initial test markers:
  - `api`
  - `unit`
  - `rag`
  - `integration`
- Verified the full backend test suite from the repository root.
- Added this Phase 32 documentation page.
- Added the Phase 32 README roadmap entry.

## Test Command

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

This is now the canonical local automated test command.

## Test Scope

Current tests cover:

- document loading
- text cleaning
- structure detection
- chunking
- embeddings with fake encoders
- Qdrant conversion logic with fake clients
- dense retrieval
- keyword retrieval
- hybrid retrieval
- reranking
- query processing
- local LLM client behavior with fake model/tokenizer objects
- generator behavior
- retrieval and generation evaluation
- baseline versus improved system comparison
- FastAPI health, query, document, feedback, error, security, and logging behavior

## Role Responsibilities

The test configuration role owns how pytest discovers tests and imports backend modules.

The test workspace role owns deterministic scratch directories for tests that need files without relying on OS temp behavior.

The unit test role verifies deterministic functions and classes without external services.

The API test role verifies HTTP contracts, status codes, response shapes, security headers, request IDs, and structured errors.

The RAG test role verifies retrieval, generation, no-answer, citation, reranking, and evaluation behavior using controlled fakes where possible.

The integration test role is reserved for composed workflows or service-boundary checks that may be slower or require extra setup.

The CI readiness role keeps the local command stable so a future GitHub Actions workflow can run the same test command.

The documentation role records the exact command, current test scope, and ownership boundaries so the project stays explainable.

## Current Limits

The project does not have GitHub Actions yet. CI/CD belongs to a later phase.

The suite currently relies on lightweight fakes for model, embedding, and Qdrant behavior. That is intentional for fast local tests, but production-like service tests should be added later.

Coverage reporting is not configured yet. It can be added after the project has stable CI.

Some tests still use manual `try`/`except` assertions for errors. They can be cleaned up with `pytest.raises` during a later test-quality pass.
