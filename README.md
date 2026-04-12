# Geo-RAG Platform - Complete System Documentation

## Overview

A production-ready **Geo-RAG (Retrieval-Augmented Generation) Platform** for satellite imagery analysis with async job queue, multi-stage pipeline, and intelligent caching.

**Key Features:**

- 🖼️ Vision extraction from satellite images (Qwen3-VL)
- 📚 Semantic & keyword-based knowledge retrieval (RAG)
- 🧠 LLM-powered analysis (Gemma 3 4B)
- ⚡ Async job queue with background workers
- 💾 Multi-layer caching (vision, embeddings, responses)
- 🌍 GIS spatial enrichment (advanced mode)
- 📊 Real-time job monitoring & tracing

> **Note for Collaborators:** Looking for a detailed breakdown of how the Embeddings, ChromaDB backend, and internal JobQueue Workers communicate? Please read our [**System Logic and Tools Overview**](docs/SYSTEM_LOGIC_AND_TOOLS.md).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server (8000)                     │
│  - Async job submission endpoints                            │
│  - Job status polling                                        │
│  - Cache management                                          │
│  - Health checks                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   [Vision Worker]  [Retriever]  [Answer Generator]
   (extracts       (semantic +    (LLM generation)
    features)      keyword search)
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
   [Job Queue]                      [Cache Layer]
   (SQLite)                    (SQLite + memory)
   - Track 4 pipeline stages
   - Store results & timing
   - Enable async flow
```

---

## File Structure

```
app/
├── main.py                 # FastAPI entry point, lifespan hooks, worker spawning
├── config.py              # Constants (models, paths, limits)
├── api/
│   ├── routes.py          # HTTP endpoints (/analyze, /status, /batch, etc.)
│   └── schemas.py         # Pydantic models (request/response types)
├── core/
│   ├── orchestrator.py     # Main analysis pipeline (vision → retrieval → LLM)
│   └── prompt_builder.py   # Construct LLM prompts (mode-specific)
├── services/
│   ├── job_queue.py        # Job lifecycle management (SQLite)
│   ├── llm_service.py      # LLM API calls (Gemma 3 4B via Ollama)
│   ├── vision_service.py   # Vision extraction (Qwen3-VL via Ollama)
│   └── rag_service.py      # Retrieval (semantic + keyword + GIS)
├── workers/
│   ├── vision_extractor.py # Background worker: image → features
│   ├── retriever.py        # Background worker: question → chunks
│   └── answer_generator.py # Background worker: context → answer
└── utils/
    ├── cache_manager.py    # Multi-layer caching (vision, embeddings, responses)
    ├── spatial_enricher.py # GIS shapefile loading & spatial queries
    └── __init__.py
```

---

## API Endpoints

### Analysis

**POST `/api/analyze`** - Submit image for async analysis

```
multipart/form-data:
  - image: file              (required)
  - question: string         (required)
  - mode: string            (default: "rag_baseline")
             "llm_only" | "rag_baseline" | "rag_advanced"

Response: { job_id, status: "queued", message }
```

**GET `/api/status/{job_id}`** - Poll for job progress

```
Response:
{
  "job_id": "...",
  "status": "queued|processing|completed|failed",
  "progress": 0-100,
  "current_stage": "vision_extraction|knowledge_retrieval|answer_generation",
  "created_at": ISO8601,
  "started_at": ISO8601,
  "completed_at": ISO8601,           # if completed
  "processing_seconds": float,        # if completed
  "result": "answer text",            # if completed
  "trace": {...},                     # if completed
  "error": "message"                  # if failed
}
```

### Batch Processing

**POST `/api/batch`** - Submit multiple images

```
multipart/form-data:
  - images: file[]           (required)
  - questions: JSON array    (required)
  - mode: string            (default: "rag_baseline")

Response: { batch_id, total_jobs, job_ids, status, message }
```

**GET `/api/batch/{batch_id}`** - Get batch progress

```
Response:
{
  "batch_id": "...",
  "total": 10,
  "completed": 5,
  "processing": 2,
  "queued": 3,
  "failed": 0,
  "progress": 50.0,
  "jobs": [
    { "job_id": "...", "status": "...", "progress": ... },
    ...
  ]
}
```

### Cache Management

**POST `/api/cache/clear`** - Clear all caches

**GET `/api/cache/stats`** - View cache statistics

### Monitoring

**GET `/api/health`** - System health check

```
Response:
{
  "status": "healthy|degraded|unhealthy",
  "vision_model": "qwen3-vl",
  "llm_model": "gemma-3-4b",
  "vision_ok": bool,
  "llm_ok": bool,
  "queue_stats": { total_jobs, active_jobs, completed_jobs, ... },
  "cache_enabled": true
}
```

**GET `/api/queue/stats`** - Job queue statistics

**GET `/api/spatial/status`** - GIS enrichment status

---

## Pipeline Stages

### Stage 1: Vision Extraction (All Modes)

- Worker: `VisionExtractor`
- Calls: `vision_service.extract_features(image_hash)`
- Output: 6 vision features (vegetation, buildings, roads, patterns, expansion signs, settlements)
- Cache: Vision features keyed by image hash
- Duration: ~2-3s per image

### Stage 2: Knowledge Retrieval (RAG Modes Only)

- Worker: `Retriever`
- Calls:
  - `rag_service.semantic_search()` - Dense vector search
  - `rag_service.keyword_search()` - BM25 inverse index
  - `rag_service.merge_and_rerank()` - Reciprocal Rank Fusion
  - `rag_service.gis_query()` - Spatial queries (advanced mode only)
- Output: Ranked knowledge chunks + GIS enrichment
- Cache: Retrieval results keyed by question hash
- Duration: ~1-2s (or instant from cache)

### Stage 3: Answer Generation

- Worker: `AnswerGenerator`
- Calls: `llm_service.generate(prompt, temperature=0.3)`
- Input: Vision + retrieval + spatial context (mode-dependent) + question
- Output: Final answer text
- Cache: Response cached by job_id
- Duration: ~3-5s per question

---

## Job States

```
queued → processing → completed
↓         ↓           (with result)
          failed
          (with error)
