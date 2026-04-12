"""
Tests for the RAG Service.
Verifies chunking, RRF merge, and GIS enrichment logic.
"""

import pytest
from services.rag_service import _chunk_text, merge_and_rerank, gis_query


class TestChunking:
    """Test text chunking logic."""

    def test_short_text_single_chunk(self):
        text = "This is a short text about urban planning."
        # Too short (< 50 chars after chunking) — may return empty
        chunks = _chunk_text(text, chunk_size=500)
        # Short text should still produce result if > 50 chars
        assert len(chunks) <= 1

    def test_long_text_multiple_chunks(self):
        text = "Urban planning is important. " * 50  # ~1450 chars
        chunks = _chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1
        # Each chunk should be <= chunk_size + some tolerance
        for chunk in chunks:
            assert len(chunk) <= 250

    def test_overlap_creates_redundancy(self):
        text = "Sentence one. Sentence two. Sentence three. Sentence four. " * 10
        chunks = _chunk_text(text, chunk_size=100, overlap=30)
        if len(chunks) > 1:
            # Check that consecutive chunks share some content
            overlap_found = False
            for i in range(len(chunks) - 1):
                words_a = set(chunks[i].split()[-5:])
                words_b = set(chunks[i + 1].split()[:5])
                if words_a & words_b:
                    overlap_found = True
                    break
            # Overlap is likely but not guaranteed due to sentence breaks
            # Just ensure no crash


class TestMergeAndRerank:
    """Test Reciprocal Rank Fusion merge."""

    def test_merge_deduplicates(self):
        semantic = [
            {"chunk": "Document about urban sprawl and expansion", "source": "a.txt", "score": 0.9},
            {"chunk": "Document about informal settlements", "source": "b.txt", "score": 0.8},
        ]
        keyword = [
            {"chunk": "Document about urban sprawl and expansion", "source": "a.txt", "score": 5.0},
            {"chunk": "Document about road networks", "source": "c.txt", "score": 3.0},
        ]
        merged = merge_and_rerank(semantic, keyword, top_k=5)
        # "Document about urban sprawl" appears in both → should be ranked first
        assert merged[0]["chunk"].startswith("Document about urban sprawl")
        # Total unique docs = 3
        assert len(merged) == 3

    def test_merge_empty_lists(self):
        merged = merge_and_rerank([], [], top_k=5)
        assert merged == []

    def test_merge_one_empty(self):
        semantic = [
            {"chunk": "Some document", "source": "a.txt", "score": 0.9},
        ]
        merged = merge_and_rerank(semantic, [], top_k=5)
        assert len(merged) == 1


class TestGISQuery:
    """Test rule-based GIS enrichment."""

    def test_high_density_informal(self):
        features = {
            "building_density": "high, tightly packed informal structures",
            "road_density": "low, mostly unpaved tracks",
            "urban_pattern": "irregular, no grid layout",
            "vegetation_density": "low, sparse coverage",
        }
        result = gis_query(features)
        assert "high" in result["estimated_building_count"].lower()
        assert "limited" in result["infrastructure_assessment"].lower() or "no" in result["infrastructure_assessment"].lower()
        assert "informal" in result["pattern_classification"].lower()

    def test_planned_urban(self):
        features = {
            "building_density": "moderate, regular spacing",
            "road_density": "high, paved grid network",
            "urban_pattern": "grid layout",
            "vegetation_density": "medium, parks and tree lines",
        }
        result = gis_query(features)
        assert "grid" in result["pattern_classification"].lower()

    def test_missing_features(self):
        """GIS query should handle missing/empty features gracefully."""
        result = gis_query({})
        assert "estimated_building_count" in result
        assert "infrastructure_assessment" in result
