"""
Build a real Tunisia (ADM2) knowledge base for ChromaDB.

What it does:
- Authenticates to Google Earth Engine (interactive login if needed).
- Loads real Tunisia admin level-2 divisions (GAUL: ADM2).
- For each division: uses centroid + buffer to compute urban metrics in GEE:
  - NDVI mean from Sentinel-2 Surface Reflectance (cloud masked, QA60)
  - Built-up fraction from ESA WorldCover (class 50)
  - Vegetation fraction from ESA WorldCover (classes 10/20/30)
- Fetches a real Wikipedia summary when available (best-effort).
- Writes one .txt file per division into `knowledge/` for ingestion by `ingest_knowledge.py`.

Usage (example):
  python build_tunisia_knowledge_adm2.py --limit 200 --buffer-km 5 --start-date 2023-01-01 --end-date 2023-12-31
"""

from __future__ import annotations

import argparse
import math
import re
import time
from pathlib import Path
from typing import Any
import os

import httpx

try:
    import ee  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency: earthengine-api. Install with `pip install -r requirements.txt`."
    ) from e


WIKIPEDIA_REST_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL_TMPL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def init_ee(project: str | None = None) -> None:
    """
    Initialize EE.

    If the user hasn’t set a default project, EE can error with:
      "ee.Initialize: no project found. Call with project= ..."

    This script supports passing the project via env var `EE_PROJECT`.
    """
    project = (project or "").strip() or os.getenv("EE_PROJECT", "").strip() or None
    try:
        ee.Initialize(project=project)
    except Exception as e:
        emsg = str(e).lower()
        if "earth engine api has not been used" in emsg or "service_disabled" in emsg:
            raise RuntimeError(
                "Earth Engine API is not enabled for your Google Cloud project.\n\n"
                f"Project: {project}\n"
                "Fix: enable `Google Earth Engine API` here, then wait a few minutes and retry:\n"
                "https://console.developers.google.com/apis/api/earthengine.googleapis.com/overview"
                f"?project={project}\n"
            ) from e
        if "not registered to use earth engine" in emsg:
            raise RuntimeError(
                "Your Google Cloud project is not registered for Earth Engine.\n\n"
                f"Project: {project}\n"
                "Fix: register your project here, then retry:\n"
                "https://console.cloud.google.com/earth-engine/configuration"
                f"?project={project}\n"
            ) from e
        # Interactive OAuth flow (browser login) for the current machine/user.
        ee.Authenticate()
        try:
            ee.Initialize(project=project)
        except Exception as e2:
            msg = str(e2)
            if "no project found" in msg.lower():
                raise RuntimeError(
                    "Earth Engine authenticated, but no GCP project is configured for EE.\n\n"
                    "Fix: set environment variable `EE_PROJECT` to your Google Cloud project ID "
                    "(the Earth Engine/billing project), then re-run this script.\n\n"
                    "Example (PowerShell):\n"
                    "  $env:EE_PROJECT = \"your-project-id\"\n"
                    "  python build_tunisia_knowledge_adm2.py --limit 5\n"
                ) from e2
            raise


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        if math.isfinite(v):
            return v
        return None
    except Exception:
        return None


def classify_ndvi(ndvi: float | None) -> str:
    if ndvi is None:
        return "unknown"
    if ndvi < 0.2:
        return "low"
    if ndvi < 0.4:
        return "medium"
    return "high"


def classify_fraction(frac: float | None) -> str:
    if frac is None:
        return "unknown"
    if frac < 0.1:
        return "low"
    if frac < 0.25:
        return "medium"
    return "high"


def urban_pattern_from_metrics(builtup_frac: float | None, veg_frac: float | None) -> str:
    # Rule-based, meant to align with your prompt builder's "urban_pattern" slot.
    if builtup_frac is None or veg_frac is None:
        return "mixed or indeterminate pattern"

    if builtup_frac >= 0.25 and veg_frac < 0.3:
        return "urban sprawl pattern"
    if builtup_frac >= 0.25 and veg_frac >= 0.3:
        return "planned grid-based urban layout"
    if builtup_frac < 0.1 and veg_frac >= 0.4:
        return "mixed or indeterminate pattern"
    return "mixed or indeterminate pattern"


