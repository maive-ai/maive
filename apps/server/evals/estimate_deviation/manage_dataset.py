"""Utilities for managing Braintrust datasets.

This script provides commands to:
- Upload YAML label files to Braintrust
- Export Braintrust dataset to YAML files (backup)
- Sync labels between local and Braintrust

Usage:
    # Upload YAML labels to Braintrust dataset
    uv run python -m evals.estimate_deviation.manage_dataset --upload

    # Export Braintrust dataset to YAML files
    uv run python -m evals.estimate_deviation.manage_dataset --export

    # Both operations
    uv run python -m evals.estimate_deviation.manage_dataset --upload --export
"""

import argparse
from pathlib import Path

import braintrust
import yaml

from src.utils.logger import logger


def upload_yaml_labels(yaml_dir: Path, dataset_name: str = "ground-truth-labels"):
    """Upload YAML label files to Braintrust dataset.

    Args:
        yaml_dir: Directory containing YAML label files
        dataset_name: Name of Braintrust dataset to upload to
    """
    logger.info("=" * 60)
    logger.info("UPLOADING YAML LABELS TO BRAINTRUST")
    logger.info("=" * 60)
    logger.info(f"Source directory: {yaml_dir}")
    logger.info(f"Target dataset: {dataset_name}")
    logger.info("")

    # Initialize dataset
    dataset = braintrust.init_dataset(
        project="discrepancy-detection", name=dataset_name
    )

    uploaded_count = 0
    error_count = 0

    # Upload each YAML file
    for yaml_file in sorted(yaml_dir.glob("*.yaml")):
        try:
            logger.info(f"Processing {yaml_file.name}...")

            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            # Validate required fields
            if "input" not in data or "expected" not in data:
                logger.warning(
                    f"  ⚠️  Skipping {yaml_file.name}: missing input or expected"
                )
                continue

            # Insert into dataset
            dataset.insert(
                input=data["input"],
                expected=data["expected"],
                metadata=data.get("metadata", {}),
            )

            uploaded_count += 1
            logger.info(
                f"  ✅ Uploaded {data['input']['uuid'][:8]}... with {len(data['expected']['deviations'])} deviations"
            )

        except Exception as e:
            logger.error(f"  ❌ Failed to upload {yaml_file.name}: {e}")
            error_count += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info("UPLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Successfully uploaded: {uploaded_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 60)


def export_dataset_to_yaml(output_dir: Path, dataset_name: str = "ground-truth-labels"):
    """Export Braintrust dataset to YAML files (backup).

    Args:
        output_dir: Directory to save YAML files to
        dataset_name: Name of Braintrust dataset to export
    """
    logger.info("=" * 60)
    logger.info("EXPORTING BRAINTRUST DATASET TO YAML")
    logger.info("=" * 60)
    logger.info(f"Source dataset: {dataset_name}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize dataset
    dataset = braintrust.init_dataset(
        project="discrepancy-detection", name=dataset_name
    )

    exported_count = 0
    error_count = 0

    # Export each record
    for record in dataset:
        try:
            uuid = record.input.get("uuid", "unknown")
            yaml_path = output_dir / f"{uuid}.yaml"

            logger.info(f"Exporting {uuid[:8]}...")

            with open(yaml_path, "w") as f:
                yaml.dump(
                    {
                        "input": record.input,
                        "expected": record.expected,
                        "metadata": record.metadata or {},
                    },
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )

            exported_count += 1
            logger.info(f"  ✅ Exported to {yaml_path.name}")

        except Exception as e:
            logger.error(f"  ❌ Failed to export record: {e}")
            error_count += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info("EXPORT SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Successfully exported: {exported_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 60)


def main():
    """Main entry point for dataset management CLI."""
    parser = argparse.ArgumentParser(
        description="Manage Braintrust datasets for discrepancy detection evals"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload YAML labels from labels/ directory to Braintrust",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export Braintrust dataset to YAML files in labels/ directory",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="ground-truth-labels",
        help="Name of Braintrust dataset to use",
    )
    parser.add_argument(
        "--labels-dir",
        type=str,
        default="evals/estimate_deviation/labels",
        help="Directory containing YAML label files",
    )

    args = parser.parse_args()

    # Resolve labels directory
    labels_dir = Path(args.labels_dir)

    # Check that at least one operation was specified
    if not args.upload and not args.export:
        parser.error("Must specify at least one operation: --upload or --export")

    # Run operations
    if args.upload:
        upload_yaml_labels(labels_dir, args.dataset_name)

    if args.export:
        export_dataset_to_yaml(labels_dir, args.dataset_name)


if __name__ == "__main__":
    main()
