# Documentation Index

Complete reference for Geo-RAG Platform **v0.3.0** (async, caching, spatial enrichment).

## 🚀 Quick Links

| Document                                           | Purpose                                             |
| -------------------------------------------------- | --------------------------------------------------- |
| **[SETUP.md](./SETUP.md)**                         | Environment setup, installation, troubleshooting    |
| **[ARCHITECTURE_v0.3.md](./ARCHITECTURE_v0.3.md)** | **NEW:** Async/cache architecture (READ THIS FIRST) |
| **[API.md](./API.md)**                             | HTTP endpoints, request/response schemas, examples  |
| **[MODE_BENCHMARKING.md](./MODE_BENCHMARKING.md)** | Research framework for comparing three modes        |
| **[CHANGELOG.md](./CHANGELOG.md)**                 | Version history and changes                         |

---

## 📁 Project Structure

See directory README files for what each folder contains:

| Directory   | Purpose                                          | README                                    |
| ----------- | ------------------------------------------------ | ----------------------------------------- |
| `/app`      | Core application (FastAPI, routes, services)     | [app/README.md](../app/README.md)         |
| `/data`     | Knowledge docs, imagery, shapefiles              | [data/README.md](../data/README.md)       |
| `/scripts`  | One-off utilities (fetch, ingest, validate)      | [scripts/README.md](../scripts/README.md) |
| `/cache`    | Persistent cache (vision, embeddings, responses) | [cache/README.md](../cache/README.md)     |
| `/tests`    | Unit and integration tests                       | pytest files                              |
| `/frontend` | Web UI (HTML, JavaScript, CSS)                   | index.html                                |

---

## 🎯 For Your Role

### **I want to...** → **Read this**

- **Get started** → [SETUP.md](./SETUP.md) + [ARCHITECTURE_v0.3.md](./ARCHITECTURE_v0.3.md)
- **Use the API** → [API.md](./API.md)
- **Understand the design** → [ARCHITECTURE_v0.3.md](./ARCHITECTURE_v0.3.md)
- **Run benchmarks** → [MODE_BENCHMARKING.md](./MODE_BENCHMARKING.md)
- **See what changed** → [CHANGELOG.md](./CHANGELOG.md)
- **Deploy to production** → [SETUP.md](./SETUP.md) (Production section)

---

## 📋 v0.3 Key Changes

**From v0.2 to v0.3:**

1. **Async Processing**
   - Requests return immediately with job_id
   - Processing happens in background
   - User polls `/api/status/{job_id}` for progress
   - 10-100x more concurrent users supported

2. **Caching**
   - Vision features cached by image hash (compute once, reuse forever)
   - Embeddings cached by query hash (7-day expiry)
   - LLM responses cached by job_id (30-day expiry)
   - ~70% cache hit rate after first image
   - ~25x faster for repeated queries

3. **Spatial Enrichment (NEW)**
   - Load shapefiles at startup (Tunisia ADM2 boundaries)
   - Detect image location from metadata
   - Query shapefiles to find administrative region
   - Enrich RAG context with regional knowledge
   - Better document retrieval

4. **Focus Shift**
   - Now focusing on **Urban Sprawl** analysis only
   - (Removed: Informal settlement classification)

---

## 🏗️ Architecture Overview

See **[ARCHITECTURE_v0.3.md](./ARCHITECTURE_v0.3.md)** for complete design.

**Quick diagram:**

```
User Request → Job Queue → Background Processors (async)
                           ├─ Vision Extract (cache-aware)
                           ├─ Spatial Enrich (shapefile lookup)
                           ├─ Knowledge Retrieval (cached)
                           └─ LLM Answer (cached)
             → Results stored in cache → User polls for status
```

---

## 📚 Document Details

### ARCHITECTURE_v0.3.md (NEW - READ THIS!)

- System design for v0.3
- Async processing explained
- Batch analysis explained
- Caching strategy
- Spatial enrichment with shapefiles
- JSON file schemas
- New file structure

### SETUP.md

- Prerequisites and environment
- Installation steps
- Running locally
- Docker deployment
- Production setup (systemd, nginx)
- Troubleshooting

### API.md

- All HTTP endpoints
- Request/response schemas
- Status codes and error handling
- Client examples (Python, JavaScript, cURL)
- Performance benchmarks

### MODE_BENCHMARKING.md

- Three analysis modes explained
- Benchmarking workflow
- Evaluation metrics
- Research framework

---

## ⏭️ Next (Phase 1)

Currently executing reorganization and Phase 1:

- [ ] **Infrastructure Setup**
  - [ ] Create cache directories and JSON schemas
  - [ ] Download/parse shapefiles for Tunisia
  - [ ] Create spatial index (rtree)
  - [ ] Update config.py for caching

- [ ] **Implementation**
  - [ ] cache_manager.py — Cache operations
  - [ ] spatial_enricher.py — Shapefile lookups
  - [ ] job_queue.py — Track jobs

- [ ] **Testing**
  - [ ] Test with single image
  - [ ] Verify caching works
  - [ ] Benchmark performance improvement

---

**Last Updated**: April 9, 2026  
**Version**: 0.3.0-dev  
**Status**: Reorganization complete, Phase 1 starting
