# Geo-RAG Platform - Quick Start & Troubleshooting

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd .
pip install -r requirements.txt
```

### 2. Start Ollama (in separate terminal)

```bash
# Ensure these models are pulled
ollama pull llava:7b
ollama pull gemma3:1b

# Start the server
ollama serve
# Ollama will be available at http://localhost:11434
```

### 3. Start Geo-RAG Platform

```bash
cd .
.venv312/Scripts/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the System

```bash
# In another terminal, from project root
python test_system.py
python test_api.py
```

### 5. Access the UI

- **Swagger Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/health

---

## Example API Usage

### Submit Image for Analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "image=@/path/to/image.jpg" \
  -F "question=What is the urban density here?" \
  -F "mode=rag_baseline"

# Response: { "job_id": "abc123", "status": "queued" }
```

### Poll for Results

```bash
curl http://localhost:8000/api/status/abc123

# Response:
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "result": "This area shows moderate urban density...",
  "processing_seconds": 7.5
}
```

### Check System Health

```bash
curl http://localhost:8000/api/health

# Response:
{
  "status": "healthy",
  "vision_ok": true,
  "llm_ok": true,
  "queue_stats": { "total_jobs": 5, "completed_jobs": 3 }
}
```

---

## Troubleshooting

### ❌ "Cannot connect to Ollama"

**Problem:** Vision or LLM service returns connection error

```
ERROR: Vision service unavailable: Connection refused
```

**Solution:**

1. Check Ollama is running: `curl http://localhost:11434/api/health`
2. If not running: `ollama serve` in separate terminal
3. Verify models are pulled: `ollama list`
4. Check firewall isn't blocking port 11434

### ❌ "Model not found"

**Problem:** Vision or LLM returns 404

```
ERROR: llava:7b not found on Ollama server
```

**Solution:**

```bash
# Pull missing models
ollama pull llava:7b
ollama pull gemma3:1b

# Verify
ollama list
# Should show both models
```

### ❌ "Job stuck in 'processing'"

**Problem:** Job doesn't move to 'completed' status

**Solution:**

1. Check workers are running:
   - Look for "Worker spawned" logs on startup
   - Verify no errors in console

2. Check job queue metadata file:

   ```bash
   ls -la cache/metadata/job_queue.json
   ```

3. Manually check job status:

   ```bash
   curl http://localhost:8000/api/status/{job_id}
   ```

4. If truly stuck, clear runtime queue/cache metadata:
   ```bash
   rm cache/metadata/job_queue.json
   # Restart server
   ```

### ❌ "Image too large error"

**Problem:** Upload fails with "Image too large: 15.2MB"

**Solution:**

- Default limit is 10MB (configurable in `app/config.py`)
- Either compress the image or increase limit:
  ```python
  # app/config.py
  MAX_IMAGE_SIZE_MB = 20  # Increase to 20MB
  ```

### ❌ "No module named ..."

**Problem:** Missing Python dependency

**Solution:**

```bash
pip install -r requirements.txt
# Or individual install
pip install fastapi uvicorn
```

### ❌ "Worker failed to start"

**Problem:** Console shows error when spawning workers

**Solution:**

1. Verify all imports work:

   ```bash
   python -c "from app.workers.vision_extractor import VisionExtractor"
   ```

2. Check queue metadata file permissions:

   ```bash
   ls -la cache/metadata/job_queue.json
   ```

3. Restart fresh:
   ```bash
   rm cache/metadata/job_queue.json
   .venv312/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### ❌ "Cache miss every time (slow responses)"

**Problem:** Cache hits aren't working, every request takes full time

**Solution:**

1. Verify caching is enabled:

   ```bash
   curl http://localhost:8000/api/cache/stats
   ```

2. Check cache storage location:

   ```bash
   ls -la cache/
   ```

3. Try clearing cache:

   ```bash
   curl -X POST http://localhost:8000/api/cache/clear
   ```

4. Re-run same query - should be instant second time

---

## Performance Diagnostics

### Check Queue Performance

```bash
curl http://localhost:8000/api/queue/stats
# Shows job counts and timing
```

### Monitor Real-time

```bash
# Watch queue metadata (Unix/Mac)
tail -f cache/metadata/job_queue.json

# Or check status polling
watch -n 1 'curl http://localhost:8000/api/status/job_id | jq .progress'
```

### Identify Slow Stage

Look at response trace:

```bash
curl http://localhost:8000/api/status/job_id | jq .trace.timing
# Output: { vision_ms: 2500, retrieval_ms: 1800, llm_ms: 4200 }
# Shows which stage is slow
```

---

## Development Tips

### Run Tests Without Server

```bash
python test_system.py    # Tests job queue + cache + prompts
python test_api.py       # Tests API routes
```

### Debug a Specific Job

```python
# In Python console
from app.services.job_queue import JobQueue
q = JobQueue()
job = q.get_job("job_id_here")
print(job)  # See full job state
```

### Enable Debug Logging

Edit `app/main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
)
```

### Simulate Worker Processing

```python
from app.workers.vision_extractor import VisionExtractor
v = VisionExtractor()
# Manually call process_job
await v.process_job("job_id")
```

---

## Database Management

### Backup Job Queue

```bash
cp cache/metadata/job_queue.json cache/metadata/job_queue.backup.json
```

### Clear Old Jobs

```python
from app.services.job_queue import JobQueue
q = JobQueue()
removed = q.cleanup_old_jobs(days=7)
print(f"Cleaned up {removed} jobs")
```

### Export Job Results

```python
from app.services.job_queue import JobQueue
q = JobQueue()
all_jobs = q.get_completed_jobs()
for job in all_jobs:
    print(f"{job['job_id']}: {job['result']['answer']}")
```

---

## Production Checklist

- [ ] Ollama running with GPU acceleration enabled
- [ ] Both models (`llava:7b`, `gemma3:1b`) pulled and tested
- [ ] API behind reverse proxy (nginx/Apache)
- [ ] CORS configured for frontend domain
- [ ] SSL/TLS enabled for `/api` endpoints
- [ ] Job queue database backed up regularly
- [ ] Cache TTL settings appropriate for usage
- [ ] Logging configured (rotation, persistence)
- [ ] Monitor job queue size (`cleanup_old_jobs` scheduled)
- [ ] Rate limiting enabled on `/analyze` endpoint
- [ ] Error alerting set up (Slack/PagerDuty)

---

## Common Questions

**Q: How long does analysis take?**
A: 6-10 seconds end-to-end (vision 2-3s, retrieval 1-2s, LLM 3-5s). Cached results are instant.

**Q: Can I run multiple analyses in parallel?**
A: Yes! Job queue is async. Default is 2 concurrent vision extractions. Increase in `VisionExtractor.max_concurrent`.

**Q: What's the difference between the three modes?**
A: llm_only (fast, vision only) < rag_baseline (medium, semantic search) < rag_advanced (slow, hybrid + GIS)

**Q: How much disk space do I need?**
A: ~100MB base + ~1MB per 10 cached images + job database grows slowly (~500KB per 1000 jobs)

**Q: Can I use this with cloud LLMs (ChatGPT, Gemini)?**
A: Yes, modify `llm_service.py` to call OpenAI/Google APIs instead of local Ollama.

---

## Getting Help

1. **Check logs:** Look for ERROR or WARNING messages in console
2. **Run tests:** `python test_system.py` and `python test_api.py`
3. **Health check:** `curl http://localhost:8000/api/health`
4. **Database state:** `python -c "from app.services.job_queue import JobQueue; JobQueue().get_stats()"`
