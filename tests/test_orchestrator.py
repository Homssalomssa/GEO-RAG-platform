"""
Tests for the Prompt Builder.
Verifies prompt structure and retrieval query construction.
"""

import pytest
from core.prompt_builder import (
    build_prompt_llm_only,
    build_prompt_rag_baseline,
    build_prompt_rag_advanced,
    build_retrieval_query,
    format_features,
    format_chunks,
)


SAMPLE_FEATURES = {
    "vegetation_density": "low, approximately 10%",
    "building_density": "high, tightly packed",
    "road_density": "medium, mostly unpaved",
    "urban_pattern": "irregular layout",
    "expansion_signs": "new construction at edges",
    "illegal_settlement_indicators": "informal structures detected",
}

SAMPLE_CHUNKS = [
    {"chunk": "Urban sprawl is characterized by low-density development", "source": "urban.txt", "score": 0.87},
    {"chunk": "Informal settlements lack proper infrastructure", "source": "settlements.txt", "score": 0.82},
]

SAMPLE_GIS = {
    "estimated_building_count": "high (50+ structures)",
    "infrastructure_assessment": "limited paved roads",
    "pattern_classification": "informal settlement",
    "density_metric": "40 structures per hectare",
}


class TestPromptTemplates:
    """Verify each mode produces well-structured prompts."""

    def test_llm_only_contains_features_no_chunks(self):
        prompt = build_prompt_llm_only("Is this expanding?", SAMPLE_FEATURES)
        assert "IMAGE FEATURES" in prompt
        assert "vegetation" in prompt.lower()
        assert "KNOWLEDGE" not in prompt  # Should NOT have RAG context
        assert "GIS" not in prompt

    def test_rag_baseline_contains_features_and_chunks(self):
        prompt = build_prompt_rag_baseline("Is this expanding?", SAMPLE_FEATURES, SAMPLE_CHUNKS)
        assert "IMAGE FEATURES" in prompt
        assert "RELEVANT KNOWLEDGE" in prompt
        assert "urban.txt" in prompt
        assert "GIS" not in prompt  # Baseline should NOT have GIS

    def test_rag_advanced_contains_all_sections(self):
        prompt = build_prompt_rag_advanced("Is this expanding?", SAMPLE_FEATURES, SAMPLE_CHUNKS, SAMPLE_GIS)
        assert "IMAGE FEATURES" in prompt
        assert "RELEVANT KNOWLEDGE" in prompt
        assert "GIS DATA" in prompt
        assert "confidence" in prompt.lower()


class TestRetrievalQueryBuild:
    """Verify retrieval queries are enriched with relevant features."""

    def test_expansion_question_includes_expansion_features(self):
        query = build_retrieval_query("Is there urban expansion?", SAMPLE_FEATURES)
        assert "expansion" in query.lower()
        assert "new construction" in query.lower()  # From expansion_signs

    def test_illegal_question_includes_settlement_features(self):
        query = build_retrieval_query("Are there illegal settlements?", SAMPLE_FEATURES)
        assert "illegal" in query.lower()
        assert "informal" in query.lower()  # From illegal_settlement_indicators

    def test_generic_question_includes_all_features(self):
        query = build_retrieval_query("What do you see?", SAMPLE_FEATURES)
        # Generic question → all features included
        assert "vegetation" in query.lower() or "building" in query.lower()

    def test_query_always_starts_with_question(self):
        query = build_retrieval_query("My question here", SAMPLE_FEATURES)
        assert query.startswith("My question here")


class TestFormatting:
    """Verify formatting functions produce readable output."""

    def test_format_features(self):
        text = format_features(SAMPLE_FEATURES)
        assert "Vegetation Density" in text
        assert "low, approximately 10%" in text

    def test_format_chunks_empty(self):
        text = format_chunks([])
        assert "No relevant knowledge" in text

    def test_format_chunks_with_data(self):
        text = format_chunks(SAMPLE_CHUNKS)
        assert "[1]" in text
        assert "urban.txt" in text
        assert "0.87" in text
