# SupportLens Phase 30 Security Basics

Status: Initial API security guardrails implemented.
Date: 2026-09-29

## Objective

Phase 30 adds the first practical security controls around the FastAPI backend.

This phase does not add authentication or production upload scanning yet. Instead, it protects the current public API surface from oversized requests, tightens accepted field sizes, and adds browser-facing response headers that are safe defaults for an API service.

## Completed

- Added `backend/app/core/security.py`.
- Added request-size limiting middleware.
- Added `API_MAX_REQUEST_BYTES` to settings and `.env.example`.
- Added structured `request_too_large` error responses for oversized request bodies.
- Added default security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- Added field-length constraints to public request schemas for:
  - query metadata filters
  - document creation placeholders
  - feedback question, answer, and comment payloads
- Expanded API tests for security headers, oversized request handling, and feedback field limits.

## Request Size Policy

The backend rejects request bodies larger than the configured limit before router logic runs.

Default:

```text
API_MAX_REQUEST_BYTES=32768
```

Oversized requests return:

```json
{
  "detail": {
    "code": "request_too_large",
    "message": "Request body exceeds the maximum allowed size of 32768 bytes."
  }
}
```

## Role Responsibilities

The security boundary role protects the API before requests reach route handlers. It owns request-size checks and safe response headers.

The configuration role owns tunable limits such as `API_MAX_REQUEST_BYTES`. It keeps security limits visible in environment configuration instead of hiding them inside route logic.

The schema validation role rejects oversized public fields for query metadata, document placeholder inputs, and feedback payloads.

The error contract role keeps security failures machine-readable by adding the `request_too_large` error code.

The API router role remains focused on business behavior. Routers should not duplicate request-size or generic header handling.

The frontend role can display a clear "request too large" message by checking `detail.code`.

The operations role can adjust the request-size limit per environment without changing code.

## Current Limits

Authentication is not implemented yet because the current API does not have user accounts, private tenant data, or write-enabled document ingestion.

Rate limiting is not implemented yet because this project is still local-first. It should be added before exposing the backend publicly.

File upload validation, MIME-type checks, antivirus scanning, and storage isolation are not implemented yet because document ingestion is still a placeholder.

Prompt-injection hardening remains handled mainly by prompt construction and grounded generation rules. Deeper adversarial testing belongs in later evaluation phases.