def fetch_wikipedia_summary(best_query: str, sleep_s: float = 0.2) -> str:
    """
    Best-effort Wikipedia summary fetch:
    1) Search the best matching title.
    2) Pull the REST API summary for that title.

    Returns empty string if nothing is found.
    """
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Search
        resp = client.get(
            WIKIPEDIA_REST_SEARCH_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": best_query,
                "format": "json",
                "srlimit": 1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return ""

        title = search_results[0].get("title", "")
        if not title:
            return ""

        # Summary
        summary_url = WIKIPEDIA_SUMMARY_URL_TMPL.format(title=httpx.utils.quote(title, safe=""))
        sresp = client.get(summary_url)
        sresp.raise_for_status()
        sdata = sresp.json()
        extract = sdata.get("extract", "")

        time.sleep(sleep_s)
        return extract.strip()


def build_division_document(
    *,
    country_name: str,
    adm1_name: str,
    adm2_name: str,
    adm2_code: str,
    lat: float | None,
    lon: float | None,
    ndvi_mean: float | None,
    builtup_frac: float | None,
    veg_frac: float | None,
    start_date: str,
    end_date: str,
    buffer_km: float,
) -> str:
    ndvi_label = classify_ndvi(ndvi_mean)
    builtup_label = classify_fraction(builtup_frac)
    veg_label = classify_fraction(veg_frac)
    urban_pattern = urban_pattern_from_metrics(builtup_frac, veg_frac)

    # These strings are designed to line up with prompt builder expectations.
    features_line = []
    features_line.append(f"- vegetation_density: {veg_label} (veg fraction: {veg_frac if veg_frac is not None else 'N/A'})")
    features_line.append(f"- building_density: {builtup_label} (built-up fraction: {builtup_frac if builtup_frac is not None else 'N/A'})")
    features_line.append(f"- urban_pattern: {urban_pattern}")
    features_line.append("- expansion_signs: derived from built-up vs vegetation fractions (rule-based)")
    features_block = "\n".join(features_line)

    return f"""Tunisia administrative division knowledge document (GAUL ADM2)

Country: {country_name}
Governorate (ADM1): {adm1_name}
Division (ADM2): {adm2_name} (code: {adm2_code})
Coordinates (centroid): lat {lat if lat is not None else 'N/A'}, lon {lon if lon is not None else 'N/A'}

Urban metrics around centroid (buffer: {buffer_km} km) computed in Google Earth Engine:
- NDVI mean (Sentinel-2 SR): {ndvi_mean if ndvi_mean is not None else 'N/A'} (label: {ndvi_label}) [{start_date} to {end_date}]
- Built-up fraction (ESA WorldCover class 50): {builtup_frac if builtup_frac is not None else 'N/A'} (label: {builtup_label})
- Vegetation fraction (ESA WorldCover classes 10/20/30): {veg_frac if veg_frac is not None else 'N/A'} (label: {veg_label})

Interpretation tags (used by RAG retrieval + prompt templates):
{features_block}
"""


def compute_metrics_for_feature(
    *,
    feature: Any,
    buffer_m: float,
    start_date: str,
    end_date: str,
) -> dict[str, float | None]:
    """
    Compute GEE metrics for a single feature using centroid+buffer.
    """
    geom = feature.geometry()
    centroid = geom.centroid(1)
    buffer = centroid.buffer(buffer_m)

    # Sentinel-2 NDVI mean (cloud masked via QA60)
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(buffer)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
    )

    def mask_s2_qa60(img: Any) -> Any:
        qa = img.select("QA60")
        # QA60 bit 10 = opaque clouds; bit 11 = cirrus clouds.
        cloud_mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
        # Reflectance is already scaled; NDVI is ratio-based so scaling isn't critical.
        return img.updateMask(cloud_mask)

    s2_masked = s2.map(mask_s2_qa60)
    ndvi_coll = s2_masked.map(lambda img: img.normalizedDifference(["B8", "B4"]).rename("ndvi"))
    ndvi_mean_img = ndvi_coll.mean().rename("ndvi")

    # WorldCover fractions at 10m
    # Note: in your EE account the correct asset is `ESA/WorldCover/v100/2020`.
    wc = ee.Image("ESA/WorldCover/v100/2020").select("Map")
    builtup = wc.eq(50).rename("builtup")
    veg = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)).rename("veg")
    water = wc.eq(80).rename("water")

    stats_img = ee.Image.cat([ndvi_mean_img, builtup, veg, water])
    stats = stats_img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer,
        scale=10,
        bestEffort=True,
        maxPixels=1e7,
    )

    ndvi_mean = _safe_float(stats.get("ndvi").getInfo())
    builtup_frac = _safe_float(stats.get("builtup").getInfo())
    veg_frac = _safe_float(stats.get("veg").getInfo())

    return {"ndvi_mean": ndvi_mean, "builtup_frac": builtup_frac, "veg_frac": veg_frac}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country-name", default="Tunisia")
    parser.add_argument("--limit", type=int, default=200, help="How many ADM2 units to generate")
    parser.add_argument("--buffer-km", type=float, default=5.0, help="Centroid buffer radius (km)")
    parser.add_argument("--start-date", default="2023-01-01")
    parser.add_argument("--end-date", default="2023-12-31")
    parser.add_argument("--out-dir", default="knowledge", help="Directory to write .txt documents")
    parser.add_argument("--ee-project", default=None, help="GCP Project ID required for Earth Engine initialization")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output .txt files")
    parser.add_argument("--wiki", action="store_true", help="Also fetch Wikipedia summaries (best-effort)")
    args = parser.parse_args()

    out_dir = Path(__file__).parent / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    init_ee(project=args.ee_project)

    # Real admin boundary dataset: GAUL Level 2 (ADM2).
    # Properties typically include: ADM0_NAME, ADM1_NAME, ADM2_NAME, ADM2_CODE.
    fc = ee.FeatureCollection("FAO/GAUL/2015/level2")
    fc = fc.filter(ee.Filter.eq("ADM0_NAME", args.country_name))
    # Sort for more stable ordering.
    fc = fc.sort("ADM2_CODE")

    total = int(fc.size().getInfo())
    if total == 0:
        raise RuntimeError("No GAUL ADM2 features found for the provided country name.")

    limit = min(total, args.limit) if args.limit and args.limit > 0 else total
    print(f"GAUL ADM2 features for {args.country_name}: {total}. Generating: {limit}")

    # Use toList() once per loop; 200 units is manageable for a first run.
    fc_list = fc.toList(limit)
    buffer_m = float(args.buffer_km) * 1000.0

    for i in range(limit):
        f = ee.Feature(fc_list.get(i))
        adm1_name = f.get("ADM1_NAME").getInfo() or ""
        adm2_name = f.get("ADM2_NAME").getInfo() or ""
        adm2_code = str(f.get("ADM2_CODE").getInfo() or "")

        # Centroid coordinates
        centroid = f.geometry().centroid(1)
        coords = centroid.coordinates().getInfo()  # [lon, lat]
        lon = _safe_float(coords[0] if coords else None)
        lat = _safe_float(coords[1] if coords else None)

        print(f"[{i+1}/{limit}] {adm1_name} / {adm2_name} (code {adm2_code})")

        metrics = compute_metrics_for_feature(
            feature=f,
            buffer_m=buffer_m,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        wiki_text = ""
        if args.wiki:
            query = f"{adm2_name} {adm1_name} Tunisia"
            try:
                wiki_text = fetch_wikipedia_summary(query)
            except Exception:
                wiki_text = ""

        doc_text = build_division_document(
            country_name=args.country_name,
            adm1_name=adm1_name,
            adm2_name=adm2_name,
            adm2_code=adm2_code,
            lat=lat,
            lon=lon,
            ndvi_mean=metrics["ndvi_mean"],
            builtup_frac=metrics["builtup_frac"],
            veg_frac=metrics["veg_frac"],
            start_date=args.start_date,
            end_date=args.end_date,
            buffer_km=float(args.buffer_km),
        )

        if wiki_text:
            doc_text += "\nWikipedia summary (best-effort):\n" + wiki_text + "\n"

        filename = f"tunisia_adm2_{_slug(adm2_code)}_{_slug(adm2_name)}.txt"
        out_path = out_dir / filename
        if out_path.exists() and not args.overwrite:
            print(f"  - Skipping existing file: {out_path.name}")
            continue

        out_path.write_text(doc_text, encoding="utf-8")
        # Small pause to avoid hammering both EE and Wikipedia.
        time.sleep(0.1)

    print("✓ Finished generating Tunisia ADM2 knowledge documents.")


if __name__ == "__main__":
    main()

