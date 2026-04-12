"""
Extract and enhance metadata with visual features from satellite imagery.

This script analyzes satellite images to extract measurable features:
- Cloud coverage percentage
- Image quality score
- Brightness/contrast metrics
- Vegetation index indicators (simple RGB-based)
- Urban density indicators (simple heuristics from color distribution)

Enhanced metadata is saved alongside original knowledge documents.
"""

import json
from pathlib import Path
import numpy as np
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from image_knowledge_index import IMAGE_KNOWLEDGE_MAP

TIMESERIES_DIR = Path("images-timeseries")
KNOWLEDGE_DIR = Path("knowledge")


def analyze_image(image_path: Path) -> dict:
    """
    Analyze a satellite image and extract visual features.

    Returns:
        Dict with extracted features like brightness, color composition, etc.
    """
    try:
        img = Image.open(image_path)
        img_array = np.array(img) / 255.0  # Normalize to 0-1

        # Image dimensions
        height, width = img_array.shape[:2]

        # Calculate brightness (mean luminance)
        brightness = float(np.mean(img_array))

        # Calculate contrast (standard deviation)
        contrast = float(np.std(img_array))

        # RGB channels
        if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            red = img_array[:, :, 0]
            green = img_array[:, :, 1]
            blue = img_array[:, :, 2]

            # Vegetation indicator (simple: high G, low R+B)
            vegetation_index = float(np.mean(green - (red + blue) / 2))

            # Urban/Built-up indicator (greyscale-ish, moderate values)
            grey = np.mean(img_array[:, :, :3], axis=2)
            water_indicator = float(np.mean(blue - green))  # Water has high blue
            urban_indicator = float(np.std(grey))  # Varied colors = developed area

            # Color balance
            red_mean = float(np.mean(red))
            green_mean = float(np.mean(green))
            blue_mean = float(np.mean(blue))
        else:
            vegetation_index = 0.0
            water_indicator = 0.0
            urban_indicator = float(np.std(img_array))
            red_mean = green_mean = blue_mean = brightness

        return {
            "resolution": [width, height],
            "brightness": round(brightness, 3),
            "contrast": round(contrast, 3),
            "vegetation_index": round(vegetation_index, 3),
            "water_indicator": round(water_indicator, 3),
            "urban_indicator": round(urban_indicator, 3),
            "color_composition": {
                "red": round(red_mean, 3),
                "green": round(green_mean, 3),
                "blue": round(blue_mean, 3)
            },
            "quality_score": round((1 - abs(brightness - 0.5)) * contrast, 3)  # Higher contrast + neutral brightness is better
        }
    except Exception as e:
        logger.error(f"Error analyzing {image_path.name}: {e}")
        return {}


def enhance_knowledge_document(adm2_code: str, visual_features_by_year: dict) -> None:
    """
    Enhance knowledge document with visual features.
    Creates an enhanced version with satellite-derived metrics.
    """
    knowledge_path = Path(KNOWLEDGE_DIR) / f"tunisia_adm2_{adm2_code}_*.txt"

    # Find the knowledge document
    matching_files = list(Path(KNOWLEDGE_DIR).glob(f"tunisia_adm2_{adm2_code}_*"))
    if not matching_files:
        logger.warning(f"No knowledge document found for ADM2 {adm2_code}")
        return

    knowledge_file = matching_files[0]
    original_content = knowledge_file.read_text()

    # Create enhanced document
    enhanced_content = original_content
    enhanced_content += "\n\n" + "="*80 + "\n"
    enhanced_content += "SATELLITE-DERIVED VISUAL FEATURES (2020-2025 Time Series)\n"
    enhanced_content += "="*80 + "\n\n"

    # Add year-by-year analysis
    for year in sorted(visual_features_by_year.keys()):
        features = visual_features_by_year[year]
        if not features:
            continue

        enhanced_content += f"\n{year} (Sentinel-2 Satellite Analysis):\n"
        enhanced_content += "-" * 40 + "\n"

        enhanced_content += f"  Brightness: {features.get('brightness', 'N/A')}\n"
        enhanced_content += f"  Contrast: {features.get('contrast', 'N/A')}\n"
        enhanced_content += f"  Vegetation Index: {features.get('vegetation_index', 'N/A')}\n"
        enhanced_content += f"  Urban Density Index: {features.get('urban_indicator', 'N/A')}\n"
        enhanced_content += f"  Water Presence Index: {features.get('water_indicator', 'N/A')}\n"
        enhanced_content += f"  Image Quality Score: {features.get('quality_score', 'N/A')}\n"
        enhanced_content += f"  RGB Composition: R={features.get('color_composition', {}).get('red')} " + \
                           f"G={features.get('color_composition', {}).get('green')} " + \
                           f"B={features.get('color_composition', {}).get('blue')}\n"

    # Save enhanced document with _enhanced suffix
    enhanced_file = knowledge_file.parent / (knowledge_file.stem + "_enhanced.txt")
    enhanced_file.write_text(enhanced_content)
    logger.info(f"Enhanced document saved: {enhanced_file.name}")


def main() -> None:
    """Extract visual features from all satellite images and enhance knowledge base."""
    logger.info("Extracting visual features from satellite imagery...\n")

    total_analyzed = 0

    for adm2_code in IMAGE_KNOWLEDGE_MAP.keys():
        meta = IMAGE_KNOWLEDGE_MAP[adm2_code]
        safe_name = meta["adm2"].lower().replace(" ", "_").replace("/", "_")
        area_dir = TIMESERIES_DIR / f"{adm2_code}_{safe_name}"

        logger.info(f"[{adm2_code}] {meta['adm2']}")

        # Collect features by year
        visual_features_by_year = {}

        for image_file in sorted(area_dir.glob("*.png")):
            year = int(image_file.name.split("_")[0])

            features = analyze_image(image_file)

            if features:
                visual_features_by_year[year] = features
                logger.info(f"  {year}: brightness={features.get('brightness')}, quality={features.get('quality_score')}")
                total_analyzed += 1
            else:
                logger.info(f"  {year}: SKIPPED")

        # Enhance knowledge document with extracted features
        enhance_knowledge_document(adm2_code, visual_features_by_year)
        logger.info("")

    logger.info(f"\n[OK] Analysis complete! Processed {total_analyzed} satellite images.")
    logger.info(f"[OK] Enhanced knowledge documents created in {KNOWLEDGE_DIR}/")


if __name__ == "__main__":
    main()
