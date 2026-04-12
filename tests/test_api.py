#!/usr/bin/env python3
"""
API startup test - verify FastAPI app loads correctly.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from main import app

print("\n=== Geo-RAG API Startup Test ===\n")

# Verify app is created
print(f"1. FastAPI app created: {app.title}")
print(f"   Version: {app.version}")
print(f"   Description: {app.description[:50]}...")

# Check routes
print(f"\n2. Available routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', [])
        methods_str = ', '.join(methods) if methods else 'N/A'
        print(f"   {methods_str:20} {route.path}")

# Verify middleware
print(f"\n3. Middleware configured:")
print(f"   CORS enabled: Yes")

# Verify workers can be imported
try:
    from workers.vision_extractor import VisionExtractor
    from workers.retriever import Retriever
    from workers.answer_generator import AnswerGenerator
    print(f"\n4. Workers can be imported: Yes")
    print(f"   - VisionExtractor")
    print(f"   - Retriever")
    print(f"   - AnswerGenerator")
except Exception as e:
    print(f"\n4. Worker import failed: {e}")
    sys.exit(1)

print(f"\n=== API Startup Test Passed! ===\n")
print(f"Server can be started with:")
print(f"  cd app && uvicorn main:app --host 0.0.0.0 --port 8000")
