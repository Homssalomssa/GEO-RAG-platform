"""
Cache Manager: Async cache operations for vision features, embeddings, and LLM responses.
Handles cache gets, sets, clearing, expiration, and statistics.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

# Import config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import CACHE_DIR, CACHE_ENABLED, CACHE_VISION_EXPIRY_DAYS, CACHE_EMBEDDINGS_EXPIRY_DAYS, CACHE_RESPONSES_EXPIRY_DAYS


class CacheManager:
    """Manages persistent caching across vision, embeddings, and LLM responses."""

    def __init__(self):
        self.cache_dir = Path(CACHE_DIR)
        self.vision_dir = self.cache_dir / "vision"
        self.embeddings_dir = self.cache_dir / "embeddings"
        self.responses_dir = self.cache_dir / "llm_responses"
        self.metadata_dir = self.cache_dir / "metadata"

        # Create directories
        for d in [self.vision_dir, self.embeddings_dir, self.responses_dir, self.metadata_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.index_file = self.metadata_dir / "cache_index.json"
        self._load_index()

    def _load_index(self):
        """Load cache metadata index."""
        if self.index_file.exists():
            with open(self.index_file) as f:
                self.index = json.load(f)
        else:
            self.index = {
                "total_items": 0,
                "storage_mb": 0,
                "hit_rate_percent": 0,
                "time_saved_hours": 0,
                "categories": {
                    "vision": {"count": 0, "storage_mb": 0, "hit_count": 0},
                    "embeddings": {"count": 0, "storage_mb": 0, "hit_count": 0, "expired_count": 0},
                    "llm_responses": {"count": 0, "storage_mb": 0, "hit_count": 0, "expired_count": 0},
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            self._save_index()

    def _save_index(self):
        """Persist cache metadata index."""
        self.index["last_updated"] = datetime.utcnow().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    @staticmethod
    def _hash_string(s: str) -> str:
        """SHA-256 hash of string."""
        return hashlib.sha256(s.encode()).hexdigest()

    async def get_vision(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached vision features by image hash."""
        if not CACHE_ENABLED:
            return None

        cache_file = self.vision_dir / f"{image_hash}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)
            self.index["categories"]["vision"]["hit_count"] += 1
            self._save_index()
            logger.info(f"Vision cache hit: {image_hash[:8]}...")
            return data.get("features")
        except Exception as e:
            logger.error(f"Error reading vision cache: {e}")
            return None

    async def set_vision(self, image_hash: str, features: Dict[str, Any]) -> bool:
        """Cache vision features by image hash (never expires)."""
        if not CACHE_ENABLED:
            return False

        cache_file = self.vision_dir / f"{image_hash}.json"

        try:
            data = {
                "image_hash": image_hash,
                "features": features,
                "cached_at": datetime.utcnow().isoformat(),
                "model_version": "gemma2:4-31b-cloud"
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Update index
            self.index["categories"]["vision"]["count"] += 1
            self.index["categories"]["vision"]["storage_mb"] += cache_file.stat().st_size / (1024 * 1024)
            self.index["total_items"] += 1
            self._save_index()

            logger.info(f"Cached vision features: {image_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Error caching vision: {e}")
            return False

    async def get_embeddings(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached embeddings by query hash (7-day expiry)."""
        if not CACHE_ENABLED:
            return None

        cache_file = self.embeddings_dir / f"{query_hash}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            # Check expiration
            expires_at = datetime.fromisoformat(data.get("expires_at", "2020-01-01"))
            if datetime.utcnow() > expires_at:
                logger.info(f"Embedding cache expired: {query_hash[:8]}...")
                await self.delete_embeddings(query_hash)
                return None

            self.index["categories"]["embeddings"]["hit_count"] += 1
            self._save_index()
            logger.info(f"Embedding cache hit: {query_hash[:8]}...")
            return data.get("results")
        except Exception as e:
            logger.error(f"Error reading embedding cache: {e}")
            return None

    async def set_embeddings(self, query_hash: str, query: str, mode: str, results: list) -> bool:
        """Cache embeddings with 7-day expiry."""
        if not CACHE_ENABLED:
            return False

        cache_file = self.embeddings_dir / f"{query_hash}.json"

        try:
            now = datetime.utcnow()
            data = {
                "query_hash": query_hash,
                "query": query,
                "mode": mode,
                "results": results,
                "cached_at": now.isoformat(),
                "expires_at": (now + timedelta(days=CACHE_EMBEDDINGS_EXPIRY_DAYS)).isoformat()
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            self.index["categories"]["embeddings"]["count"] += 1
            self.index["categories"]["embeddings"]["storage_mb"] += cache_file.stat().st_size / (1024 * 1024)
            self.index["total_items"] += 1
            self._save_index()

            logger.info(f"Cached embeddings: {query_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Error caching embeddings: {e}")
            return False

    async def get_response(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get cached LLM response by job_id (30-day expiry)."""
        if not CACHE_ENABLED:
            return None

        cache_file = self.responses_dir / f"{job_id}_result.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            # Check expiration
            expires_at = datetime.fromisoformat(data.get("expires_at", "2020-01-01"))
            if datetime.utcnow() > expires_at:
                logger.info(f"Response cache expired: {job_id}")
                await self.delete_response(job_id)
                return None

            self.index["categories"]["llm_responses"]["hit_count"] += 1
            self._save_index()
            logger.info(f"Response cache hit: {job_id}")
            return data
        except Exception as e:
            logger.error(f"Error reading response cache: {e}")
            return None

    async def set_response(self, job_id: str, answer: str, trace: Dict = None) -> bool:
        """Cache LLM response with 30-day expiry."""
        if not CACHE_ENABLED:
            return False

        cache_file = self.responses_dir / f"{job_id}_result.json"

        try:
            now = datetime.utcnow()
            data = {
                "job_id": job_id,
                "answer": answer,
                "analysis_trace": trace or {},
                "cached_at": now.isoformat(),
                "expires_at": (now + timedelta(days=CACHE_RESPONSES_EXPIRY_DAYS)).isoformat()
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            self.index["categories"]["llm_responses"]["count"] += 1
            self.index["categories"]["llm_responses"]["storage_mb"] += cache_file.stat().st_size / (1024 * 1024)
            self.index["total_items"] += 1
            self._save_index()

            logger.info(f"Cached response: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False

    async def delete_vision(self, image_hash: str) -> bool:
        """Delete vision cache for image."""
        cache_file = self.vision_dir / f"{image_hash}.json"
        if cache_file.exists():
            cache_file.unlink()
            return True
        return False

    async def delete_embeddings(self, query_hash: str) -> bool:
        """Delete embeddings cache for query."""
        cache_file = self.embeddings_dir / f"{query_hash}.json"
        if cache_file.exists():
            cache_file.unlink()
            self.index["categories"]["embeddings"]["expired_count"] += 1
            self._save_index()
            return True
        return False

    async def delete_response(self, job_id: str) -> bool:
        """Delete response cache for job."""
        cache_file = self.responses_dir / f"{job_id}_result.json"
        if cache_file.exists():
            cache_file.unlink()
            self.index["categories"]["llm_responses"]["expired_count"] += 1
            self._save_index()
            return True
        return False

    async def clear_all(self) -> bool:
        """Clear all cache."""
        try:
            import shutil
            for directory in [self.vision_dir, self.embeddings_dir, self.responses_dir]:
                shutil.rmtree(directory, ignore_errors=True)
                directory.mkdir(parents=True, exist_ok=True)

            self.index = {
                "total_items": 0,
                "storage_mb": 0,
                "hit_rate_percent": 0,
                "time_saved_hours": 0,
                "categories": {
                    "vision": {"count": 0, "storage_mb": 0, "hit_count": 0},
                    "embeddings": {"count": 0, "storage_mb": 0, "hit_count": 0, "expired_count": 0},
                    "llm_responses": {"count": 0, "storage_mb": 0, "hit_count": 0, "expired_count": 0},
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            self._save_index()
            logger.info("All cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.index
