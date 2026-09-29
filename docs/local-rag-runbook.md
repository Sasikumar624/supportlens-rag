# Local Full RAG Runbook

Use this when you want real local answering through the frontend.

## 1. Prepare Environment

From the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

```env
ENABLE_QUERY_PIPELINE=true
```

## 2. Start Qdrant

```powershell
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Qdrant dashboard:

```text
http://localhost:6333/dashboard
```

## 3. Install Backend Dependencies

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

## 4. Build The Vector Index

This downloads the source pages from `data/sources.csv`, chunks them, embeds them,
and stores the vectors in Qdrant.

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.ingestion.index_cli --reset
```

## 5. Start Backend With RAG Enabled

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

First startup can take time because it loads:

- embedding model: `BAAI/bge-small-en-v1.5`
- reranker model: `cross-encoder/ms-marco-MiniLM-L6-v2`
- local LLM: `Qwen/Qwen2.5-1.5B-Instruct`

Health check:

```text
http://127.0.0.1:8000/health
```

## 6. Start Frontend

Open a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

Try:

```text
How do I reset OpenWrt when I cannot reach the web UI?
```

## Common Failures

If the backend says `Query pipeline is not configured`, check `.env`:

```env
ENABLE_QUERY_PIPELINE=true
```

If indexing cannot connect to Qdrant, start Docker/Qdrant first.

If model download fails, check internet access. Hugging Face models are downloaded
the first time the backend/indexer loads them.
