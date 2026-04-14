# How to Run the Geo-RAG Platform

Use two terminals: one for backend, one for frontend.

## 1. Start Ollama + Models

```bash
ollama pull llava:7b
ollama pull gemma3:1b
ollama serve
```

## 2. Start the Backend (FastAPI)

The backend handles the AI models, RAG database, and API routing.

1. Open your first terminal.
2. Navigate to the project root:
   ```bash
   cd .
   ```
3. Start the server with the environment that has dependencies installed:
   ```bash
   .venv312\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   *(The backend will now be listening on `http://localhost:8000` or `http://127.0.0.1:8000`)*

## 3. Start the Frontend (Vite + React)

The frontend is the UI you interact with in the browser.

1. Open your second terminal.
2. Navigate to the frontend directory:
   ```bash
   cd ./frontend
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   *(The frontend will usually be accessible at `http://localhost:5175` or `http://localhost:5173` depending on port availability. Check the terminal output for the exact URL.)*

---

**Troubleshooting:**
- **"Failed to fetch" in browser**: This usually means either the Python backend terminal crashed or was closed.
- **Port already in use**: If Python tells you `[winerror 10048]`, you already have a backend running in the background or in another terminal. You must kill it before starting a new one.
- **Wrong Python environment**: if `No module named uvicorn` appears, use the exact virtual env Python path (example above).

## Artifact Safety Before Push

Do not commit runtime-generated files. This repo now ignores common runtime artifacts, including:
- `cache/vision/*.json`
- `cache/embeddings/*.json`
- `cache/llm_responses/*.json`
- `cache/metadata/cache_index.json`
- `cache/metadata/job_queue.json`
- `tmp/`

Quick check before push:
```bash
git status --short
```
