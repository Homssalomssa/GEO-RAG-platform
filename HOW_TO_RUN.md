# How to Run the Geo-RAG Platform

To start the Geo-RAG Platform manually, you need to open two separate terminal windows—one for the backend and one for the frontend.

## 1. Start the Backend (FastAPI)

The backend handles the AI models, RAG database, and API routing.

1. Open your first terminal.
2. Navigate to the backend directory:
   ```bash
   cd "d:\CAPSTONE\project 10\app"
   ```
3. Start the server (make sure you activate your virtual environment if you use one):
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   *(The backend will now be listening on `http://localhost:8000` or `http://127.0.0.1:8000`)*

## 2. Start the Frontend (Vite + React)

The frontend is the UI you interact with in the browser.

1. Open your second terminal.
2. Navigate to the frontend directory:
   ```bash
   cd "d:\CAPSTONE\project 10\frontend"
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
