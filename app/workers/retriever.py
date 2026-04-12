"""
Retriever Worker — Background async task
Retrieves knowledge chunks for questions and populates cache.
Runs after vision extraction completes.
"""

import asyncio
import hashlib
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.job_queue import JobQueue
from utils.cache_manager import CacheManager
from utils.spatial_enricher import SpatialEnricher
from services.rag_service import semantic_search, keyword_search, merge_and_rerank

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves knowledge chunks and enriches with spatial context."""

    def __init__(self):
        self.job_queue = JobQueue()
        self.cache = CacheManager()
        self.spatial_enricher = SpatialEnricher()

    async def process_job(self, job_id: str):
        """Process a single job: retrieve knowledge and update cache."""
        try:
            job = self.job_queue.get_job(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found")
                return

            # Check if vision stage completed
            if job["stages"]["vision_extraction"] != "completed":
                logger.debug(f"Retriever: Vision not ready for {job_id}, skipping")
                return

            question = job["request"]["question"]
            mode = job["request"]["mode"]
            image_hash = job["request"]["image_hash"]

            logger.info(f"Retriever: Processing {job_id} (question: {question[:50]}...)")

            # Update job status
            self.job_queue.update_stage(job_id, "knowledge_retrieval", "processing", percent=30)

            # Compute query hash
            query_hash = hashlib.sha256(f"{question}{mode}".encode()).hexdigest()

            # Check cache
            cached_results = await self.cache.get_embeddings(query_hash)
            if cached_results:
                logger.info(f"Retriever: Cache HIT for query {query_hash[:8]}...")
                self.job_queue.update_stage(job_id, "knowledge_retrieval", "completed", percent=50)
                return

            # Cache miss → retrieve
            logger.info(f"Retriever: Cache MISS, querying knowledge base...")

            # Spatial enrichment
            spatial_context = ""
            if self.spatial_enricher.shapefiles_loaded:
                # In real scenario, extract coordinates from image metadata
                # For now, skip spatial enrichment
                logger.debug("Retriever: Spatial enrichment enabled but no image coords")

            # Semantic + keyword retrieval
            semantic_results = semantic_search(f"{question} {spatial_context}", top_k=5)
            keyword_results = keyword_search(question, top_k=3)

            # Merge with RRF
            merged_results = merge_and_rerank(semantic_results, keyword_results)

            # Store in cache
            await self.cache.set_embeddings(query_hash, question, mode, merged_results)
            logger.info(f"Retriever: Cached retrieval results for {query_hash[:8]}...")

            # Update job
            self.job_queue.update_stage(job_id, "knowledge_retrieval", "completed", percent=50)

        except Exception as e:
            logger.error(f"Retrieval failed for {job_id}: {e}")
            self.job_queue.set_error(job_id, str(e), stage="knowledge_retrieval", traceback=str(e))

    async def run(self):
        """
        Main worker loop: Continuously process jobs waiting for retrieval.
        """
        logger.info("Retriever Worker starting...")

        while True:
            try:
                # Get active jobs
                active = self.job_queue.get_active_jobs()

                # Find jobs with vision done, retrieval pending
                for job in active:
                    if (job["stages"]["vision_extraction"] == "completed" and
                        job["stages"]["knowledge_retrieval"] == "pending"):

                        job_id = job["job_id"]
                        await self.process_job(job_id)

                # Sleep before next check
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Retriever Worker error: {e}")
                await asyncio.sleep(5)


async def main():
    """Entry point for retriever worker."""
    retriever = Retriever()
    await retriever.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
