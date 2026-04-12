"""
Orchestrator — The brain of the Geo-RAG system.

Coordinates vision, retrieval, and LLM services based on the
requested analysis mode. This is the ONLY file that knows about
all services.

Stateless. Each call to analyze() is independent.
"""

import time
import logging

from api.schemas import (
    AnalysisMode, AnalyzeResponse, VisionFeatures,
    RetrievedChunk, GISData, ReasoningTrace, TimingInfo,
)
from services import vision_service, llm_service, rag_service
from core.prompt_builder import (
    build_prompt_llm_only,
    build_prompt_rag_baseline,
    build_prompt_rag_advanced,
    build_retrieval_query,
)

logger = logging.getLogger(__name__)


async def analyze(image_base64: str, question: str, mode: AnalysisMode) -> AnalyzeResponse:
    """
    Main orchestration function.

    Flow:
        1. Vision extraction (all modes)
        2. Retrieval (RAG modes only)
        3. Prompt construction (mode-specific)
        4. LLM generation
        5. Response assembly

    Returns a fully traced, timed response for evaluation.
    """
    steps = []
    timing = {}
    total_start = time.time()

    # ------------------------------------------------------------------
    # Step 1: Vision Feature Extraction (ALL modes)
    # ------------------------------------------------------------------
    steps.append("1. Extracting visual features from satellite image using Qwen3-VL...")
    t0 = time.time()

    try:
        features_dict = await vision_service.extract_features(image_base64)
    except ConnectionError as e:
        logger.error(f"Vision service unavailable: {e}")
        raise
    except ValueError as e:
        logger.warning(f"Vision parsing partial failure: {e}")
        # Use whatever we got
        features_dict = {
            "vegetation_density": "extraction failed",
            "building_density": "extraction failed",
            "road_density": "extraction failed",
            "urban_pattern": "extraction failed",
            "expansion_signs": "extraction failed",
            "illegal_settlement_indicators": "extraction failed",
        }
        steps.append("   ⚠ Vision extraction partially failed, using fallback values")

    timing["vision_ms"] = int((time.time() - t0) * 1000)
    steps.append(f"   ✓ Extracted 6 features in {timing['vision_ms']}ms")

    vision_features = VisionFeatures(**features_dict)

    # ------------------------------------------------------------------
    # Step 2: Retrieval (mode-dependent)
    # ------------------------------------------------------------------
    retrieved_chunks: list[RetrievedChunk] = []
    gis_data_obj: GISData | None = None
    timing["retrieval_ms"] = 0
    timing["gis_ms"] = 0

    if mode in (AnalysisMode.RAG_BASELINE, AnalysisMode.RAG_ADVANCED):
        # Build enriched retrieval query
        retrieval_query = build_retrieval_query(question, features_dict)
        steps.append(f"2. Built retrieval query: '{retrieval_query[:100]}...'")

        t0 = time.time()

        if mode == AnalysisMode.RAG_BASELINE:
            # Semantic search only
            raw_chunks = rag_service.semantic_search(retrieval_query)
            steps.append(f"   ✓ Semantic search returned {len(raw_chunks)} chunks")

        elif mode == AnalysisMode.RAG_ADVANCED:
            # Hybrid: semantic + keyword + merge
            semantic_results = rag_service.semantic_search(retrieval_query)
            keyword_results = rag_service.keyword_search(retrieval_query)
            raw_chunks = rag_service.merge_and_rerank(semantic_results, keyword_results)
            steps.append(
                f"   ✓ Hybrid retrieval: {len(semantic_results)} semantic + "
                f"{len(keyword_results)} keyword → {len(raw_chunks)} merged"
            )

        timing["retrieval_ms"] = int((time.time() - t0) * 1000)

        # Convert to schema objects
        retrieved_chunks = [
            RetrievedChunk(chunk=c["chunk"], source=c["source"], score=c["score"])
            for c in raw_chunks
        ]

        # GIS enrichment (advanced mode only)
        if mode == AnalysisMode.RAG_ADVANCED:
            t0 = time.time()
            gis_dict = rag_service.gis_query(features_dict)
            gis_data_obj = GISData(**gis_dict)
            timing["gis_ms"] = int((time.time() - t0) * 1000)
            steps.append(f"   ✓ GIS enrichment: {gis_dict.get('pattern_classification', 'N/A')}")

    else:
        steps.append("2. Skipped retrieval (LLM-only mode)")

    # ------------------------------------------------------------------
    # Step 3: Prompt Construction
    # ------------------------------------------------------------------
    chunks_for_prompt = [
        {"chunk": c.chunk, "source": c.source, "score": c.score}
        for c in retrieved_chunks
    ]

    if mode == AnalysisMode.LLM_ONLY:
        prompt = build_prompt_llm_only(question, features_dict)
        steps.append("3. Built LLM-only prompt (features + question)")

    elif mode == AnalysisMode.RAG_BASELINE:
        prompt = build_prompt_rag_baseline(question, features_dict, chunks_for_prompt)
        steps.append("3. Built RAG baseline prompt (features + chunks + question)")

    elif mode == AnalysisMode.RAG_ADVANCED:
        gis_for_prompt = gis_data_obj.model_dump() if gis_data_obj else {}
        prompt = build_prompt_rag_advanced(
            question, features_dict, chunks_for_prompt, gis_for_prompt
        )
        steps.append("3. Built RAG advanced prompt (features + chunks + GIS + question)")

    # ------------------------------------------------------------------
    # Step 4: LLM Generation
    # ------------------------------------------------------------------
    steps.append("4. Generating answer with Gemma 3 4B...")
    t0 = time.time()

    try:
        answer = await llm_service.generate(prompt)
    except ConnectionError as e:
        logger.error(f"LLM service unavailable: {e}")
        raise
    except RuntimeError as e:
        logger.error(f"LLM generation failed: {e}")
        answer = "Error: LLM failed to generate a response. Please try again."

    timing["llm_ms"] = int((time.time() - t0) * 1000)
    steps.append(f"   ✓ Generated {len(answer)} chars in {timing['llm_ms']}ms")

    # ------------------------------------------------------------------
    # Step 5: Assemble Response
    # ------------------------------------------------------------------
    timing["total_ms"] = int((time.time() - total_start) * 1000)
    steps.append(f"5. Total pipeline time: {timing['total_ms']}ms")

    return AnalyzeResponse(
        mode=mode,
        vision_features=vision_features,
        retrieved_context=retrieved_chunks,
        gis_data=gis_data_obj,
        answer=answer,
        reasoning_trace=ReasoningTrace(
            steps=steps,
            timing=TimingInfo(**timing),
        ),
    )
