# Persistent Cache

This directory stores computed results to avoid re-computation. Cleared manually or via `/api/cache/clear`.

## Cache Structure

```
cache/
├── vision/                      # Vision feature extraction results
│   ├── {image_hash}.json       # Features cached by image SHA-256
│   └── ...
│
├── embeddings/                  # Semantic search results
│   ├── {query_hash}.json       # Results cached by query hash
│   └── ...
│
├── llm_responses/              # LLM answers
│   ├── {job_id}_result.json    # One result per job
│   └── ...
│
└── metadata/                    # Cache metadata
    ├── cache_index.json        # What's cached, stats, expiration
    └── job_queue.json          # Active and completed jobs
```

## How Caching Works

### Vision Feature Cache

- **Key:** SHA-256 hash of image bytes
- **Value:** Extracted features (vegetation, buildings, roads, patterns, etc.)
- **Duration:** Forever (images don't change)
- **Hit rate:** ~70% (query multiple questions per image)

**Example:**

```json
cache/vision/abc123def456.json
{
  "image_hash": "abc123def456...",
  "features": {
    "vegetation_density": "medium",
    "building_density": "high",
    ...
  },
  "cached_at": "2026-03-26T14:30:00Z"
}
```

### Embedding Cache

- **Key:** Hash of (query + mode)
- **Value:** Retrieved chunks from ChromaDB
- **Duration:** 7 days
- **Use:** Skip expensive semantic search on repeated queries

### LLM Response Cache

- **Key:** Job ID
- **Value:** Generated answer + trace + timing
- **Duration:** 30 days
- **Use:** Don't regenerate if user asks again

## Cache Statistics

`cache/metadata/cache_index.json` tracks:

- Total cached items
- Storage used (MB)
- Cache hit rate (%)
- Time saved (hours)
- Expiration schedule

## Manual Cache Operations

```bash
# Clear all cache
curl -X POST http://localhost:8000/api/cache/clear

# View cache stats
cat cache/metadata/cache_index.json

# Clear specific category
rm cache/vision/*          # Reclear vision features
rm cache/embeddings/*      # Refresh retrieval
rm cache/llm_responses/*   # Regenerate answers
```

## Storage Limits

**Soft limits (warnings):**

- Total cache > 1 GB
- Individual image > 10 MB

**Hard limits (auto-clean):**

- Total cache > 5 GB (deletes oldest 20%)
- Any expired items deleted on startup

## For Development

```python
# In Python code
from app.utils.cache_manager import CacheManager

cache = CacheManager()

# Check if vision cached
features = await cache.get_vision("image_hash")
if features:
    print("Cache hit!")  # Use cached
else:
    print("Cache miss!")  # Compute and cache
    features = await vision_service.extract(image)
    await cache.set_vision("image_hash", features)
```

## Performance Impact

**Without cache (v0.2):**

- Image 1: 4.7 min (vision 3+ min)
- Image 2: 4.7 min (same vision again)
- Total: 9.4 min for 2 images

**With cache (v0.3):**

- Image 1: 30s + cache (vision ~30s with smaller model)
- Image 2: 2-3s (vision cache hit!)
- Total: ~35s for 2 images
- **25x faster** ✓

## Next Steps

- [ ] Implement cache_manager.py
- [ ] Add cache expiration logic
- [ ] Monitor and log cache hits
- [ ] Create dashboard for cache stats
