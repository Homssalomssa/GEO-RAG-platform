# Setup & Deployment Guide

**Geo-RAG Platform v0.1.0-MVP**

This guide covers local development setup, Ollama configuration, and deployment options.

---

## Prerequisites

- **OS**: Linux, macOS, or Windows (with WSL2)
- **Python**: 3.11 or higher
- **RAM**: 8GB+ (4GB for models, 4GB for runtime)
- **Disk**: 20GB+ (for model cache)
- **Ollama**: Running locally or on a remote host

---

## Quick Start (Local Development)

### Step 1: Install Python Dependencies

```bash
# Clone or navigate to project directory
cd /d/CAPSTONE/project\ 10

# Create virtual environment
python -m venv venv

# Activate
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Setup Ollama

**Option A: Local Ollama Installation**

```bash
# Download and install Ollama from https://ollama.ai
# On Linux:
curl https://ollama.ai/install.sh | sh

# Start Ollama daemon
ollama serve &

# In another terminal, pull required models:
ollama pull qwen3-vl:235b-cloud
ollama pull gemma3:1b

# Verify models are available
curl http://localhost:11434/api/tags | jq '.models[].name'
```

**Option B: Remote Ollama Service**

If Ollama is running on a different host:

```bash
# Create .env file with remote URL
echo "OLLAMA_BASE_URL=http://remote-host:11434" > .env

# Verify connectivity
curl http://remote-host:11434/api/tags
```

### Step 3: Initialize Knowledge Base

```bash
# Ingest knowledge documents into ChromaDB
python ingest_knowledge.py --glob "*.txt"

# Expected output:
# Reading: urban_planning.txt
# Reading: settlement_patterns.txt
# Reading: land_use_definitions.txt
# Reading: tunisia_adm2_39236_ariana_ville.txt
# ...
# Ingesting 5 documents...
# OK Successfully ingested 47 chunks into ChromaDB
```

**Verify ingestion**:
```bash
python -c "from services.rag_service import _get_collection; print(f'ChromaDB contains {_get_collection().count()} chunks')"
```

### Step 4: Start Backend Server

```bash
python main.py

# Expected output:
# 11:42:35 | INFO    | uvicorn | Uvicorn running on http://0.0.0.0:8000
# 11:42:35 | INFO    | uvicorn | Press CTRL+C to quit
```

### Step 5: Test Health Check

```bash
# In another terminal
curl http://localhost:8000/api/health | jq

# Expected response:
# {
#   "status": "healthy",
#   "ollama_connected": true,
#   "chroma_connected": true,
#   "vision_model": "qwen3-vl:235b-cloud",
#   "llm_model": "gemma3:1b"
# }
```

### Step 6: Open Frontend

Navigate to: **http://localhost:8000**

You should see the Geo-RAG interface. Upload a satellite image and ask a question!

---

## Environment Configuration

### Create `.env` File

```bash
# Optional: create .env for custom configuration
# (defaults in config.py already work)
cat > .env << EOF
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
VISION_MODEL=qwen3-vl:235b-cloud
LLM_MODEL=gemma3:1b

# RAG Configuration
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=geo_knowledge

# Image Upload
MAX_IMAGE_SIZE_MB=10
EOF
```

### Configuration Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `OLLAMA_BASE_URL` | URL | http://localhost:11434 | Ollama API endpoint |
| `VISION_MODEL` | str | qwen3-vl:235b-cloud | Must match available models in Ollama |
| `LLM_MODEL` | str | gemma3:1b | Must match available models in Ollama |
| `CHROMA_PERSIST_DIR` | path | ./chroma_db | ChromaDB storage (auto-created) |
| `CHROMA_COLLECTION_NAME` | str | geo_knowledge | Collection name in ChromaDB |
| `MAX_IMAGE_SIZE_MB` | int | 10 | Max permitted image size |

---

## Troubleshooting

### Error: "Cannot connect to Ollama at http://localhost:11434"

**Cause**: Ollama is not running or unreachable

**Solution**:
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# If it fails, start Ollama
ollama serve &

# If remote, verify URL is correct
export OLLAMA_BASE_URL=http://your-host:11434
curl $OLLAMA_BASE_URL/api/tags
```

### Error: "Model 'qwen3-vl:235b-cloud' not found"

**Cause**: Vision model not pulled in Ollama

**Solution**:
```bash
ollama pull qwen3-vl:235b-cloud
ollama pull gemma3:1b

# Verify
ollama list
```

### Error: "ChromaDB is empty, returning no results"

**Cause**: Knowledge base not ingested

**Solution**:
```bash
python ingest_knowledge.py --glob "*.txt"

# Verify it worked
python -c "from services.rag_service import _get_collection; print(_get_collection().count())"
```

### Error: "Vision parsing partial failure"

**Cause**: Vision model returned unparseable output

**Solution**:
- Check Ollama logs: `ollama serve` output
- Try a different satellite image
- Ensure image is valid (not corrupt)
- Lower LLM temperature if needed: edit `config.py`

### Error: "LLM returned empty response after retry"

**Cause**: Gemma3 model not generating text

**Solution**:
```bash
# Test Ollama LLM directly
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma3:1b", "prompt": "Hello", "stream": false}'

# If empty response, try re-pulling model
ollama pull gemma3:1b
```

### Error: "420 Unknown or loading model"

**Cause**: Ollama is still loading the model into memory

