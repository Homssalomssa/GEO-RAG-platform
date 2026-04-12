# Geo-RAG System Architecture

**Version**: 0.1.0-MVP
**Last Updated**: March 25, 2026
**Purpose**: Satellite imagery analysis with Retrieval-Augmented Generation (RAG) for urban planning insights

---

## System Overview

Geo-RAG is a multimodal knowledge system that combines:
- **Vision Analysis**: Structured feature extraction from satellite imagery
- **Knowledge Retrieval**: Domain knowledge via vector + keyword search
- **LLM Reasoning**: Evidence-based answers with full traceability

The system is designed to **benchmark three distinct analysis modes** for research evaluation of information utilization.

```
User Input (image + question)
    ↓
[Vision Pipeline] → Extract 6 structured image features
    ↓
[Multi-Mode Analysis]
    ├─ LLM-Only: Vision features → LLM
    ├─ RAG Baseline: Vision features + semantic search → LLM
    └─ RAG Advanced: Vision + hybrid search + GIS enrichment → LLM
    ↓
[Output] → Answer + full reasoning trace + timing breakdown
```

---

## Component Architecture

### 1. Frontend Layer (`/frontend`)

**Files**:
- `index.html` - UI structure with image upload, mode selector, results panels
- `app.js` - Client-side logic for image handling, API calls, result rendering
- `style.css` - Styling and responsive layout

**Key Features**:
- Drag-and-drop image upload with preview
- Mode selection buttons (LLM-only, RAG baseline, RAG advanced)
- Comparison toggle to run all 3 modes sequentially
- Collapsible result sections for features, chunks, GIS data, trace
- Health check polling every 30s

**API Calls**:
- `POST /api/analyze` - Main analysis endpoint
- `GET /api/health` - Service health status

### 2. API Layer (`/api`)

**Files**:
- `routes.py` - HTTP request handlers (Flask-like routing)
- `schemas.py` - Pydantic models for request/response validation

**Endpoints**:

| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/api/analyze` | POST | Main analysis pipeline | image + question + mode | AnalyzeResponse |
| `/api/vision/extract` | POST | Vision-only debug | image | VisionFeatures |
| `/api/rag/query` | POST | RAG retrieval test | query + top_k | {results: [], count: int} |
| `/api/rag/ingest` | POST | Ingest documents | {documents: [{text, source}]} | {status, chunks_ingested} |
| `/api/health` | GET | Service health | - | HealthResponse |

**Schemas**:

```python
# Request
AnalyzeRequest: image_base64, question, mode (AnalysisMode enum)

# Response
AnalyzeResponse:
  - mode: AnalysisMode
  - vision_features: VisionFeatures (6 fields)
  - retrieved_context: list[RetrievedChunk]
  - gis_data: GISData (advanced mode only)
  - answer: str
  - reasoning_trace: ReasoningTrace (steps + timing)
```

**Validation**:
- Image type: JPEG, PNG, TIFF, WebP only
- Image size: max 10MB
- Question: 1-500 characters
- Mode: enum {llm_only, rag_baseline, rag_advanced}

---

### 3. Core Orchestration (`/core`)

**File**: `orchestrator.py`

**Function**: `analyze(image_base64, question, mode) → AnalyzeResponse`

**Workflow**:

```
1. Vision Extraction (ALL modes)
   └─ Call vision_service.extract_features(image_base64)
   └─ Returns 6 fields: vegetation_density, building_density, road_density,
                        urban_pattern, expansion_signs, illegal_settlement_indicators

2. Retrieval (mode-dependent)

   If LLM_ONLY:
   └─ Skip retrieval

   If RAG_BASELINE:
   └─ Build retrieval_query using question + relevant features
   └─ Call rag_service.semantic_search(retrieval_query)
   └─ Top-k semantic results only

   If RAG_ADVANCED:
   └─ Build retrieval_query
   └─ Call semantic_search() + keyword_search()
   └─ Merge with Reciprocal Rank Fusion (RRF)
   └─ Call rag_service.gis_query(features) for enrichment

3. Prompt Construction (mode-specific)
   └─ Format vision features, retrieved chunks, GIS data
   └─ Call appropriate prompt builder

