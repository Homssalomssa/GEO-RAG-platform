"""
Interactive Satellite Imagery Visualization Dashboard.

Displays:
- Time-series satellite images for each area (2020-2025)
- Associated knowledge base metadata
- Image comparisons across years
- Cloud coverage and quality metrics

Usage:
  python visualize_imagery_dashboard.py

Then open http://localhost:8001 in your browser.
"""

import json
from pathlib import Path
from typing import Any
import base64

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Load image-knowledge index
from image_knowledge_index import IMAGE_KNOWLEDGE_MAP

# Define directories
TIMESERIES_DIR = Path("images-timeseries")
KNOWLEDGE_DIR = Path("knowledge")

app = FastAPI(title="Geo-RAG Imagery Dashboard", version="1.0.0")


@app.get("/api/areas", tags=["Data"])
def get_areas() -> dict:
    """Get all 5 Tunisia areas with metadata."""
    areas = []
    for code in IMAGE_KNOWLEDGE_MAP.keys():
        meta = IMAGE_KNOWLEDGE_MAP[code]
        area_dir = TIMESERIES_DIR / f"{code}_{meta['adm2'].lower().replace(' ', '_').replace('/', '_')}"

        images = sorted([f.name for f in area_dir.glob("*.png")])

        areas.append({
            "code": code,
            "adm1": meta["adm1"],
            "adm2": meta["adm2"],
            "image_count": len(images),
            "years": [int(img.split("_")[0]) for img in images if img.endswith(".png")]
        })

    return {"areas": areas, "total": len(areas)}


@app.get("/api/area/{adm2_code}", tags=["Data"])
def get_area_images(adm2_code: str) -> dict:
    """Get all images for a specific area."""
    if adm2_code not in IMAGE_KNOWLEDGE_MAP:
        raise HTTPException(status_code=404, detail="Area not found")

    meta = IMAGE_KNOWLEDGE_MAP[adm2_code]
    safe_name = meta["adm2"].lower().replace(" ", "_").replace("/", "_")
    area_dir = TIMESERIES_DIR / f"{adm2_code}_{safe_name}"

    if not area_dir.exists():
        raise HTTPException(status_code=404, detail="Area directory not found")

    # Load metadata if available
    metadata_file = area_dir / "metadata.json"
    area_metadata = {}
    if metadata_file.exists():
        area_metadata = json.loads(metadata_file.read_text())

    images = sorted([f.name for f in area_dir.glob("*.png")])

    return {
        "code": adm2_code,
        "adm1": meta["adm1"],
        "adm2": meta["adm2"],
        "images": images,
        "metadata": area_metadata,
        "knowledge_doc": meta["knowledge"]
    }


@app.get("/api/image/{adm2_code}/{year}", tags=["Data"])
def get_image_url(adm2_code: str, year: int) -> dict:
    """Get image URL for a specific area and year."""
    if adm2_code not in IMAGE_KNOWLEDGE_MAP:
        raise HTTPException(status_code=404, detail="Area not found")

    meta = IMAGE_KNOWLEDGE_MAP[adm2_code]
    safe_name = meta["adm2"].lower().replace(" ", "_").replace("/", "_")
    area_dir = TIMESERIES_DIR / f"{adm2_code}_{safe_name}"

    image_file = area_dir / f"{year}_{safe_name}_{adm2_code}.png"

    if not image_file.exists():
        raise HTTPException(status_code=404, detail=f"Image for {year} not found")

    return {"url": f"/images/{adm2_code}/{year}"}


@app.get("/images/{adm2_code}/{year}", tags=["Images"])
def serve_image(adm2_code: str, year: int):
    """Serve satellite image file."""
    if adm2_code not in IMAGE_KNOWLEDGE_MAP:
        raise HTTPException(status_code=404, detail="Area not found")

    meta = IMAGE_KNOWLEDGE_MAP[adm2_code]
    safe_name = meta["adm2"].lower().replace(" ", "_").replace("/", "_")
    area_dir = TIMESERIES_DIR / f"{adm2_code}_{safe_name}"

    image_file = area_dir / f"{year}_{safe_name}_{adm2_code}.png"

    if not image_file.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_file, media_type="image/png")