```

**Progress Breakdown:**

- Vision extraction: 0-25%
- Knowledge retrieval: 25-50%
- Answer generation: 50-100%

---

## Analysis Modes

### 1. **LLM-Only** (`llm_only`)

- Uses only vision features
- No knowledge base access
- Fast, baseline for comparison
- Best for: Quick answers with visual context only

### 2. **RAG Baseline** (`rag_baseline`)

- Vision extraction + semantic search only
- Hybrid retrieval disabled
- Faster than advanced
- Best for: Standard RAG with semantic relevance

### 3. **RAG Advanced** (`rag_advanced`)

- Vision + semantic + keyword + GIS enrichment
- Hybrid retrieval with RRF reranking
- Slowest but most contextual
- Best for: Complex spatial analysis with full context

---

## Caching Strategy

### Vision Cache

- **Key:** SHA256 hash of image bytes
- **Content:** 6 extracted features
- **TTL:** 30 days
- **Hit Ratio:** High (same image analyzed multiple ways)

### Embeddings Cache

- **Key:** SHA256 hash of (question + mode)
- **Content:** Retrieved chunks + GIS data
- **TTL:** 90 days
- **Hit Ratio:** Medium (question variation)

### Response Cache

- **Key:** job_id
- **Content:** Final answer + full trace
- **TTL:** 7 days
- **Hit Ratio:** Low (unique questions per image)

**Cache Enable:** `ENABLE_CACHING=true` in env

---

## Configuration

Edit `app/config.py`:

```python
# LLM & Vision Models
VISION_MODEL = "qwen3-vl"           # Ollama-hosted vision model
LLM_MODEL = "gemma-3-4b"            # Ollama-hosted LLM
OLLAMA_BASE_URL = "http://localhost:11434"

# Constraints
MAX_IMAGE_SIZE_MB = 10
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/tiff", "image/webp"]

# Caching
ENABLE_CACHING = True
CACHE_STORAGE = "sqlite"  # or "memory"

# Job Cleanup
JOB_ARCHIVE_AFTER_DAYS = 7
```

---

## Running the System

### Prerequisites

- Python 3.11+
- Ollama running locally (models must be pulled):
  ```bash
  ollama pull qwen3-vl
  ollama pull gemma-3-4b
  ollama serve  # on port 11434
  ```

### Startup

```bash
# Option 1: From project root
python -m app.main

# Option 2: Direct from app directory
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Option 3: Production
cd app
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

**Access:**

- API: http://localhost:8000/api/\*
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Testing

### System Integration Test

```bash
python test_system.py
```

Tests:

- Job creation & lifecycle
- Stage transitions
- Cache read/write
- Prompt building
- Queue statistics

### API Startup Test

```bash
python test_api.py
```

Tests:

- FastAPI app creation
- Route registration
- Worker imports
- Middleware setup

---

## Performance Targets

| Stage                 | Duration  | Cache Hit                     |
| --------------------- | --------- | ----------------------------- |
| Vision Extraction     | 2-3s      | Instant                       |
| Knowledge Retrieval   | 1-2s      | Instant                       |
| Answer Generation     | 3-5s      | N/A                           |
| **Total (no cache)**  | **6-10s** | N/A                           |
| **Total (cache hit)** | **3-5s**  | **Vision + Retrieval cached** |

---

## Error Handling

### Connection Errors

- Vision service unavailable → Fallback features
- LLM service unavailable → Error response
- Job queue unavailable → HTTP 500

### Validation Errors

- Invalid image type → HTTP 400
- Invalid mode → HTTP 400
- Empty question → HTTP 400
- Image too large → HTTP 400

### Pipeline Errors

- Vision extraction fails → Fallback, continue
- Retrieval fails → Stop, mark failed
- LLM fails → Return error message

---

## Logging

All modules log to:

- **Level:** INFO (configurable in `main.py`)
- **Format:** `HH:MM:SS | LEVEL | module | message`
- **Destination:** stdout (rotate logs in production)

Key log markers:

- `Created job {job_id}` - Job submitted
- `Vision: Processing {job_id}` - Vision extraction started
- `Retriever: Processing {job_id}` - Retrieval started
- `Answer Generator: Processing {job_id}` - Answer generation started
- `Completed {job_id}` - Job done (any worker)

---

## Future Enhancements

- [ ] Multi-GPU vision/LLM inference
- [ ] Distributed job queue (Redis)
- [ ] Streaming responses (Server-Sent Events)
- [ ] User authentication & quota management
- [ ] A/B testing framework for prompts
- [ ] Fine-tuned LLM for geo-analysis
- [ ] Real-time map overlay visualization
- [ ] Cost tracking per analysis

---

## License & Attribution

Built as part of CAPSTONE Project 10 - Geo-RAG Analysis Platform.

Models:

- Vision: Qwen3-VL (Alibaba)
- LLM: Gemma 3 4B (Google DeepMind)
- Embedding: (configured in `rag_service.py`)

---

## Contact & Support

For issues or questions:

1. Check logs: `tail -f app.log`
2. Review test output: `python test_system.py`
3. Verify Ollama health: `curl http://localhost:11434/api/health`
