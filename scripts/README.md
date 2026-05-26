# Utility Scripts

This directory contains one-off scripts for data collection, ingestion, validation, and analysis. These are NOT part of the main appâ€”they're utilities to set up and manage data.

## Scripts

### Core Utilities (v0.3)

- **ingest_knowledge.py** â€” Load text documents into ChromaDB

  ```bash
  python scripts/ingest_knowledge.py --glob "data/knowledge/*.txt"
  ```

- **spatial_setup.py** [NEW] â€” Download and index shapefiles for spatial enrichment
  ```bash
  python scripts/spatial_setup.py
  # Downloads Tunisia ADM2 boundaries, creates rtree index
  ```

### Data Collection

- **fetch_satellite_imagery_gee.py** â€” Download single-year Sentinel-2 imagery

  ```bash
  python scripts/fetch_satellite_imagery_gee.py --year 2024
  ```

- **fetch_timeseries_imagery_gee.py** â€” Download 6-year collection (2020-2025)
  ```bash
  python scripts/fetch_timeseries_imagery_gee.py
  # Creates data/imagery/timeseries/ with 30 images
  ```

### Validation & Analysis

- **verify_knowledge_base.py** â€” Check that documents are ingested and accessible

  ```bash
  python scripts/verify_knowledge_base.py
  ```

- **image_knowledge_index.py** â€” Map images to knowledge documents by region

  ```bash
  python scripts/image_knowledge_index.py
  ```

- **summarize_timeseries.py** â€” Statistics and reporting for imagery collection
  ```bash
  python scripts/summarize_timeseries.py
  ```

### Exploration & Setup

- **explore_tunisia_codes.py** â€” Find GAUL ADM2 codes for Tunisia regions

  ```bash
  python scripts/explore_tunisia_codes.py
  ```

- **visualize_imagery_dashboard.py** [Optional] â€” Create interactive visualization

  ```bash
  python scripts/visualize_imagery_dashboard.py
  ```

- **enhance_knowledge_metadata.py** â€” Add metadata to knowledge documents

  ```bash
  python scripts/enhance_knowledge_metadata.py
  ```

- **build_tunisia_knowledge_adm2.py** â€” Build region-specific knowledge
  ```bash
  python scripts/build_tunisia_knowledge_adm2.py
  ```

## Typical Workflow

```bash
# 1. Setup (one time)
python scripts/fetch_timeseries_imagery_gee.py        # Download 30 images
python scripts/ingest_knowledge.py --glob "..."       # Ingest documents
python scripts/spatial_setup.py                       # Create shapefile index
python scripts/verify_knowledge_base.py               # Verify everything

# 2. Analysis (repeated)
python app/main.py                                    # Start server
# ... use web UI or /api/batch endpoint ...
```

## Environment

These scripts assume:

- Google Earth Engine account (`earthengine-api` configured)
- Dependencies in `requirements.txt` installed
- `data/` directory exists

## To Add More Scripts

1. Place new script in `scripts/` directory
2. Document it here (add description + usage)
3. Make it idempotent (can run multiple times safely)
4. Add error handling for missing data

## Context

Unlike `app/`, which runs constantly as the server:

- Scripts are run **_once_** or **_on-demand_**
- They prepare data, not process requests
- Examples: fetch imagery, ingest documents, validate setup

