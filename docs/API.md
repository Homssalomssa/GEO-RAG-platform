# API Reference

**Geo-RAG Platform v0.1.0-MVP**

Complete reference for all HTTP endpoints, request/response schemas, and error codes.

---

## Base URL

```
http://localhost:8000/api
```

Or if remote:
```
http://{host}:{port}/api
```

---

## Endpoints

### 1. Main Analysis Endpoint

Analyzes a satellite image with a question using one of three modes.

**Endpoint**: `POST /api/analyze`

**Request** (Multipart Form Data):

| Field | Type | Required | Constraints | Example |
|-------|------|----------|-------------|---------|
| `image` | File | ✅ | JPEG/PNG/TIFF/WebP, ≤10MB | satellite.png |
| `question` | Text | ✅ | 1-500 characters | "Is there urban expansion?" |
| `mode` | Text | ✅ | `llm_only` \| `rag_baseline` \| `rag_advanced` | "rag_baseline" |

**Response** (200 OK):

```json
{
  "mode": "rag_baseline",
  "vision_features": {
    "vegetation_density": "low, approximately 5-10% coverage",
    "building_density": "high, tightly packed structures",
    "road_density": "moderate, mix of paved and unpaved",
    "urban_pattern": "irregular, informal layout",
    "expansion_signs": "active construction visible, new structures emerging",
    "illegal_settlement_indicators": "makeshift structures, no grid layout"
  },
  "retrieved_context": [
    {
      "chunk": "Informal settlements often develop on marginal land...",
      "source": "settlement_patterns.txt",
      "score": 0.87
    },
    {
      "chunk": "Urban sprawl typically involves unplanned expansion...",
      "source": "urban_planning.txt",
      "score": 0.82
    }
  ],
  "gis_data": null,
  "answer": "Based on the satellite analysis and retrieved knowledge, this appears to be an informal settlement with active expansion. The irregular layout and informal structures suggest unplanned development...",
  "reasoning_trace": {
    "steps": [
      "1. Extracting visual features from satellite image using Qwen3-VL...",
      "   ✓ Extracted 6 features in 3500ms",
      "2. Built retrieval query: 'Is there urban expansion? urban pattern: irregular, informal layout expansion signs: active construction visible, new structures emerging'",
      "   ✓ Semantic search returned 5 chunks",
      "3. Built RAG baseline prompt (features + chunks + question)",
      "4. Generating answer with Gemma3 1B...",
      "   ✓ Generated 450 chars in 1200ms",
      "5. Total pipeline time: 4800ms"
    ],
    "timing": {
      "vision_ms": 3500,
      "retrieval_ms": 150,
      "gis_ms": 0,
      "llm_ms": 1200,
      "total_ms": 4800
    }
  }
}
```

**Error Responses**:

| Status | Condition | Example Response |
|--------|-----------|-------------------|
| 400 | Invalid image type | `{"detail": "Unsupported image type: image/gif. Supported: image/jpeg, image/png, image/tiff, image/webp"}` |
| 400 | Image too large | `{"detail": "Image too large: 15.2MB (max 10MB)"}` |
| 400 | Question empty | `{"detail": "Question cannot be empty"}` |
| 400 | Question too long | `{"detail": "Question too long (max 500 chars)"}` |
| 400 | Invalid mode | `{"detail": "Invalid mode: invalid_mode. Must be one of: llm_only, rag_baseline, rag_advanced"}` |
| 503 | Ollama unreachable | `{"detail": "Cannot connect to Ollama at http://localhost:11434"}` |
| 500 | Vision parsing failed | `{"detail": "Analysis failed: Could not parse vision output..."}` |
| 500 | LLM generation failed | `{"detail": "Analysis failed: LLM returned empty response after retry"}` |

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "image=@satellite.png" \
  -F "question=Is there evidence of illegal settlement?" \
  -F "mode=rag_baseline"
```

**Python Example**:

```python
import requests

with open("satellite.png", "rb") as f:
    files = {"image": f}
    data = {
        "question": "Is there evidence of illegal settlement?",
        "mode": "rag_baseline"
    }
    response = requests.post(
        "http://localhost:8000/api/analyze",
        files=files,
        data=data
    )

