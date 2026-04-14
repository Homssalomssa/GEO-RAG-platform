# Geo-RAG Platform

A production-ready **Geo-RAG (Retrieval-Augmented Generation) Platform** designed for satellite imagery analysis. It uses a scalable micro-architecture featuring an asynchronous job pipeline, strict local AI inference, and dynamic embedding caching.

##  Key Features

-  **Vision Extraction**: Processes raw satellite images locally using `llava:7b`.
-  **RAG Pipeline**: Semantic knowledge retrieval powered by `all-MiniLM-L6-v2` and `ChromaDB`.
-  **LLM Analysis**: Synthesizes extracted vision features and geospatial context safely via `gemma3:1b`.
-  **Asynchronous Queue**: Job state trackers continuously map progression across multiple decoupled background workers.
-  **Modern UI**: Full Vite + React Integration featuring an interactive upload terminal.

---

##  Architecture Overview

The backend uses a **Singleton JobQueue** that coordinates asynchronous tasks across four major background stages without blocking the Web API:

1. **Vision Extraction**: Passes the uploaded image array to Ollama's vision model to extract density mappings and structural indicators.
2. **Spatial Enrichment** *(pending implementation)*: Reserved stage for geospatial enrichment logic.
3. **Knowledge Retrieval**: Generates high-dimension embeddings of the prompt and pulls relevant urban geography chunks from local storage.
4. **Answer Generation**: Mates the extracted visual observations with the RAG knowledge and hands it to the language model for a detailed final report.

*(For an in-depth breakdown of the codebase modules, please refer to the [**System Logic and Tools Overview**](docs/SYSTEM_LOGIC_AND_TOOLS.md)).*

---

##  Getting Started

The platform runs 100% locally and safely requires zero cloud API keys (No OpenAI or Google Cloud required). 

### Prerequisites

1. Ensure **Node.js** and **Python 3.11+** are installed.
2. Ensure you have **Ollama** installed and running locally.
3. Obtain the required local instruction models via terminal:
   ```bash
   ollama pull llava:7b
   ollama pull gemma3:1b
   ```

### 1. Launch the Backend
Open a terminal inside the project root:
```bash
cd app
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
This boots the FastAPI service on `http://localhost:8000`.

### 2. Launch the Frontend
Open a **second terminal** inside the project root:
```bash
cd frontend
npm install
npm run dev
```
This boots the Vite React server, usually launching the UI at `http://localhost:5173` or `5175`.

---

##  Testing
You can verify the FastAPI endpoints and orchestrator pipelines using the included test suites from the root directory:
```bash
python tests/test_system.py
```

##  Security
All vector queries and visual analyses run completely offline. The repository `.gitignore` automatically secures any `.env` environments and large local `chroma_db` stores.


## License & Attribution

Built as part of CAPSTONE Project 10 - Geo-RAG Analysis Platform.
