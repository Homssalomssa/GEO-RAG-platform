"""
Fetch satellite imagery from Google Earth Engine for 5 Tunisia ADM2 areas.

What it does:
- Authenticates to Google Earth Engine.
- Loads real Tunisia admin level-2 divisions (GAUL: ADM2).
- For each of the 5 target divisions:
  - Fetches Sentinel-2 Surface Reflectance imagery (cloud-masked, QA60)
  - Generates a 256x256 PNG thumbnail centered on the division centroid
  - Saves to `images/` directory

Usage:
  python fetch_satellite_imagery_gee.py --out-dir images --ee-project YOUR_GCP_PROJECT

Target areas (5 Tunisia ADM2):
  - 39236: Ariana Ville
  - 39237: El Mnihla
  - 39238: Ettadhamen
  - 39239: Kalaat El Andalous
  - 39240: Raoued
"""

import argparse
import os
from pathlib import Path
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


def fetch_sentinel2_thumbnail(
    geometry: Any,
    adm2_name: str,
    adm2_code: str,
    size: int = 256,
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
) -> bytes | None:
    """
    Fetch a Sentinel-2 RGB thumbnail for a given geometry.

    Args:
        geometry: EE geometry (e.g., division boundary or centroid buffer)
        adm2_name: Name of the area (for display)
        adm2_code: Code of the area
        size: Thumbnail size in pixels (e.g., 256)
        start_date: Start date for image collection
        end_date: End date for image collection

    Returns:
        PNG bytes or None if no suitable images found
    """
    try:
        # Create buffer around centroid for cleaner framing
        centroid = geometry.centroid(1)
        buffer_geom = centroid.buffer(5000)  # 5 km buffer

        # Fetch Sentinel-2 imagery with cloud masking
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(buffer_geom)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        )

        if s2.size().getInfo() == 0:
            print(f"  [WARN] No Sentinel-2 images found for {adm2_name} (code {adm2_code})")
            return None

        # Select median composite for better cloud removal
        composite = s2.median()

        # Apply simple cloud mask using SCL band (Scene Classification)
        # SCL band: 4=vegetation, 5=water, 6=cloud_low_proba, 7=cloud_med_proba, 8=cloud_high_proba, 9=cirrus, 10=snow
        # Keep only clear pixels (0-5)
        scl = composite.select("SCL")
        cloud_mask = scl.lt(6)  # Everything below 6 is clear (buildings, vegetation, water)
        masked = composite.updateMask(cloud_mask)

        # Select RGB bands and scale for visualization
        rgb = masked.select(RGB_BANDS)

        # Generate thumbnail
        url = rgb.getThumbURL({
            "min": 0,
            "max": 3000,  # Use conservative max for better contrast (S2 surface reflectance)
            "dimensions": [size, size],
            "region": buffer_geom,
            "format": "png"
        })

        # Download the PNG
        import httpx
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content

    except Exception as e:
        print(f"  [ERROR] Error fetching Sentinel-2 for {adm2_name}: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="images", help="Output directory for PNGs")
    parser.add_argument("--ee-project", default=None, help="GCP Project ID for EE")
    parser.add_argument("--size", type=int, default=256, help="Thumbnail size (pixels)")
    parser.add_argument("--start-date", default="2023-01-01", help="Start date for imagery")
    parser.add_argument("--end-date", default="2023-12-31", help="End date for imagery")
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

    # Filter to only target ADM2 codes
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

        print(f"[{code}] {adm1_name} / {adm2_name}")

        # Fetch thumbnail
        geometry = feature.geometry()
        png_bytes = fetch_sentinel2_thumbnail(
            geometry,
            adm2_name=adm2_name,
            adm2_code=adm2_code,
            size=args.size,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        if png_bytes:
            # Sanitize filename
            safe_name = adm2_name.lower().replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_{code}.png"
            out_path = out_dir / filename

            out_path.write_bytes(png_bytes)
            file_size_kb = len(png_bytes) / 1024
            print(f"  [SAVED] {out_path.name} ({file_size_kb:.1f} KB)")
        else:
            print(f"  [FAIL] Failed to fetch imagery for {adm2_name}")

        print()

    print("[OK] Satellite imagery fetch complete!")
    print(f"Images saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
