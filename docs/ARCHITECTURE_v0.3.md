# Geo-RAG Platform — New Architecture v0.3.0

**Async-First, Cache-Aware, Spatially-Enriched RAG**

---

## Problem Statement (Why Redesign)

**Current (v0.2.0) Issues**:

- ❌ Qwen3-VL 235B takes 3-4 minutes per image → blocking pipeline
- ❌ Synchronous processing → user waits for full analysis
- ❌ No vision feature caching → recomputes for every query
- ❌ Weak spatial context → RAG doesn't understand "where" in image
- ❌ Single-request design → can't handle multiple images

**Solution**:

- ✅ Async/await non-blocking pipeline
- ✅ Cache vision features on disk (compute once, query many times)
- ✅ Smaller models (Ollama cloud: 1-3B instead of 235B)
- ✅ Shapefile enrichment (add administrative/geographic context)
- ✅ Batch processing queue (analyze multiple images in parallel)

---

## New Architecture (v0.3.0)

```
┌────────────────────────────────────────────────────────────────┐
│                     Frontend (React)                            │
│  - Upload image + question                                     │
│  - Async progress tracking                                     │
│  - Batch upload (zip of images)                                │
└────────────────────┬───────────────────────────────────────────┘
                     │
        ┌────────────▼──────────────┐
        │  API Routes (Async)       │
        │ - /api/analyze (async)    │
        │ - /api/batch (async)      │
        │ - /api/status/:job_id     │
        │ - /api/cache/clear        │
        └────────────┬──────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌──────────────┐ ┌───────────┐ ┌──────────────────┐
│ Job Queue    │ │ Cache     │ │ Shapefile Index  │
│ (Redis/DB)   │ │ Layer     │ │ (Spatial Context)│
│              │ │           │ │                  │
│ - pending    │ │ {         │ │ - Admin Bounds   │
│ - processing │ │   "img_1" │ │ - Region Names   │
│ - completed  │ │   : {     │ │ - Metadata       │
└──────┬───────┘ │     vision│ │                  │
       │         │     : {..}│ │ Enrich RAG:      │
       │         │     embeds│ │ "In Ariana Ville │
       │         │     : [..}│ │  region, known   │
       │         │   }       │ │  for..."         │
       │         │ }         │ │                  │
       │         └───────────┘ └──────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│   Orchestrator (Async Pipeline)         │
│  Step 1: Check cache for vision         │
│  Step 2: If miss → async vision extract │
│  Step 3: Async retrieval (RAG)          │
│  Step 4: Enrich with shapefile context  │
│  Step 5: Async LLM generation           │
│  Step 6: Store in cache                 │
└─────────────────────────────────────────┘
       │
    ┌──┴──┬──────┬──────────┐
    │     │      │          │
    ▼     ▼      ▼          ▼
┌─────┐ ┌───┐ ┌────┐ ┌──────────┐
│Vision│ │RAG│ │LLM │ │ Shapefile│
│Cloud │ │   │ │    │ │ Lookup   │
│Model │ │   │ │    │ │          │
└─────┘ └───┘ └────┘ └──────────┘
(smaller: 1.5B) (cached) (cached) (indexed)

    ▼
Response (to queue, not directly to user)

Frontend polls /api/status/:job_id for progress
```

---

## Key Design Principles

### 1. **Async/Await (Non-Blocking)**

**Before (Synchronous)**:

```
User Request
  → Block on Vision (3 min)
  → Block on Retrieval (0.2 sec)
  → Block on LLM (1.5 sec)
  → Return (3+ min later)
  ❌ User sits waiting, server thread tied up
```

**After (Asynchronous)**:

```
User Request
  → Create background Job
  → Return job_id immediately ✓
  → Server processes in background
  → User polls /api/status/:job_id
  → Results ready when available
  ✅ Server handles 10x more concurrent users
```

**Implementation Pattern**:

```python
# Old (synchronous, blocks)
@app.post("/api/analyze")
def analyze_image(image, question, mode):
    result = analyze(image, question, mode)  # Waits 3+ min
    return result

# New (asynchronous, non-blocking)
@app.post("/api/analyze")
async def analyze_image(image, question, mode):
    job_id = str(uuid.uuid4())
    # Schedule in background, return immediately
    asyncio.create_task(process_job(job_id, image, question, mode))
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = await db.get_job(job_id)
    return {
        "job_id": job_id,
        "status": job.status,  # "queued", "processing", "completed", "failed"
        "progress": job.progress,  # 0-100%
        "result": job.result if job.status == "completed" else None,
        "eta_seconds": estimate_remaining_time(job)
    }
```

