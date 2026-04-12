"""
Vision Extractor Worker — Background async task
Extracts vision features from images and populates cache.
Runs continuously, dequeuing jobs waiting for vision stage.
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.job_queue import JobQueue
from utils.cache_manager import CacheManager
from services.vision_service import extract_features as get_vision_features
from config import VISION_MODEL

logger = logging.getLogger(__name__)


class VisionExtractor:
    """Extracts vision features from satellite images."""

    def __init__(self):
        self.job_queue = JobQueue()
        self.cache = CacheManager()
        self.max_concurrent = 2  # Ollama cloud throttling

    async def process_job(self, job_id: str):
        """Process a single job: extract vision and update cache."""
        try:
            job = self.job_queue.get_job(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found")
                return

            image_hash = job["request"]["image_hash"]
            logger.info(f"Vision: Processing {job_id} (image {image_hash[:8]}...)")

            # Update job status
            self.job_queue.update_job_status(job_id, "processing")
            self.job_queue.update_stage(job_id, "vision_extraction", "processing", percent=10)

            # Check cache first
            cached_features = await self.cache.get_vision(image_hash)
            if cached_features:
                logger.info(f"Vision: Cache HIT for {image_hash[:8]}...")
                self.job_queue.update_stage(job_id, "vision_extraction", "completed", percent=25)
                return

            # Cache miss → extract
            logger.info(f"Vision: Cache MISS, calling {VISION_MODEL}...")
            features = await get_vision_features(image_hash)

            # Store in cache
            await self.cache.set_vision(image_hash, features)
            logger.info(f"Vision: Cached features for {image_hash[:8]}...")

            # Update job
            self.job_queue.update_stage(job_id, "vision_extraction", "completed", percent=25)

        except Exception as e:
            logger.error(f"Vision extraction failed for {job_id}: {e}")
            self.job_queue.set_error(job_id, str(e), stage="vision_extraction", traceback=str(e))

    async def run(self):
        """
        Main worker loop: Continuously dequeue and process jobs.
        Maintains max_concurrent limit.
        """
        logger.info("Vision Extractor Worker starting...")
        active_tasks = set()

        while True:
            try:
                # Get queued jobs
                active = self.job_queue.get_active_jobs()
                queued_jobs = [j for j in active if j["status"] == "queued"]

                # Process up to max_concurrent
                for job in queued_jobs:
                    if len(active_tasks) >= self.max_concurrent:
                        break

                    job_id = job["job_id"]
                    task = asyncio.create_task(self.process_job(job_id))
                    active_tasks.add(task)
                    task.add_done_callback(active_tasks.discard)

                # Sleep before next check
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Vision Worker error: {e}")
                await asyncio.sleep(5)


async def main():
    """Entry point for vision extractor worker."""
    extractor = VisionExtractor()
    await extractor.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