4. LLM Generation
   └─ Call llm_service.generate(prompt)
   └─ Returns answer string

5. Response Assembly
   └─ Collect all outputs into AnalyzeResponse
   └─ Include reasoning trace with step-by-step log + timing
```

**Timing Structure**:
```python
TimingInfo:
  - vision_ms: Time for feature extraction
  - retrieval_ms: Time for search (0 if LLM-only)
  - gis_ms: Time for GIS enrichment (0 if not advanced)
  - llm_ms: Time for LLM generation
  - total_ms: End-to-end pipeline time
```

---

### 4. Vision Service (`/services/vision_service.py`)

**Models**: Qwen3-VL 235B Cloud (via Ollama)

**Function**: `extract_features(image_base64) → dict`

**Feature Extraction**:
```json
{
  "vegetation_density": "low/medium/high with % estimate",
  "building_density": "density and arrangement description",
  "road_density": "paved/unpaved + network density",
  "urban_pattern": "grid/irregular/radial/sprawl",
  "expansion_signs": "signs of new development",
  "illegal_settlement_indicators": "informal structure patterns"
}
```

**Extraction Process**:
1. Send base64 image + JSON extraction prompt to Ollama
2. Attempt JSON parsing → return parsed dict
3. If JSON fails → fallback regex extraction from raw text
4. Validate all 6 keys present; fill missing with "extraction failed"

**Error Handling**:
- If Ollama unreachable → raise ConnectionError
- If JSON unparseable → attempt regex extraction
- If both fail → raise ValueError

---

### 5. RAG Service (`/services/rag_service.py`)

**Storage**: ChromaDB (persistent at `./chroma_db`)

#### 5.1 Document Ingestion

**Function**: `ingest_documents(documents) → int`

```python
# Input format
documents = [
  {"text": "...", "source": "filename.txt"},
  ...
]
```

**Process**:
1. **Chunking**: Split text into 500-char chunks with 100-char overlap
   - Attempts to break at sentence boundaries (. or \n)
   - Filters out chunks < 50 chars
2. **Embedding**: Encode chunks using sentence-transformers (all-MiniLM-L6-v2)
3. **Storage**: Add to ChromaDB with metadata
   ```python
   {
     "id": "doc_{N}_{i}",
     "document": chunk_text,
     "embedding": embedding_vector,
     "metadata": {"source": filename, "chunk_index": i}
   }
   ```
4. **BM25 Index**: Rebuild full BM25 index from all ChromaDB documents
5. **Return**: Total number of chunks ingested

#### 5.2 Retrieval Strategies

**Semantic Search**:
- Encode query using same embedding model
- ChromaDB cosine similarity search (top-k results)
- Returns: list of {chunk, source, score}

**Keyword Search (BM25)**:
- Tokenize query (lowercase, split on whitespace)
- BM25 scoring against all indexed chunks
- Returns: top-k scored results

**Hybrid (RRF Merge)**:
- Run both semantic and keyword search
- Reciprocal Rank Fusion formula:
  ```
  RRF_score(doc) = Σ [1 / (k + rank)] for each ranking list
  where k = 60 (configurable, CHROMA_K constant)
  ```
- Deduplication by chunk text (first 100 chars used as key)
- Return: merged, resorted, deduplicated top-k

#### 5.3 Retrieval Query Building

**Source**: `core/prompt_builder.py::build_retrieval_query()`

**Logic**:
1. Check if question contains topic keywords (expand, growth, sprawl, illegal, etc.)
2. Map topics to relevant vision features
3. If no match → use all 6 features as fallback
4. Concatenate question + relevant feature values
5. Return enriched query

**Example**:
```
Input Q: "Is there illegal settlement?"
Features: illegal_settlement_indicators="irregular layout detected"
Output Q: "Is there illegal settlement? illegal settlement indicators: irregular layout detected"
```

#### 5.4 GIS Enrichment (Rule-Based)

**Function**: `gis_query(features) → dict`

**Output Fields**:
```python
{
  "estimated_building_count": "low/moderate/high with structure count estimate",
  "infrastructure_assessment": "issues identified (unpaved roads, no grid, sparse vegetation)",
  "pattern_classification": "informal/planned grid/sprawl/mixed",
  "density_metric": "structures per hectare estimate"
}
```

**Rules**:
- High building density + unpaved roads + irregular pattern → informal settlement
- Regular spacing + paved grid + tree lines → planned urban
- Sparse + low density → rural or undeveloped

**Note**: GIS enrichment is rule-based pattern matching, not actual geospatial queries. Future version could integrate real GIS databases (OpenStreetMap, etc.).

---

### 6. LLM Service (`/services/llm_service.py`)

**Models**: Gemma3 1B (via Ollama)

**Function**: `generate(prompt, temperature, max_tokens) → str`

**Process**:
1. Send prompt to Ollama `/api/generate` endpoint
2. If response empty → retry once
3. If second attempt empty → raise RuntimeError
4. Return generated text

**Configuration**:
- Temperature: 0.3 (low for analytical consistency)
- Max tokens: 1024
- Timeout: 120 seconds (vision models slow)

**Error Handling**:
- If Ollama unreachable → ConnectionError
- If HTTP error → ConnectionError
- If response empty → retry, then RuntimeError

---

### 7. Prompt Builder (`/core/prompt_builder.py`)

**Three Mode-Specific Prompts**:

#### LLM-Only
```
Input: Vision features + question
Output: Answer based ONLY on features, no external knowledge
Structure: Direct answer, supporting evidence, limitations
```

#### RAG Baseline
```
Input: Vision features + semantic-retrieved chunks + question
Output: Answer grounded in both features and knowledge
Structure: Direct answer, feature evidence, knowledge sources (cite by [1], [2]),
           distinction between observed vs. knowledge-based
