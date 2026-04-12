"""
Spatial Setup: Download and index shapefiles for Tunisia ADM2 regions.
Fetches geographic boundaries using Google Earth Engine or falls back to OSM/GADM.
Creates RTtree spatial index for fast location lookups during RAG enrichment.
"""

import os
import sys
import json
import tempfile
import shutil
import logging
from pathlib import Path

try:
    import geopandas as gpd
    from shapely.geometry import Point
    import rtree
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path to import app config
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import SHAPEFILE_DIR, SHAPEFILE_INDEX_PATH, TUNISIA_REGIONS


def download_shapefiles_gee():
    """
    Download Tunisia ADM2 boundaries using Google Earth Engine.
    Falls back to alternative methods if GEE is unavailable.
    """
    try:
        import ee
        ee.Initialize()
        logger.info("Google Earth Engine initialized")
        return download_from_gee()
    except Exception as e:
        logger.warning(f"GEE unavailable ({e}), falling back to alternative source...")
        return download_from_alternative()


def download_from_gee():
    """Fetch GEE dataset: FAO/GAUL/2015/level2 for Tunisia ADM2."""
    import ee

    logger.info("Downloading Tunisia ADM2 boundaries from Google Earth Engine...")

    # FAO/GAUL dataset contains administrative boundaries
    # Level 2 = ADM2 (second administrative division)
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level2")

    # Filter for Tunisia (country code TN = 231)
    tunisia = gaul.filter(ee.Filter.eq("ADM0_CODE", 231))

    # Get only our 5 regions of interest
    region_codes = list(TUNISIA_REGIONS.keys())
    region_filter = ee.Filter.inList("ADM2_CODE", [int(code) for code in region_codes])
    regions = tunisia.filter(region_filter)

    logger.info(f"Found {regions.size().getInfo()} regions in GEE")

    # Download as GeoJSON
    geojson_data = regions.getDownloadURL(filetype='geojson', selectors=['ADM2_CODE', 'ADM2_NAME', 'geometry'])

    return geojson_data


def download_from_alternative():
    """
    Fall back to downloading from Natural Earth or OSM.
    Uses GeoDataFrames to fetch and filter administrative boundaries.
    """
    logger.info("Downloading from Natural Earth (ne_10m_admin_2_counties)...")

    if not GEOPANDAS_AVAILABLE:
        logger.error("GeoPandas required. Install: pip install geopandas")
        return None

    # Natural Earth provides high-quality administrative boundaries
    # Download ADM2 (counties/administrative level 2) dataset
    try:
        # Natural Earth 10m resolution ADM2
        ne_url = "https://naciscdn.org/naturalearth/10m/admin/ne_10m_admin_2_counties.zip"

        with tempfile.TemporaryDirectory() as tmpdir:
            import zipfile
            import urllib.request

            logger.info(f"Downloading from {ne_url}...")
            zip_path = os.path.join(tmpdir, "ne_adm2.zip")
            urllib.request.urlretrieve(ne_url, zip_path)

            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            # Load shapefile
            shp_file = os.path.join(tmpdir, "ne_10m_admin_2_counties.shp")
            gdf = gpd.read_file(shp_file)

            # Filter for Tunisia (ADM0_A3 = TUN)
            tunisia = gdf[gdf['ADM0_A3'] == 'TUN'].copy()

            logger.info(f"Found {len(tunisia)} ADM2 regions in Tunisia")

            # Convert to GeoJSON-like format
            return tunisia.to_geo_dict() if hasattr(tunisia, 'to_geo_dict') else None

    except Exception as e:
        logger.warning(f"Natural Earth download failed: {e}")
        logger.info("Trying OSM via Overpass API...")
        return download_from_osm()


