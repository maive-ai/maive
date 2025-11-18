"""Prelabel script for discrepancy detection evaluation.

This script:
- Loads dataset entries from dataset.json by UUID
- Downloads estimate, form, and transcript files from S3
- Runs the discrepancy detection workflow
- Optionally logs to Braintrust if ENABLE_BRAINTRUST_LOGGING=true

Usage:
    esc run <env> -- uv run python -m evals.estimate_deviation.prelabel \
        --uuid <uuid> \
        --level 1

Note: Tracing is now controlled by the ENABLE_BRAINTRUST_LOGGING environment variable.
"""

import argparse
import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import boto3

from src.utils.logger import logger
from src.workflows.discrepancy_detection_v2 import DiscrepancyDetectionV2Workflow


def load_dataset_entry(dataset_path: str, uuid: str) -> dict[str, Any]:
    """Load a specific dataset entry by UUID.

    Args:
        dataset_path: Path to the dataset JSON file
        uuid: UUID of the entry to load

    Returns:
        dict: The dataset entry

    Raises:
        ValueError: If UUID not found in dataset
    """
    logger.info(f"Loading dataset from: {dataset_path}")
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    for entry in dataset:
        if entry.get("uuid") == uuid:
            logger.info(f"✅ Found dataset entry for UUID: {uuid}")
            return entry

    raise ValueError(f"UUID {uuid} not found in dataset")


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """Parse S3 URI into bucket and key.

    Args:
        s3_uri: S3 URI in format s3://bucket/key

    Returns:
        tuple: (bucket, key)

    Raises:
        ValueError: If URI format is invalid
    """
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI format: {s3_uri}")

    parts = s3_uri[5:].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: {s3_uri}")

    return parts[0], parts[1]


@asynccontextmanager
async def download_from_s3(s3_client, s3_uri: str, suffix: str = ""):
    """Download a file from S3 to a temporary file.

    Args:
        s3_client: boto3 S3 client
        s3_uri: S3 URI in format s3://bucket/key
        suffix: File suffix for the temp file (e.g., '.json', '.m4a')

    Yields:
        str: Path to the downloaded temp file

    Raises:
        Exception: If download fails
    """
    tmp_path = None
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        # Download from S3
        bucket, key = parse_s3_uri(s3_uri)
        logger.info(f"   Downloading {s3_uri}")
        s3_client.download_file(bucket, key, tmp_path)
        logger.info(f"   ✅ Downloaded to {tmp_path}")

        yield tmp_path

    finally:
        # Cleanup
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


async def prelabel_entry(
    uuid: str,
    dataset_path: str,
    level: int,
) -> dict[str, Any]:
    """Run prelabeling on a single dataset entry.

    Args:
        uuid: UUID of the dataset entry
        dataset_path: Path to dataset.json
        level: Maximum deviation class level to include

    Returns:
        dict: Prelabel result with deviations
    """
    s3_client = boto3.client("s3")

    # Load dataset entry
    entry = load_dataset_entry(dataset_path, uuid)

    # Download and parse estimate (required)
    estimate_s3_uri = entry.get("estimate_s3_uri")
    if not estimate_s3_uri:
        raise ValueError("No estimate_s3_uri in dataset entry")

    async with download_from_s3(s3_client, estimate_s3_uri, ".json") as estimate_path:
        with open(estimate_path, "r") as f:
            estimate_data = json.load(f)

    # Download and parse form (optional)
    form_s3_uri = entry.get("form_s3_uri")
    if form_s3_uri:
        async with download_from_s3(s3_client, form_s3_uri, ".json") as form_path:
            with open(form_path, "r") as f:
                form_data = json.load(f)
    else:
        form_data = None

    # Download and parse transcripts (required, use first one)
    rilla_transcripts_s3_uri = entry.get("rilla_transcripts_s3_uri", [])
    if not rilla_transcripts_s3_uri:
        raise ValueError("No rilla_transcripts_s3_uri in dataset entry")

    async with download_from_s3(
        s3_client, rilla_transcripts_s3_uri[0], ".json"
    ) as transcript_path:
        with open(transcript_path, "r") as f:
            transcript_data = json.load(f)

    # Create workflow and run analysis
    workflow = DiscrepancyDetectionV2Workflow(level=level)

    # Write transcript to temp file for workflow
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_transcript:
        json.dump(transcript_data, temp_transcript)
        temp_transcript_path = temp_transcript.name

    try:
        deviations = await workflow.run(
            estimate_data=estimate_data,
            form_data=form_data,
            audio_path=None,
            transcript_path=temp_transcript_path,
        )
    finally:
        # Clean up temp file
        Path(temp_transcript_path).unlink(missing_ok=True)

    # Optionally log to Braintrust if enabled
    workflow.log_workflow_execution(
        estimate_data=estimate_data,
        form_data=form_data,
        transcript_data=transcript_data,
        deviations=deviations,
        metadata={
            "uuid": uuid,
            "project_id": entry["project_id"],
            "job_id": entry["job_id"],
            "estimate_id": entry["estimate_id"],
            "prelabel": True,
            "rilla_links": entry.get("rilla_links", []),
            "project_created_date": entry.get("project_created_date"),
            "estimate_sold_date": entry.get("estimate_sold_date"),
        },
    )

    return {
        "uuid": uuid,
        "deviations": deviations,
    }


async def main():
    """Main entry point for prelabel script."""
    parser = argparse.ArgumentParser(
        description="Prelabel dataset entries for discrepancy detection evaluation"
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="evals/estimate_deviation/dataset.json",
        help="Path to the dataset JSON file",
    )
    parser.add_argument(
        "--uuid",
        required=True,
        help="UUID of the dataset entry to prelabel",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Maximum deviation class level to include (1=level 1 only, 2=levels 1-2, 3=all levels). Default: 1",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DISCREPANCY DETECTION PRELABELING")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset_path}")
    logger.info(f"UUID: {args.uuid}")
    logger.info(
        f"Class Level: {args.level} ({'Level 1 only' if args.level == 1 else f'Levels 1-{args.level}' if args.level == 2 else 'All levels'})"
    )

    try:
        result = await prelabel_entry(
            uuid=args.uuid,
            dataset_path=args.dataset_path,
            level=args.level,
        )

        print("\n" + "=" * 60)
        print("PRELABEL RESULT")
        print("=" * 60)
        print(f"UUID: {result['uuid']}")
        print(f"Deviations Found: {len(result['deviations'])}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Failed to prelabel dataset entry: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
