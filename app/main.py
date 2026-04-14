"""
Geo-RAG Platform — FastAPI Entry Point v0.3

Starts the server, includes routes, spawns background workers.
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

# Global task references for workers
worker_tasks = []

from workers.vision_extractor import VisionExtractor
from workers.retriever import Retriever
from workers.answer_generator import AnswerGenerator

vision_worker = VisionExtractor()
retriever_worker = Retriever()
answer_worker = AnswerGenerator()


# -----------------------------------------------------------------
# Create FastAPI App
# -----------------------------------------------------------------

app = FastAPI(
    title="Geo-RAG Platform",
    description="Satellite imagery analysis with async RAG pipeline",
    version="0.3.0"
)

# CORS — allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: allow all. Lock down in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.on_event("startup")
async def start_workers():
    logger.info("Starting Geo-RAG Platform v0.3...")
    logger.info("Spawning background workers...")
    worker_tasks.append(asyncio.create_task(vision_worker.run()))
    worker_tasks.append(asyncio.create_task(retriever_worker.run()))
    worker_tasks.append(asyncio.create_task(answer_worker.run()))


@app.on_event("shutdown")
async def stop_workers():
    logger.info("Shutting down Geo-RAG Platform...")
    for task in worker_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    worker_tasks.clear()
    logger.info("Workers stopped")

# Serve frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


# -----------------------------------------------------------------
# Run
# -----------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

