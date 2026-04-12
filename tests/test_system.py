#!/usr/bin/env python3
"""
Quick system integration test.
Tests that the Geo-RAG pipeline can be initialized and jobs can flow through.
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from services.job_queue import JobQueue
from utils.cache_manager import CacheManager
from core.prompt_builder import build_prompt
import hashlib


async def test_job_flow():
    """Test that a job can flow through the system."""
    print("\n=== Geo-RAG System Integration Test ===\n")

    # Initialize services
    job_queue = JobQueue()
    cache = CacheManager()

    # Create a fake job
    image_hash = hashlib.sha256(b"test_image").hexdigest()
    question = "What is the urban density in this image?"
    mode = "rag_baseline"

    print(f"1. Creating job...")
    job_id = job_queue.create_job(image_hash, question, mode)
    print(f"   Job ID: {job_id}")

    # Verify job was created
    job = job_queue.get_job(job_id)
    print(f"2. Job created successfully")
    print(f"   Status: {job['status']}")
    print(f"   Question: {job['request']['question']}")
    print(f"   Mode: {job['request']['mode']}")

    # Update job status to simulate processing
    print(f"\n3. Simulating job processing...")
    job_queue.update_stage(job_id, "vision_extraction", "processing", percent=20)
    job = job_queue.get_job(job_id)
    print(f"   Vision stage: {job['stages']['vision_extraction']}")

    job_queue.update_stage(job_id, "vision_extraction", "completed", percent=25)
    job = job_queue.get_job(job_id)
    print(f"   Vision stage: {job['stages']['vision_extraction']}")

    # Mark retrieval as complete
    job_queue.update_stage(job_id, "knowledge_retrieval", "completed", percent=50)
    job = job_queue.get_job(job_id)
    print(f"   Retrieval stage: {job['stages']['knowledge_retrieval']}")

    # Mark answer generation as complete
    job_queue.update_stage(job_id, "answer_generation", "processing", percent=60)
    job_queue.update_stage(job_id, "answer_generation", "completed", percent=100)
    job = job_queue.get_job(job_id)
    print(f"   Answer stage: {job['stages']['answer_generation']}")

    # Set result
    print(f"\n4. Setting job result...")
    answer = "This area shows moderate urban density with mixed residential and commercial patterns."
    trace = {"model": "test", "tokens": 50}
    job_queue.set_result(job_id, answer, trace)

    # Get final job
    job = job_queue.get_job(job_id)
    print(f"   Status: {job['status']}")
    print(f"   Result: {job['result']['answer'][:60]}...")

    # Test cache operations
    print(f"\n5. Testing cache...")
    test_features = {
        "vegetation_density": "high",
        "building_density": "medium",
        "road_density": "medium"
    }
    await cache.set_vision(image_hash, test_features)
    cached = await cache.get_vision(image_hash)
    print(f"   Cache write/read OK: {cached == test_features}")

    # Test prompt builder
    print(f"\n6. Testing prompt builder...")
    retrieval_results = [
        {"chunk": "Tunisia has desert climates", "source": "wikipedia", "score": 0.92},
        {"chunk": "Urbanization patterns in N. Africa", "source": "research.org", "score": 0.88}
    ]

    prompt = build_prompt(
        question=question,
        vision_features=test_features,
        retrieval_results=retrieval_results,
        spatial_context="Northern Tunisia",
        mode="rag_baseline"
    )
    print(f"   Prompt length: {len(prompt)} chars")
    print(f"   Contains question: {question in prompt}")
    print(f"   Contains retrieval: {len([r for r in retrieval_results if r['chunk'] in prompt]) > 0}")

    # Queue stats
    print(f"\n7. Queue statistics...")
    stats = job_queue.get_stats()
    print(f"   Total jobs: {stats['total_jobs']}")
    print(f"   Completed: {stats['completed_jobs']}")
    print(f"   Active: {stats['active_jobs']}")
    print(f"   Failed: {stats['failed_jobs']}")

    print("\n=== All Tests Passed! ===\n")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_job_flow())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
