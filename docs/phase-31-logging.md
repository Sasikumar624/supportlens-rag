# SupportLens Phase 31 Logging

Status: Initial backend request and outcome logging implemented.
Date: 2026-09-29

## Objective

Phase 31 makes backend behavior observable enough for local debugging, API integration, and later production troubleshooting.

Earlier phases configured the Python logging format, but the API did not yet emit request lifecycle logs or route-level outcome logs. This phase adds request IDs, access-style request logs, and safe application outcome logs without storing raw questions, answers, or request bodies.

## Completed

- Added request lifecycle logging middleware.
- Added `X-Request-ID` response headers.
- Preserved caller-provided `X-Request-ID` values when present.
- Generated a UUID request ID when clients do not send one.
- Logged request completion with:
  - request ID
  - HTTP method
  - request path
  - response status code
  - request duration in milliseconds
- Logged unhandled request failures with request ID, method, path, and duration.
- Added query outcome logs with:
  - refusal state
  - source count
  - total query time
- Added document registry logs with document count.
- Added feedback logs with feedback ID and rating.
- Expanded API tests for generated and caller-provided request IDs.

## Log Examples

Request lifecycle logs:

```text
request_completed request_id=... method=POST path=/api/query status_code=200 duration_ms=12.345
```

Query outcome logs:

```text
query_completed refused=False source_count=2 total_time_ms=8.431
```

Feedback logs:

```text
feedback_stored feedback_id=1 rating=4
```

## Privacy Boundary

Logs intentionally avoid raw request bodies, user questions, generated answers, full source text, comments, and API keys.

This keeps logs useful for debugging and operations without turning them into a second copy of user input or model output.

## Role Responsibilities

The logging configuration role owns the root log format and output stream.

The request logging role owns request IDs, request lifecycle logs, response status, and latency.

The query logging role records high-level RAG outcomes such as refusal state, source count, and elapsed time.

The document logging role records source registry counts so document endpoint behavior can be checked quickly.

The feedback logging role records feedback IDs and ratings without storing feedback comments in logs.

The privacy role decides what must not be logged. It keeps sensitive request content, answers, comments, and retrieved text out of logs.

The frontend and integration role can pass `X-Request-ID` to connect client-side errors with backend logs.

The operations role can use request IDs, status codes, and durations to debug failures and slow requests.

## Current Limits

Logs are text-formatted rather than JSON-formatted. Structured JSON logging can be added when deployment and log aggregation targets are chosen.

There is no external observability backend yet. Logs currently go to stdout.

Request IDs are returned to clients but are not yet propagated into lower-level retriever, Qdrant, embedding, or LLM calls.

Latency logs are endpoint-level. Detailed dense retrieval, sparse retrieval, reranking, and LLM timing will improve after the production pipeline exposes those measurements consistently.
