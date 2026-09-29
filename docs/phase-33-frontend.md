# SupportLens Phase 33 Frontend

Status: Production-grade Next.js support console implemented.
Date: 2026-09-29

## Objective

Phase 33 adds a production-grade frontend for asking technical support questions and reviewing grounded answers from the SupportLens API.

The UI is designed as an operational support console: polished enough for a real user workflow, while still staying inside the existing Phase 33 API surface. Knowledge-base analytics and retrieval debugging are reserved for later phases.

## Completed

- Added a `frontend/` Next.js app scaffold.
- Added typed client helpers for:
  - `GET /health`
  - `POST /api/query`
  - `POST /api/feedback`
- Added environment configuration with `NEXT_PUBLIC_API_BASE_URL`.
- Built a production-grade SupportLens console with:
  - application shell
  - backend health indicator
  - question input
  - metadata filters for product, version, category, language, source type, and document ID
  - curated example prompts
  - Ask action
  - answer rendering
  - no-answer/refusal indicator
  - source citation inspector
  - source confidence labels
  - retrieval, generation, and total timing tiles
  - loading skeletons
  - empty, error, success, and feedback states
  - helpful and not-helpful feedback actions with optional comment
- Added responsive styling for desktop and mobile layouts.
- Added `lucide-react` icons for production-grade controls and status indicators.
- Added this Phase 33 documentation page.
- Added the Phase 33 README roadmap entry.

## Frontend Usage

Install dependencies from the frontend directory:

```bash
cd frontend
npm install
```

Run the frontend:

```bash
npm run dev
```

By default, the frontend calls the backend at:

```text
http://localhost:8000
```

Override this with:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Role Responsibilities

The frontend role owns the browser experience. It captures the user question, manages optional metadata filters, checks backend health, calls the API, renders answers and citations, shows loading/error/empty/success states, and submits lightweight feedback.

The API role still owns HTTP validation, status codes, response shapes, error contracts, and CORS. The frontend consumes those contracts but does not duplicate backend validation beyond simple empty-question prevention.

The query pipeline role still owns retrieval, reranking, prompt construction, generation, no-answer handling, and citations. The frontend only displays the pipeline result returned by `POST /api/query`.

The source display role presents enough citation metadata for users to inspect where an answer came from: document label, section, document ID, product, page when available, source URL, score, and confidence label.

The feedback role maps UI actions into the existing rating contract. Helpful submits rating `5`; not helpful submits rating `1`. Optional comments are passed through the existing feedback schema.

The configuration role keeps backend location outside the code through `NEXT_PUBLIC_API_BASE_URL`, so local and deployed environments can point at different API hosts.

The design-system role keeps controls consistent: icon buttons for actions, compact filters, clear status pills, bounded surfaces, responsive layout, and stable dimensions for repeated source cards and metric tiles.

## Current Limits

The frontend does not include the Phase 34 knowledge-base view.

The frontend does not include the Phase 35 retrieval debug view.

Feedback is submitted through the existing backend endpoint, which currently stores feedback in memory only.

The query pipeline must still be attached to the backend process; otherwise the backend returns `503 Service Unavailable` and the frontend displays that error.
