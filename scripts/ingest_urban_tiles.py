"""
Ingest urban_tiles vector metadata into ChromaDB.

Usage (from project root):
    python scripts/ingest_urban_tiles.py --reset
    python scripts/ingest_urban_tiles.py --city cairo --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from config import URBAN_TILES_DIR
from services.rag_service import ingest_documents, reset_knowledge_base, _get_collection

EXPECTED_TILES = 104


def _pct(value: float) -> str:
    return f"{float(value) * 100:.1f}%"


def build_tile_text(city: str, record: dict) -> str:
    bbox = record.get("bbox", [])
    lulc = record.get("lulc_stats", {})
    urban = record.get("urban_features", {})
    bbox_str = ", ".join(f"{v:.4f}" for v in bbox) if bbox else "unknown"
    header = (
        f"City: {city} | Tile: {record.get('region_id', 'unknown')} | BBox: [{bbox_str}]\n"
        f"Land cover: built_up={_pct(lulc.get('built_up', 0))}, "
        f"vegetation={_pct(lulc.get('vegetation', 0))}, water={_pct(lulc.get('water', 0))}\n"
        f"Urban: building_density={urban.get('building_density', 'unknown')}, "
        f"road_pattern={urban.get('road_pattern', 'unknown')}, "
        f"avg_building_size={urban.get('avg_building_size', 'unknown')}\n"
        "---\n"
    )
    return header + record.get("text_description", "").strip()


def resolve_image_path(record: dict, city_dir: Path) -> Path | None:
    raw = record.get("image_path", "")
    if not raw:
        return None
    name = Path(raw.replace("\\", "/")).name
    stem = Path(name).stem
    for ext in (".tif", ".jpg", ".tiff"):
        candidate = city_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def load_documents(city_filter: str | None = None) -> list[dict]:
    tiles_root = Path(URBAN_TILES_DIR)
    if not tiles_root.is_absolute():
        tiles_root = ROOT / tiles_root
    documents = []
    cities = sorted(p.name for p in tiles_root.iterdir() if p.is_dir())
    if city_filter:
        cities = [c for c in cities if c == city_filter]
        if not cities:
            raise SystemExit(f"City not found: {city_filter}")
    for city in cities:
        vectors_path = tiles_root / city / "vectors" / "all_vectors.json"
        if not vectors_path.exists():
            print(f"SKIP {city}: no all_vectors.json")
            continue
        records = json.loads(vectors_path.read_text(encoding="utf-8"))
        city_dir = tiles_root / city
        for record in records:
            region_id = record.get("region_id", "unknown")
            image = resolve_image_path(record, city_dir)
            if image is None:
                print(f"WARN missing image for {city}/{region_id}")
            rel_image = str(image.relative_to(ROOT)).replace("\\", "/") if image else ""
            lulc = record.get("lulc_stats", {})
            urban = record.get("urban_features", {})
            documents.append({
                "text": build_tile_text(city, record),
                "source": f"urban_tiles/{city}/{region_id}",
                "skip_chunking": True,
                "metadata": {
                    "city": city,
                    "region_id": region_id,
                    "image_path": rel_image,
                    "bbox": json.dumps(record.get("bbox", [])),
                    "built_up": float(lulc.get("built_up", 0)),
                    "vegetation": float(lulc.get("vegetation", 0)),
                    "water": float(lulc.get("water", 0)),
                    "building_density": str(urban.get("building_density", "")),
                    "road_pattern": str(urban.get("road_pattern", "")),
                },
            })
    return documents


def main():
    parser = argparse.ArgumentParser(description="Ingest urban_tiles into ChromaDB")
    parser.add_argument("--reset", action="store_true", help="Wipe geo_knowledge before ingest")
    parser.add_argument("--city", help="Ingest only this city folder")
    parser.add_argument("--dry-run", action="store_true", help="Build docs without writing to Chroma")
    args = parser.parse_args()
    documents = load_documents(args.city)
    print(f"Prepared {len(documents)} tile documents")
    if args.dry_run:
        for doc in documents[:3]:
            print(f"  {doc['source']} ({len(doc['text'])} chars)")
        return
    if args.reset:
        print("Resetting knowledge base...")
        reset_knowledge_base()
    count = ingest_documents(documents, skip_chunking=True)
    total = _get_collection().count()
    print(f"Ingested {count} chunks; collection count={total}")
    if not args.city and total != EXPECTED_TILES:
        print(f"WARN expected {EXPECTED_TILES} chunks, got {total}")


if __name__ == "__main__":
    main()
