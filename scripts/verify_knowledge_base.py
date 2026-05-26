"""Verify urban_tiles knowledge base in ChromaDB."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from services.rag_service import _get_collection, semantic_search

EXPECTED = 104
CITIES = [
    "cairo", "chicago", "dubai", "istanbul", "manhattan", "paris",
    "sao_paulo", "singapore", "sydney", "tokyo", "tunis", "venice",
]


def main():
    print("=" * 70)
    print("URBAN TILES KNOWLEDGE BASE VERIFICATION")
    print("=" * 70)
    collection = _get_collection()
    count = collection.count()
    ok = count == EXPECTED
    print(f"ChromaDB chunks: {count} (expected {EXPECTED}) -> {'OK' if ok else 'FAIL'}")
    results = collection.get(include=["metadatas"])
    sources = [m.get("source", "") for m in results["metadatas"]]
    for city in CITIES:
        n = sum(1 for s in sources if s.startswith(f"urban_tiles/{city}/"))
        print(f"  {city}: {n} tiles")
    sample = semantic_search("high built-up organic road network cairo")
    if sample:
        print(f"Sample search top source: {sample[0]['source']} (score {sample[0]['score']})")
        ok = ok and sample[0]["source"].startswith("urban_tiles/")
    else:
        print("Sample search: no results")
        ok = False
    print("=" * 70)
    print("STATUS:", "PASS" if ok else "FAIL — run: python scripts/ingest_urban_tiles.py --reset")
    print("=" * 70)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
