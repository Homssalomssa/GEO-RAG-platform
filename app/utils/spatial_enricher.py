"""
Spatial Enricher: Query shapefiles to enrich RAG context with geographic information.
Detects image location and finds administrative region for spatial enrichment.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import sys

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    from shapely.geometry import Point
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import SHAPEFILE_DIR, SHAPEFILE_INDEX_PATH, TUNISIA_REGIONS, SPATIAL_ENRICHMENT_ENABLED


class SpatialEnricher:
    """Enriches RAG context with geographic/administrative information."""

    def __init__(self):
        self.shapefile_dir = Path(SHAPEFILE_DIR)
        self.shapefiles_loaded = False
        self.gdf = None
        self._load_shapefiles()

    def _load_shapefiles(self):
        """Load shapefiles into GeoDataFrame."""
        if not SPATIAL_ENRICHMENT_ENABLED:
            logger.info("Spatial enrichment disabled in config")
            return

        if not GEOPANDAS_AVAILABLE:
            logger.warning("GeoPandas not available, spatial enrichment disabled")
            return

        try:
            # Try loading GeoJSON first (more portable)
            geojson_file = self.shapefile_dir / "tunisia_adm2.geojson"
            if geojson_file.exists():
                self.gdf = gpd.read_file(geojson_file)
                logger.info(f"Loaded {len(self.gdf)} regions from GeoJSON")
                self.shapefiles_loaded = True
                return

            # Fall back to shapefile
            shp_file = self.shapefile_dir / "tunisia_adm2.shp"
            if shp_file.exists():
                self.gdf = gpd.read_file(shp_file)
                logger.info(f"Loaded {len(self.gdf)} regions from shapefile")
                self.shapefiles_loaded = True
                return

            logger.warning(f"No shapefiles found in {self.shapefile_dir}")

        except Exception as e:
            logger.error(f"Error loading shapefiles: {e}")

    async def get_region_from_coordinates(self, lon: float, lat: float) -> Optional[Dict[str, str]]:
        """
        Query shapefiles to find administrative region for coordinates.
        Returns region code and name if found.
        """
        if not self.shapefiles_loaded or self.gdf is None:
            return None

        try:
            point = Point(lon, lat)

            # Find region containing point
            for idx, row in self.gdf.iterrows():
                if row.geometry.contains(point):
                    region_code = str(int(row.get('ADM2_CODE', 0)))
                    region_name = row.get('ADM2_NAME', 'Unknown')

                    if region_code in TUNISIA_REGIONS:
                        return {
                            "code": region_code,
                            "name": region_name,
                            "config_name": TUNISIA_REGIONS[region_code]
                        }

            logger.debug(f"Point ({lon}, {lat}) not in any region")
            return None

        except Exception as e:
            logger.error(f"Error querying shapefiles: {e}")
            return None

    async def enrich_rag_context(self, region_info: Dict[str, str]) -> str:
        """
        Build geographic context string to prepend to RAG retrieval.
        Enriches knowledge base queries with regional awareness.
        """
        if not region_info:
            return ""

        context = f"""
Geographic Context:
- Region: {region_info['config_name']} (ADM2 code: {region_info['code']})
- Administrative name: {region_info['name']}

Focus area: Urban sprawl analysis in {region_info['config_name']}, Tunisia
        """.strip()

        return context

    async def extract_image_location(self, image_metadata: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        """
        Extract geographic coordinates from image metadata.
        Handles EXIF GPS data or embedded metadata.
        Returns (longitude, latitude) or None.
        """
        try:
            # Check common metadata fields
            for key in ['gps_longitude', 'longitude', 'lon', 'x']:
                if key in image_metadata:
                    lon = float(image_metadata[key])
                    for key2 in ['gps_latitude', 'latitude', 'lat', 'y']:
                        if key2 in image_metadata:
                            lat = float(image_metadata[key2])
                            return (lon, lat)

            # Check nested structure
            if 'coordinates' in image_metadata:
                coords = image_metadata['coordinates']
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    return (float(coords[0]), float(coords[1]))

            logger.debug("No location metadata found in image")
            return None

        except Exception as e:
            logger.error(f"Error extracting image location: {e}")
            return None

    async def spatial_query_knowledge(self, query: str, region_info: Dict[str, str], knowledge_retriever: Any = None) -> str:
        """
        Enhance knowledge retrieval query with spatial context.
        If retriever provided, can filter by region-specific documents.
        """
        if not region_info:
            return query

        # Enhance query with region context
        enhanced_query = f"{query} [Region context: {region_info['config_name']}, Tunisia]"

        return enhanced_query

    def get_status(self) -> Dict[str, Any]:
        """Get spatial enrichment status."""
        return {
            "enabled": SPATIAL_ENRICHMENT_ENABLED,
            "shapefiles_loaded": self.shapefiles_loaded,
            "region_count": len(self.gdf) if self.gdf is not None else 0,
            "coverage": "Tunisia ADM2" if self.shapefiles_loaded else "None"
        }
