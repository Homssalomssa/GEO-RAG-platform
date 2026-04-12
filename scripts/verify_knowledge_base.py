"""
Verify that satellite images and knowledge documents are complete and properly paired.
"""

from pathlib import Path
from image_knowledge_index import IMAGE_KNOWLEDGE_MAP


def verify_knowledge_base() -> None:
    """Verify all images and knowledge documents exist."""
    project_root = Path(__file__).parent

    print("=" * 70)
    print("KNOWLEDGE BASE VERIFICATION REPORT")
    print("=" * 70)
    print()

    all_ok = True

    for adm2_code, metadata in IMAGE_KNOWLEDGE_MAP.items():
        image_path = project_root / metadata["image"]
        knowledge_path = project_root / metadata["knowledge"]

        image_exists = image_path.exists()
        knowledge_exists = knowledge_path.exists()

        image_status = "[OK]" if image_exists else "[MISSING]"
        knowledge_status = "[OK]" if knowledge_exists else "[MISSING]"

        if not image_exists or not knowledge_exists:
            all_ok = False

        print(f"ADM2: {adm2_code} ({metadata['adm2']})")
        print(f"  Satellite Image:   {image_status} {metadata['image']}")
        if image_exists:
            size_mb = image_path.stat().st_size / (1024 * 1024)
            print(f"                     Size: {size_mb:.2f} MB")
        print(f"  Knowledge Doc:     {knowledge_status} {metadata['knowledge']}")
        if knowledge_exists:
            size_kb = knowledge_path.stat().st_size / 1024
            lines = len(knowledge_path.read_text().splitlines())
            print(f"                     Size: {size_kb:.1f} KB ({lines} lines)")
        print()

    print("=" * 70)
    if all_ok:
        print("STATUS: ALL FILES PRESENT AND VERIFIED")
    else:
        print("STATUS: SOME FILES MISSING - PLEASE RUN SETUP SCRIPTS")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  Total ADM2 areas: {len(IMAGE_KNOWLEDGE_MAP)}")
    print(f"  Total satellite images: {sum(1 for code in IMAGE_KNOWLEDGE_MAP if (project_root / IMAGE_KNOWLEDGE_MAP[code]['image']).exists())}")
    print(f"  Total knowledge documents: {sum(1 for code in IMAGE_KNOWLEDGE_MAP if (project_root / IMAGE_KNOWLEDGE_MAP[code]['knowledge']).exists())}")


if __name__ == "__main__":
    verify_knowledge_base()
