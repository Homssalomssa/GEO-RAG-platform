"""
Time-Series Satellite Imagery Summary and Statistics

Displays comprehensive stats about the multi-year satellite imagery collection
"""

from pathlib import Path
import json


def summarize_timeseries():
    """Generate summary statistics for time-series imagery."""

    base_dir = Path(__file__).parent / "images-timeseries"

    print("\n" + "="*80)
    print("TIME-SERIES SATELLITE IMAGERY SUMMARY")
    print("="*80)
    print()

    # Overall stats
    all_pngs = list(base_dir.glob("*/*.png"))
    total_size = sum(f.stat().st_size for f in all_pngs) / (1024**2)

    print(f"Dataset Overview:")
    print(f"  Total images:        {len(all_pngs)}")
    print(f"  Total size:          {total_size:.1f} MB")
    print(f"  Image resolution:    2048x2048 pixels (high-res)")
    print(f"  Time period:         2020-2025 (6 years)")
    print(f"  Sample areas:        5 Tunisia ADM2 divisions")
    print()

    print("="*80)
    print("PER-AREA BREAKDOWN")
    print("="*80)
    print()

    # Per-area stats
    areas = sorted([d for d in base_dir.iterdir() if d.is_dir()])
    grand_total_size = 0
    grand_total_images = 0

    for area_dir in areas:
        area_name = area_dir.name
        adm2_code = area_name.split("_")[0]
        friendly_name = "_".join(area_name.split("_")[1:]).replace("_", " ").title()

        pngs = sorted(area_dir.glob("*.png"))
        area_size_mb = sum(f.stat().st_size for f in pngs) / (1024**2)

        print(f"[{adm2_code}] {friendly_name}")
        print(f"  Images:  {len(pngs)} (2020-2025)")
        print(f"  Size:    {area_size_mb:.1f} MB ({area_size_mb/len(pngs):.1f} MB/image)")

        # Show per-year breakdown
        years = {}
        for png in pngs:
            year = png.name.split("_")[0]
            size_kb = png.stat().st_size / 1024
            years[year] = size_kb

        year_str = ", ".join([f"{y}:{s:.0f}KB" for y, s in sorted(years.items())])
        print(f"  Years:   {year_str}")
        print()

        grand_total_size += area_size_mb
        grand_total_images += len(pngs)

    print("="*80)
    print("TOTALS")
    print("="*80)
    print(f"  Grand Total Images:  {grand_total_images}")
    print(f"  Grand Total Size:    {grand_total_size:.1f} MB")
    print(f"  Average per Image:   {(grand_total_size*1024)/grand_total_images:.0f} KB")
    print()

    # Check metadata files
    print("="*80)
    print("METADATA")
    print("="*80)

    metadata_files = list(base_dir.glob("*/metadata.json"))
    print(f"  Area metadata files: {len(metadata_files)}/5")

    summary_file = base_dir / "_metadata_summary.json"
    if summary_file.exists():
        summary = json.loads(summary_file.read_text())
        print(f"  Generated at:        {summary.get('generated_at', 'N/A')}")
        print(f"  Image resolution:    {summary.get('image_resolution', 'N/A')}x{summary.get('image_resolution', 'N/A')}")
        print(f"  Years:               {summary.get('years_fetched', [])}")
    print()

    print("="*80)
    print("USAGE")
    print("="*80)
    print(f"Base directory: {base_dir.resolve()}")
    print()
    print("To access time-series for an area:")
    print("  images-timeseries/39236_ariana_ville/2020_ariana_ville_39236.png")
    print("  images-timeseries/39236_ariana_ville/2021_ariana_ville_39236.png")
    print("  ... (2022-2025)")
    print()


if __name__ == "__main__":
    summarize_timeseries()
