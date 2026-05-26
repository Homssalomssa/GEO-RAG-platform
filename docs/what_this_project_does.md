# What This Project Does — Geo-RAG Platform

**Purpose of this document:** A single, self-contained reference for developers and coding assistants. Read this file first before changing code. It describes what the project is, how data flows end-to-end, what every major directory contains, and how components connect.

**Canonical architecture doc:** [ARCHITECTURE_v0.3.md](./ARCHITECTURE_v0.3.md) — async job pipeline, cache layers, workers, and v0.3 design rationale. Use that file for full system design; this document is the onboarding map.

**Project name:** Geo-RAG Platform (CAPSTONE Project 10)  
**Version:** 0.3.0 (async job pipeline + React UI)  
**One-line summary:** Upload satellite imagery, ask a natural-language question, and get an evidence-based urban/geospatial analysis by combining local vision AI, vector retrieval (RAG), and a local LLM — entirely offline via Ollama.

---

## Table of Contents

1. [What Problem It Solves](#1-what-problem-it-solves)
2. [High-Level Architecture](#2-high-level-architecture)
3. [End-to-End Request Flow](#3-end-to-end-request-flow)
4. [Analysis Modes (Research Benchmark)](#4-analysis-modes-research-benchmark)
5. [Directory Map — Every Folder Explained](#5-directory-map--every-folder-explained)
6. [Backend (`app/`) — Module by Module](#6-backend-app--module-by-module)
7. [Frontend (`frontend/`) — UI and API Client](#7-frontend-frontend--ui-and-api-client)
8. [Data Layer — Knowledge, Imagery, Shapefiles](#8-data-layer--knowledge-imagery-shapefiles)
9. [Urban Tiles Dataset (`urban_tiles/`)](#9-urban-tiles-dataset-urban_tiles)
10. [Scripts (`scripts/`) — Offline Setup Utilities](#10-scripts-scripts--offline-setup-utilities)
11. [Cache and Job Persistence (`cache/`)](#11-cache-and-job-persistence-cache)
12. [Vector Database (`chroma_db/`)](#12-vector-database-chroma_db)
13. [Tests (`tests/`)](#13-tests-tests)
14. [Configuration and Environment](#14-configuration-and-environment)
15. [How to Run (Canonical)](#15-how-to-run-canonical)
16. [API Contract Summary](#16-api-contract-summary)
17. [Two Execution Paths (Important)](#17-two-execution-paths-important)
18. [Known Gaps, Inconsistencies, and TODOs](#18-known-gaps-inconsistencies-and-todos)
19. [Where to Look When Debugging](#19-where-to-look-when-debugging)
20. [Related Documentation](#20-related-documentation)

---

## 1. What Problem It Solves

Urban planners and researchers need to interpret **satellite/aerial imagery** with **domain knowledge** (administrative boundaries, land-use definitions, regional statistics). Raw vision LLMs hallucinate; pure RAG ignores what is actually in the image.

Geo-RAG combines:

| Layer | Role |
|-------|------|
| **Vision** | Extract six structured features from the image (vegetation, buildings, roads, urban pattern, expansion, informal settlement indicators) |
| **Retrieval (RAG)** | Pull relevant text chunks from a local ChromaDB knowledge base (global urban_tiles city tiles) |
| **GIS enrichment** | Rule-based (and planned shapefile-based) geospatial context |
| **LLM** | Synthesize features + retrieved knowledge into a cited, structured answer |

The platform also supports **three analysis modes** so capstone research can compare how much retrieval and GIS help answer quality.

Everything runs **locally** — Ollama for vision/LLM, sentence-transformers for embeddings, ChromaDB for vectors. No cloud API keys required for core operation.

---

## 2. High-Level Architecture

> Full v0.3 design (diagrams, cache schema, worker contracts, migration notes): **[ARCHITECTURE_v0.3.md](./ARCHITECTURE_v0.3.md)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                                       │
│  React + Vite UI  →  upload image(s), question, mode  →  poll for results   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTP  /api/*
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FastAPI  (app/main.py)                                    │
│  • CORS, routes (app/api/routes.py)                                          │
│  • On startup: spawn 3 asyncio background workers                            │
│  • Optionally serves static frontend from /frontend                          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
   ┌──────────────┐        ┌──────────────┐        ┌──────────────────┐
   │ Vision       │        │ Retriever    │        │ Answer           │
   │ Extractor    │   →    │ Worker       │   →    │ Generator        │
   │ Worker       │        │              │        │ Worker           │
   └──────┬───────┘        └──────┬───────┘        └────────┬─────────┘
          │                       │                          │
          ▼                       ▼                          ▼
   vision_service          rag_service                 llm_service
   (Ollama llava)          (ChromaDB + BM25)           (Ollama gemma3)
          │                       │                          │
          └───────────────────────┴──────────────────────────┘
                                  │
                    JobQueue (JSON) + CacheManager (JSON files)
                                  │
                    chroma_db/  +  urban_tiles/ (ingested via scripts/ingest_urban_tiles.py)
```

**External runtime dependency:** [Ollama](https://ollama.ai) at `http://localhost:11434` with models `llava:7b` (vision) and `gemma3:1b` (text).

---

## 3. End-to-End Request Flow

This is the **production path** used by the UI and `/api/analyze`.

### Step 0 — User submits analysis

- **Frontend:** `POST /api/analyze` with `multipart/form-data`: `image`, `question`, `mode`.
- **Backend:** `app/api/routes.py` → `analyze_image_async()`.

### Step 1 — Validation and job creation

1. Validate image MIME type (`jpeg`, `png`, `tiff`, `webp`), size (≤ 10 MB), question (non-empty, ≤ 500 chars), mode enum.
2. SHA-256 hash the image bytes → `image_hash`.
3. `JobQueue.create_job(image_hash, question, mode)` → short `job_id` (8 hex chars).
4. Write raw image to `/tmp/{job_id}.img` (used by vision worker; deleted after vision stage).
5. Return immediately: `{ job_id, status: "queued" }` — **non-blocking**.

### Step 2 — Vision Extractor Worker (`app/workers/vision_extractor.py`)

Loop (every ~1s): find jobs with `status == "queued"`.

For each job (max 2 concurrent):

1. Set job `processing`, stage `vision_extraction`.
2. **Cache check:** `CacheManager.get_vision(image_hash)` — if hit, skip Ollama.
3. **Cache miss:** read `/tmp/{job_id}.img`, base64-encode, call `vision_service.extract_features()`.
4. Store features in `cache/vision/{image_hash}.json`.
5. Mark stage `vision_extraction` → `completed` (progress ~25%).
6. Delete temp image file.

**Vision output (6 fields):** `vegetation_density`, `building_density`, `road_density`, `urban_pattern`, `expansion_signs`, `illegal_settlement_indicators`.

### Step 3 — Retriever Worker (`app/workers/retriever.py`)

Loop (every ~0.5s): jobs where `vision_extraction == completed` and `knowledge_retrieval == pending`.

1. Mark `spatial_enrichment` completed (currently a **no-op** placeholder).
2. Hash `question + mode` → `query_hash`.
3. **Cache check:** `get_embeddings(query_hash)`.
4. **Cache miss:**
   - `semantic_search(question + spatial_context)` — ChromaDB cosine similarity, top 5.
   - `keyword_search(question)` — BM25, top 3.
   - `merge_and_rerank()` — Reciprocal Rank Fusion (RRF, k=60).
5. Store in `cache/embeddings/{query_hash}.json` (7-day TTL).
6. Mark `knowledge_retrieval` → `completed` (~50% progress).

**Note:** Workers always run hybrid retrieval; they do **not** branch on `llm_only` vs `rag_advanced` the way `orchestrator.py` does. Mode mainly affects the final prompt in the answer worker.

### Step 4 — Answer Generator Worker (`app/workers/answer_generator.py`)

Loop: jobs where `knowledge_retrieval == completed` and `answer_generation == pending`.

1. Load vision features from cache (required).
2. Load retrieval results from cache (required).
3. `prompt_builder.build_prompt(question, vision_features, retrieval_results, spatial_context, mode)`.
4. `llm_service.generate(prompt)` via Ollama.
5. Cache response in `cache/llm_responses/{job_id}_result.json`.
6. `JobQueue.set_result()` → status `completed`, progress 100%.

### Step 5 — User polls status

- **Frontend:** `GET /api/status/{job_id}` every 500 ms (max ~2.5 min).
- When `status === "completed"`, display `result`, `vision_features`, `retrieved_context`, timing.

### Batch flow

- `POST /api/batch` — multiple images + JSON array of questions; shared `batch_id`.
- `GET /api/batch/{batch_id}` — aggregate progress across jobs.

---

## 4. Analysis Modes (Research Benchmark)

Defined in `app/api/schemas.py` as `AnalysisMode` enum:

| Mode | Value | Vision | Retrieval | GIS in prompt | Intended use |
|------|-------|--------|-----------|---------------|--------------|
| **LLM Only** | `llm_only` | Yes | Skipped in orchestrator; workers still retrieve* | No | Baseline: image features only |
| **RAG Baseline** | `rag_baseline` | Yes | Semantic search only (orchestrator); workers use hybrid | No | Simple RAG |
| **RAG Advanced** | `rag_advanced` | Yes | Hybrid + GIS enrichment (orchestrator) | Yes | Full pipeline |

\*See [§17 Two Execution Paths](#17-two-execution-paths-important) — async workers do not fully honor `llm_only` today.

**Prompt differences** (`app/core/prompt_builder.py`):

- `build_prompt_llm_only` — features + question only.
- `build_prompt_rag_baseline` — features + retrieved chunks + question.
- `build_prompt_rag_advanced` — features + chunks + GIS block + question.

**Retrieval query enrichment** (`build_retrieval_query`): maps question keywords (e.g. "illegal", "sprawl") to relevant vision feature keys and appends feature values to the search query (used by synchronous orchestrator, not fully wired in async retriever worker).

---

## 5. Directory Map — Every Folder Explained

```
project 10/                          # Repository root
├── app/                             # ★ Python backend (FastAPI + workers)
├── frontend/                        # ★ React + Vite UI (primary interface)
├── frontend-backup/                 # Legacy vanilla JS UI (superseded)
├── data/                            # Source datasets (knowledge, imagery, shapefiles)
├── urban_tiles/                     # Global city tile library + vector metadata (not wired to app yet)
├── cache/                           # Runtime: job queue JSON, vision/embedding/LLM caches
├── chroma_db/                       # Runtime: ChromaDB persistence (created after ingest; gitignored)
├── scripts/                         # One-off setup: ingest, GEE fetch, spatial index, validation
├── tests/                           # pytest suites
├── docs/                            # Human documentation (including this file)
├── requirements.txt                 # Python dependencies
├── README.md                        # User-facing quick start
├── HOW_TO_RUN.md                    # Two-terminal run instructions
├── START.bat / START.sh             # Automated setup + launch scripts
└── .gitignore                       # Ignores chroma_db/, cache/*.json, venv, etc.
```

### What is NOT in git (generated at runtime)

- `chroma_db/` — vector store after ingestion
- `cache/vision/*.json`, `cache/embeddings/*.json`, `cache/llm_responses/*.json`
- `cache/metadata/job_queue.json`, `cache_index.json`
- `/tmp/{job_id}.img` — transient upload buffers
- `app/cache/` — may appear if backend was started with CWD = `app/` (see §14)

---

## 6. Backend (`app/`) — Module by Module

### `app/main.py` — Entry point

- Creates FastAPI app v0.3.0.
- CORS `allow_origins=["*"]` (MVP).
- Includes `api.routes` router at `/api`.
- **Startup:** `asyncio.create_task` for three workers (vision, retriever, answer).
- **Shutdown:** cancels worker tasks.
- Mounts `../frontend` as static files at `/` if folder exists (serving built or raw frontend depends on build state; dev usually uses Vite on port 5173).

**Run from project root:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Run from app/ (START.bat):**
```bash
cd app && python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
This affects relative paths like `./cache` and `./chroma_db`.

---

### `app/config.py` — Single source of settings

| Setting | Default | Meaning |
|---------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `VISION_MODEL` | `llava:7b` | Vision model (docs sometimes say qwen3-vl; config/README use llava) |
| `LLM_MODEL` | `gemma3:1b` | Text generation |
| `CACHE_DIR` | `./cache` | Relative to process CWD |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB path |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers |
| `SEMANTIC_TOP_K` / `KEYWORD_TOP_K` | 5 / 3 | Retrieval limits |
| `RRF_K` | 60 | RRF constant |
| `SHAPEFILE_DIR` | `./data/shapefiles` | Tunisia ADM2 boundaries |
| `TUNISIA_REGIONS` | 39236–39240 | Five Ariana governorate ADM2 codes |
| `SPATIAL_ENRICHMENT_ENABLED` | `True` | Flag for shapefile loading |

Override via `.env` (python-dotenv loaded on import).

---

### `app/api/routes.py` — HTTP API

| Endpoint | Method | Behavior |
|----------|--------|----------|
| `/api/analyze` | POST | Async job: image file + question + mode → `job_id` |
| `/api/batch` | POST | Multiple images + questions JSON |
| `/api/status/{job_id}` | GET | Poll progress/result |
| `/api/batch/{batch_id}` | GET | Batch aggregate status |
| `/api/cache/clear` | POST | Wipe all cache tiers |
| `/api/cache/stats` | GET | Cache index statistics |
| `/api/health` | GET | `{ status, vision_model, llm_model }` |
| `/api/queue/stats` | GET | Job queue metrics |
| `/api/spatial/status` | GET | Shapefile load status |

Singleton: `job_queue = JobQueue()` at module level.

---

### `app/api/schemas.py` — Pydantic contracts

Request/response models: `AnalyzeRequest`, `AnalyzeResponse`, `VisionFeatures`, `RetrievedChunk`, `GISData`, `ReasoningTrace`, `TimingInfo`, `AnalysisMode` enum.

Used by orchestrator and tests; async API returns dicts shaped similarly in `get_job_status`.

---

### `app/services/` — External integrations

#### `job_queue.py`

- **Singleton** `JobQueue` with file lock (`filelock`).
- Persists to `{CACHE_DIR}/metadata/job_queue.json`.
- Job fields: `status`, `stages` (4 keys), `progress`, `timing`, `result`, `error`, `request` (hash, question, mode).
- Stages: `vision_extraction` → `spatial_enrichment` → `knowledge_retrieval` → `answer_generation`.

#### `vision_service.py`

- POST `{OLLAMA}/api/generate` with `images: [base64]` and structured JSON prompt.
- Parses JSON; fallback regex per field; raises if &lt; 3 fields recovered.

#### `rag_service.py`

- **ChromaDB** `PersistentClient` + collection `geo_knowledge` (cosine HNSW).
- **Ingestion:** 500-char chunks, 100-char overlap, sentence-transformer embeddings, BM25 rebuild.
- **semantic_search** — embedding query → ChromaDB.
- **keyword_search** — BM25Okapi over all chunks.
- **merge_and_rerank** — RRF dedupe by first 100 chars of chunk.
- **gis_query** — rule-based metrics from vision feature strings (orchestrator advanced mode).

#### `llm_service.py`

- POST `{OLLAMA}/api/generate`, temperature 0.3, max 1024 tokens, retry once on empty response.

---

### `app/workers/` — Async pipeline (v0.3)

| File | Class | Trigger condition |
|------|-------|-------------------|
| `vision_extractor.py` | `VisionExtractor` | `status == queued` |
| `retriever.py` | `Retriever` | vision done, retrieval pending |
| `answer_generator.py` | `AnswerGenerator` | retrieval done, answer pending |

Each worker has `run()` infinite loop and `process_job(job_id)`.

---

### `app/core/` — Business logic

#### `orchestrator.py` — **Synchronous** full pipeline

`analyze(image_base64, question, mode) → AnalyzeResponse`:

1. Vision (all modes)
2. Retrieval (mode-dependent: skip / semantic only / hybrid + GIS)
3. Mode-specific prompt
4. LLM generate
5. Assemble trace + timing

**Used by:** `tests/test_integration.py`, `tests/test_orchestrator.py` — **not** called from `routes.py` in v0.3.

#### `prompt_builder.py`

- Mode templates + `build_retrieval_query()` + unified `build_prompt()` for workers.

---

### `app/utils/`

#### `cache_manager.py`

Three tiers under `CACHE_DIR`:

| Tier | Path | Key | TTL |
|------|------|-----|-----|
| Vision | `vision/{image_hash}.json` | Image SHA-256 | Never |
| Embeddings | `embeddings/{query_hash}.json` | SHA-256(question+mode) | 7 days |
| LLM responses | `llm_responses/{job_id}_result.json` | job_id | 30 days |

Metadata: `metadata/cache_index.json` (hit counts, sizes).

#### `spatial_enricher.py`

- Loads `data/shapefiles/tunisia_adm2.geojson` or `.shp` via GeoPandas (optional dep).
- `get_region_from_coordinates(lon, lat)` — point-in-polygon for Tunisia ADM2.
- `enrich_rag_context(region_info)` — text block for prompts.
- **Not fully connected** to retriever worker (TODO in `retriever.py`).

---

## 7. Frontend (`frontend/`) — UI and API Client

**Stack:** React 18, Vite 5, Tailwind CSS 3.  
**Dev server:** port 5173, proxies `/api` → `http://127.0.0.1:8000` (`vite.config.js`).

### Page flow (`src/App.jsx`)

1. **Upload** — drag/drop images, question textarea, mode selector, Analyze button.
2. **Results** — progress bar, polling messages, result cards per image.
3. **System Status** — polls `/api/health` every 5s.

### Key modules

| Path | Role |
|------|------|
| `src/utils/api.js` | `submitAnalysis`, `checkJobStatus`, `pollJobStatus` |
| `src/utils/constants.js` | `API_BASE='/api'`, polling limits, mode metadata |
| `src/hooks/useAnalysis.js` | Reusable analyze + poll hook (optional; App.jsx duplicates logic) |
| `src/components/upload/*` | UploadZone, ImageGrid, AnalysisSettings |
| `src/components/results/*` | LoadingProgress, ResultCard |
| `src/components/shared/ModeSelector.jsx` | Three mode cards |

### User journey (code path)

```
UploadPage → handleAnalyze() in App.jsx
  → submitAnalysis(file, question, mode)
  → pollJobStatus(jobId, onProgress)
  → ResultsPage renders answer, visionFeatures, retrievedContext
```

---

## 8. Data Layer — Knowledge, Imagery, Shapefiles

### `data/knowledge/` — RAG source documents (13 .txt files)

- **Domain:** `urban_planning.txt`, `settlement_patterns.txt`, `land_use_definitions.txt`
- **Tunisia ADM2:** `tunisia_adm2_{39236..39240}_*.txt` (+ `_enhanced` variants with GEE-derived NDVI, built-up fraction, vegetation fraction, interpretation tags)

Example content structure (per region):

- Administrative hierarchy (country, governorate, ADM2 code)
- Centroid coordinates
- Earth Engine metrics (NDVI, WorldCover fractions)
- Tags aligned with vision feature names for better retrieval

**Ingestion:** must populate ChromaDB before RAG returns useful results:

```bash
# From project root — ensure PYTHONPATH includes app or run from app/
cd app && python -c "
import sys; sys.path.insert(0, '.')
from services.rag_service import ingest_documents
from pathlib import Path
docs = []
for p in Path('../data/knowledge').glob('*.txt'):
    docs.append({'text': p.read_text(encoding='utf-8'), 'source': p.name})
print(ingest_documents(docs))
"
```

**Quirk:** `scripts/ingest_knowledge.py` sets `KNOWLEDGE_DIR = scripts/knowledge` (wrong path). `START.bat` passes `--glob "data/knowledge/*.txt"` but globs inside `scripts/knowledge/`, so automated ingest in START.bat may find **zero files** unless paths are fixed. Manual ingest from `data/knowledge/` is required today.

---

### `data/imagery/timeseries/`

Sentinel-2 derived PNG/TIFF collections per Tunisia ADM2 region (2020–2025), with `metadata.json` per folder. Used for experiments and scripts — **not** auto-loaded by the web upload flow (users upload their own images).

Regions: `39236_ariana_ville`, `39237_el_mnihla`, `39238_ettadhamen`, `39239_kalaat_el_andalous`, `39240_raoued`.

---

### `data/shapefiles/`

- Tunisia ADM2 boundaries (`tunisia_adm2.shp` / `.geojson` when setup completes)
- `rtree_index.idx` — spatial index from `scripts/spatial_setup.py`
- `metadata.json` — index metadata

Consumed by `SpatialEnricher` when GeoPandas is installed.

---

## 9. Urban Tiles Dataset (`urban_tiles/`)

**Purpose:** Pre-cut global urban satellite tiles with derived metadata for future large-scale retrieval or benchmarking. **Ingested into ChromaDB** via `scripts/ingest_urban_tiles.py` (104 tiles, 12 cities). Not loaded automatically on image upload.

### Structure per city

```
urban_tiles/{city}/
├── tile_0000.jpg / tile_0000.tif   # Image tiles
├── tile_0001.jpg / ...
└── vectors/
    ├── all_vectors.json            # Full tile index for city
    ├── batch_3.json, batch_6.json  # Partial batches (embedding pipeline checkpoints)
```

### Cities present

`cairo`, `chicago`, `dubai`, `istanbul`, `manhattan`, `paris`, `sao_paulo`, `singapore`, `sydney`, `tokyo`, `tunis`, `venice` (tile counts vary; São Paulo and Tokyo have the most tiles).

### Vector JSON schema (per tile entry)

Each record in `vectors/all_vectors.json` includes:

- `region_id` — e.g. `tile_0000`
- `geometry` — GeoJSON polygon
- `bbox` — `[min_lon, min_lat, max_lon, max_lat]`
- `image_path` — relative path to `.tif`
- `lulc_stats` — land-cover fractions (`built_up`, `vegetation`, etc.)

**Intended future use:** global RAG context, cross-city comparison, or precomputed embeddings — described in UI copy for `rag_advanced` but not implemented in backend workers yet.

---

## 10. Scripts (`scripts/`) — Offline Setup Utilities

| Script | Purpose |
|--------|---------|
| `ingest_urban_tiles.py` | Load `urban_tiles/*/vectors/all_vectors.json` into ChromaDB |
| `spatial_setup.py` | Download/index Tunisia ADM2 (GEE or fallback) |
| `spatial_setup_fallback.py` | Alternative shapefile source |
| `fetch_satellite_imagery_gee.py` | Single-year Sentinel-2 via Google Earth Engine |
| `fetch_timeseries_imagery_gee.py` | Multi-year imagery → `data/imagery/timeseries/` |
| `build_tunisia_knowledge_adm2.py` | Generate region knowledge text files |
| `enhance_knowledge_metadata.py` | Add GEE stats to knowledge docs |
| `verify_knowledge_base.py` | Sanity-check ChromaDB contents |
| `image_knowledge_index.py` | Static map ADM2 code → image path + knowledge path |
| `explore_tunisia_codes.py` | Lookup GAUL ADM2 codes |
| `summarize_timeseries.py` | Imagery collection stats |
| `visualize_imagery_dashboard.py` | Optional dashboard |

**Typical first-time setup:**

```bash
python scripts/fetch_timeseries_imagery_gee.py   # optional; needs GEE auth
# ingest knowledge (fix path or use manual method in §8)
python scripts/spatial_setup.py
python scripts/verify_knowledge_base.py
```

Scripts are **not** imported by the running server; run manually from repo root.

---

## 11. Cache and Job Persistence (`cache/`)

Documented in `cache/README.md`. At runtime:

```
cache/
├── vision/{sha256}.json
├── embeddings/{query_hash}.json
├── llm_responses/{job_id}_result.json
└── metadata/
    ├── cache_index.json    # stats
    └── job_queue.json      # all jobs
```

**Job lifecycle states:** `queued` → `processing` → `completed` | `failed` (also `cached` mentioned in stats).

**Why it matters:** Re-asking questions on the same image avoids re-running llava (largest cost). Repeating identical question+mode skips ChromaDB queries.

---

## 12. Vector Database (`chroma_db/`)

- Created on first `ingest_documents()` call.
- Collection: `geo_knowledge`, cosine space.
- **Gitignored** — each developer must ingest locally.
- BM25 index lives **in memory** inside `rag_service` (rebuilt on ingest); not persisted separately.

---

## 13. Tests (`tests/`)

| File | What it tests |
|------|----------------|
| `test_system.py` | Job queue + cache + prompt smoke (no Ollama) |
| `test_api.py` | FastAPI app loads, routes exist |
| `test_rag.py` | Chunking, RRF, GIS rules |
| `test_vision.py` | Vision parsing (needs Ollama) |
| `test_orchestrator.py` | Prompt builder + retrieval query |
| `test_integration.py` | Full **synchronous** `orchestrator.analyze()` (needs Ollama + ChromaDB) |
| `test_end2end_realimages.py` | Real image fixtures |

Run from root:

```bash
python tests/test_system.py
pytest tests/ -v
```

**Import path note:** Many tests add `app/` to `sys.path` and import `from services...` or `from core...` as if CWD were `app/`.

---

## 14. Configuration and Environment

### Python dependencies (`requirements.txt`)

`fastapi`, `uvicorn`, `python-multipart`, `pydantic`, `httpx`, `chromadb`, `sentence-transformers`, `rank-bm25`, `Pillow`, `python-dotenv`, `filelock`.

Optional (scripts/spatial): `geopandas`, `rtree`, `earthengine-api`.

### Node dependencies (`frontend/package.json`)

`react`, `react-dom`, `vite`, `tailwindcss`, etc.

### Path sensitivity

`CACHE_DIR` and `CHROMA_PERSIST_DIR` are **relative paths**. Starting uvicorn from `app/` vs project root changes where `cache/` and `chroma_db/` land. Prefer **project root**:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 15. How to Run (Canonical)

### Prerequisites

1. Python 3.11+, Node.js
2. Ollama running: `ollama serve`
3. Models: `ollama pull llava:7b` and `ollama pull gemma3:1b`
4. Ingest urban tiles into ChromaDB: `python scripts/ingest_urban_tiles.py --reset`
5. `pip install -r requirements.txt`

### Terminal 1 — Backend

```bash
cd "d:\CAPSTONE\project 10"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). API calls proxy to port 8000.

### Alternative: `START.bat`

Automates Ollama check, model pull, ingest attempt, spatial setup, starts backend from `app/` and frontend — may serve UI at `http://localhost:8000` if using static mount only.

---

## 16. API Contract Summary

### POST `/api/analyze`

**Form fields:** `image` (file), `question` (string), `mode` (`llm_only` | `rag_baseline` | `rag_advanced`)

**Response:**
```json
{ "job_id": "a1b2c3d4", "status": "queued", "message": "..." }
```

### GET `/api/status/{job_id}`

**While running:**
```json
{
  "job_id": "...",
  "status": "processing",
  "progress": 30,
  "current_stage": "knowledge_retrieval",
  "created_at": "...",
  "started_at": "..."
}
```

**When completed:**
```json
{
  "status": "completed",
  "progress": 100,
  "result": "<answer string>",
  "vision_features": { ... },
  "retrieved_context": [ { "chunk", "source", "score" } ],
  "spatial_context": "",
  "trace": { ... },
  "processing_seconds": 12.5
}
```

---

## 17. Two Execution Paths (Important)

| Aspect | Async path (production API) | Sync path (orchestrator) |
|--------|----------------------------|---------------------------|
| Entry | `routes.py` → JobQueue | `orchestrator.analyze()` |
| Vision | `vision_extractor` worker | `vision_service` in-process |
| Retrieval | Always hybrid in `retriever` worker | Mode-aware: skip / semantic / hybrid+GIS |
| LLM | `answer_generator` worker | Direct `llm_service` call |
| Response | Poll JSON job result | Immediate `AnalyzeResponse` |
| Tests | `test_system.py`, `test_api.py` | `test_integration.py` |

When fixing mode-specific behavior, update **both** paths or consolidate on one.

---

## 18. Known Gaps, Inconsistencies, and TODOs

1. **Spatial enrichment** — Stage exists in job queue; `retriever.py` marks it complete without calling `SpatialEnricher` (TODO comment).
2. **`llm_only` in async workers** — Retriever still runs ChromaDB search; answer worker still injects chunks. Orchestrator correctly skips retrieval for `llm_only`.
3. **Model naming in docs/comments** — README says `llava:7b`; older docs mention `qwen3-vl`; `orchestrator.py` log strings mention Qwen/Gemma 4B; `config.py` uses `llava:7b` + `gemma3:1b`.
4. **`ingest_knowledge.py` path** — `KNOWLEDGE_DIR` points to `scripts/knowledge/` not `data/knowledge/`.
5. **`urban_tiles/`** — Wired via offline ingest; upload flow still uses user images + question-based retrieval.
6. **`frontend-backup/`** — Old static UI; ignore unless migrating.
7. **Windows temp path** — Routes write `/tmp/{job_id}.img`; on Windows this may resolve to `C:\tmp` — ensure directory exists or switch to `tempfile` module.
8. **Duplicate cache locations** — `cache/` at repo root vs `app/cache/` if server CWD differs.
9. **GIS in advanced async mode** — `build_prompt` for `rag_advanced` uses placeholder GIS dict, not `rag_service.gis_query(features)`.

---

## 19. Where to Look When Debugging

| Symptom | Check |
|---------|--------|
| Job stuck at queued | Vision worker running? Ollama up? `/tmp/{job_id}.img` exists? |
| Job fails at vision | Ollama logs, `VISION_MODEL` pulled, image size/type |
| Empty RAG context | `chroma_db/` populated? Run ingest. `collection.count()` |
| 404 job not found | `cache/metadata/job_queue.json`, same `CACHE_DIR` CWD |
| Frontend "Failed to fetch" | Backend on 8000, Vite proxy, CORS |
| Slow repeat queries | Vision cache hit? Embedding cache hit? |
| Wrong region knowledge | Ask city-specific questions; Tunisia shapefiles only for spatial stage when wired |

**Log format:** `%(asctime)s | %(levelname)-7s | %(name)s | %(message)s` in `main.py`.

---

## 20. Related Documentation

| File | Focus |
|------|--------|
| `README.md` | Quick start, features |
| `HOW_TO_RUN.md` | Two-terminal instructions |
| `docs/ARCHITECTURE_v0.3.md` | **Canonical** system architecture (async workers, cache, spatial enrichment) |
| `docs/SYSTEM_LOGIC_AND_TOOLS.md` | Tools and workers summary |
| `docs/API.md` | Endpoint reference |
| `docs/MODE_BENCHMARKING.md` | Research mode comparison |
| `app/README.md` | Backend-only notes |
| `data/README.md` | Data layout |
| `cache/README.md` | Cache tiers |
| `scripts/README.md` | Script catalog |

---

## Quick Reference — Mental Model

```
Upload image + question
    → Job ticket (JSON queue)
    → Vision (Ollama llava) → 6 JSON features → cache by image hash
    → Retrieve (ChromaDB + BM25 + RRF) → top chunks → cache by query hash
    → Prompt (mode-specific template)
    → Answer (Ollama gemma3) → cache by job id
    → Poll until completed → show in React UI
```

**Core value:** Structured vision features + global urban tile knowledge retrieved at answer time, with full offline operation suitable for capstone evaluation of RAG vs non-RAG modes.

---

*Last updated: May 2026 — reflects codebase state at Geo-RAG v0.3 (async workers + React frontend).*