```

#### RAG Advanced
```
Input: Vision features + hybrid-retrieved chunks + GIS data + question
Output: Comprehensive answer with multi-source grounding
Structure: Direct answer, feature evidence, knowledge sources, GIS metrics,
           confidence assessment (low/medium/high)
```

**Formatting Helpers**:
- `format_features()` - Vision features as readable block
- `format_chunks()` - Retrieved chunks with metadata
- `format_gis()` - GIS enrichment data

---

## Data Flow (End-to-End)

```
Frontend
  ├─ User uploads image (JPEG/PNG/TIFF/WebP)
  ├─ User types question (≤500 chars)
  ├─ User selects mode (LLM-only / RAG baseline / RAG advanced)
  └─ Optionally: check "Run comparison" to execute all 3 modes

API Layer (/api/analyze)
  ├─ Validate: image type, size, question length, mode enum
  ├─ Convert image to base64
  └─ Call core.orchestrator.analyze()

Orchestrator
  ├─ [Vision] Extract image features
  ├─ [Retrieval - mode dependent]
  │   ├─ Build retrieval query (question + relevant features)
  │   ├─ LLM-Only: skip
  │   ├─ RAG Baseline: semantic search
  │   └─ RAG Advanced: semantic + keyword + RRF merge + GIS
  ├─ [Prompt] Format prompt (mode-specific template)
  ├─ [LLM] Generate answer
  └─ Return AnalyzeResponse with trace

Frontend
  ├─ Display answer
  ├─ Show vision features (collapsible)
  ├─ Show retrieved chunks with scores (collapsible)
  ├─ Show GIS data (advanced mode only)
  ├─ Show reasoning trace with timing breakdown
  └─ If comparison: show side-by-side results from all 3 modes
```

---

## Knowledge Base

**Location**: `./knowledge/` (source files) + `./chroma_db/` (ChromaDB persistent storage)

**Current Knowledge Files**:
- `tunisia_adm2_*.txt` - Administrative division descriptions (5 files, ~900 bytes each)
- `urban_planning.txt` - Urban planning domain knowledge
- `settlement_patterns.txt` - Settlement pattern classifications
- `land_use_definitions.txt` - Land use definitions

**Key Issue**: Knowledge base is small and domain-specific to Tunisia. For production use, ingest additional:
- OpenStreetMap extracts
- Remote sensing literature
- Urban development case studies
- Satellite imagery interpretive guides

**Ingestion Workflow**:
```
python ingest_knowledge.py --glob "*.txt"
  ↓
Reads all matching files from /knowledge/
  ↓
