"""
Central configuration for the Geo-RAG platform.
All external URLs, model names, and tunable parameters live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Ollama Configuration ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Vision model: Cloud-based or local alternative
# Cloud options: Claude API, OpenAI Vision, etc.
# Local fallback: llava:7b (if no cloud API available)
VISION_MODEL = os.getenv("VISION_MODEL", "llava:7b")

# Reasoning model: Gemma 3 1B - Already locally downloaded
# Fast, efficient, excellent for local inference
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:1b")

# --- Cache Configuration (v0.3) ---
CACHE_ENABLED = True
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
CACHE_VISION_EXPIRY_DAYS = None  # Never expire (images don't change)
CACHE_EMBEDDINGS_EXPIRY_DAYS = 7
CACHE_RESPONSES_EXPIRY_DAYS = 30

# --- Spatial Configuration (v0.3) ---
SHAPEFILE_DIR = os.getenv("SHAPEFILE_DIR", "./data/shapefiles")
SHAPEFILE_INDEX_PATH = os.getenv("SHAPEFILE_INDEX_PATH", "./data/shapefiles/rtree_index")
SPATIAL_ENRICHMENT_ENABLED = True

# Tunisia focus regions (ADM2 codes)
TUNISIA_REGIONS = {
    "39236": "Ariana Ville",
    "39237": "El Mnihla",
    "39238": "Ettadhamen",
    "39239": "Kalaat El Andalous",
    "39240": "Raoued"
}

# --- LLM Generation Parameters ---
LLM_TEMPERATURE = 0.3       # Low for analytical consistency
LLM_MAX_TOKENS = 1024       # Enough for thorough answer
OLLAMA_TIMEOUT = 120         # Seconds â€” vision models can be slow

# --- RAG Configuration ---
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME = "geo_knowledge"
# Cities available in urban_tiles knowledge base (folder names)
URBAN_TILE_CITIES = [
    "cairo", "chicago", "dubai", "istanbul", "manhattan", "paris",
    "sao_paulo", "singapore", "sydney", "tokyo", "tunis", "venice",
]

URBAN_TILES_DIR = os.getenv("URBAN_TILES_DIR", "./urban_tiles")

# Embedding model for ChromaDB (runs locally via sentence-transformers)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Retrieval parameters
SEMANTIC_TOP_K = 5
KEYWORD_TOP_K = 3
RRF_K = 60                  # Reciprocal Rank Fusion constant

# --- Image Configuration ---
MAX_IMAGE_SIZE_MB = 10
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/tiff", "image/webp"]

