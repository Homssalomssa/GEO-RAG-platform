"""
End-to-end test with REAL satellite imagery from 2025 for each of the 5 Tunisia areas.

Tests the complete Geo-RAG pipeline:
1. Load real Sentinel-2 satellite image
2. Extract features using vision model
3. Retrieve relevant knowledge from RAG
4. Generate analysis report

Run with: pytest tests/test_end2end_realimages.py -v -s
"""

import pytest
import base64
from pathlib import Path

from services.rag_service import ingest_documents, _get_collection
from core.orchestrator import analyze
from api.schemas import AnalysisMode


# Satellite image paths (using 2025 imagery - most recent)
REAL_SATELLITE_IMAGES = {
    "ariana_ville": "images-timeseries/39236_ariana_ville/2025_ariana_ville_39236.png",
    "el_mnihla": "images-timeseries/39237_el_mnihla/2025_el_mnihla_39237.png",
    "ettadhamen": "images-timeseries/39238_ettadhamen/2025_ettadhamen_39238.png",
    "kalaat_el_andalous": "images-timeseries/39239_kalaat_el_andalous/2025_kalaat_el_andalous_39239.png",
    "raoued": "images-timeseries/39240_raoued/2025_raoued_39240.png",
}


@pytest.fixture(scope="session")
def real_satellite_image_2025_ariana():
    """Load real 2025 Sentinel-2 image for Ariana Ville."""
    image_path = Path(REAL_SATELLITE_IMAGES["ariana_ville"])
    assert image_path.exists(), f"Satellite image not found: {image_path}"

    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@pytest.fixture(scope="session")
def test_documents_enhanced():
    """Load enhanced knowledge base documents with visual features."""
    enhanced_docs_dir = Path("knowledge")
    documents = []

    for doc_file in enhanced_docs_dir.glob("*_enhanced.txt"):
        content = doc_file.read_text()
        documents.append({
            "text": content,
            "source": doc_file.name
        })

    assert len(documents) == 5, "Expected 5 enhanced knowledge documents"
    return documents


@pytest.fixture(scope="session")
def setup_enhanced_knowledge_base(test_documents_enhanced):
    """Setup knowledge base with enhanced documents."""
    import asyncio
    asyncio.run(ingest_documents(test_documents_enhanced))

    collection = _get_collection()
    chunk_count = collection.count()
    print(f"\nEnhanced knowledge base initialized with {chunk_count} chunks (from {len(test_documents_enhanced)} documents)")

    yield chunk_count


class TestEndToEndWithRealImagery:
    """Full end-to-end tests using real satellite imagery."""

    @pytest.mark.asyncio
    async def test_ariana_ville_2025_rag_baseline(
        self, real_satellite_image_2025_ariana, setup_enhanced_knowledge_base
    ):
        """
        Analyze Ariana Ville using 2025 satellite imagery with RAG support.

        This test:
        1. Loads real Sentinel-2 2025 image for Ariana Ville
        2. Extracts satellite features
        3. Retrieves relevant knowledge from enhanced knowledge base
        4. Generates analysis using both vision + RAG
        """
        question = "What are the urban development patterns and building density indicators for this area?"

        result = await analyze(
            real_satellite_image_2025_ariana,
            question,
            AnalysisMode.RAG_BASELINE
        )

        # Verify response structure
        assert result.mode == AnalysisMode.RAG_BASELINE
        assert result.vision_features is not None
        assert len(result.answer) > 0
        assert len(result.retrieved_context) > 0  # RAG should retrieve knowledge

        # Verify vision features were extracted
        assert result.vision_features.building_density is not None
        assert result.vision_features.vegetation_density is not None

        # Print results for inspection
        print(f"\n[Ariana Ville 2025] Question: {question}")
        print(f"[RAG Retrieved {len(result.retrieved_context)} chunks]")
        print(f"[Vision Features] Building: {result.vision_features.building_density}, Veg: {result.vision_features.vegetation_density}")
        print(f"[Answer] {result.answer[:200]}...")

    @pytest.mark.asyncio
    async def test_ariana_ville_2025_rag_advanced(
        self, real_satellite_image_2025_ariana, setup_enhanced_knowledge_base
    ):
        """Test advanced RAG mode with GIS features."""
        question = "Analyze urban expansion and expansion signs in this satellite image."

        result = await analyze(
            real_satellite_image_2025_ariana,
            question,
            AnalysisMode.RAG_ADVANCED
        )

        # Advanced mode should include GIS data
        assert result.gis_data is not None or len(result.retrieved_context) > 0

        print(f"\n[Advanced RAG] Retrieved {len(result.retrieved_context)} context chunks")
        if result.gis_data:
            print(f"[GIS Features] {result.gis_data}")

    @pytest.mark.asyncio
    async def test_vision_only_all_areas(self, setup_enhanced_knowledge_base):
        """Test vision-only analysis for all 5 areas using 2025 imagery."""
        test_results = []

        for area_name, image_path in REAL_SATELLITE_IMAGES.items():
            path = Path(image_path)
            assert path.exists(), f"Missing image: {path}"

            with open(path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Simple question for vision-only analysis
            question = "Describe the building density and vegetation coverage visible in this image."

            result = await analyze(image_b64, question, AnalysisMode.LLM_ONLY)

            test_results.append({
                "area": area_name,
                "building_density": result.vision_features.building_density,
                "vegetation_density": result.vision_features.vegetation_density,
                "answer_length": len(result.answer)
            })

        # Print summary
        print("\n[Vision-Only Analysis - All 5 Areas (2025)]")
        print("-" * 60)
        for r in test_results:
            print(f"{r['area']:25} | Building: {r['building_density']:15} | Veg: {r['vegetation_density']}")
        print()

        # All areas should have valid responses
        assert all(r["answer_length"] > 0 for r in test_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
