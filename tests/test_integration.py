"""
Integration tests for the full Geo-RAG pipeline end-to-end.

Tests verify that the pipeline works from image upload through final response,
using minimal test fixtures (small mock images, short documents).

Run with: pytest tests/test_integration.py -v
"""

import pytest
import asyncio
import json
from pathlib import Path
from PIL import Image
import io
import base64

from services.rag_service import ingest_documents, _get_collection
from core.orchestrator import analyze
from api.schemas import AnalysisMode


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def minimal_test_image():
    """Create a minimal test satellite image (256x256) with varied patterns as base64."""
    # Create a more realistic test image with some features the vision model can analyze
    img = Image.new('RGB', (256, 256), color=(100, 150, 100))  # Green background (vegetation)
    pixels = img.load()

    # Add some "buildings" - gray squares
    for i in range(50, 150, 30):
        for j in range(50, 150, 30):
            for di in range(20):
                for dj in range(20):
                    if i+di < 256 and j+dj < 256:
                        pixels[i+di, j+dj] = (150, 150, 150)  # Gray buildings

    # Add some "roads" - brown/tan lines
    for i in range(0, 256, 60):
        for j in range(256):
            if i < 256:
                pixels[i, j] = (180, 160, 100)  # Road color

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return base64.b64encode(img_bytes.getvalue()).decode('utf-8')


@pytest.fixture(scope="session")
def test_documents():
    """Minimal test documents for knowledge base."""
    return [
        {
            "text": "Urban planning is the discipline of developing and designing cities. "
                   "Satellite imagery helps planners identify settlement patterns and infrastructure.",
            "source": "test_urban_planning.txt"
        },
        {
            "text": "Informal settlements are urban areas that develop outside official planning. "
                   "They often exhibit irregular street patterns and mixed building types.",
            "source": "test_informal_settlement.txt"
        },
        {
            "text": "Building density is measured as structures per unit area. "
                   "High density areas often indicate urban development.",
            "source": "test_density_metrics.txt"
        }
    ]


@pytest.fixture(scope="session")
def setup_test_knowledge_base(test_documents):
    """Setup test knowledge base before running tests."""
    # Ingest test documents
    asyncio.run(ingest_documents(test_documents))

    # Verify ingestion
    collection = _get_collection()
    chunk_count = collection.count()
    print(f"\nTest knowledge base initialized with {chunk_count} chunks")

    yield chunk_count

    # Cleanup would go here (optional for testing)


# =============================================================================
# Integration Tests
# =============================================================================

class TestPipelineIntegration:
    """Test full end-to-end pipeline with all three modes."""

    @pytest.mark.asyncio
    async def test_llm_only_mode(self, minimal_test_image, setup_test_knowledge_base):
        """Test LLM-only analysis mode."""
        question = "Is there evidence of urban development?"

        result = await analyze(minimal_test_image, question, AnalysisMode.LLM_ONLY)

        # Verify response structure
        assert result.mode == AnalysisMode.LLM_ONLY
        assert result.vision_features is not None
        assert len(result.answer) > 0
        assert result.reasoning_trace is not None

        # Vision features should be populated
        assert result.vision_features.building_density is not None

        # No retrieval in LLM-only
        assert len(result.retrieved_context) == 0
        assert result.gis_data is None

        # Timing should have values
        assert result.reasoning_trace.timing.vision_ms > 0
        assert result.reasoning_trace.timing.llm_ms > 0
        assert result.reasoning_trace.timing.retrieval_ms == 0

    @pytest.mark.asyncio
    async def test_rag_baseline_mode(self, minimal_test_image, setup_test_knowledge_base):
        """Test RAG baseline mode (semantic search only)."""
        question = "What are informal settlements?"

        result = await analyze(minimal_test_image, question, AnalysisMode.RAG_BASELINE)

        # Verify response structure
        assert result.mode == AnalysisMode.RAG_BASELINE
        assert result.vision_features is not None
        assert len(result.answer) > 0

        # Should have retrieved context
        assert len(result.retrieved_context) > 0, "Should retrieve at least one chunk"

        # Each chunk should have metadata
        for chunk in result.retrieved_context:
            assert len(chunk.chunk) > 0
            assert chunk.source is not None
            assert chunk.score >= 0.0

        # No GIS in baseline
        assert result.gis_data is None

        # Timing
        assert result.reasoning_trace.timing.retrieval_ms > 0

    @pytest.mark.asyncio
    async def test_rag_advanced_mode(self, minimal_test_image, setup_test_knowledge_base):
        """Test RAG advanced mode (hybrid search + GIS)."""
        question = "Is there high building density in urban areas?"

        result = await analyze(minimal_test_image, question, AnalysisMode.RAG_ADVANCED)

        # Verify response structure
        assert result.mode == AnalysisMode.RAG_ADVANCED
        assert result.vision_features is not None
        assert len(result.answer) > 0

        # Should have retrieved context
        assert len(result.retrieved_context) > 0

        # Should have GIS data
        assert result.gis_data is not None
        assert result.gis_data.estimated_building_count is not None
        assert result.gis_data.infrastructure_assessment is not None

        # Timing should include GIS
        assert result.reasoning_trace.timing.gis_ms >= 0

    @pytest.mark.asyncio
    async def test_all_modes_same_input(self, minimal_test_image, setup_test_knowledge_base):
        """Test that all three modes work with the same input."""
        question = "What is the settlement pattern?"

        results = {}
        for mode in [AnalysisMode.LLM_ONLY, AnalysisMode.RAG_BASELINE, AnalysisMode.RAG_ADVANCED]:
            result = await analyze(minimal_test_image, question, mode)
            results[mode.value] = result

        # All should complete successfully
        for mode, result in results.items():
            assert len(result.answer) > 0, f"{mode} mode returned empty answer"

        # LLM-Only has no retrieval
        assert len(results["llm_only"].retrieved_context) == 0

        # Both RAG modes have retrieval
        assert len(results["rag_baseline"].retrieved_context) > 0
        assert len(results["rag_advanced"].retrieved_context) > 0

        # Only advanced has GIS
        assert results["rag_baseline"].gis_data is None
        assert results["rag_advanced"].gis_data is not None

    @pytest.mark.asyncio
    async def test_reasoning_trace_completeness(self, minimal_test_image, setup_test_knowledge_base):
        """Test that reasoning trace captures all pipeline steps."""
        result = await analyze(minimal_test_image, "Test question?", AnalysisMode.RAG_BASELINE)

        trace = result.reasoning_trace

        # Should have steps
        assert len(trace.steps) > 0

        # Steps should mention key stages
        steps_text = " ".join(trace.steps).lower()
        assert "vision" in steps_text or "extract" in steps_text
        assert "retrieval" in steps_text or "search" in steps_text or "semantic" in steps_text

        # Timing should be complete
        timing = trace.timing
        assert timing.total_ms > 0
        assert timing.vision_ms > 0
        assert timing.llm_ms > 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_image(self):
        """Test that invalid image is handled gracefully."""
        invalid_base64 = "not-valid-base64-image"

        # Should raise ValueError or handle gracefully
        with pytest.raises((ValueError, Exception)):
            await analyze(invalid_base64, "Test question?", AnalysisMode.LLM_ONLY)


