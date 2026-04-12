"""
Spatial Setup - Fallback: Create synthetic shapefiles for Tunisia ADM2 regions.
When network access to GEE/Natural Earth/OSM is unavailable, generates local boundaries
based on known coordinates for the 5 focus regions.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

try:
    import geopandas as gpd
    import rtree
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import SHAPEFILE_DIR, SHAPEFILE_INDEX_PATH, TUNISIA_REGIONS


# Tunisia region centers with 15km radius circles
# Centers are approximate coordinates for each ADM2 region
# 15km ≈ 0.135 degrees at this latitude
REGION_CENTERS = {
    "39236": {  # Ariana Ville
        "name": "Ariana Ville",
        "center": (10.1750, 36.8000),
    },
    "39237": {  # El Mnihla
        "name": "El Mnihla",
        "center": (10.1750, 36.7700),
    },
    "39238": {  # Ettadhamen
        "name": "Ettadhamen",
        "center": (10.2000, 36.8300),
    },
    "39239": {  # Kalaat El Andalous
        "name": "Kalaat El Andalous",
        "center": (10.1500, 36.7500),
    },
    "39240": {  # Raoued
        "name": "Raoued",
        "center": (10.2400, 36.8100),
    },
}

# 15 km radius in degrees (approximate: 15/111.32 ≈ 0.1347 degrees)
RADIUS_DEGREES = 0.135


def create_synthetic_shapefiles():
    """Create synthetic shapefiles for Tunisia regions using 15km circles."""
    if not GEOPANDAS_AVAILABLE:
        logger.error("GeoPandas required. Install: pip install geopandas shapely rtree")
        return False

    logger.info("Creating synthetic shapefiles for Tunisia ADM2 regions (15km circles)...")

    try:
        from shapely.geometry import Point

        # Create geometries as circles
        features = []
        for adm2_code, region_data in REGION_CENTERS.items():
            lon, lat = region_data["center"]
            # Create circle using buffer (15km ≈ 0.135 degrees at this latitude)
            center_point = Point(lon, lat)
            circle = center_point.buffer(RADIUS_DEGREES)

            features.append({
                "type": "Feature",
                "properties": {
                    "ADM2_CODE": int(adm2_code),
                    "ADM2_NAME": region_data["name"],
                    "ADM0_CODE": 231,  # Tunisia
                    "ADM0_NAME": "Tunisia",
                    "center_lon": lon,
                    "center_lat": lat,
                    "radius_km": 15
                },
                "geometry": circle.__geo_interface__
            })

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features)
        gdf.set_crs("EPSG:4326", inplace=True)

        logger.info(f"Created {len(gdf)} region circles (15km radius)")

        # Save shapefiles
        Path(SHAPEFILE_DIR).mkdir(parents=True, exist_ok=True)

        # Save as GeoJSON
        geojson_path = Path(SHAPEFILE_DIR) / "tunisia_adm2.geojson"
        gdf.to_file(geojson_path, driver='GeoJSON')
        logger.info(f"Saved GeoJSON to {geojson_path}")

        # Save as shapefile
        shp_path = Path(SHAPEFILE_DIR) / "tunisia_adm2.shp"
        gdf.to_file(shp_path)
        logger.info(f"Saved shapefiles to {SHAPEFILE_DIR}")

        # Create spatial index
        logger.info("Creating RTtree spatial index...")
        index_dir = Path(SHAPEFILE_INDEX_PATH)
        index_dir.parent.mkdir(parents=True, exist_ok=True)

        idx = rtree.index.Index(str(index_dir))
        for i, row in gdf.iterrows():
            bounds = row.geometry.bounds
            idx.insert(i, bounds)

        logger.info(f"Spatial index created with {len(gdf)} geometries")

        # Save metadata
        metadata = {
            "source": "Synthetic (offline fallback)",
            "country": "Tunisia",
            "level": "ADM2",
            "regions": TUNISIA_REGIONS,
            "crs": "EPSG:4326",
            "record_count": len(gdf),
            "geometry_type": "circles",
            "radius_km": 15,
            "created_at": datetime.utcnow().isoformat(),
            "note": "Generated using 15km radius circles centered on region coordinates for offline environments"
        }

        metadata_path = Path(SHAPEFILE_DIR) / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")

        logger.info("✓ Spatial setup complete (15km circles)")
        return True

    except Exception as e:
        logger.error(f"Error creating synthetic shapefiles: {e}")
        return False


if __name__ == "__main__":
    success = create_synthetic_shapefiles()
    sys.exit(0 if success else 1)
