#!/bin/bash
# Complete Geo-RAG Platform Setup & Launch Script
# Sets up knowledge base, starts all services

set -e

PROJECT_DIR="d:/CAPSTONE/project 10"
cd "$PROJECT_DIR"

echo "==========================================="
echo "GEO-RAG PLATFORM - COMPLETE SETUP"
echo "==========================================="
echo ""

# Step 1: Check Ollama
echo "Step 1: Verifying Ollama..."
if ! curl -s http://localhost:11434/api/health > /dev/null; then
    echo "  ERROR: Ollama not running at localhost:11434"
    echo "  Start it with: ollama serve"
    exit 1
fi
echo "  OK: Ollama is running"

# Step 2: Pull models
echo ""
echo "Step 2: Ensuring models are available..."
echo "  Pulling qwen3-vl:235b-cloud..."
ollama pull qwen3-vl:235b-cloud 2>&1 | grep -E "pulling|verifying|success" || true
echo "  Pulling gemma3:1b..."
ollama pull gemma3:1b 2>&1 | grep -E "pulling|verifying|success" || true
echo "  OK: Models ready"

# Step 3: Setup knowledge base
echo ""
echo "Step 3: Setting up knowledge base (ChromaDB)..."
if [ ! -d "chroma_db" ]; then
    echo "  Ingesting documents into ChromaDB..."
    cd "$PROJECT_DIR"
    python scripts/ingest_knowledge.py --glob "data/knowledge/*.txt" 2>&1 | tail -5
    echo "  OK: Knowledge base ready"
else
    echo "  OK: ChromaDB already exists"
fi

# Step 4: Setup spatial data
echo ""
echo "Step 4: Setting up spatial enrichment..."
if [ ! -d "data/shapefiles" ] || [ ! -f "data/shapefiles/rtree_index.idx" ]; then
    echo "  Setting up spatial index..."
    python scripts/spatial_setup.py 2>&1 | tail -3
    echo "  OK: Spatial data ready"
else
    echo "  OK: Spatial data already available"
fi

# Step 5: Start backend
echo ""
echo "Step 5: Starting Geo-RAG Platform..."
cd "$PROJECT_DIR/app"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 5

# Step 6: Verify
echo ""
echo "Step 6: Verifying system..."
HEALTH=$(curl -s http://localhost:8000/api/health | grep -o '"status":"[^"]*"' || echo '"status":"unknown"')
echo "  API Status: $HEALTH"

echo ""
echo "==========================================="
echo "GEO-RAG PLATFORM IS RUNNING!"
echo "==========================================="
echo ""
echo "Frontend: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Usage:"
echo "  1. Open http://localhost:8000 in your browser"
echo "  2. Upload a satellite image"
echo "  3. Ask a question about urban sprawl"
echo "  4. Results appear as they complete"
echo ""
