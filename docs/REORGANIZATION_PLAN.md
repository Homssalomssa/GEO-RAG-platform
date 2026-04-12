# Project Reorganization Plan

## Current Mess
- 12 Python scripts scattered in root
- No clear separation of concerns
- Hard to understand project structure
- Mixed utilities, core app, and data

## Target Structure

```
project-10/
├── app/                          # Core application
│   ├── main.py                   # FastAPI server entry
│   ├── config.py                 # Configuration
│   ├── api/                      # HTTP routes & schemas
│   ├── core/                     # Pipeline orchestration
│   ├── services/                 # Ollama/ChromaDB integration
│   ├── workers/                  # Background tasks
│   └── utils/                    # Helper utilities
│
├── data/                         # All data files
│   ├── knowledge/                # Knowledge documents (text)
│   ├── imagery/                  # Satellite imagery
│   │   ├── timeseries/          # Multi-year collection
│   │   └── single/              # Single year
│   ├── shapefiles/              # Geographic boundaries
│   └── README.md                # Data documentation
│
├── scripts/                      # One-off utilities (not in app)
│   ├── fetch_imagery.py
│   ├── ingest_knowledge.py
│   ├── spatial_setup.py
│   └── README.md                # Scripts documentation
│
├── cache/                        # Persistent cache (auto-created)
│   ├── vision/
│   ├── embeddings/
│   ├── llm_responses/
│   └── metadata/
│
├── tests/                        # Tests
├── docs/                         # Documentation
│   ├── ARCHITECTURE_v0.3.md
│   ├── SETUP.md
│   ├── API.md
│   └── README.md                # Docs index
│
├── frontend/                     # Web UI (moved from root)
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── requirements.txt
├── pytest.ini
└── README.md                     # Project overview
```

## Migration Steps

### Phase 1: Create New Structure
- [ ] Create app/ directory
- [ ] Create data/ directory with subdirs
- [ ] Create scripts/ directory
- [ ] Create docs/ directory

### Phase 2: Move Files
- [ ] Move config.py, main.py → app/
- [ ] Move api/, core/, services/ → app/
- [ ] Move knowledge/, imagery/ → data/
- [ ] Move ingest_*.py, fetch_*.py → scripts/
- [ ] Move all .md files → docs/
- [ ] Move frontend → frontend/

### Phase 3: Update Imports
- [ ] Update import paths in main.py
- [ ] Update imports in all Python files
- [ ] Test that app still runs

### Phase 4: Document
- [ ] Add README.md to each directory
- [ ] Update main documentation
- [ ] List what goes where

## Expected After Reorganization

✅ **Clear structure**: Each directory has one purpose
✅ **Self-documenting**: README.md in each folder explains what it contains
✅ **Maintainable**: Easy to find and modify code
✅ **Scalable**: Room to grow without chaos
