"""
Simple script to clean pricebook_items.json by removing otherVendors field.

Usage:
    uv run python scripts/clean_pricebook.py
"""

import json
from pathlib import Path


def clean_items(items: list[dict]) -> list[dict]:
    """Remove otherVendors field from items."""
    cleaned = []
    for item in items:
        cleaned_item = {k: v for k, v in item.items() if k != "otherVendors"}
        cleaned.append(cleaned_item)
    return cleaned


def main():
    """Clean the pricebook items file."""
    # Use evals output directory since that's where the file is
    input_file = Path("evals/estimate_deviation/output/pricebook_items.json")
    output_file = Path("evals/estimate_deviation/output/pricebook_items_cleaned.json")

    print(f"Loading {input_file}...")
    with open(input_file, "r") as f:
        data = json.load(f)

    original_size = input_file.stat().st_size / (1024 * 1024)
    print(f"  Original file size: {original_size:.2f} MB")

    print("\nCleaning items...")
    if "materials" in data:
        data["materials"] = clean_items(data["materials"])
        print(f"  Cleaned {len(data['materials'])} materials")

    if "services" in data:
        data["services"] = clean_items(data["services"])
        print(f"  Cleaned {len(data['services'])} services")

    if "equipment" in data:
        data["equipment"] = clean_items(data["equipment"])
        print(f"  Cleaned {len(data['equipment'])} equipment")

    print(f"\nWriting to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    new_size = output_file.stat().st_size / (1024 * 1024)
    savings = ((original_size - new_size) / original_size) * 100

    print(f"  New file size: {new_size:.2f} MB")
    print(f"  Size reduction: {savings:.1f}%")
    print(f"\n✓ Cleaned pricebook saved to {output_file}")


if __name__ == "__main__":
    main()
