# API Query & Output Generation Flow

This document explains how queries are handled and outputs are generated in this project. It is designed for both human readers and code assistants to quickly understand the integration points and flow.

---

## Key Files & Their Roles

| File                             | Purpose                                                             |
| -------------------------------- | ------------------------------------------------------------------- |
| `app/main.py`                    | FastAPI entry point; creates app, enables CORS, mounts frontend     |
| `app/api/routes.py`              | HTTP endpoints: `/analyze`, `/status/{job_id}`, `/batch`, `/health` |
| `app/api/schemas.py`             | Pydantic models for request/response validation                     |
| `app/core/orchestrator.py`       | Main orchestration logic - coordinates all services                 |
| `app/core/prompt_builder.py`     | Constructs mode-specific prompts for LLM                            |
| `app/services/vision_service.py` | Vision extraction via Qwen3-VL (Ollama)                             |
| `app/services/rag_service.py`    | RAG retrieval: semantic + keyword search via ChromaDB & BM25        |
| `app/services/llm_service.py`    | LLM text generation via Gemma 3 (Ollama)                            |
| `app/services/job_queue.py`      | Persistent job tracking for async processing                        |
| `app/config.py`                  | Central configuration (models, paths, timeouts)                     |

---

## End-to-End Query Flow

```mermaid
graph TD
    A[Frontend: User Request] --> B[POST /api/analyze (routes.py)]
    B --> C[Job Created, orchestrator.analyze()]
    C --> D[vision_service.extract_features()]
    C --> E{Mode}
    E -- LLM-Only --> F[Prompt Builder: Vision + Question]
    E -- RAG Baseline --> G[rag_service.semantic_search()]
    E -- RAG Advanced --> H[rag_service.semantic_search() + keyword_search() + gis_query()]
    G --> I[Prompt Builder: Vision + Chunks + Question]
    H --> J[Prompt Builder: Vision + Chunks + GIS + Question]
    F & I & J --> K[llm_service.generate()]
    K --> L[Assemble AnalyzeResponse]
    L --> M[Return JSON to Frontend]
```

---

## Step-by-Step Function Call Mapping

1. **API Entry**
   - `routes.py:analyze_image_async()`
     - Validates input, creates job, returns job_id
2. **Orchestration**
   - `orchestrator.analyze()`
     - Coordinates all processing steps
3. **Vision Feature Extraction**
   - `vision_service.extract_features()`
     - Returns 6 structured features
4. **Retrieval (RAG modes only)**
   - `rag_service.semantic_search()` / `keyword_search()` / `gis_query()`
     - Retrieves relevant knowledge chunks and GIS data
5. **Prompt Building**
   - `prompt_builder.build_prompt_{mode}()`
     - Assembles prompt for LLM
6. **LLM Generation**
   - `llm_service.generate()`
     - Generates answer text
7. **Response Assembly**
   - Orchestrator assembles final response (features, context, answer, trace)
8. **Output**
   - JSON response returned to frontend

---

## Data Flow by Mode

| Mode         | Input            | Services Used                         | Retrieval          | Output                           |
| ------------ | ---------------- | ------------------------------------- | ------------------ | -------------------------------- |
| LLM-Only     | Image + Question | Vision + LLM                          | None               | Features → Answer                |
| RAG Baseline | Image + Question | Vision + Retrieval + LLM              | Semantic           | Features + Chunks → Answer       |
| RAG Advanced | Image + Question | Vision + Hybrid Retrieval + GIS + LLM | Semantic + Keyword | Features + Chunks + GIS → Answer |

---

## Timing & Trace

- Each response includes timing for each step and a reasoning trace for evaluation and debugging.

---

## Integration Tips

- To hook into the query/output pipeline, start at `app/api/routes.py` and trace through the orchestrator and service layers.
- For custom logic, extend or wrap the orchestrator or service modules as needed.

---

_For further details, see the referenced files and consult the architecture documentation._
