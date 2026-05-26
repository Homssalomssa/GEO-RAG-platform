# Data Files

This directory contains all data used by Geo-RAG: knowledge documents, satellite imagery, and geographic shapefiles.

## Structure

```
data/
├── knowledge/          # Text documents for RAG knowledge base
│   ├── *.txt          # Domain documents (auto-ingested)
│   └── README.md
│
├── imagery/           # Satellite imagery collection
│   ├── timeseries/    # Multi-year images (2020-2025)
│   │   ├── 39236_ariana_ville/
│   │   ├── 39237_el_mnihla/
│   │   └── ... (5 regions total)
│   ├── single/        # Single-year imagery
│   └── README.md
│
├── shapefiles/        # Geographic boundaries (NEW for v0.3)
│   ├── tunisia_adm2.shp
│   ├── tunisia_adm2.dbf
│   ├── ...
│   └── README.md
│
└── README.md (this file)
```

## Knowledge Documents (legacy archive)
## Primary knowledge base (urban_tiles)

ChromaDB is populated from `urban_tiles/{city}/vectors/all_vectors.json` (104 global city tiles).

```bash
python scripts/ingest_urban_tiles.py --reset
python scripts/verify_knowledge_base.py
```

Legacy Tunisia `.txt` files in `data/knowledge/` are no longer ingested by default.



Source text files ingested into ChromaDB for RAG retrieval.

**Current documents:**

- `urban_planning.txt` — Principles of urban development
- `settlement_patterns.txt` — Urban settlement classification
- `land_use_definitions.txt` — Land use taxonomy
- `tunisia_adm2_*.txt` — Regional administrative knowledge (5 regions)

**How to add more:**

```bash
# 1. Place .txt files in data/knowledge/
# 2. Run ingestion
python scripts/ingest_knowledge.py --glob "data/knowledge/*.txt"
# 3. Verify
python scripts/verify_knowledge_base.py
```

## Imagery

Satellite imagery from Sentinel-2 (Google Earth Engine).

### Time-Series (6 years × 5 regions)

- **Location:** `data/imagery/timeseries/`
- **Coverage:** 2020, 2021, 2022, 2023, 2024, 2025
- **Regions:**
  - 39236 - Ariana Ville
  - 39237 - El Mnihla
  - 39238 - Ettadhamen
  - 39239 - Kalaat El Andalous
  - 39240 - Raoued
- **Resolution:** 2048×2048 pixels
- **Total:** 30 images, ~91 MB

### Single Year (for testing)

- **Location:** `data/imagery/single/`
- **Use:** Quick tests, examples

**How to fetch more:**

```bash
# Single year (2024)
python scripts/fetch_satellite_imagery_gee.py

# Multi-year (2020-2025)
python scripts/fetch_timeseries_imagery_gee.py
```

## Shapefiles (NEW for v0.3)

Geographic boundaries for spatial enrichment of RAG queries.

**Purpose:** When analyzing an image:

1. Detect geographic location (coordinates from image metadata)
2. Query shapefile: "What region is this?"
3. Enrich RAG context with regional knowledge
4. Better retrieval and more accurate answers

**To add:**

```bash
# Download Tunisia ADM2 shapefiles
python scripts/spatial_setup.py

# Creates spatial index for fast lookup
# Auto-loaded on app startup
```

## Focus: Urban Sprawl (v0.3+)

All documents and imagery are now curated for **urban sprawl analysis**:

- Knowledge: Urban expansion, infrastructure, development patterns
- Imagery: Urban growth in Tunisia over 6 years
- Shapefiles: Administrative boundaries and zones
- Vision: Building density, road networks, expansion signs

(Removed: Informal settlement focus)

## Cache

Vision features and retrieval results are cached here automatically.
See `cache/README.md`


