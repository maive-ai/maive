"""Prelabel script for discrepancy detection evaluation.

This script:
- Loads dataset entries from dataset.json by UUID
- Downloads estimate, form, and transcript files from S3
- Runs the discrepancy detection workflow
- Uploads JSON files to Braintrust as JSONAttachments
- Logs results as prelabel data for review and correction

Usage:
    esc run <env> -- uv run python -m evals.estimate_deviation.prelabel \
        --uuid <uuid> \
        --level 1 \
        --trace \
        --experiment-name "prelabel-2025-01-10"
"""

import argparse
import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import boto3
from pydantic import BaseModel, Field

from src.utils.braintrust_tracing import (
    JSONAttachment,
    braintrust_experiment,
    braintrust_span,
)
from src.utils.logger import logger
from src.workflows.discrepancy_detection_v2 import DiscrepancyDetectionV2Workflow


class BraintrustSpanInput(BaseModel):
    """Input structure for Braintrust span logging.

    Contains only the actual JSON data files being processed.
    Uses Braintrust JSONAttachment objects to upload JSON content to Braintrust storage
    for viewing/downloading in the Braintrust UI.
    """

    estimate: JSONAttachment | None = None
    form: JSONAttachment | None = None
    rilla_transcripts: list[JSONAttachment] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class BraintrustSpanMetadata(BaseModel):
    """Metadata structure for Braintrust span logging.

    Contains identifying information and context about the data.
    """

    uuid: str
    project_id: str
    job_id: str
    estimate_id: str
    prelabel: bool
    rilla_links: list[str] = Field(default_factory=list)
    project_created_date: str | None = None
    estimate_sold_date: str | None = None
    model_config = {"arbitrary_types_allowed": True}


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
    experiment: Any | None = None,
) -> dict[str, Any]:
    """Run prelabeling on a single dataset entry.

    Args:
        uuid: UUID of the dataset entry
        dataset_path: Path to dataset.json
        level: Maximum deviation class level to include
        experiment: Optional Braintrust experiment for tracing

    Returns:
        dict: Prelabel result with deviations
    """
    s3_client = boto3.client("s3")

    # Load dataset entry
    entry = load_dataset_entry(dataset_path, uuid)

    # Download and parse JSON files for Braintrust attachments
    span_input = BraintrustSpanInput()

    # Download and parse estimate (required)
    estimate_s3_uri = entry.get("estimate_s3_uri")
    if not estimate_s3_uri:
        raise ValueError("No estimate_s3_uri in dataset entry")

    async with download_from_s3(s3_client, estimate_s3_uri, ".json") as estimate_path:
        with open(estimate_path, "r") as f:
            estimate_data = json.load(f)

        if JSONAttachment is not None and experiment is not None:
            span_input.estimate = JSONAttachment(
                data=estimate_data, filename="estimate.json"
            )

    # Download and parse form (optional)
    form_s3_uri = entry.get("form_s3_uri")
    if form_s3_uri:
        async with download_from_s3(s3_client, form_s3_uri, ".json") as form_path:
            with open(form_path, "r") as f:
                form_data = json.load(f)

            if JSONAttachment is not None and experiment is not None:
                span_input.form = JSONAttachment(data=form_data, filename="form.json")
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

        if JSONAttachment is not None and experiment is not None:
            span_input.rilla_transcripts.append(
                JSONAttachment(data=transcript_data, filename="transcript_0.json")
            )

    # Run workflow with parsed data
    workflow = DiscrepancyDetectionV2Workflow(level=level)

    deviations = await workflow.execute_with_parsed_data(
        estimate_data=estimate_data,
        form_data=form_data,
        transcript_data=transcript_data,
    )

    # Build metadata
    span_metadata = BraintrustSpanMetadata(
        uuid=uuid,
        project_id=entry["project_id"],
        job_id=entry["job_id"],
        estimate_id=entry["estimate_id"],
        prelabel=True,  # Always true for prelabel script
        rilla_links=entry.get("rilla_links", []),
        project_created_date=entry.get("project_created_date"),
        estimate_sold_date=entry.get("estimate_sold_date"),
    )

    # Log to Braintrust
    with braintrust_span(
        experiment,
        name=f"discrepancy_detection_{uuid[:8]}",
        input=span_input.model_dump(),
        metadata=span_metadata.model_dump(),
    ) as span:
        if span:
            output_data = {
                "deviations": [d.model_dump() for d in deviations],
            }
            # Set both output and expected for prelabeling
            span.log(output=output_data, expected=output_data)

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
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable Braintrust tracing for this run",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Name for Braintrust experiment (defaults to timestamp)",
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
    logger.info(f"Tracing: {'Enabled' if args.trace else 'Disabled'}")
    if args.trace and args.experiment_name:
        logger.info(f"Experiment: {args.experiment_name}")
    logger.info("")

    try:
        if args.trace:
            with braintrust_experiment(
                experiment_name=args.experiment_name,
                project_name="discrepancy-detection",
            ) as experiment:
                result = await prelabel_entry(
                    uuid=args.uuid,
                    dataset_path=args.dataset_path,
                    level=args.level,
                    experiment=experiment,
                )
        else:
            result = await prelabel_entry(
                uuid=args.uuid,
                dataset_path=args.dataset_path,
                level=args.level,
                experiment=None,
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
