# System Logic & Components Explained

This document explains the core logic behind the tools, workers, services, and databases that make up the Geo-RAG platform.

## 1. Core Tools & Frameworks Used

- **FastAPI (Python)**: Our high-performance backend routing framework. It handles async requests from the UI immediately without blocking, converting them into background jobs.
- **Node.js, Vite & React**: The frontend stack. Vite provides lightning-fast UI serving, while React is used to build the interactive mapping and upload terminals.
- **Ollama**: Our local AI inference engine. It runs Large Language Models without requiring internet access or cloud API keys.
  - **qwen3-vl**: Used as the Vision Model to "see" and extract density and pattern metrics out of the raw pixels.
  - **gemma3**: Our text-reasoning LLM that combines the vision data with GIS knowledge to write final geospatial reports.

## 2. Background Workers & Services Logic

Because analyzing gigantic satellite images takes time, doing it synchronously would freeze the user's browser. We solved this by using an asynchronous **Job Queue Pipeline**:

1. **JobQueue (Singleton Tracker)**: When a user uploads an image, the FastAPI `routes.py` creates a "Job Ticket" tracking 3 stages: Vision, Retrieval, and Answer. It stores everything in a local `.json` to persist the state.
2. **Vision Extractor Worker**: A script that runs in an infinite loop parsing the queue. It takes the image, sends it to `vision_service.py` (which asks Ollama's Qwen3-VL what it sees), and saves the quantified observations (features like high/low building density) to cache.
3. **Retriever Worker**: Once Vision is done, this worker parses the user's text question and queries our Knowledge Base to find related geographical context. 
4. **Answer Generator Worker**: With both the Vision Features and the Retrieved Knowledge, this worker gives the entire package to `llm_service.py` (running Gemma3) to write an expert-level final response.

## 3. RAG: Embeddings & Vector Database

**Retrieval-Augmented Generation (RAG)** is what separates this platform from a basic ChatGPT wrapper. We don't just rely on the LLM's brain; we inject highly localized topological data dynamically.

- **The Database (ChromaDB)**: We chose `ChromaDB` as our Vector Storage Database. It runs completely locally in the `/chroma_db` folder (which is explicitly ignored in `.gitignore`, protecting it from git bloat). 
- **The Embedding Model (`all-MiniLM-L6-v2`)**: Before text can be searched mathematically, it must be vectorized into a spatial array. We use `sentence-transformers` locally to map geographical facts to a high-dimensional space.
- **Hybrid Search (Reciprocal Rank Fusion)**: When a user asks "Are there informal settlements here?", the retriever doesn't just look for exact word matches (like traditional database `SQL` lookups). It uses the embeddings to find *semantically similar* records in ChromaDB, merges it with BM25 keyword matching, and sends the most relevant Tunisian ADM2 historical reports right into the LLM logic!

---
*Prepared for Github Distribution. All external keys (like Google Earth Engine, though not active yet in the v0.3 logic) and local databases are safely secured via `.gitignore`.*
