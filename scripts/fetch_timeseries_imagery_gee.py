"""
Fetch HIGH-RESOLUTION satellite imagery time series from Google Earth Engine.

What it does:
- Authenticates to Google Earth Engine.
- For each of the 5 target Tunisia ADM2 areas:
  - Fetches Sentinel-2 imagery for 5 years (2020-2025)
  - Generates 2048x2048 PNG thumbnails (HIGH RESOLUTION)
  - Saves one image per year with metadata
  - Creates a metadata JSON with cloud coverage, dates, etc.

This creates a time-series dataset to track urban development over 5 years.

Usage:
  python fetch_timeseries_imagery_gee.py --out-dir images-timeseries --ee-project YOUR_GCP_PROJECT

Output structure:
  images-timeseries/
    39236_ariana_ville/
      2020_ariana_ville_39236.png
      2021_ariana_ville_39236.png
      ...metadata.json
    39237_el_mnihla/
      ...
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any

try:
    import ee  # type: ignore
except Exception as e:
    raise RuntimeError(
        "Missing dependency: earthengine-api. Install with `pip install -r requirements.txt`."
    ) from e


# The 5 target Tunisia ADM2 codes
TARGET_ADM2_CODES = [
    "39236",  # Ariana Ville
    "39237",  # El Mnihla
    "39238",  # Ettadhamen
    "39239",  # Kalaat El Andalous
    "39240",  # Raoued
]

# Years to fetch (2020-2025)
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

# Sentinel-2 RGB bands
RGB_BANDS = ["B4", "B3", "B2"]  # Red, Green, Blue


def init_ee(project: str | None = None) -> None:
    """Initialize Google Earth Engine."""
    project = (project or "").strip() or os.getenv("EE_PROJECT", "").strip() or None
    try:
        ee.Initialize(project=project)
    except Exception as e:
        emsg = str(e).lower()
        if "earth engine api has not been used" in emsg or "service_disabled" in emsg:
            raise RuntimeError(
                "Earth Engine API is not enabled for your Google Cloud project.\n"
                f"Project: {project}\n"
                "Fix: enable `Google Earth Engine API` here:\n"
                "https://console.developers.google.com/apis/api/earthengine.googleapis.com/overview"
            ) from e
        if "not registered to use earth engine" in emsg:
            raise RuntimeError(
                "Your Google Cloud project is not registered for Earth Engine.\n"
                "Fix: register your project here:\n"
                "https://console.cloud.google.com/earth-engine/configuration"
            ) from e
        # Interactive OAuth flow
        ee.Authenticate()
        try:
            ee.Initialize(project=project)
        except Exception as e2:
            if "no project found" in str(e2).lower():
                raise RuntimeError(
                    "Earth Engine authenticated, but no GCP project configured.\n"
                    "Set environment variable `EE_PROJECT` to your Google Cloud project ID."
                ) from e2
            raise


def fetch_sentinel2_annual_thumbnail(
    geometry: Any,
    year: int,
    adm2_name: str,
    adm2_code: str,
    size: int = 2048,
) -> tuple[bytes | None, dict]:
    """
    Fetch a Sentinel-2 RGB thumbnail for a given year.

    Args:
        geometry: EE geometry
        year: Year to fetch (e.g., 2023)
        adm2_name: Name of the area
        adm2_code: Code of the area
        size: Thumbnail size in pixels (2048 for high resolution)

    Returns:
        (PNG bytes or None, metadata dict with cloud coverage, date, etc.)
    """
    metadata = {
        "year": year,
        "adm2_code": adm2_code,
        "adm2_name": adm2_name,
        "image_size": size,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "cloud_coverage": None,
        "image_count": 0,
        "median_date": None,
        "status": "pending"
    }

    try:
        # Create buffer around centroid for cleaner framing
        centroid = geometry.centroid(1)
        buffer_geom = centroid.buffer(5000)  # 5 km buffer

        # Fetch Sentinel-2 imagery for the entire year with cloud filter
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(buffer_geom)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 70))  # Less than 70% cloud cover
        )

        image_count = int(s2.size().getInfo())
        metadata["image_count"] = image_count

        if image_count == 0:
            print(f"      [WARN] No Sentinel-2 images found for {year}")
            metadata["status"] = "no_images"
            return None, metadata

        # Use the first image with lowest cloud content instead of median
        # This is faster and more reliable than computing median
        s2_sorted = s2.sort("CLOUDY_PIXEL_PERCENTAGE")
        img = ee.Image(s2_sorted.first())

        cloud_percent = float(img.getNumber("CLOUDY_PIXEL_PERCENTAGE").getInfo())
        metadata["cloud_coverage"] = cloud_percent

        # Select RGB bands directly
        rgb = img.select(RGB_BANDS)

        # Generate high-resolution thumbnail
        url = rgb.getThumbURL({
            "min": 0,
            "max": 3000,
            "dimensions": [size, size],
            "region": buffer_geom,
            "format": "png"
        })

        # Download the PNG
        import httpx
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            png_bytes = resp.content
            metadata["status"] = "success"
            metadata["file_size_kb"] = len(png_bytes) / 1024
            return png_bytes, metadata

    except Exception as e:
        print(f"      [ERROR] Error fetching {year}: {str(e)[:60]}")
        metadata["status"] = f"error: {str(e)[:50]}"
        return None, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="images-timeseries", help="Output directory for time-series images")
    parser.add_argument("--ee-project", default=None, help="GCP Project ID for EE")
    parser.add_argument("--size", type=int, default=2048, help="Thumbnail size in pixels")
    args = parser.parse_args()

    # Setup output directory
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {out_dir.resolve()}\n")

    # Initialize Earth Engine
    print("Initializing Google Earth Engine...")
    init_ee(project=args.ee_project)
    print("[OK] Earth Engine initialized\n")

    # Load GAUL ADM2 boundaries for Tunisia
    print("Loading Tunisia ADM2 boundaries from GAUL...")
    fc = (
        ee.FeatureCollection("FAO/GAUL/2015/level2")
        .filter(ee.Filter.eq("ADM0_NAME", "Tunisia"))
        .sort("ADM2_CODE")
    )

    # Process each target ADM2 code
    all_metadata = {}

    for code in TARGET_ADM2_CODES:
        feature_filtered = fc.filter(ee.Filter.eq("ADM2_CODE", int(code)))
        size_check = int(feature_filtered.size().getInfo())

        if size_check == 0:
            print(f"[FAIL] ADM2 code {code} not found in GAUL")
            continue

        feature = ee.Feature(feature_filtered.first())
        adm1_name = feature.get("ADM1_NAME").getInfo() or ""
        adm2_name = feature.get("ADM2_NAME").getInfo() or ""
        adm2_code = str(feature.get("ADM2_CODE").getInfo() or "")
        geometry = feature.geometry()

        safe_name = adm2_name.lower().replace(" ", "_").replace("/", "_")
        area_dir = out_dir / f"{code}_{safe_name}"
        area_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{code}] {adm1_name} / {adm2_name}")

        # Fetch annual imagery for 2020-2025
        area_metadata = {
            "adm2_code": code,
            "adm2_name": adm2_name,
            "adm1_name": adm1_name,
            "yearly_images": []
        }

        for year in YEARS:
            print(f"  Fetching {year}...", end=" ")

            png_bytes, meta = fetch_sentinel2_annual_thumbnail(
                geometry,
                year=year,
                adm2_name=adm2_name,
                adm2_code=adm2_code,
                size=args.size
            )

            if png_bytes:
                filename = f"{year}_{safe_name}_{code}.png"
                img_path = area_dir / filename
                img_path.write_bytes(png_bytes)
                file_size_mb = len(png_bytes) / (1024 * 1024)
                print(f"[SAVED] {file_size_mb:.2f} MB  (cloud: {meta.get('cloud_coverage', 'N/A'):.1f}%)")
                meta["filename"] = filename
                area_metadata["yearly_images"].append(meta)
            else:
                print(f"[SKIPPED]")
                area_metadata["yearly_images"].append(meta)

        # Save metadata JSON for this area
        metadata_file = area_dir / "metadata.json"
        metadata_file.write_text(json.dumps(area_metadata, indent=2))
        print(f"  [OK] Metadata saved to {metadata_file.name}\n")

        all_metadata[code] = area_metadata

    # Save overall metadata
    overall_metadata = {
        "generated_at": datetime.now().isoformat(),
        "total_areas": len(TARGET_ADM2_CODES),
        "image_resolution": args.size,
        "years_fetched": YEARS,
        "areas": all_metadata
    }

    summary_file = out_dir / "_metadata_summary.json"
    summary_file.write_text(json.dumps(overall_metadata, indent=2))

    print("[OK] Time-series satellite imagery fetch complete!")
    print(f"Images saved to: {out_dir.resolve()}")
    print(f"Metadata saved to: {summary_file.name}")


if __name__ == "__main__":
    main()
