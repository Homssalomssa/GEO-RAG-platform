"""
Answer Generator Worker — Background async task
Generates final LLM answers using cached vision + retrieval + spatial context.
Runs after retrieval stage completes.
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
from services.llm_service import generate as generate_answer
from core.prompt_builder import build_prompt

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates final answers using cached features and retrieval."""

    def __init__(self):
        self.job_queue = JobQueue()
        self.cache = CacheManager()
        self.spatial_enricher = SpatialEnricher()

    async def process_job(self, job_id: str):
        """Process a single job: generate answer and store in cache."""
        try:
            job = self.job_queue.get_job(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found")
                return

            # Check if retrieval stage completed
            if job["stages"]["knowledge_retrieval"] != "completed":
                logger.debug(f"Answer Generator: Retrieval not ready for {job_id}, skipping")
                return

            question = job["request"]["question"]
            mode = job["request"]["mode"]
            city = (job["request"].get("city") or "").strip().lower()
            image_hash = job["request"]["image_hash"]

            logger.info(f"Answer Generator: Processing {job_id}")

            # Update job status
            self.job_queue.update_stage(job_id, "answer_generation", "processing", percent=60)

            # Fetch cached vision features
            vision_features = await self.cache.get_vision(image_hash)
            if not vision_features:
                raise ValueError(f"Vision features not found for {image_hash}")

            # Fetch cached retrieval results
            query_hash = hashlib.sha256(f"{question}{mode}{city}".encode()).hexdigest()
            retrieval_results = await self.cache.get_embeddings(query_hash)
            if not retrieval_results:
                raise ValueError(f"Retrieval results not found for {query_hash}")

            # Get spatial context from job payload when available
            spatial_context = job.get("spatial_context", "")
            if city:
                focus = f"Knowledge base focus city: {city.replace('_', ' ').title()}"
                spatial_context = f"{focus}\n{spatial_context}".strip()

            # Build prompt with all context
            prompt = build_prompt(
                question=question,
                vision_features=vision_features,
                retrieval_results=retrieval_results,
                spatial_context=spatial_context,
                mode=mode
            )

            logger.info(f"Answer Generator: Calling LLM for {job_id}...")

            # Generate answer
            answer = await generate_answer(prompt, temperature=0.3)

            # Store in response cache
            trace = {
                "vision_features": vision_features,
                "spatial_context": spatial_context,
                "retrieved_documents": len(retrieval_results) if isinstance(retrieval_results, list) else 0,
                "llm_prompt_length": len(prompt)
            }

            await self.cache.set_response(job_id, answer, trace)
            logger.info(f"Answer Generator: Cached answer for {job_id}")

            # Store full result with all analysis data
            full_result = {
                "answer": answer,
                "trace": trace,
                "vision_features": vision_features,
                "retrieved_context": retrieval_results if isinstance(retrieval_results, list) else [],
                "spatial_context": spatial_context
            }

            self.job_queue.set_result(job_id, answer, full_result)
            self.job_queue.update_stage(job_id, "answer_generation", "completed", percent=100)

            logger.info(f"Answer Generator: Completed {job_id}")

        except Exception as e:
            logger.error(f"Answer generation failed for {job_id}: {e}")
            self.job_queue.set_error(job_id, str(e), stage="answer_generation", traceback=str(e))

    async def run(self):
        """
        Main worker loop: Continuously process jobs waiting for answer generation.
        """
        logger.info("Answer Generator Worker starting...")

        while True:
            try:
                # Get active jobs
                active = self.job_queue.get_active_jobs()

                # Find jobs with retrieval done, answer pending
                for job in active:
                    if (job["stages"]["knowledge_retrieval"] == "completed" and
                        job["stages"]["answer_generation"] == "pending"):

                        job_id = job["job_id"]
                        await self.process_job(job_id)

                # Sleep before next check
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Answer Generator Worker error: {e}")
                await asyncio.sleep(5)


async def main():
    """Entry point for answer generator worker."""
    generator = AnswerGenerator()
    await generator.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
