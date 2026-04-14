@echo off
REM Complete Geo-RAG Platform Setup & Launch Script (Windows)

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo GEO-RAG PLATFORM - COMPLETE SETUP
echo ==========================================
echo.

REM Step 1: Check Ollama
echo Step 1: Verifying Ollama...
curl -s http://localhost:11434/api/health > nul 2>&1
if errorlevel 1 (
    echo   ERROR: Ollama not running at localhost:11434
    echo   Start it with: ollama serve
    exit /b 1
)
echo   OK: Ollama is running
echo.

REM Step 2: Pull models
echo Step 2: Ensuring models are available...
echo   Pulling llava:7b...
call ollama pull llava:7b
echo   Pulling gemma3:1b...
call ollama pull gemma3:1b
echo   OK: Models ready
echo.

REM Step 3: Setup knowledge base
echo Step 3: Setting up knowledge base...
if not exist "chroma_db" (
    echo   Ingesting documents into ChromaDB...
    cd /d "%~dp0"
    python scripts/ingest_knowledge.py --glob "data/knowledge/*.txt"
    echo   OK: Knowledge base ready
) else (
    echo   OK: ChromaDB already exists
)
echo.

REM Step 4: Setup spatial data
echo Step 4: Setting up spatial enrichment...
if not exist "data\shapefiles\rtree_index.idx" (
    echo   Setting up spatial index...
    python scripts/spatial_setup.py
    echo   OK: Spatial data ready
) else (
    echo   OK: Spatial data already available
)
echo.

REM Step 5: Start backend
echo Step 5: Starting Geo-RAG Platform...
cd /d "%~dp0app"
start "Geo-RAG Backend" python -m uvicorn main:app --host 0.0.0.0 --port 8000
timeout /t 5 /nobreak

REM Step 6: Start frontend
echo.
echo Step 6: Starting frontend...
cd /d "%~dp0frontend"
call npm install
start "Geo-RAG Frontend" npm run dev

REM Step 7: Verify
echo.
echo Step 7: Verifying system...
curl -s http://localhost:8000/api/health 2>&1 | find "status"
echo.

echo ==========================================
echo GEO-RAG PLATFORM IS RUNNING!
echo ==========================================
echo.
echo Frontend: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Usage:
echo   1. Open http://localhost:8000 in your browser
echo   2. Upload a satellite image
echo   3. Ask a question about urban sprawl
echo   4. Results appear as they complete
echo.
pause