def download_from_osm():
    """
    Fetch administrative boundaries from OpenStreetMap via Overpass API.
    Less reliable but doesn't require external libraries.
    """
    logger.info("Downloading from OpenStreetMap Overpass API...")

    try:
        import urllib.request
        import json

        # Overpass query for Tunisia ADM2 boundaries
        overpass_url = "https://overpass-api.de/api/interpreter"

        # Query: get all admin_level=6 (ADM2 equivalent in OSM) in Tunisia
        query = """
        [bbox:-8.6,30.2,11.6,37.6];
        (
          relation["boundary"="administrative"]["admin_level"="6"];
        );
        out geojson;
        """

        data = urllib.parse.urlencode({'data': query})
        req = urllib.request.Request(overpass_url, data=data.encode('utf-8'))

        logger.info("Querying Overpass API (this may take a moment)...")
        with urllib.request.urlopen(req, timeout=60) as response:
            geojson = json.loads(response.read())

        logger.info(f"Retrieved {len(geojson.get('features', []))} features from OSM")
        return geojson

    except Exception as e:
        logger.error(f"OSM Overpass failed: {e}")
        return None


def create_spatial_index(gdf):
    """
    Create RTtree spatial index for fast geometry lookups.
    Enables efficient "point in polygon" queries during analysis.
    """
    if not GEOPANDAS_AVAILABLE:
        logger.error("GeoPandas required for spatial indexing")
        return False

    logger.info("Creating spatial index (RTtree)...")

    try:
        # Create index directory
        index_dir = Path(SHAPEFILE_INDEX_PATH)
        index_dir.parent.mkdir(parents=True, exist_ok=True)

        # Create RTtree spatial index
        idx = rtree.index.Index(str(index_dir))

        for i, row in gdf.iterrows():
            geom = row.geometry
            if geom.is_valid:
                bounds = geom.bounds  # (minx, miny, maxx, maxy)
                idx.insert(i, bounds)

        logger.info(f"Spatial index created with {len(gdf)} geometries")
        return True

    except Exception as e:
        logger.error(f"Failed to create spatial index: {e}")
        return False


def save_shapefiles(gdf):
    """Save shapefiles and metadata to data/shapefiles/."""

    # Create directory
    Path(SHAPEFILE_DIR).mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving shapefiles to {SHAPEFILE_DIR}...")

    try:
        # Save as GeoJSON (more portable than shapefile)
        geojson_path = os.path.join(SHAPEFILE_DIR, "tunisia_adm2.geojson")
        gdf.to_file(geojson_path, driver='GeoJSON')
        logger.info(f"Saved GeoJSON to {geojson_path}")

        # Also save as shapefile
        shp_path = os.path.join(SHAPEFILE_DIR, "tunisia_adm2.shp")
        gdf.to_file(shp_path)
        logger.info(f"Saved shapefiles to {SHAPEFILE_DIR}")

        # Save metadata
        metadata = {
            "source": "Natural Earth / Google Earth Engine",
            "country": "Tunisia",
            "level": "ADM2",
            "regions": TUNISIA_REGIONS,
            "crs": str(gdf.crs),
            "crs_authority": "EPSG:4326",
            "record_count": len(gdf),
            "created_at": Path(geojson_path).stat().st_mtime
        }

        metadata_path = os.path.join(SHAPEFILE_DIR, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")

        return True

    except Exception as e:
        logger.error(f"Error saving shapefiles: {e}")
        return False


def main():
    """Download shapefiles and create spatial index."""

    if not GEOPANDAS_AVAILABLE:
        logger.error("GeoPandas is required. Install with:")
        logger.error("  pip install geopandas shapely rtree fiona")
        return False

    logger.info(f"Setting up spatial data for {len(TUNISIA_REGIONS)} Tunisia regions...")

    # Download shapefiles
    geojson_data = download_shapefiles_gee()

    if not geojson_data:
        logger.error("Failed to download shapefiles from all sources")
        return False

    # Convert to GeoDataFrame
    try:
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        logger.info(f"Loaded {len(gdf)} regions into GeoDataFrame")
    except Exception as e:
        logger.error(f"Error converting to GeoDataFrame: {e}")
        return False

    # Save shapefiles
    if not save_shapefiles(gdf):
        return False

    # Create spatial index
    if not create_spatial_index(gdf):
        logger.warning("Spatial index creation failed, but shapefiles saved")
        return False

    logger.info("✓ Spatial setup complete")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
