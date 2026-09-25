# SupportLens Phase 1 Environment Setup

Status: Complete for initial backend development.
Date: 2026-09-25

## Completed

- Verified Git is available.
- Installed and verified Python 3.12.10 for this project.
- Created a local virtual environment at `.venv`.
- Upgraded pip inside `.venv`.
- Installed backend dependencies from `backend/requirements.txt`.
- Added `.env.example` with local development defaults.
- Added backend dependency list at `backend/requirements.txt`.
- Added a minimal FastAPI app entrypoint at `backend/app/main.py`.
- Added centralized environment configuration at `backend/app/core/config.py`.
- Added centralized logging setup at `backend/app/core/logging.py`.
- Added package initialization files for the backend.
- Verified `pip check` reports no broken requirements.
- Verified key imports for FastAPI, PyMuPDF, Sentence Transformers, Qdrant client, BM25, and Pytest.
- Verified `GET /health` with FastAPI's test client.

## Python Version Decision

Use Python 3.12.10 for this project.

Python 3.14 was tested first, but dependency installation failed while building `pydantic-core` because its Rust binding stack did not support Python 3.14 in this environment. Python 3.12 installed the same dependency set successfully using stable wheels.

The project records this with `.python-version`.

## Intended Local Setup Commands

From a fresh clone, after Python 3.12 is available:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Run the backend health check locally:

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/health
```

Expected response shape:

```json
{
  "status": "ok",
  "app": "SupportLens",
  "environment": "development"
}
```

## Phase 1 Exit Criteria

- Git available: complete
- `.env.example` present: complete
- Dependency file present: complete
- Basic application configuration present: complete
- Basic logging present: complete
- Minimal FastAPI app present: complete
- Python available: complete with Python 3.12.10
- Virtual environment created: complete
- Dependencies installed: complete
- Dependency consistency verified: complete
- Health endpoint verified: complete