@app.get("/api/knowledge/{adm2_code}", tags=["Data"])
def get_knowledge_document(adm2_code: str) -> dict:
    """Get knowledge base document for an area."""
    if adm2_code not in IMAGE_KNOWLEDGE_MAP:
        raise HTTPException(status_code=404, detail="Area not found")

    knowledge_path = Path(IMAGE_KNOWLEDGE_MAP[adm2_code]["knowledge"])

    if not knowledge_path.exists():
        raise HTTPException(status_code=404, detail="Knowledge document not found")

    content = knowledge_path.read_text()
    return {
        "adm2_code": adm2_code,
        "content": content,
        "file": str(knowledge_path)
    }


@app.get("/", tags=["UI"])
def get_dashboard() -> HTMLResponse:
    """Serve the main dashboard HTML."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Geo-RAG Imagery Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 20px;
                text-align: center;
            }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { font-size: 1.1em; opacity: 0.9; }
            .content { padding: 40px; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-card .value { font-size: 2.5em; font-weight: bold; }
            .stat-card .label { opacity: 0.9; margin-top: 10px; }
            .area-selector {
                margin-bottom: 40px;
            }
            .area-selector label { display: block; margin-bottom: 10px; font-weight: 600; }
            .area-selector select {
                width: 100%;
                padding: 12px;
                border: 2px solid #667eea;
                border-radius: 6px;
                font-size: 1em;
                cursor: pointer;
            }
            .area-display {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 30px;
            }
            .image-section {
                display: flex;
                flex-direction: column;
            }
            .image-container {
                background: #f5f5f5;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                flex: 1;
            }
            .image-container img {
                width: 100%;
                height: auto;
                border-radius: 6px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .year-selector {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 20px;
            }
            .year-btn {
                padding: 8px 16px;
                border: 2px solid #e0e0e0;
                background: white;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
            }
            .year-btn:hover {
                border-color: #667eea;
                color: #667eea;
            }
            .year-btn.active {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            .metadata-section {
                background: #f9f9f9;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .metadata-section h3 {
                margin-bottom: 15px;
                color: #667eea;
            }
            .metadata-item {
                margin-bottom: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid #e0e0e0;
            }
            .metadata-item:last-child {
                border-bottom: none;
            }
            .metadata-label {
                font-weight: 600;
                color: #666;
                font-size: 0.9em;
            }
            .metadata-value {
                color: #333;
                margin-top: 5px;
            }
            .knowledge-section {
                background: #f0f4ff;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #d0d8ff;
            }
            .knowledge-section h4 { color: #667eea; margin-bottom: 10px; }
            .knowledge-text {
                font-size: 0.9em;
                color: #555;
                line-height: 1.6;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .loading { text-align: center; color: #999; font-style: italic; }
            .error { background: #fee; color: #c33; padding: 15px; border-radius: 6px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Geo-RAG Imagery Dashboard</h1>
                <p>Satellite time-series analysis for 5 Tunisia areas (2020-2025)</p>
            </div>

            <div class="content">
                <div class="stats-grid" id="stats"></div>

                <div class="area-selector">
                    <label for="areaSelect">Select Area:</label>
                    <select id="areaSelect" onchange="loadArea()">
                        <option value="">Loading areas...</option>
                    </select>
                </div>

                <div id="areaContent"></div>
            </div>
        </div>

        <script>
            async function loadAreas() {
                try {
                    const resp = await fetch('/api/areas');
                    const data = await resp.json();

                    // Display stats
                    document.getElementById('stats').innerHTML = `
                        <div class="stat-card">
                            <div class="value">${data.total}</div>
                            <div class="label">Tunisia Areas</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">30</div>
                            <div class="label">Satellite Images</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">6</div>
                            <div class="label">Years (2020-2025)</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">2048x2048</div>
                            <div class="label">Resolution (pixels)</div>
                        </div>
                    `;

                    // Populate area selector
                    const select = document.getElementById('areaSelect');
                    select.innerHTML = '';
                    data.areas.forEach(area => {
                        const option = document.createElement('option');
                        option.value = area.code;
                        option.textContent = `${area.adm2} (${area.code})`;
                        select.appendChild(option);
                    });

                    // Load first area by default
                    if (data.areas.length > 0) {
                        select.value = data.areas[0].code;
                        loadArea();
                    }
                } catch (err) {
                    console.error('Error loading areas:', err);
                }
            }

            async function loadArea() {
                const code = document.getElementById('areaSelect').value;
                if (!code) return;

                try {
                    const resp = await fetch(`/api/area/${code}`);
                    if (!resp.ok) throw new Error('Area not found');
                    const data = await resp.json();

                    let html = '<div class="area-display"><div class="image-section">';
                    html += `<h2>${data.adm2} (ADM2 Code: ${code})</h2>`;
                    html += '<div class="image-container"><img id="mainImage" src="" alt="Satellite Image"></div>';
                    html += '<div class="year-selector" id="yearButtons"></div>';
                    html += '</div><div>';
                    html += '<div class="metadata-section">';
                    html += `<h3>Area Information</h3>
                            <div class="metadata-item">
                                <div class="metadata-label">Governorate (ADM1)</div>
                                <div class="metadata-value">${data.adm1}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Division (ADM2)</div>
                                <div class="metadata-value">${data.adm2}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Total Images</div>
                                <div class="metadata-value">${data.images.length}</div>
                            </div>
                            <div class="metadata-item">
                                <div class="metadata-label">Years Coverage</div>
                                <div class="metadata-value">2020-2025</div>
                            </div>`;
                    html += '</div>';

                    // Knowledge base section
                    const knowledgeResp = await fetch(`/api/knowledge/${code}`);
                    if (knowledgeResp.ok) {
                        const knowledge = await knowledgeResp.json();
                        html += `<div class="knowledge-section">
                                <h4>Knowledge Base Document</h4>
                                <div class="knowledge-text">${knowledge.content.substring(0, 500)}...</div>
                            </div>`;
                    }

                    html += '</div></div>';
                    document.getElementById('areaContent').innerHTML = html;

                    // Create year buttons
                    const years = [2020, 2021, 2022, 2023, 2024, 2025];
                    let buttons = '';
                    years.forEach((year, idx) => {
                        buttons += `<button class="year-btn ${idx === 0 ? 'active' : ''}" onclick="loadImage('${code}', ${year})">${year}</button>`;
                    });
                    document.getElementById('yearButtons').innerHTML = buttons;

                    // Load first year image
                    loadImage(code, 2020);
                } catch (err) {
                    document.getElementById('areaContent').innerHTML = `<div class="error">Error loading area: ${err.message}</div>`;
                }
            }

            async function loadImage(code, year) {
                try {
                    const imageUrl = `/images/${code}/${year}`;
                    document.getElementById('mainImage').src = imageUrl;

                    // Update active button
                    document.querySelectorAll('.year-btn').forEach(btn => {
                        btn.classList.remove('active');
                        if (btn.textContent === String(year)) {
                            btn.classList.add('active');
                        }
                    });
                } catch (err) {
                    console.error('Error loading image:', err);
                }
            }

            // Initialize on page load
            window.addEventListener('load', loadAreas);
        </script>
    </body>
    </html>
    """)


if __name__ == "__main__":
    print("\n[INFO] Starting Geo-RAG Imagery Dashboard...")
    print("[INFO] Open browser: http://localhost:8001\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)
