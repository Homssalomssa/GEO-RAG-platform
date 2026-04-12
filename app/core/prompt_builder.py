"""
Prompt Builder — Constructs prompts for each analysis mode.

This is isolated from the orchestrator because:
1. Prompts are the most important thing for academic evaluation
2. They need to be easy to inspect, modify, and version
3. Each mode has a different prompt structure
"""


def format_features(features: dict) -> str:
    """Format vision features as a readable block for prompt injection."""
    lines = []
    labels = {
        "vegetation_density": "Vegetation Density",
        "building_density": "Building Density",
        "road_density": "Road Network",
        "urban_pattern": "Urban Pattern",
        "expansion_signs": "Expansion Signs",
        "illegal_settlement_indicators": "Illegal Settlement Indicators",
    }
    for key, label in labels.items():
        value = features.get(key, "not detected")
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def format_chunks(chunks: list[dict]) -> str:
    """Format retrieved knowledge chunks for prompt injection."""
    if not chunks:
        return "No relevant knowledge retrieved."

    lines = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown")
        text = chunk.get("chunk", "")
        score = chunk.get("score", 0)
        lines.append(f"[{i}] (source: {source}, relevance: {score:.2f})\n{text}")
    return "\n\n".join(lines)


def format_gis(gis_data: dict) -> str:
    """Format GIS enrichment data for prompt injection."""
    if not gis_data:
        return "No GIS data available."

    labels = {
        "estimated_building_count": "Estimated Building Count",
        "infrastructure_assessment": "Infrastructure Assessment",
        "pattern_classification": "Settlement Pattern Classification",
        "density_metric": "Density Metric",
    }
    lines = []
    for key, label in labels.items():
        value = gis_data.get(key, "N/A")
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


# -----------------------------------------------------------------
# Prompt Templates — One per mode
# -----------------------------------------------------------------

def build_prompt_llm_only(question: str, features: dict) -> str:
    """
    Mode: LLM Only
    Input: vision features + question
    No external knowledge.
    """
    features_text = format_features(features)

    return f"""You are an urban planning analyst specializing in satellite imagery interpretation.

Analyze the following features extracted from a satellite image and answer the question.
Base your analysis ONLY on the provided image features. Do not speculate beyond what the features indicate.

=== IMAGE FEATURES ===
{features_text}

=== QUESTION ===
{question}

Provide a clear, evidence-based answer. Reference specific features from the analysis above. Structure your response with:
1. Direct answer to the question
2. Supporting evidence from the features
3. Any limitations of the analysis"""


def build_prompt_rag_baseline(question: str, features: dict, chunks: list[dict]) -> str:
    """
    Mode: RAG Baseline
    Input: vision features + semantic retrieval + question
    """
    features_text = format_features(features)
    chunks_text = format_chunks(chunks)

    return f"""You are an urban planning analyst with access to domain knowledge.
You analyze satellite imagery features and use retrieved knowledge to provide well-grounded answers.

=== IMAGE FEATURES ===
{features_text}

=== RELEVANT KNOWLEDGE ===
{chunks_text}

=== QUESTION ===
{question}

Provide a clear, evidence-based answer that:
1. References specific features from the image analysis
2. Grounds your reasoning in the retrieved knowledge (cite sources by number, e.g., [1])
3. Clearly distinguishes between what you observe and what the knowledge base says
4. Notes any contradictions between observed features and retrieved knowledge"""


def build_prompt_rag_advanced(
    question: str,
    features: dict,
    chunks: list[dict],
    gis_data: dict
) -> str:
    """
    Mode: RAG Advanced
    Input: vision features + hybrid retrieval + GIS data + question
    """
    features_text = format_features(features)
    chunks_text = format_chunks(chunks)
    gis_text = format_gis(gis_data)

    return f"""You are an expert urban planning analyst with access to domain knowledge and structured geospatial data.
You provide comprehensive analyses by combining satellite imagery features, retrieved knowledge, and GIS metrics.

=== IMAGE FEATURES ===
{features_text}

=== RELEVANT KNOWLEDGE ===
{chunks_text}

=== GIS DATA ===
{gis_text}

=== QUESTION ===
{question}

Provide a comprehensive, evidence-based answer that:
1. References specific features from the image analysis
2. Grounds your reasoning in the retrieved knowledge (cite sources by number, e.g., [1])
3. Incorporates the GIS data metrics where relevant
4. Clearly distinguishes between:
   - Observed features (from satellite analysis)
   - Knowledge-based reasoning (from retrieved documents)
   - Data-driven metrics (from GIS data)
5. Provides a confidence assessment (low/medium/high) for your conclusions with justification"""


# -----------------------------------------------------------------
# Retrieval Query Builder
# -----------------------------------------------------------------

# Maps question topics to relevant vision feature keys
_TOPIC_FEATURE_MAP = {
    "expand": ["expansion_signs", "building_density", "urban_pattern"],
    "growth": ["expansion_signs", "building_density", "urban_pattern"],
    "sprawl": ["expansion_signs", "building_density", "urban_pattern", "vegetation_density"],
    "illegal": ["illegal_settlement_indicators", "urban_pattern", "road_density"],
    "informal": ["illegal_settlement_indicators", "urban_pattern", "road_density"],
    "settlement": ["illegal_settlement_indicators", "building_density", "urban_pattern"],
    "land use": ["vegetation_density", "building_density", "road_density", "urban_pattern"],
    "vegetation": ["vegetation_density"],
    "green": ["vegetation_density"],
    "road": ["road_density", "urban_pattern"],
    "infrastructure": ["road_density", "urban_pattern", "building_density"],
    "density": ["building_density", "vegetation_density", "road_density"],
}


def build_retrieval_query(question: str, features: dict) -> str:
    """
    Build a retrieval query that combines the question with relevant vision features.

    This is NOT just the raw question — it's enriched with feature context
    for better retrieval precision.
    """
    parts = [question]

    # Find which features are relevant to this question
    question_lower = question.lower()
    relevant_keys = set()

    for topic, keys in _TOPIC_FEATURE_MAP.items():
        if topic in question_lower:
            relevant_keys.update(keys)

    # Default: use all features if no topic matched
    if not relevant_keys:
        relevant_keys = set(features.keys())

    # Add relevant feature values to the query
    for key in relevant_keys:
        value = features.get(key, "")
        if value and value != "not detected":
            # Use the human-readable label
            label = key.replace("_", " ")
            parts.append(f"{label}: {value}")

    return " ".join(parts)


# -----------------------------------------------------------------
# Main Prompt Builder (for v0.3 async workers)
# -----------------------------------------------------------------

def build_prompt(
    question: str,
    vision_features: dict,
    retrieval_results: list,
    spatial_context: str = "",
    mode: str = "rag_baseline"
) -> str:
    """
    Build final prompt for LLM generation.
    Unified interface for all analysis modes.
    """
    if mode == "rag_baseline":
        return build_prompt_rag_baseline(question, vision_features, retrieval_results)
    elif mode == "rag_advanced":
        # Advanced mode with spatial context as GIS data
        gis_data = {
            "region": spatial_context,
            "pattern_classification": "urban sprawl analysis"
        }
        return build_prompt_rag_advanced(question, vision_features, retrieval_results, gis_data)
    else:  # Default to LLM only
        return build_prompt_llm_only(question, vision_features)
