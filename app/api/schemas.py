"""
Pydantic schemas for API request/response validation.
These define the data contracts between frontend and backend.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# --- Enums ---

class AnalysisMode(str, Enum):
    """The 3 evaluation modes for academic comparison."""
    LLM_ONLY = "llm_only"
    RAG_BASELINE = "rag_baseline"
    RAG_ADVANCED = "rag_advanced"


# --- Request Schemas ---

class AnalyzeRequest(BaseModel):
    """Main analysis request. Image is sent as base64."""
    image_base64: str = Field(..., description="Base64-encoded satellite image")
    question: str = Field(..., max_length=500, description="Natural language question about the image")
    mode: AnalysisMode = Field(default=AnalysisMode.RAG_BASELINE, description="Analysis mode for comparison")


class RAGQueryRequest(BaseModel):
    """Direct RAG query without image (for testing retrieval)."""
    query: str = Field(..., max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class IngestRequest(BaseModel):
    """Document ingestion request."""
    documents: list[dict] = Field(
        ...,
        description="List of {'text': '...', 'source': '...'} dicts"
    )


# --- Response Schemas ---

class VisionFeatures(BaseModel):
    """Structured output from the vision pipeline."""
    vegetation_density: str = ""
    building_density: str = ""
    road_density: str = ""
    urban_pattern: str = ""
    expansion_signs: str = ""
    illegal_settlement_indicators: str = ""


class RetrievedChunk(BaseModel):
    """A single retrieved knowledge chunk."""
    chunk: str
    source: str
    score: float


class GISData(BaseModel):
    """Structured GIS enrichment data."""
    estimated_building_count: str = ""
    infrastructure_assessment: str = ""
    pattern_classification: str = ""
    density_metric: str = ""


class TimingInfo(BaseModel):
    """Latency breakdown for each pipeline step."""
    vision_ms: int = 0
    retrieval_ms: int = 0
    gis_ms: int = 0
    llm_ms: int = 0
    total_ms: int = 0


class ReasoningTrace(BaseModel):
    """Full trace of what the orchestrator did."""
    steps: list[str] = []
    timing: TimingInfo = TimingInfo()


class AnalyzeResponse(BaseModel):
    """Main analysis response with full traceability."""
    mode: AnalysisMode
    vision_features: VisionFeatures
    retrieved_context: list[RetrievedChunk] = []
    gis_data: Optional[GISData] = None
    answer: str
    reasoning_trace: ReasoningTrace


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    ollama_connected: bool
    chroma_connected: bool
    vision_model: str
    llm_model: str
