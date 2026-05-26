"""
Job Queue: Persistent job tracking for async request processing.
Tracks status, progress, timing, and results for each analysis job.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import sys
from filelock import FileLock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import CACHE_DIR

logger = logging.getLogger(__name__)


class JobQueue:
    """Manages job lifecycle and persistent storage. (Singleton)"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(JobQueue, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.queue_file = Path(CACHE_DIR) / "metadata" / "job_queue.json"
        self.lock_file = self.queue_file.with_suffix(".lock")
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.jobs = {}
        self._load_queue()
        self._initialized = True

    def _load_queue(self):
        """Load job queue from persistent storage."""
        with FileLock(str(self.lock_file)):
            if self.queue_file.exists():
                try:
                    with open(self.queue_file) as f:
                        data = json.load(f)
                        self.jobs = data.get("jobs", {})
                        logger.info(f"Loaded {len(self.jobs)} jobs from queue")
                except Exception as e:
                    logger.error(f"Error loading job queue: {e}")
                    self.jobs = {}
            else:
                self.jobs = {}

    def _save_queue(self):
        """Persist job queue to storage."""
        with FileLock(str(self.lock_file)):
            try:
                data = {"jobs": self.jobs, "saved_at": datetime.utcnow().isoformat()}
                with open(self.queue_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving job queue: {e}")

    def create_job(self, image_hash: str, question: str, mode: str, batch_id: Optional[str] = None, city: str = "") -> str:
        """Create new job and return job_id."""
        job_id = str(uuid.uuid4())[:8]

        self.jobs[job_id] = {
            "job_id": job_id,
            "batch_id": batch_id,
            "status": "queued",
            "request": {
                "image_hash": image_hash,
                "question": question,
                "mode": mode,
                "city": city or ""
            },
            "stages": {
                "vision_extraction": "pending",
                "spatial_enrichment": "pending",
                "knowledge_retrieval": "pending",
                "answer_generation": "pending"
            },
            "progress": {
                "current_stage": None,
                "percent_complete": 0
            },
            "timing": {
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None,
                "processing_seconds": None
            },
            "result": None,
            "error": None
        }

        self._save_queue()
        logger.info(f"Created job {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update job status (queued, processing, cached, completed, failed)."""
        if job_id not in self.jobs:
            return False

        self.jobs[job_id]["status"] = status

        if status == "processing" and self.jobs[job_id]["timing"]["started_at"] is None:
            self.jobs[job_id]["timing"]["started_at"] = datetime.utcnow().isoformat()

        if status == "completed" and self.jobs[job_id]["timing"]["completed_at"] is None:
            completed = datetime.utcnow()
            started_at = self.jobs[job_id]["timing"]["started_at"]

            # If started_at is None, set it now
            if started_at is None:
                started_at = datetime.utcnow().isoformat()
                self.jobs[job_id]["timing"]["started_at"] = started_at

            started = datetime.fromisoformat(started_at)
            processing_seconds = (completed - started).total_seconds()

            self.jobs[job_id]["timing"]["completed_at"] = completed.isoformat()
            self.jobs[job_id]["timing"]["processing_seconds"] = processing_seconds

        self._save_queue()
        return True

    def update_stage(self, job_id: str, stage: str, status: str, percent: int = 0) -> bool:
        """Update processing stage status."""
        if job_id not in self.jobs:
            return False

        if stage not in self.jobs[job_id]["stages"]:
            return False

        self.jobs[job_id]["stages"][stage] = status
        self.jobs[job_id]["progress"]["current_stage"] = stage
        self.jobs[job_id]["progress"]["percent_complete"] = percent

        self._save_queue()
        return True

    def set_result(self, job_id: str, answer: str, full_result: Dict[str, Any] = None) -> bool:
        """Set job result."""
        if job_id not in self.jobs:
            return False

        self.jobs[job_id]["result"] = {
            "answer": answer,
            **(full_result or {})
        }
        self.update_job_status(job_id, "completed")
        self._save_queue()
        return True

    def set_error(self, job_id: str, message: str, stage: str = None, traceback: str = None) -> bool:
        """Set job error."""
        if job_id not in self.jobs:
            return False

        self.jobs[job_id]["error"] = {
            "message": message,
            "stage": stage,
            "traceback": traceback
        }
        self.update_job_status(job_id, "failed")
        self._save_queue()
        return True

    def get_active_jobs(self) -> list:
        """Get all active (non-completed) jobs."""
        return [
            job for job in self.jobs.values()
            if job["status"] in ["queued", "processing"]
        ]

    def get_completed_jobs(self) -> list:
        """Get all completed jobs."""
        return [
            job for job in self.jobs.values()
            if job["status"] in ["completed", "cached"]
        ]

    def cleanup_old_jobs(self, days_to_keep: int = 30) -> int:
        """Remove jobs older than specified days."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        jobs_to_remove = []

        for job_id, job in self.jobs.items():
            completed_at = job.get("timing", {}).get("completed_at")
            if completed_at:
                completed = datetime.fromisoformat(completed_at)
                if completed < cutoff:
                    jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.jobs[job_id]

        self._save_queue()
        logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
        return len(jobs_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        active = self.get_active_jobs()
        completed = self.get_completed_jobs()
        failed = [job for job in self.jobs.values() if job["status"] == "failed"]

        return {
            "total_jobs": len(self.jobs),
            "active_jobs": len(active),
            "completed_jobs": len(completed),
            "failed_jobs": len(failed),
            "completion_rate": len(completed) / max(len(self.jobs), 1) * 100
        }