For each file:
  - Chunking (500-char, 100-char overlap)
  - Embedding (all-MiniLM-L6-v2)
  - Store in ChromaDB
  ↓
Rebuild BM25 index from all chunks
  ↓
Print: "OK Successfully ingested N chunks into ChromaDB"
```

---

## Three Analysis Modes (Research Benchmarking)

The three modes enable **comparative evaluation** of information utilization:

### Mode 1: LLM-Only
- **Purpose**: Baseline — LLM reasoning without retrieval
- **Input**: Image features (vision model output)
- **Processing**: Generate answer based ONLY on vision
- **Metric**: Answer quality without external knowledge
- **Research Q**: "How much does the LLM reason purely from visual input?"

### Mode 2: RAG Baseline
- **Purpose**: Simple retrieval — semantic search only
- **Input**: Image features + top-5 semantic neighbors
- **Processing**: Semantic search (no keyword, no ranking)
- **Metric**: Answer quality with basic semantic retrieval
- **Research Q**: "Does semantic search alone improve answer quality?"

### Mode 3: RAG Advanced
- **Purpose**: Full retrieval pipeline with enrichment
- **Input**: Image features + hybrid search (semantic + keyword) + GIS enrichment
- **Processing**: RRF ranking + rule-based GIS metrics
- **Metric**: Answer quality with full context
- **Research Q**: "Do hybrid retrieval + GIS enrichment outperform simple retrieval?"

**Benchmarking Output**:
```json
{
  "mode": "rag_advanced",
  "timing": {
    "vision_ms": 3500,
    "retrieval_ms": 250,
    "gis_ms": 50,
    "llm_ms": 1200,
    "total_ms": 5000
  },
  "retrieved_context": [
    {"chunk": "...", "source": "...", "score": 0.92},
    ...
  ],
  "answer": "Based on visual features and domain knowledge, ...",
  "reasoning_trace": [
    "1. Extracting visual features...",
    "2. Built retrieval query: '...'",
    "3. Hybrid retrieval: 5 semantic + 3 keyword → 5 merged",
    "4. GIS enrichment: informal/unplanned settlement pattern",
    "5. Generating answer with Gemma3 1B...",
    "5. Total pipeline time: 5000ms"
  ]
}
```

---

## Configuration

**File**: `config.py`

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| OLLAMA_BASE_URL | str | http://localhost:11434 | Ollama API endpoint |
| VISION_MODEL | str | qwen3-vl:235b-cloud | Vision model name |
| LLM_MODEL | str | gemma3:1b | Reasoning model name |
| LLM_TEMPERATURE | float | 0.3 | LLM sampling temperature |
| LLM_MAX_TOKENS | int | 1024 | Max tokens per generation |
| OLLAMA_TIMEOUT | int | 120 | Request timeout (seconds) |
| CHROMA_PERSIST_DIR | str | ./chroma_db | ChromaDB storage path |
| CHROMA_COLLECTION_NAME | str | geo_knowledge | Collection name |
| EMBEDDING_MODEL | str | all-MiniLM-L6-v2 | Embedding model |
| SEMANTIC_TOP_K | int | 5 | Semantic search results |
| KEYWORD_TOP_K | int | 3 | Keyword search results |
| RRF_K | int | 60 | RRF constant for ranking |
| MAX_IMAGE_SIZE_MB | int | 10 | Max upload size |
| SUPPORTED_IMAGE_TYPES | list | [jpeg, png, tiff, webp] | Allowed image types |

**Override via Environment**:
```bash
export VISION_MODEL="qwen3-vl:235b-cloud"
export LLM_MODEL="gemma3:1b"
export OLLAMA_BASE_URL="http://remote-host:11434"
python main.py
```

---

## Error Handling

| Layer | Failure | Recovery | User Impact |
|-------|---------|----------|------------|
| API Input | Invalid image type | 400 Bad Request | Clear error message |
| API Input | Image too large | 400 Bad Request | "Max 10MB" message |
| API Input | Question empty | 400 Bad Request | "Question required" message |
| Vision | Ollama down | 503 Service Unavailable | "Vision service offline" |
| Vision | JSON parse fails | Fallback regex extraction | Partial features extracted |
| Vision | All extraction fails | Use defaults ("not detected") | Pipeline continues |
| Retrieval | ChromaDB query fails | Return empty list | LLM answers without context |
| LLM | Ollama model missing | 503 Service Unavailable | "Model not available" |
| LLM | Generation timeout | ConnectionError (120s) | "LLM timeout" |
| LLM | Empty response | Retry once, then error | "LLM failed" |

---

## Testing

**Unit Tests**: `/tests/`
- `test_rag.py` - Chunking, RRF, GIS query logic
- `test_vision.py` - Vision feature extraction (requires Ollama)
- `test_orchestrator.py` - Orchestration logic

**Run Tests**:
```bash
pytest tests/ -v
```

**Current Gaps**:
- No integration tests (full end-to-end pipeline)
- No test images (only unit test logic)
- No mock Ollama server

---

## Future Enhancements

1. **Real GIS Integration**
   - Replace rule-based GIS query with actual OSM database queries
   - Add elevation, slope, hydrology data

2. **Multimodal Features**
   - OCR for text in satellite images
   - Temporal analysis (multi-date imagery comparison)
   - Spectral indices (NDVI, NDBI, NDWI)

3. **Knowledge Base Expansion**
   - Ingest satellite interpretation literature
   - Add real estate / land registry data
   - Integrate official administrative boundaries

4. **Performance Optimization**
   - Cache embeddings for known queries
   - Persist BM25 index to disk
   - Batch image analysis

5. **Evaluation & Benchmarking**
   - Formal evaluation metrics (BLEU, ROUGE, token F1)
   - Human evaluation framework
   - Comparison with other RAG systems

---

## Deployment

**Prerequisites**:
- Python 3.11+
- Ollama (installed and running with qwen3-vl and gemma3 models)
- ~4GB RAM (embeddings + ChromaDB)
- ~2GB for model cache

**Quick Start**:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ingest knowledge base
python ingest_knowledge.py --glob "*.txt"

# 3. Start backend
python main.py  # FastAPI on 0.0.0.0:8000

# 4. Open frontend
# http://localhost:8000
```

