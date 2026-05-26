"""
RAG Service — ChromaDB + BM25 hybrid retrieval.

Handles:
- Document ingestion (chunking + embedding into ChromaDB)
- Semantic search (vector similarity)
- Keyword search (BM25)
- Hybrid merge (Reciprocal Rank Fusion)
- GIS enrichment (rule-based MVP)
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

from config import (
    CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL,
    SEMANTIC_TOP_K, KEYWORD_TOP_K, RRF_K,
)

logger = logging.getLogger(__name__)

# --- Module-level state ---
# Initialized once on first use, not on import (avoids startup crashes).

_chroma_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None
_embedder: Optional[SentenceTransformer] = None
_bm25_index: Optional[BM25Okapi] = None
_bm25_documents: list[dict] = []  # Parallel list for BM25 results


def _get_embedder() -> SentenceTransformer:
    """Lazy-load the embedding model."""
    global _embedder
    if _embedder is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_collection() -> chromadb.Collection:
    """Lazy-load ChromaDB client and collection."""
    global _chroma_client, _collection
    if _collection is None:
        logger.info(f"Connecting to ChromaDB at: {CHROMA_PERSIST_DIR}")
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' has {_collection.count()} documents")
    return _collection




def _reset_module_state():
    global _chroma_client, _collection, _bm25_index, _bm25_documents
    _collection = None
    _bm25_index = None
    _bm25_documents = []


def reset_knowledge_base() -> None:
    global _chroma_client
    _reset_module_state()
    _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    try:
        _chroma_client.delete_collection(CHROMA_COLLECTION_NAME)
        logger.info("Deleted collection")
    except Exception:
        logger.info("Collection did not exist")
    _chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    _reset_module_state()


def _normalize_chroma_metadata(meta: dict) -> dict:
    out = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
        else:
            out[key] = str(value)
    return out

# ---------------------------------------------------------------------
# Document Ingestion
# ---------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    Simple but effective for an MVP.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)
            if break_point > chunk_size * 0.5:  # Only break if past halfway
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if len(c) > 50]  # Drop tiny fragments


def ingest_documents(documents: list[dict], *, skip_chunking: bool = False) -> int:
    """
    Chunk and embed documents into ChromaDB.

    Args:
        documents: List of {"text": "...", "source": "..."} dicts

    Returns:
        Number of chunks ingested
    """
    collection = _get_collection()
    embedder = _get_embedder()
    total_chunks = 0

    for doc in documents:
        text = doc.get("text", "")
        source = doc.get("source", "unknown")
        extra_meta = doc.get("metadata") or {}
        doc_skip = doc.get("skip_chunking", skip_chunking)

        if not text.strip():
            continue

        if doc_skip:
            chunks = [text.strip()]
        else:
            chunks = _chunk_text(text)
        if not chunks:
            continue

        embeddings = embedder.encode(chunks).tolist()

        existing_count = collection.count()
        ids = [f"doc_{existing_count + total_chunks + i}" for i in range(len(chunks))]

        metadatas = []
        for i in range(len(chunks)):
            meta = {"source": source, "chunk_index": i, **extra_meta}
            metadatas.append(_normalize_chroma_metadata(meta))

        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_chunks += len(chunks)
        logger.info(f"Ingested {len(chunks)} chunks from '{source}'")

    _rebuild_bm25_index()

    return total_chunks


def _rebuild_bm25_index():
    """Rebuild the BM25 index from all documents in ChromaDB."""
    global _bm25_index, _bm25_documents

    collection = _get_collection()
    count = collection.count()

    if count == 0:
        _bm25_index = None
        _bm25_documents = []
        return

    # Fetch all documents from ChromaDB
    results = collection.get(include=["documents", "metadatas"])
    _bm25_documents = [
        {"chunk": doc, "source": meta.get("source", "unknown")}
        for doc, meta in zip(results["documents"], results["metadatas"])
    ]

    # Tokenize for BM25
    tokenized = [doc["chunk"].lower().split() for doc in _bm25_documents]
    _bm25_index = BM25Okapi(tokenized)
    logger.info(f"BM25 index rebuilt with {len(_bm25_documents)} documents")


# ---------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------

def semantic_search(query: str, top_k: int = None, city: str = None) -> list[dict]:
    """
    Vector similarity search in ChromaDB.

    Returns list of {"chunk": ..., "source": ..., "score": ...}
    """
    top_k = top_k or SEMANTIC_TOP_K
    collection = _get_collection()

    if collection.count() == 0:
        logger.warning("ChromaDB is empty, returning no results")
        return []

    embedder = _get_embedder()
    query_embedding = embedder.encode([query]).tolist()

    where = {"city": city} if city else None
    query_kwargs = {
        "query_embeddings": query_embedding,
        "n_results": min(top_k, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where
    results = collection.query(**query_kwargs)

    chunks = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "chunk": doc,
            "source": meta.get("source", "unknown"),
            "score": round(1 - distance, 4)  # Convert distance to similarity
        })

    return chunks


def keyword_search(query: str, top_k: int = None, city: str = None) -> list[dict]:
    """
    BM25 keyword search over all ingested documents.

    Returns list of {"chunk": ..., "source": ..., "score": ...}
    """
    top_k = top_k or KEYWORD_TOP_K

    if _bm25_index is None or not _bm25_documents:
        # Try rebuilding if empty
        _rebuild_bm25_index()
        if _bm25_index is None:
            logger.warning("BM25 index is empty, returning no results")
            return []

    tokenized_query = query.lower().split()
    scores = _bm25_index.get_scores(tokenized_query)

    # Get top-k indices sorted by score
    scored_indices = sorted(
        enumerate(scores), key=lambda x: x[1], reverse=True
    )[:top_k]

    prefix = f"urban_tiles/{city}/" if city else None
    results = []
    for idx, score in scored_indices:
        if score <= 0:
            continue
        source = _bm25_documents[idx]["source"]
        if prefix and not source.startswith(prefix):
            continue
        results.append({
            "chunk": _bm25_documents[idx]["chunk"],
            "source": source,
            "score": round(float(score), 4),
        })
        if len(results) >= top_k:
            break

    return results


def merge_and_rerank(
    semantic_results: list[dict],
    keyword_results: list[dict],
    top_k: int = None
) -> list[dict]:
    """
    Reciprocal Rank Fusion (RRF) of semantic + keyword results.

    RRF_score(doc) = sum(1 / (k + rank)) for each list containing the doc.

    Returns deduplicated, reranked list.
    """
    top_k = top_k or SEMANTIC_TOP_K

    # Build RRF scores keyed by chunk text (simple dedup)
    rrf_scores: dict[str, dict] = {}

    for rank, item in enumerate(semantic_results):
        key = item["chunk"][:100]  # Use first 100 chars as key
        if key not in rrf_scores:
            rrf_scores[key] = {"chunk": item["chunk"], "source": item["source"], "score": 0}
        rrf_scores[key]["score"] += 1 / (RRF_K + rank + 1)

    for rank, item in enumerate(keyword_results):
        key = item["chunk"][:100]
        if key not in rrf_scores:
            rrf_scores[key] = {"chunk": item["chunk"], "source": item["source"], "score": 0}
        rrf_scores[key]["score"] += 1 / (RRF_K + rank + 1)

    # Sort by RRF score and return top-k
    merged = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
    return [{"chunk": m["chunk"], "source": m["source"], "score": round(m["score"], 4)} for m in merged[:top_k]]


# ---------------------------------------------------------------------
# GIS Enrichment (Rule-based MVP)
# ---------------------------------------------------------------------

def gis_query(features: dict) -> dict:
    """
    Rule-based GIS enrichment from vision features.

    In production, this would query OpenStreetMap or a GIS database.
    For the MVP, it translates qualitative vision features into
    semi-quantitative assessments.
    """
    building_density = features.get("building_density", "").lower()
    road_density = features.get("road_density", "").lower()
    urban_pattern = features.get("urban_pattern", "").lower()
    vegetation = features.get("vegetation_density", "").lower()

    # Estimate building count category
    if any(w in building_density for w in ["high", "dense", "tightly", "packed"]):
        est_buildings = "high (estimated 50+ structures visible)"
        density_metric = "approximately 30-50 structures per hectare"
    elif any(w in building_density for w in ["medium", "moderate"]):
        est_buildings = "moderate (estimated 20-50 structures visible)"
        density_metric = "approximately 15-30 structures per hectare"
    else:
        est_buildings = "low (estimated <20 structures visible)"
        density_metric = "approximately <15 structures per hectare"

    # Infrastructure assessment
    infra_issues = []
    if any(w in road_density for w in ["unpaved", "dirt", "track", "low"]):
        infra_issues.append("limited paved road network")
    if any(w in urban_pattern for w in ["irregular", "informal", "no grid"]):
        infra_issues.append("no planned street grid detected")
    if any(w in vegetation for w in ["low", "sparse", "minimal"]):
        infra_issues.append("limited green spaces or vegetation buffer")

    infra = "; ".join(infra_issues) if infra_issues else "standard infrastructure patterns observed"

    # Pattern classification
    if "irregular" in urban_pattern or "informal" in urban_pattern:
        pattern_class = "informal/unplanned settlement pattern"
    elif "grid" in urban_pattern:
        pattern_class = "planned grid-based urban layout"
    elif "sprawl" in urban_pattern:
        pattern_class = "urban sprawl pattern"
    else:
        pattern_class = "mixed or indeterminate pattern"

    return {
        "estimated_building_count": est_buildings,
        "infrastructure_assessment": infra,
        "pattern_classification": pattern_class,
        "density_metric": density_metric,
    }


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

def check_health() -> bool:
    """Check if ChromaDB is accessible."""
    try:
        collection = _get_collection()
        _ = collection.count()
        return True
    except Exception:
        return False