**Solution**:
- Wait 30-60 seconds for model to load
- Check Ollama logs
- Restart Ollama if necessary

---

## Running Tests

### Prerequisites

```bash
pip install pytest pytest-asyncio
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
# RAG service tests
pytest tests/test_rag.py -v

# Individual test
pytest tests/test_rag.py::TestChunking::test_long_text_multiple_chunks -v
```

### Expected Output

```
tests/test_rag.py::TestChunking::test_short_text_single_chunk PASSED
tests/test_rag.py::TestChunking::test_long_text_multiple_chunks PASSED
tests/test_rag.py::TestMergeAndRerank::test_merge_deduplicates PASSED
...
======================== 8 passed in 0.45s ========================
```

---

## Docker Deployment (Optional)

### Build Docker Image

```bash
# Create Dockerfile (if not present)
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run
CMD ["python", "main.py"]
EOF

# Build
docker build -t geo-rag:latest .
```

### Run Docker Container

```bash
# Option 1: Ollama on host network
docker run \
  --network host \
  -p 8000:8000 \
  -v geo-rag-chroma:/app/chroma_db \
  geo-rag:latest

# Option 2: Ollama on remote host
docker run \
  -e OLLAMA_BASE_URL=http://remote-host:11434 \
  -p 8000:8000 \
  -v geo-rag-chroma:/app/chroma_db \
  geo-rag:latest
```

### Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-cache:/root/.ollama
    command: serve

  geo-rag:
    build: .
    ports:
      - "8000:8000"
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
    volumes:
      - geo-rag-chroma:/app/chroma_db
    depends_on:
      - ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama-cache:
  geo-rag-chroma:
```

Run with:
```bash
docker-compose up -d
```

---

## Production Deployment

### Systemd Service (Linux)

```ini
# /etc/systemd/system/geo-rag.service
[Unit]
Description=Geo-RAG Platform
After=network.target ollama.service

[Service]
Type=simple
User=geo-rag
WorkingDirectory=/opt/geo-rag
Environment="PATH=/opt/geo-rag/venv/bin"
Environment="OLLAMA_BASE_URL=http://localhost:11434"
ExecStart=/opt/geo-rag/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable geo-rag
sudo systemctl start geo-rag
sudo systemctl status geo-rag
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name geo-rag.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long operations
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test single request
ab -n 1 -c 1 -p image.bin -T multipart/form-data http://localhost:8000/api/analyze

# Load test (5 concurrent requests, 10 total)
ab -n 10 -c 5 http://localhost:8000/api/health
```

---

## Monitoring

### Check Logs

```bash
# If running with Python
# Logs go to stdout (caught by systemd)

# If using docker-compose
docker-compose logs -f geo-rag

# Ollama logs
docker-compose logs -f ollama
```

### Monitor ChromaDB

```bash
python -c "
from services.rag_service import _get_collection
col = _get_collection()
print(f'Total chunks: {col.count()}')
print(f'Collection metadata: {col.metadata}')
"
```

### Monitor Diskspace (ChromaDB & Model Cache)

```bash
# ChromaDB storage
du -sh ./chroma_db

# Ollama model cache (Linux)
du -sh ~/.ollama/models

# Ollama model cache (macOS)
du -sh ~/.ollama/models
```

---

## Scaling Considerations

### Single Machine Bottlenecks

1. **Vision Model** (Qwen3-VL 235B): ~30-40s per image
2. **LLM Generation** (Gemma3 1B): ~1-2s per response
3. **Embeddings** (all-MiniLM-L6-v2): ~100ms per chunk

**Total per request**: ~40s (vision-bound)

### Optimization Strategies

1. **Model Quantization**
   - Use smaller Qwen3-VL model (1.5B instead of 235B)
   - Quantize Gemma3 to INT8

2. **Batch Processing**
   - Buffer images, process in batches
   - Parallelize vision extraction

3. **Caching**
   - Cache embeddings for duplicate questions
   - Cache vision features by image hash

4. **Distributed Setup**
   - Run multiple Ollama instances behind load balancer
   - Distribute ChromaDB reads across replicas

---

## Cleanup

### Reset Knowledge Base

```bash
# Delete ChromaDB and reingest
rm -rf ./chroma_db
python ingest_knowledge.py --glob "*.txt"
```

### Clean Cache

```bash
# Remove Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -name "*.pyc" -delete

# Remove model cache (optional)
# WARNING: This will require re-downloading models
rm -rf ~/.ollama/models  # Linux/macOS
```

### Reset to Fresh State

```bash
# Deactivate venv
deactivate

# Remove venv
rm -rf venv

# Remove ChromaDB
rm -rf chroma_db

# Remove build artifacts
rm -rf build dist *.egg-info __pycache__

# Reinstall everything
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python ingest_knowledge.py --glob "*.txt"
```

---

## Next Steps

1. **Read ARCHITECTURE.md** for system design details
2. **Read API.md** for endpoint reference
3. **Read MODE_BENCHMARKING.md** for research mode descriptions
4. **Review CHANGELOG.md** for list of changes made
5. **Upload your own satellite images** and test the system!

---

## Support

If you encounter issues:

1. Check **Troubleshooting** section above
2. Review logs: `python main.py` (see console output)
3. Test endpoints directly: `curl http://localhost:8000/api/health`
4. Verify Ollama models: `ollama list`
5. Check ChromaDB: `python -c "from services.rag_service import _get_collection; print(_get_collection().count())"`