See `SETUP.md` for detailed deployment instructions including Docker.

---

## Code Organization

```
project-10/
├── main.py                      # FastAPI app entry point
├── config.py                    # Centralized configuration
├── requirements.txt             # Python dependencies
├── ingest_knowledge.py          # Knowledge base ingestion script
│
├── api/                         # HTTP routes & schemas
│   ├── routes.py               # FastAPI route handlers
│   └── schemas.py              # Pydantic request/response models
│
├── core/                        # Business logic orchestration
│   ├── orchestrator.py         # Main analysis pipeline
│   └── prompt_builder.py       # Mode-specific prompt templates
│
├── services/                    # Integration with external systems
│   ├── vision_service.py        # Ollama vision model
│   ├── llm_service.py           # Ollama LLM generation
│   └── rag_service.py           # ChromaDB + BM25 retrieval
│
├── frontend/                    # User interface
│   ├── index.html              # HTML structure
│   ├── app.js                   # Client-side logic
│   └── style.css               # Styling
│
├── knowledge/                   # Domain knowledge source files
│   ├── *.txt                    # Knowledge documents (ingested at startup)
│   └── ...
│
├── chroma_db/                   # ChromaDB persistence (auto-created)
│   └── ...
│
├── tests/                       # Unit tests
│   ├── test_rag.py             # RAG service tests
│   ├── test_vision.py          # Vision service tests
│   └── test_orchestrator.py    # Orchestration tests
│
├── ARCHITECTURE.md             # This file
├── SETUP.md                    # Deployment + environment setup
├── API.md                      # API endpoint reference
├── MODE_BENCHMARKING.md        # Research mode documentation
└── CHANGELOG.md                # Version history & changes
```

---

## References

- **ChromaDB**: https://docs.trychroma.com
- **Sentence-Transformers**: https://www.sbert.net
- **BM25**: https://en.wikipedia.org/wiki/Okapi_BM25
- **Reciprocal Rank Fusion**: https://plg.uwaterloo.ca/~gvcormac/rrf.html
- **Ollama**: https://ollama.ai
- **FastAPI**: https://fastapi.tiangolo.com