result = response.json()
print(result["answer"])
```

---

### 2. Vision-Only Endpoint (Debug)

Extract structured features from an image without RAG or LLM reasoning.

**Endpoint**: `POST /api/vision/extract`

**Request** (Multipart Form Data):

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `image` | File | ✅ | JPEG/PNG/TIFF/WebP, ≤10MB |

**Response** (200 OK):

```json
{
  "vegetation_density": "low, approximately 5-10% coverage",
  "building_density": "high, tightly packed structures",
  "road_density": "moderate, mix of paved and unpaved",
  "urban_pattern": "irregular, informal layout",
  "expansion_signs": "active construction visible, new structures emerging",
  "illegal_settlement_indicators": "makeshift structures, no grid layout"
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| 503 | Ollama unreachable |
| 500 | Vision parsing failed |

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/vision/extract \
  -F "image=@satellite.png"
```

---

### 3. RAG Query Endpoint (Debug)

Query the knowledge base directly without image or LLM reasoning.

**Endpoint**: `POST /api/rag/query`

**Request** (JSON):

```json
{
  "query": "What are indicators of informal settlements?",
  "top_k": 5
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `query` | String | ✅ | 1-500 characters |
| `top_k` | Integer | ❌ | 1-20 (default: 5) |

**Response** (200 OK):

```json
{
  "results": [
    {
      "chunk": "Informal settlements often lack basic infrastructure...",
      "source": "settlement_patterns.txt",
      "score": 0.91
    },
    {
      "chunk": "Unplanned urban areas exhibit irregular spatial patterns...",
      "source": "urban_planning.txt",
      "score": 0.85
    }
  ],
  "count": 2
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are indicators of informal settlements?", "top_k": 5}'
```

---

### 4. Document Ingestion Endpoint

Ingest new knowledge documents into the vector database.

**Endpoint**: `POST /api/rag/ingest`

**Request** (JSON):

```json
{
  "documents": [
    {
      "text": "Urban sprawl is the uncontrolled expansion of urban areas into surrounding areas...",
      "source": "my_document.txt"
    },
    {
      "text": "Satellite imagery enables detection of informal settlements through pattern analysis...",
      "source": "another_document.txt"
    }
  ]
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `documents` | Array | ✅ | List of {text, source} objects |
| `documents[].text` | String | ✅ | Document content (will be chunked) |
| `documents[].source` | String | ✅ | Source identifier (for attribution) |

**Response** (200 OK):

```json
{
  "status": "success",
  "chunks_ingested": 12
}
```

**Process**:
1. Text is split into 500-character chunks (100-char overlap)
2. Chunks are embedded using all-MiniLM-L6-v2
3. Embeddings stored in ChromaDB
4. BM25 index rebuilt
5. Returns total chunks ingested

**Error Responses**:

| Status | Condition |
|--------|-----------|
| 400 | No documents provided |
| 500 | ChromaDB write failed |

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "Urban planning principles guide sustainable development...",
        "source": "planning_guide.txt"
      }
    ]
  }'
```

**Python Example**:

```python
import requests

new_docs = [
    {
        "text": "Satellite imagery interpretation requires understanding...",
        "source": "interpretation_guide.txt"
    }
]

response = requests.post(
    "http://localhost:8000/api/rag/ingest",
    json={"documents": new_docs}
)

print(response.json())  # {"status": "success", "chunks_ingested": 5}
```

---

### 5. Health Check Endpoint

Check system health and model availability.

**Endpoint**: `GET /api/health`

**Request**: No parameters

**Response** (200 OK):

```json
{
  "status": "healthy",
  "ollama_connected": true,
  "chroma_connected": true,
  "vision_model": "qwen3-vl:235b-cloud",
  "llm_model": "gemma3:1b"
}
```

**Response** (200 OK, Degraded):

```json
{
  "status": "degraded",
  "ollama_connected": false,
  "chroma_connected": true,
  "vision_model": "qwen3-vl:235b-cloud",
  "llm_model": "gemma3:1b"
}
```

**Statuses**:

| Status | Condition |
|--------|-----------|
| `healthy` | Both Ollama and ChromaDB connected |
| `degraded` | One service unavailable |
| `offline` | All services unavailable |

**cURL Example**:

```bash
curl http://localhost:8000/api/health | jq
```

**Python Example**:

```python
import requests

response = requests.get("http://localhost:8000/api/health")
health = response.json()

if health["status"] == "healthy":
    print("System ready!")
else:
    print(f"System degraded: Ollama={health['ollama_connected']}, ChromaDB={health['chroma_connected']}")
```

---

## Analysis Modes Explained

### LLM-Only Mode

**Request**:
```json
{
  "image": <satellite_image>,
  "question": "Is there urban expansion?",
  "mode": "llm_only"
}
```

**Processing**:
1. Extract vision features from image
2. **Skip** knowledge base retrieval
3. Construct prompt with features + question
4. Generate answer using only vision

**Response Fields**:
- `vision_features`: ✅ Populated (6 fields)
- `retrieved_context`: ❌ Empty list
- `gis_data`: ❌ null
- `answer`: Generated answer without external knowledge
- `timing.retrieval_ms`: 0

**Use Case**: Baseline LLM reasoning without retrieval

---

### RAG Baseline Mode

**Request**:
```json
{
  "image": <satellite_image>,
  "question": "Is there urban expansion?",
  "mode": "rag_baseline"
}
```

**Processing**:
1. Extract vision features
2. Build retrieval query (question + relevant features)
3. **Semantic search only**: top-5 results
4. Construct prompt with features + chunks + question
5. Generate answer

**Response Fields**:
- `vision_features`: ✅ Populated
- `retrieved_context`: ✅ Populated (5 chunks with scores)
- `gis_data`: ❌ null
- `answer`: Generated answer grounded in vision + knowledge
- `timing.retrieval_ms`: ~150-300ms

**Use Case**: Test quality improvement from simple semantic retrieval

---

### RAG Advanced Mode

**Request**:
```json
{
  "image": <satellite_image>,
  "question": "Is there urban expansion?",
  "mode": "rag_advanced"
}
```

**Processing**:
1. Extract vision features
2. Build retrieval query
3. **Hybrid search**: semantic + keyword search, merged with RRF
4. **GIS enrichment**: rule-based metrics from features
5. Construct prompt with all context + question
6. Generate answer

**Response Fields**:
- `vision_features`: ✅ Populated
- `retrieved_context`: ✅ Populated (merged results, typically 5 chunks)
- `gis_data`: ✅ Populated (4 fields: building count, infrastructure, pattern, density)
- `answer`: Generated answer with confidence assessment
- `timing.retrieval_ms`: ~200-400ms (includes merge)
- `timing.gis_ms`: ~20-50ms

**Use Case**: Full pipeline with all context sources for best answer quality

---

## Request/Response Schemas

### VisionFeatures (JSON)

```json
{
  "vegetation_density": "string (low/medium/high + percentage)",
  "building_density": "string (description + density)",
  "road_density": "string (paved/unpaved + network description)",
  "urban_pattern": "string (grid/irregular/radial/sprawl)",
  "expansion_signs": "string (signs of new development)",
  "illegal_settlement_indicators": "string (informal settlement patterns)"
}
```

### RetrievedChunk (JSON)

```json
{
  "chunk": "string (text from knowledge base, ~100-500 chars)",
  "source": "string (filename of source document)",
  "score": "float (relevance score, 0.0-1.0)"
}
```

### GISData (JSON)

```json
{
  "estimated_building_count": "string (low/moderate/high + structure estimate)",
  "infrastructure_assessment": "string (issues identified)",
  "pattern_classification": "string (informal/planned/sprawl/mixed)",
  "density_metric": "string (structures per hectare)"
}
```

### ReasoningTrace (JSON)

```json
{
  "steps": [
    "string (step-by-step log)",
    "..."
  ],
  "timing": {
    "vision_ms": "integer (ms for feature extraction)",
    "retrieval_ms": "integer (ms for search)",
    "gis_ms": "integer (ms for GIS enrichment)",
    "llm_ms": "integer (ms for LLM generation)",
    "total_ms": "integer (total end-to-end)"
  }
}
```

### AnalyzeResponse (JSON)

```json
{
  "mode": "string (llm_only|rag_baseline|rag_advanced)",
  "vision_features": { VisionFeatures object },
  "retrieved_context": [ RetrievedChunk, ... ],
  "gis_data": { GISData object } or null,
  "answer": "string (generated answer)",
  "reasoning_trace": { ReasoningTrace object }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example Scenario |
|------|---------|-------------------|
| 200 | Success | Analysis completed successfully |
| 400 | Bad Request | Invalid image type, question empty |
| 503 | Service Unavailable | Ollama not running or model missing |
| 500 | Internal Server Error | Unexpected failure in pipeline |

### Error Response Format

All errors return JSON:

```json
{
  "detail": "string (human-readable error message)"
}
```

**Example**:
```json
{
  "detail": "Cannot connect to Ollama at http://localhost:11434"
}
```

### Retry Logic

**Client should retry with exponential backoff:**

```python
import time
import requests

def analyze_with_retry(image_path, question, mode, max_retries=3):
    for attempt in range(max_retries):
        try:
            with open(image_path, "rb") as f:
                response = requests.post(
                    "http://localhost:8000/api/analyze",
                    files={"image": f},
                    data={
                        "question": question,
                        "mode": mode
                    },
                    timeout=180  # 3 min for vision model
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Attempt {attempt+1} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

result = analyze_with_retry("satellite.png", "Is there urban expansion?", "rag_baseline")
```

---

## Rate Limiting

**Note**: No built-in rate limiting in MVP. For production:
- Implement via API gateway (nginx, Kong, etc.)
- Recommended: 1 request per 5 seconds per client
- Queue system for burst loads

---

## Authentication

**Note**: No authentication in MVP. For production:
- Add API key validation
- Implement JWT tokens
- Use OAuth2.0

Example with API key:

```python
headers = {
    "X-API-Key": "your-secret-key"
}
response = requests.post(
    "http://localhost:8000/api/analyze",
    files=files,
    data=data,
    headers=headers
)
```

---

## OpenAPI / Swagger UI

FastAPI automatically generates interactive API documentation:

```
http://localhost:8000/docs          # Swagger UI
http://localhost:8000/redoc         # ReDoc
http://localhost:8000/openapi.json  # OpenAPI schema
```

Access these URLs in your browser to explore and test endpoints interactively.

---

## SDK / Client Libraries

### Python Requests (Recommended)

```python
import requests

client = requests.Session()

# Analyze
response = client.post(
    "http://localhost:8000/api/analyze",
    files={"image": open("image.png", "rb")},
    data={"question": "Your question?", "mode": "rag_baseline"}
)
result = response.json()

# Health check
health = client.get("http://localhost:8000/api/health").json()
```

### JavaScript / Fetch

```javascript
// Analyze
const formData = new FormData();
formData.append('image', imageFile);
formData.append('question', 'Your question?');
formData.append('mode', 'rag_baseline');

const response = await fetch('http://localhost:8000/api/analyze', {
    method: 'POST',
    body: formData
});

const result = await response.json();
console.log(result.answer);
```

### cURL

See examples in each endpoint section above.

---

## Performance Benchmarks

**Estimated timings** (per request, Ollama running locally):

| Step | Duration | Notes |
|------|----------|-------|
| Vision extraction | 3000-4000ms | Qwen3-VL 235B is slow |
| Retrieval (semantic) | 100-200ms | ChromaDB similarity search |
| Retrieval (keyword) | 50-100ms | BM25 scoring |
| Retrieval (merge) | 20-50ms | RRF deduplication |
| GIS enrichment | 5-20ms | Rule-based, very fast |
| LLM generation | 1000-2000ms | Gemma3 1B token generation |
| **Total** | **4500-6500ms** | Vision-bound |

**Bottleneck**: Vision model. Consider smaller model or quantization for faster inference.

---

## Changelog for API

See `CHANGELOG.md` for version history and breaking changes.