**Benefits**:

- Server responds in < 100ms (create job + return ID)
- User can do other things while processing
- Can handle 100 concurrent requests with same resources
- Single server thread doesn't block

---

### 2. **Caching Strategy**

**What to Cache**:

```
Cache Layer (JSON files on disk)
├── vision_features/
│   ├── image_hash_abc123.json       # Vision features (reuse for any question)
│   └── image_hash_def456.json
├── embeddings/
│   ├── query_hash_xyz789.json       # Query -> retrieved chunks (reuse if same question)
│   └── query_hash_uvw456.json
├── llm_responses/
│   ├── job_abc123_llm.json          # LLM answer (don't regenerate)
│   └── responses_index.json         # Quick lookup
└── metadata/
    ├── image_metadata.json           # Image timestamps, file info
    └── cache_index.json              # What's cached, expires, sizes
```

**Cache Hit Example**:

```
Request 1:
  Image: 2020_ariana_ville.png
  Q: "What settlement patterns?"
  → Vision extract (3 min)
  → Cache: features_abc123.json
  → Retrieval → Cache: query_xyz789.json
  → LLM → Cache: response_job123.json

Request 2 (same image, different question):
  Image: 2020_ariana_ville.png
  Q: "Is there urban sprawl?"
  → HIT: Use cached vision_abc123.json (instant!)
  → New retrieval (fresh context)
  → LLM (new answer)
  ✅ Skip 3-minute vision extraction
```

**Caching Rules**:

- Vision features: Cache by image hash (SHA-256), reuse forever (image doesn't change)
- Embeddings: Cache by query+mode hash, expire after 7 days (knowledge may update)
- LLM responses: Cache by (image_hash + query_hash + mode), expire after 30 days
- Metadata index: Update on every cache operation (quick JSON write)

**Cache Miss Handling**:

```python
async def get_vision_features(image_hash, image_bytes):
    # Try cache first
    cached = await cache.get(f"vision/{image_hash}.json")
    if cached:
        return cached  # Instant (< 5ms)

    # Cache miss → compute
    print(f"Cache miss for {image_hash}, computing vision features...")
    features = await vision_service.extract_features(image_bytes)

    # Store in cache
    await cache.set(f"vision/{image_hash}.json", features)

    return features
```

---

### 3. **Batch Analysis**

**Process Multiple Images in Parallel**:

```
Batch Upload (zip with 10 images + questions.json):
  questions.json:
  [
    {"image": "2020_ariana.png", "question": "Settlement pattern?"},
    {"image": "2021_ariana.png", "question": "Settlement pattern?"},
    ...
  ]

Pipeline:
  ├─ Job 1: 2020_ariana (async, background)
  ├─ Job 2: 2021_ariana (async, parallel)
  ├─ Job 3: 2022_ariana (async, parallel)
  ├─ Job 4: 2023_ariana (async, parallel)
  └─ ... (up to 4-8 concurrent, configurable)

User polls /api/batch/{batch_id}:
  {
    "batch_id": "batch_xyz",
    "status": "processing",
    "total": 10,
    "completed": 3,
    "failed": 0,
    "pending": 7,
    "progress": 30,
    "results": [
      {"job_id": "job_1", "image": "2020_ariana.png", "status": "completed", "answer": "..."},
      {"job_id": "job_2", "image": "2021_ariana.png", "status": "completed", "answer": "..."},
      {"job_id": "job_3", "image": "2022_ariana.png", "status": "processing", "progress": 65},
      ...
    ]
  }
```

**Concurrency Limits**:

- Max concurrent vision extractions: 2 (avoid Ollama overload)
- Max concurrent LLM calls: 3 (separate from vision)
- Max queued jobs: 100
- Timeout per job: 10 minutes (for vision + retrieval + LLM)

---

### 4. **Shapefile Enrichment**

**Load at Startup**:

```python
# Load all shapefiles once
shapefiles = {
    "tunisia_adm2": load_shapefile("data/tunisia_adm2.shp"),
    "tunisia_adm1": load_shapefile("data/tunisia_adm1.shp"),
    "landuse_zones": load_shapefile("data/landuse_zones.shp"),
}

# Create spatial index (fast lookup)
spatial_index = create_rtree_index(shapefiles)
```

**During Analysis** (enrich RAG context):

```python
async def enrich_with_spatial_context(image_metadata, vision_features):
    """
    Use image location (from metadata) to find intersecting shapefiles.
    Add spatial context to RAG query.
    """

    # Image has coordinates (from GEE or EXIF)
    lat, lon = image_metadata["centroid_lat"], image_metadata["centroid_lon"]

    # Find intersecting features
    intersects = spatial_index.intersection((lon, lat, lon, lat))

    context = {
        "location": {
            "lat": lat,
            "lon": lon,
            "geometry": image_metadata.get("geometry")
        },
        "administrative": {},
        "landuse": {},
        "climatic": {}
    }

    # Query each shapefile
    for geom_id in intersects:
        feature = shapefiles["tunisia_adm2"].get_feature(geom_id)
        context["administrative"]["adm2_name"] = feature.properties.get("NAME_2")
        context["administrative"]["adm2_code"] = feature.properties.get("GAUL_CODE")
        context["administrative"]["population"] = feature.properties.get("POP_EST")

    # This context augments the RAG query
    # → Better retrieval of region-specific documents
    # → More accurate answers

    return context
```

**Impact on RAG**:

```
Before:
  Q: "Is there illegal settlement?"
  Retrieved: Generic documents about settlements
  → Generic answer

After (with spatial context):
  Q: "Is there illegal settlement in Ariana Ville?"
  Spatial Context: {
    "region": "Ariana Ville",
    "population": 456000,
    "known_issues": "rapid urbanization",
    "adm2_code": 39236
  }
  Retrieved: Ariana-specific settlement documents
  → Targeted answer with regional knowledge
```

---

## JSON Files Needed

### 1. **Vision Feature Cache** (`cache/vision/{image_hash}.json`)

```json
{
  "image_hash": "abc123def456...",
  "image_filename": "2020_ariana_ville_39236.png",
  "timestamp_cached": "2026-03-26T14:30:00Z",
  "vision_model": "llama2-vision:3b",
  "features": {
    "vegetation_density": "medium, approximately 25% coverage",
    "building_density": "high, tightly packed",
    "road_density": "moderate, mix of paved and unpaved",
    "urban_pattern": "irregular, informal layout",
    "expansion_signs": "visible in southern portion",
    "illegal_settlement_indicators": "makeshift structures, no grid"
  },
  "confidence_scores": {
    "vegetation_density": 0.85,
    "building_density": 0.92,
    "road_density": 0.78,
    "urban_pattern": 0.81,
    "expansion_signs": 0.65,
    "illegal_settlement_indicators": 0.72
  },
  "processing_time_ms": 180000,
  "model_version": "0.3.0",
  "expires_at": null
}
```

### 2. **Query Embeddings Cache** (`cache/embeddings/{query_hash}.json`)

```json
{
  "query_hash": "xyz789uvw456...",
  "original_query": "Is there illegal settlement?",
  "mode": "rag_advanced",
  "timestamp_cached": "2026-03-26T14:31:00Z",
  "retrieval_model": "all-MiniLM-L6-v2",
  "semantic_results": [
    {
      "rank": 1,
      "chunk": "Informal settlements often develop without planning...",
      "source": "settlement_patterns.txt",
      "similarity_score": 0.91,
      "is_cached": false
    },
    {
      "rank": 2,
      "chunk": "Urban sprawl exhibits characteristics...",
      "source": "urban_planning.txt",
      "similarity_score": 0.87,
      "is_cached": false
    }
  ],
  "keyword_results": [
    {
      "rank": 1,
      "chunk": "Illegal settlements...",
      "source": "settlement_patterns.txt",
      "bm25_score": 5.2
    }
  ],
  "merged_results": [
    {
      "chunk": "Informal settlements...",
      "source": "settlement_patterns.txt",
      "rrf_score": 0.0328,
      "semantic_rank": 1,
      "keyword_rank": 1
    }
  ],
  "processing_time_ms": 250,
  "expires_at": "2026-04-02T14:31:00Z"
}
```

### 3. **LLM Response Cache** (`cache/llm_responses/{job_id}_result.json`)

```json
{
  "job_id": "job_abc123xyz",
  "image_hash": "abc123def456...",
  "query_hash": "xyz789uvw456...",
  "mode": "rag_advanced",
  "timestamp_cached": "2026-03-26T14:32:30Z",
  "llm_model": "gemma2:3b",
  "answer": "Based on satellite analysis, there are clear indicators of informal settlement...",
  "reasoning_trace": {
    "steps": [
      "1. Extracted vision features: 180s",
      "2. Spatial context enrichment: detected Ariana Ville region",
      "3. Semantic retrieval: found 5 relevant chunks (250ms cache hit)",
      "4. RRF merge: ranked and deduplicated",
      "5. LLM generation: 45s with Gemma2:3b"
    ],
    "timing": {
      "vision_ms": 180000,
      "retrieval_ms": 250,
      "gis_ms": 50,
      "spatial_enrichment_ms": 30,
      "llm_ms": 45000,
      "total_ms": 225330
    }
  },
  "vision_features": {
    "vegetation_density": "medium",
    "building_density": "high",
    "...": "..."
  },
  "retrieved_context": [{ "chunk": "...", "source": "...", "score": 0.91 }],
  "gis_data": {
    "pattern_classification": "informal/unplanned",
    "...": "..."
  },
  "processing_time_ms": 225330,
  "model_version": "0.3.0",
  "expires_at": "2026-04-26T14:32:30Z"
}
```

### 4. **Cache Metadata Index** (`cache/metadata/cache_index.json`)

```json
{
  "last_updated": "2026-03-26T14:32:30Z",
  "cache_version": "0.3.0",
  "storage": {
    "total_size_mb": 245.3,
    "vision_features_mb": 150.2,
    "embeddings_mb": 45.1,
    "llm_responses_mb": 50.0
  },
  "statistics": {
    "total_images_cached": 32,
    "total_queries_cached": 156,
    "total_responses_cached": 412,
    "cache_hit_rate": 0.72,
    "avg_vision_extract_ms": 180000,
    "avg_cache_lookup_ms": 5,
    "time_saved_hours": 42.5
  },
  "expiration_schedule": {
    "vision_features": "never",
    "embeddings": "7 days",
    "llm_responses": "30 days"
  },
  "recent_items": [
    {
      "type": "vision",
      "key": "vision/abc123def456.json",
      "size_mb": 0.02,
      "cached_at": "2026-03-26T14:30:00Z",
      "last_accessed": "2026-03-26T14:32:00Z",
      "hit_count": 5
    },
    {
      "type": "embedding",
      "key": "embeddings/xyz789uvw456.json",
      "size_mb": 0.15,
      "cached_at": "2026-03-26T14:31:00Z",
      "last_accessed": "2026-03-26T14:31:50Z",
      "hit_count": 12
    },
    {
      "type": "llm_response",
      "key": "llm_responses/job_abc123xyz_result.json",
      "size_mb": 0.8,
      "cached_at": "2026-03-26T14:32:30Z",
      "last_accessed": "2026-03-26T14:32:35Z",
      "hit_count": 1
    }
  ]
}
```

### 5. **Job Queue Metadata** (`cache/metadata/job_queue.json`)

```json
{
  "active_jobs": [
    {
      "job_id": "job_active_1",
      "status": "processing",
      "image": "2020_ariana_ville_39236.png",
      "question": "What settlement patterns?",
      "mode": "rag_advanced",
      "created_at": "2026-03-26T14:35:00Z",
      "started_at": "2026-03-26T14:35:10Z",
      "current_stage": "vision_extraction",
      "progress": 65,
      "eta_seconds": 95
    },
    {
      "job_id": "job_active_2",
      "status": "queued",
      "image": "2021_ariana_ville_39236.png",
      "question": "Urban expansion?",
      "mode": "rag_baseline",
      "created_at": "2026-03-26T14:35:05Z",
      "start_time_estimate": "2026-03-26T14:36:35Z"
    }
  ],
  "completed_jobs": [
    {
      "job_id": "job_completed_1",
      "status": "completed",
      "image": "2019_ariana_ville_39236.png",
      "created_at": "2026-03-26T14:30:00Z",
      "completed_at": "2026-03-26T14:34:45Z",
      "total_time_ms": 285000,
      "result_file": "llm_responses/job_completed_1_result.json"
    }
  ],
  "queue_stats": {
    "total_queued": 47,
    "total_processing": 2,
    "total_completed_today": 156,
    "avg_processing_time_ms": 225000,
    "max_concurrent_jobs": 4
  }
}
```

### 6. **Spatial Index Metadata** (`data/shapefile_index.json`)

```json
{
  "shapefiles": [
    {
      "name": "tunisia_adm2",
      "file": "data/shapefiles/tunisia_adm2.shp",
      "description": "Tunisia administrative level 2 (GAUL 2015)",
      "features_count": 24,
      "indexed": true,
      "last_loaded": "2026-03-26T09:15:00Z",
      "properties": ["NAME_2", "GAUL_CODE", "SHAPE_AREA", "SHAPE_LEN"],
      "bounds": {
        "north": 37.35,
        "south": 30.25,
        "east": 11.55,
        "west": 8.7
      }
    },
    {
      "name": "landuse_zones",
      "file": "data/shapefiles/landuse_zones.shp",
      "description": "Land use zones and classifications",
      "features_count": 156,
      "indexed": true,
      "last_loaded": "2026-03-26T09:15:30Z",
      "properties": ["ZONE_TYPE", "ZONE_NAME", "PROTECTION_LEVEL"],
      "bounds": {
        "north": 37.35,
        "south": 30.25,
        "east": 11.55,
        "west": 8.7
      }
    }
  ],
  "spatial_index": "rtree",
  "crs": "EPSG:4326",
  "ready": true
}
```

---

## Async Processing Explained (Simple)

### Before (Synchronous - Blocking)

```
User clicks "Analyze"
  ↓
Server: "Okay, I'll wait..."
Server starts: extract_vision(image)  ← WAITS 3 MINUTES
Server blocked during this time (can't handle other users)
Server: "Vision done!"
Server: "Okay, I'll wait..."
Server starts: retrieve_knowledge(question)  ← WAITS 0.2 sec
Server: "Retrieval done!"
Server: "Okay, I'll wait..."
Server starts: generate_answer(...)  ← WAITS 1.5 sec
Server: "Answer ready!"
Server returns: {"answer": "..."}
Total time: 3 + 0.2 + 1.5 = 4.7 minutes
User stares at loading spinner 🔄🔄🔄
```

### After (Asynchronous - Non-Blocking)

```
User clicks "Analyze"
  ↓
Server: "Got it! Here's your job ID: abc123"
Server returns immediately: {"job_id": "abc123", "status": "queued"}
User gets response in < 100ms ✓
  ├─ User can close browser, check later
  ├─ User can upload more images
  └─ Server is free to help other users

Meanwhile (in background):
Background Task 1:
  extract_vision(image)  ← Runs WITHOUT BLOCKING
  (3 minutes pass, server still helping other users)
  Save to cache

Background Task 2 (starts after Task 1):
  retrieve_knowledge(question)  ← Runs WITHOUT BLOCKING
  (0.2 seconds)

Background Task 3 (starts after Task 2):
  generate_answer(...)  ← Runs WITHOUT BLOCKING
  (1.5 seconds)

Job completed, result stored

User polls: GET /api/status/abc123
Server responds immediately:
{
  "status": "completed",
  "answer": "Based on satellite analysis...",
  "timing": {...}
}
```

### Key Difference

**Synchronous (Old)**:

- 1 user = server uses 1 thread, blocked for 4.7 minutes
- 10 users = server needs 10 threads, uses 10x resources
- Scaling = throw more servers at it

**Asynchronous (New)**:

- 1 user = server uses 1 thread, but only for 0.1 seconds
- 10 users = server uses same thread for all (round-robin)
- Scaling = handle 10-100x users with same hardware

---

## Batch Analysis Explained

### Single Image (Current)

```
User: "Analyze this one image"
Server: "Processing..."
(4.7 minutes later)
Server: "Done"
```

### Batch (New) - 10 Images at Once

```
User: Uploads zip with 10 images + questions.json
Server: "Processing batch of 10 images"

Queue:
Job 1: ████░░░░  (65% - vision extraction almost done)
Job 2: ██░░░░░░░ (20% - waiting for vision to start)
Job 3: ░░░░░░░░░ (0% - queued)
Job 4: ░░░░░░░░░ (0% - queued)
...

With parallel processing (2 vision at a time):
Timeline:
T+0:00 - Job 1 starts vision (3 min)
T+0:05 - Job 2 starts vision (3 min)  [while Job 1 computing]
T+3:10 - Job 1 finishes vision, starts retrieval
T+3:15 - Job 3 starts vision
T+3:10 - Job 1 retrieval + LLM (1.7 min)
...

Total time for 10 images:
Sequential: 10 × 4.7 = 47 minutes
Batch (2 parallel): ~12-15 minutes ✓

User can:
- Poll for progress
- Get partial results as they complete
- Download results as CSV/JSON
```

---

## New File Structure

```
project-10/
├── cache/                           [NEW - persistent cache]
│   ├── vision/
│   │   ├── abc123def456.json       [Vision features cached once]
│   │   ├── xyz789uvw456.json
│   │   └── ...
│   ├── embeddings/
│   │   ├── query_hash_1.json       [Retrieval results]
│   │   └── ...
│   ├── llm_responses/
│   │   ├── job_abc123xyz_result.json
│   │   └── ...
│   └── metadata/
│       ├── cache_index.json        [Cache statistics]
│       └── job_queue.json          [Active/completed jobs]
│
├── data/                            [NEW - spatial data]
│   ├── shapefiles/
│   │   ├── tunisia_adm2.shp       [Administrative boundaries]
│   │   ├── tunisia_adm2.prj
│   │   ├── tunisia_adm2.dbf
│   │   └── ...
│   ├── shapefile_index.json        [Index for quick lookup]
│   └── spatial_metadata.json
│
├── config.py                        [UPDATED - cache + model settings]
├── main.py                          [UPDATED - add async routes]
├── ingest_knowledge.py              [UNCHANGED]
│
├── api/
│   ├── routes.py                   [UPDATED - add async, batch, status endpoints]
│   └── schemas.py                  [UPDATED - add job/batch schemas]
│
├── core/
│   ├── orchestrator.py             [UPDATED - async pipeline]
│   ├── cache_manager.py            [NEW - cache operations]
│   ├── spatial_enricher.py         [NEW - shapefile integration]
│   └── prompt_builder.py           [UNCHANGED]
│
├── services/
│   ├── vision_service.py           [UPDATED - smaller models]
│   ├── llm_service.py              [UPDATED - smaller models]
│   ├── rag_service.py              [UNCHANGED]
│   └── job_queue.py                [NEW - async job management]
│
├── workers/                         [NEW - background tasks]
│   ├── vision_extractor.py         [Extract vision in background]
│   ├── retriever.py                [Retrieve in background]
│   └── answer_generator.py         [Generate LLM answer in background]
│
└── utils/
    ├── shapefile_loader.py         [NEW - load/index shapefiles]
    ├── spatial_indexer.py          [NEW - rtree indexing]
    └── hash_utils.py               [NEW - image/query hashing]
```

---

## Model Switching Strategy

### Current (Too Slow)

```
Vision: qwen3-vl:235b-cloud  (takes 3+ min)
LLM:    gemma3:1b            (okay, 1-2 sec)
```

### Recommended (Fast with Cache)

```
Vision: llama2-vision:3b-cloud  (takes 30-45 sec)
        OR
        qwen2-vl:1.5b-cloud    (takes 25-35 sec)

LLM:    gemma2:3b-cloud        (1.5-2.5 sec, better quality)
        OR
        mistral:3b-cloud       (similar speed)
```

**With Caching**:

- Vision: Extract once (30s), use forever (cache hits ~70% of time)
- LLM: Generate once per question, reuse
- Effective speed: 2-3 seconds per request (after first image)

---

## Summary Table

| Aspect                  | Now (v0.2)              | New (v0.3)                         |
| ----------------------- | ----------------------- | ---------------------------------- |
| **Model**               | Qwen3-VL 235B (3 min)   | LLaVA 3B cloud (30s)               |
| **Processing**          | Sync (blocks)           | Async (non-blocking)               |
| **Concurrency**         | 1 (or multiple servers) | 10+ concurrent users               |
| **Caching**             | None                    | Vision + embeddings + responses    |
| **Spatial Context**     | None                    | Shapefile enrichment               |
| **Batch Analysis**      | No                      | Yes (10+ images parallel)          |
| **User Feedback**       | Waits 4+ min            | Gets job ID in 100ms, polls status |
| **Time to First Image** | 4+ min                  | 30s (then 2-3s for followup Qs)    |
| **Through put**         | 6 images/hour           | 30+ images/hour                    |

---

## Next Steps

1. **Set up cache directories** + JSON schemas ✓
2. **Download shapefiles** for Tunisia + create spatial index
3. **Update config.py** for smaller models + cache settings
4. **Implement cache_manager.py** (get/set/clear operations)
5. **Implement spatial_enricher.py** (shapefile lookups)
6. **Refactor routes.py** for async + job queue
7. **Implement job_queue.py** (persistent tracking)
8. **Create background workers** (vision, retrieval, LLM)
9. **Test with batch of 10 satellite images**

Ready to start?
