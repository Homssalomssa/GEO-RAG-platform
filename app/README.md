# Application Core

This directory contains the main Geo-RAG application code.

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

**Updated for v0.3:**

- `OLLAMA_BASE_URL` — Ollama endpoint
- `VISION_MODEL` — Vision model name (currently: qwen3-vl:235b-cloud, will update)
- `LLM_MODEL` — Reasoning model (currently: gemma3:1b)
- `CACHE_DIR` — Cache persistence location
- `CACHE_ENABLED` — Toggle caching on/off
- `SHAPEFILE_INDEX` — Path to spatial index

### api/routes.py

**To be updated for v0.3:**

- `/api/analyze` → NOW async, returns job_id
- `/api/batch` → NEW, upload zip with multiple images
- `/api/status/{job_id}` → NEW, check job progress
- `/api/cache/clear` → NEW, clear cache
- Existing endpoints (health, rag/query, rag/ingest)

### core/orchestrator.py

**To be refactored for v0.3:**

- Old: Synchronous step-by-step analysis
- New: Async pipeline with caching layer
- Checks cache before extracting vision
- Enrich RAG queries with spatial context
- Returns job status updates

## Starting the Server

```bash
cd /d/CAPSTONE/project\ 10
python app/main.py
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

## Next Steps (v0.3)

- [ ] Add cache_manager.py for cache operations
- [ ] Add spatial_enricher.py for shapefile integration
- [ ] Add job_queue.py for tracking jobs
- [ ] Create workers/ for background processing
- [ ] Update routes.py for async/batch endpoints
- [ ] Update orchestrator.py for async pipeline
