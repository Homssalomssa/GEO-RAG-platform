"""
API Routes — v0.3 Async Job Queue Edition

Handles:
- Async job submission (returns job_id immediately)
- Job status polling
- Batch processing
- Health checks
"""

import asyncio
import base64
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from api.schemas import (
    AnalysisMode, AnalyzeResponse, RAGQueryRequest,
    IngestRequest, HealthResponse, VisionFeatures,
)
from services.job_queue import JobQueue
from config import VISION_MODEL, LLM_MODEL, MAX_IMAGE_SIZE_MB, SUPPORTED_IMAGE_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Global job queue instance
job_queue = JobQueue()


# ------------------------------------------------------------------
# Async Analysis Endpoint (v0.3)
# ------------------------------------------------------------------

@router.post("/analyze")
async def analyze_image_async(
    image: UploadFile = File(..., description="Satellite image file"),
    question: str = Form(..., description="Question about the image"),
    mode: str = Form(default="rag_baseline", description="Analysis mode"),
):
    """
    Submit image for async analysis. Returns job_id immediately.

    Usage:
    1. POST image + question → get job_id
    2. Poll GET /api/status/{job_id} for progress
    3. Result available when status == "completed"
    """
    # Validate image type
    if image.content_type and image.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {image.content_type}"
        )

    # Validate mode
    try:
        AnalysisMode(mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

    # Validate question
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 chars)")

    # Read and hash image
    image_bytes = await image.read()
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"Image too large: {size_mb:.1f}MB")

    import hashlib
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    # Create job in queue
    job_id = job_queue.create_job(image_hash, question.strip(), mode)

    # Persist raw image bytes so the vision worker can base64-encode them
    tmp_dir = Path("/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{job_id}.img"
    tmp_path.write_bytes(image_bytes)

    logger.info(f"Created job {job_id} for image {image_hash[:8]}...")

    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Job queued. Poll /api/status/{job_id} for progress"
    }


# ------------------------------------------------------------------
# Batch Analysis Endpoint (v0.3)
# ------------------------------------------------------------------

@router.post("/batch")
async def batch_analyze(
    images: list = File(..., description="Multiple image files"),
    questions: str = Form(..., description="JSON array of questions"),
    mode: str = Form(default="rag_baseline", description="Analysis mode"),
):
    """
    Submit multiple images for batch async analysis.

    Returns batch_id. Poll /api/batch/{batch_id} for overall progress.
    """
    import json
    import hashlib

    if not images:
        raise HTTPException(status_code=400, detail="No images provided")

    try:
        questions_list = json.loads(questions)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid questions JSON")

    if len(questions_list) != len(images):
        raise HTTPException(
            status_code=400,
            detail=f"Number of questions ({len(questions_list)}) must match images ({len(images)})"
        )

    # Create jobs for each image
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    job_ids = []

    for img, q in zip(images, questions_list):
        img_bytes = await img.read() if hasattr(img, 'read') else img
        img_hash = hashlib.sha256(img_bytes).hexdigest()
        job_id = job_queue.create_job(img_hash, q, mode, batch_id=batch_id)
        tmp_dir = Path("/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"{job_id}.img"
        tmp_path.write_bytes(img_bytes)
        job_ids.append(job_id)

    logger.info(f"Created batch {batch_id} with {len(job_ids)} jobs")

    return {
        "batch_id": batch_id,
        "total_jobs": len(job_ids),
        "job_ids": job_ids,
        "status": "queued",
        "message": f"Batch queued. Poll /api/batch/{batch_id} for progress"
    }


# ------------------------------------------------------------------
# Job Status Endpoint (v0.3)
# ------------------------------------------------------------------

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Poll for job progress and result.

    Returns:
    - status: queued, processing, completed, failed
    - progress: 0-100%
    - current_stage: which pipeline stage
    - result: answer + trace when completed
    """
    job = job_queue.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"]["percent_complete"],
        "current_stage": job["progress"]["current_stage"],
        "created_at": job["timing"]["created_at"],
        "started_at": job["timing"]["started_at"],
    }

    # Add result if completed
    if job["status"] == "completed" and job["result"]:
        response["result"] = job["result"].get("answer", "")
        response["vision_features"] = job["result"].get("vision_features", {})
        response["retrieved_context"] = job["result"].get("retrieved_context", [])
        response["spatial_context"] = job["result"].get("spatial_context", "")
        response["trace"] = job["result"].get("trace", {})
        response["completed_at"] = job["timing"]["completed_at"]
        response["processing_seconds"] = job["timing"]["processing_seconds"]

    # Add error if failed
    if job["status"] == "failed" and job["error"]:
        response["error"] = job["error"]["message"]
        response["error_stage"] = job["error"]["stage"]

    return response


# ------------------------------------------------------------------
# Batch Status Endpoint
# ------------------------------------------------------------------

@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """
    Get overall batch progress and individual job statuses.
    """
    # Get all jobs with matching batch_id
    batch_jobs = [j for j in job_queue.jobs.values() if j.get("batch_id") == batch_id]

    if not batch_jobs:
        raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")

    completed = sum(1 for j in batch_jobs if j["status"] == "completed")
    processing = sum(1 for j in batch_jobs if j["status"] == "processing")
    failed = sum(1 for j in batch_jobs if j["status"] == "failed")
    queued = sum(1 for j in batch_jobs if j["status"] == "queued")

    return {
        "batch_id": batch_id,
        "total": len(batch_jobs),
        "completed": completed,
        "processing": processing,
        "queued": queued,
        "failed": failed,
        "progress": (completed / len(batch_jobs) * 100) if batch_jobs else 0,
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "progress": j["progress"]["percent_complete"]
            }
            for j in batch_jobs
        ]
    }


# ------------------------------------------------------------------
# Cache Management
# ------------------------------------------------------------------

@router.post("/cache/clear")
async def clear_cache():
    """Clear all caches (vision, embeddings, responses)."""
    from utils.cache_manager import CacheManager
    cache = CacheManager()
    success = await cache.clear_all()
    return {"status": "success" if success else "failed", "message": "Cache cleared"}


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    from utils.cache_manager import CacheManager
    cache = CacheManager()
    return cache.get_stats()


# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------

@router.get("/health")
async def health_check():
    """Check system health."""
    return {
        "status": "healthy",
        "message": "Geo-RAG Platform is running!",
        "vision_model": VISION_MODEL,
        "llm_model": LLM_MODEL
    }


# ------------------------------------------------------------------
# Ray Tracing Endpoints (Optional - for debugging)
# ------------------------------------------------------------------

@router.get("/queue/stats")
async def get_queue_stats():
    """Get job queue statistics."""
    return job_queue.get_stats()


@router.get("/spatial/status")
async def get_spatial_status():
    """Get spatial enrichment status."""
    from utils.spatial_enricher import SpatialEnricher
    enricher = SpatialEnricher()
    return enricher.get_status()