# =============================================================================
# RAG Service Integration Tests
# =============================================================================

class TestRAGServiceIntegration:
    """Test RAG service specifically."""

    @pytest.mark.asyncio
    async def test_document_ingestion_and_retrieval(self, test_documents):
        """Test that ingested documents can be retrieved."""
        # Clear and re-ingest
        chunk_count = await ingest_documents(test_documents)
        assert chunk_count > 0

        # Verify retrieval works
        from services.rag_service import semantic_search

        results = semantic_search("urban planning satellite imagery")
        assert len(results) > 0, "Should retrieve documents"

        for result in results:
            assert len(result["chunk"]) > 0
            assert "source" in result
            assert "score" in result

    def test_retrieval_query_building(self):
        """Test retrieval query enrichment with features."""
        from core.prompt_builder import build_retrieval_query

        question = "Is there urban expansion?"
        features = {
            "urban_pattern": "irregular, informal layout",
            "expansion_signs": "active construction",
            "building_density": "high"
        }

        query = build_retrieval_query(question, features)

        # Query should include question
        assert question in query

        # Query should include relevant features
        assert "urban" in query.lower() or "expansion" in query.lower()

    def test_rrf_merge(self):
        """Test Reciprocal Rank Fusion merge."""
        from services.rag_service import merge_and_rerank

        semantic_results = [
            {"chunk": "Document A about urban planning", "source": "a.txt", "score": 0.9},
            {"chunk": "Document B about settlements", "source": "b.txt", "score": 0.8},
        ]

        keyword_results = [
            {"chunk": "Document A about urban planning", "source": "a.txt", "score": 5.0},
            {"chunk": "Document C about density", "source": "c.txt", "score": 3.0},
        ]

        merged = merge_and_rerank(semantic_results, keyword_results, top_k=5)

        # Should merge without duplication
        assert len(merged) <= 3  # At most 3 unique docs

        # Document A should rank highest (appears in both)
        if len(merged) > 0:
            assert "Document A" in merged[0]["chunk"]

    def test_gis_query(self):
        """Test rule-based GIS enrichment."""
        from services.rag_service import gis_query

        features = {
            "building_density": "high, tightly packed informal structures",
            "road_density": "low, mostly unpaved tracks",
            "urban_pattern": "irregular, no grid layout",
            "vegetation_density": "low, sparse coverage"
        }

        result = gis_query(features)

        assert "estimated_building_count" in result
        assert "infrastructure_assessment" in result
        assert "pattern_classification" in result
        assert "density_metric" in result

        # Based on features, should classify as informal
        assert "informal" in result["pattern_classification"].lower()


# =============================================================================
# Vision Service Integration Tests
# =============================================================================

class TestVisionServiceIntegration:
    """Test vision service feature extraction."""

    @pytest.mark.asyncio
    async def test_vision_feature_extraction(self, minimal_test_image):
        """Test that vision service extracts all 6 features."""
        from services.vision_service import extract_features

        features = await extract_features(minimal_test_image)

        # Should have all 6 expected fields
        expected_fields = [
            "vegetation_density",
            "building_density",
            "road_density",
            "urban_pattern",
            "expansion_signs",
            "illegal_settlement_indicators"
        ]

        for field in expected_fields:
            assert field in features, f"Missing field: {field}"
            assert isinstance(features[field], str)
            assert len(features[field]) > 0


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (deselect with '-m \"not asyncio\"')"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
