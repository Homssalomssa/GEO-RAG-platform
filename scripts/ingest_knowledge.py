"""
Knowledge Base Ingestion Script.

Run this once to populate ChromaDB with the knowledge documents.

Usage:
    python ingest_knowledge.py --glob "tunisia_adm2_*.txt"
"""

import asyncio
import argparse
from pathlib import Path
from services.rag_service import ingest_documents


KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
DEFAULT_GLOB = "tunisia_adm2_*.txt"


async def main():
    """Read matching .txt files from the knowledge directory and ingest them."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"Glob pattern of knowledge docs to ingest (default: {DEFAULT_GLOB!r})",
    )
    args = parser.parse_args()

    documents = []

    for filepath in sorted(KNOWLEDGE_DIR.glob(args.glob)):
        print(f"Reading: {filepath.name}")
        text = filepath.read_text(encoding="utf-8")
        documents.append({
            "text": text,
            "source": filepath.name,
        })

    if not documents:
        print("No documents found in knowledge/ directory.")
        return

    print(f"\nIngesting {len(documents)} documents...")
    count = await asyncio.to_thread(ingest_documents, documents)
    print(f"OK Successfully ingested {count} chunks into ChromaDB")


if __name__ == "__main__":
    asyncio.run(main())
