# Application Core

This directory contains the backend Geo-RAG application code.

## Structure

- **main.py** — FastAPI server entry point. Starts the server and mounts routes.
- **config.py** — Centralized configuration (model names, timeouts, cache settings, etc.)
- **api/** — HTTP routes and request/response schemas
- **core/** — Pipeline orchestration (analyzer, prompt builders)
- **services/** — Integration with external systems (Ollama, ChromaDB)
- **workers/** — Background job processors (async vision, retrieval, LLM)
- **utils/** — Helper utilities (caching, spatial indexing, hashing)

## How It Works

1. **Request arrives** → `api/routes.py` validates and creates a Job
2. **Job queued** → Returns job_id to user immediately
3. **Background worker** → `workers/` processes stages asynchronously:
   - Vision feature extraction
   - Spatial enrichment (currently placeholder stage)
   - Knowledge retrieval
   - LLM answer generation
4. **Results cached** → Stored in `cache/` for reuse
5. **User polls** → `/api/status/{job_id}` checks progress
6. **Results ready** → User retrieves answer

## Key Files

### main.py

- Creates FastAPI app
- Configures middleware (CORS, logging)
- Includes routers from api/routes.py
- Serves frontend static files from /frontend

### config.py

- `OLLAMA_BASE_URL` — Ollama endpoint
- `VISION_MODEL` — Vision model name (default: `llava:7b`)
- `LLM_MODEL` — Reasoning model (currently: gemma3:1b)
- `CACHE_DIR` — Cache persistence location
- `CACHE_ENABLED` — Toggle caching on/off
- `SHAPEFILE_INDEX` — Path to spatial index

### api/routes.py

- `/api/analyze` → async, returns `job_id`
- `/api/batch` → async batch processing
- `/api/status/{job_id}` → polling for progress/result
- `/api/cache/clear` and `/api/cache/stats` → cache controls
- `/api/health` and `/api/queue/stats` → diagnostics

### core/orchestrator.py

Supports direct/synchronous orchestration path used by tests and internal flows.
The API/UI path uses queue workers in `workers/`.

## Starting the Server

```bash
cd ..
.venv312\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Runs on http://0.0.0.0:8000
```

## To Test

```bash
# Single image (async)
curl -X POST http://localhost:8000/api/analyze \
  -F "image=@image.png" \
  -F "question=Question?" \
  -F "mode=rag_baseline"

# Returns: {"job_id": "abc123", "status": "queued"}

# Check status
curl http://localhost:8000/api/status/abc123

# Returns: {"status": "completed", "answer": "..."}
```

## Artifact Safety

Runtime files are generated under `cache/` and should not be committed.
Tracked docs/schemas in `cache/` remain part of the repo; generated JSON data does not.
