"""
Simplified discrepancy detection workflow for evaluation purposes.

This workflow analyzes sales calls for discrepancies using pre-collected dataset files:
- Loads dataset entries by UUID
- Downloads estimate, form, recording, and transcript from S3
- Analyzes with AI for discrepancies
- Outputs results without any CRM updates (evaluation-only)

Uses the AI provider abstraction, defaulting to Gemini but configurable via AI_PROVIDER env var.
"""

import argparse
import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from pydantic import BaseModel, Field

from src.ai.base import ContentAnalysisRequest
from src.ai.providers import get_ai_provider
from src.utils.logger import logger


class DiscrepancyReview(BaseModel):
    """Structured output for discrepancy review."""

    needs_review: bool = Field(
        description="True if discrepancies were found and the job needs review, False otherwise"
    )
    hold_explanation: str = Field(
        description="Concise explanation of discrepancies found with timestamps (HH:MM:SS format)"
    )


class DiscrepancyDetectionV2Workflow:
    """Simplified workflow for detecting discrepancies using S3 dataset files."""

    def __init__(self):
        """Initialize the workflow."""
        self.ai_provider = get_ai_provider()
        self.s3_client = boto3.client("s3")

    def _load_dataset_entry(self, dataset_path: str, uuid: str) -> dict[str, Any]:
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

    @asynccontextmanager
    async def _download_from_s3(self, s3_uri: str, suffix: str = ""):
        """Download a file from S3 to a temporary file.

        Args:
            s3_uri: S3 URI in format s3://bucket/key
            suffix: File suffix for the temp file (e.g., '.json', '.m4a')

        Yields:
            str: Path to the temporary file

        Raises:
            ValueError: If S3 URI is invalid
        """
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")

        # Parse S3 URI
        parts = s3_uri[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")

        bucket, key = parts

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=suffix, delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

            try:
                logger.info(f"   Downloading {s3_uri}")
                # Download from S3
                self.s3_client.download_fileobj(
                    Bucket=bucket, Key=key, Fileobj=tmp_file
                )
                logger.info(f"   ✅ Downloaded to {tmp_path}")

                yield tmp_path
            finally:
                # Cleanup
                Path(tmp_path).unlink(missing_ok=True)

    async def execute_for_dataset_entry(
        self, uuid: str, dataset_path: str
    ) -> dict[str, Any]:
        """Execute the discrepancy detection workflow for a dataset entry.

        Args:
            uuid: UUID of the dataset entry to process
            dataset_path: Path to the dataset JSON file

        Returns:
            dict: Workflow result with status and details

        Raises:
            ValueError: If dataset entry not found or files missing
            Exception: For other errors
        """
        try:
            logger.info("=" * 60)
            logger.info(f"DISCREPANCY DETECTION V2 WORKFLOW - UUID {uuid}")
            logger.info("=" * 60)

            # Step 1: Load dataset entry
            logger.info(f"\nStep 1: Loading dataset entry for UUID {uuid}")
            entry = self._load_dataset_entry(dataset_path, uuid)

            logger.info(f"   Project ID: {entry['project_id']}")
            logger.info(f"   Job ID: {entry['job_id']}")
            logger.info(f"   Estimate ID: {entry['estimate_id']}")
            logger.info(f"   Labels: {len(entry.get('labels', []))} expected issues")

            # Step 2: Download estimate from S3
            logger.info("\nStep 2: Downloading estimate from S3")
            estimate_s3_uri = entry.get("estimate_s3_uri")
            if not estimate_s3_uri:
                raise ValueError("No estimate_s3_uri in dataset entry")

            async with self._download_from_s3(estimate_s3_uri, ".json") as estimate_path:
                with open(estimate_path, "r") as f:
                    estimate_data = json.load(f)
                logger.info("✅ Estimate data loaded")

                # Step 3: Download form from S3
                logger.info("\nStep 3: Downloading form submission from S3")
                form_s3_uri = entry.get("form_s3_uri")
                if not form_s3_uri:
                    logger.warning("⚠️ No form_s3_uri in dataset entry")
                    form_data = None
                else:
                    async with self._download_from_s3(form_s3_uri, ".json") as form_path:
                        with open(form_path, "r") as f:
                            form_data = json.load(f)
                        logger.info("✅ Form data loaded")

                # Step 4: Download recording and transcript from S3 (if available)
                recording_uris = entry.get("rilla_recordings_s3_uri", [])
                transcript_uris = entry.get("rilla_transcripts_s3_uri", [])

                recording_path = None
                transcript_path = None

                if recording_uris and len(recording_uris) > 0:
                    logger.info(
                        f"\nStep 4a: Downloading recording from S3 ({len(recording_uris)} available)"
                    )
                    # Use first recording if multiple
                    async with self._download_from_s3(
                        recording_uris[0], ".m4a"
                    ) as rec_path:
                        recording_path = rec_path
                        logger.info("✅ Recording downloaded")

                        if transcript_uris and len(transcript_uris) > 0:
                            logger.info(
                                f"\nStep 4b: Downloading transcript from S3 ({len(transcript_uris)} available)"
                            )
                            async with self._download_from_s3(
                                transcript_uris[0], ".json"
                            ) as trans_path:
                                transcript_path = trans_path
                                logger.info("✅ Transcript downloaded")

                                # Step 5: Analyze with AI
                                review_result = await self._analyze_content(
                                    estimate_data=estimate_data,
                                    form_data=form_data,
                                    audio_path=recording_path,
                                    transcript_path=transcript_path,
                                )
                        else:
                            logger.warning(
                                "⚠️ No transcript available, using audio only"
                            )
                            # Step 5: Analyze with AI (audio only)
                            review_result = await self._analyze_content(
                                estimate_data=estimate_data,
                                form_data=form_data,
                                audio_path=recording_path,
                                transcript_path=None,
                            )
                elif transcript_uris and len(transcript_uris) > 0:
                    logger.info("\nStep 4: Downloading transcript from S3 (no recording)")
                    async with self._download_from_s3(
                        transcript_uris[0], ".json"
                    ) as trans_path:
                        transcript_path = trans_path
                        logger.info("✅ Transcript downloaded")

                        # Step 5: Analyze with AI (transcript only)
                        review_result = await self._analyze_content(
                            estimate_data=estimate_data,
                            form_data=form_data,
                            audio_path=None,
                            transcript_path=transcript_path,
                        )
                else:
                    raise ValueError(
                        "No recording or transcript available in dataset entry"
                    )

            logger.info("\n✅ Analysis complete")
            logger.info(f"   Needs Review: {review_result.needs_review}")
            logger.info(f"   Explanation: {review_result.hold_explanation}")

            # Compare with expected labels
            expected_labels = entry.get("labels", [])
            logger.info(f"\n📋 Expected Labels from Dataset: {len(expected_labels)}")
            if expected_labels:
                for label in expected_labels:
                    logger.info(f"   • {label}")

            logger.info("\n✅ DISCREPANCY DETECTION V2 WORKFLOW COMPLETE")

            return {
                "status": "success",
                "uuid": uuid,
                "project_id": entry["project_id"],
                "job_id": entry["job_id"],
                "estimate_id": entry["estimate_id"],
                "needs_review": review_result.needs_review,
                "explanation": review_result.hold_explanation,
                "expected_labels": expected_labels,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error during workflow: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise

    async def _analyze_content(
        self,
        estimate_data: dict,
        form_data: dict | None,
        audio_path: str | None,
        transcript_path: str | None,
    ) -> DiscrepancyReview:
        """Analyze estimate, form, and audio/transcript for discrepancies.

        Args:
            estimate_data: Estimate data from S3 JSON file
            form_data: Form submission data from S3 JSON file
            audio_path: Path to the audio file (optional)
            transcript_path: Path to the transcript JSON file (optional)

        Returns:
            DiscrepancyReview: Analysis result

        Raises:
            ValueError: If neither audio_path nor transcript_path provided
        """
        if not audio_path and not transcript_path:
            raise ValueError("Either audio_path or transcript_path must be provided")

        logger.info("\nStep 5: Analyzing content for discrepancies")

        # Extract estimate items for the prompt
        estimate_items = estimate_data.get("items", [])
        formatted_estimate = {
            "estimate_id": estimate_data.get("id"),
            "name": estimate_data.get("name"),
            "subtotal": estimate_data.get("subtotal"),
            "tax": estimate_data.get("tax"),
            "items": [
                {
                    "description": item.get("description"),
                    "quantity": item.get("qty"),
                    "unit_rate": item.get("unitRate"),
                    "total": item.get("total"),
                    "sku_name": item.get("sku", {}).get("name", ""),
                }
                for item in estimate_items
            ],
        }

        # Extract notes to production from form
        notes_to_production = None
        if form_data:
            units = form_data.get("units", [])
            for unit in units:
                if unit.get("name") == "Notes to Production":
                    notes_to_production = unit
                    break

        if not notes_to_production:
            notes_to_production = {"message": "No Notes to Production found"}

        # Load transcript if provided
        transcript_text = None
        if transcript_path:
            logger.info(f"   Loading transcript from: {transcript_path}")
            with open(transcript_path, "r") as f:
                transcript_data = json.load(f)

            # Format transcript for readability
            transcript_lines = []
            for entry in transcript_data:
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("transcript", "")
                timestamp = entry.get("start_time", "00:00:00")
                transcript_lines.append(f"[{timestamp}] {speaker}: {text}")

            transcript_text = "\n".join(transcript_lines)
            logger.info(f"   Loaded transcript with {len(transcript_data)} entries")

        # Load and build the prompt from template
        prompt_template_path = Path(__file__).parent / "discrepancy_detection_prompt.md"
        with open(prompt_template_path, "r") as f:
            prompt_template = f.read()

        # Format the template with estimate and notes data
        prompt = prompt_template.format(
            estimate_data=json.dumps(formatted_estimate, indent=2),
            notes_to_production=json.dumps(notes_to_production, indent=2),
        )

        # Use AI provider to analyze with structured output
        logger.info("   Initiating AI analysis...")

        request = ContentAnalysisRequest(
            audio_path=audio_path,
            transcript_text=transcript_text,
            prompt=prompt,
            temperature=0.7,
        )

        review_result = await self.ai_provider.analyze_content_with_structured_output(
            request=request,
            response_model=DiscrepancyReview,
        )

        return review_result


async def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description="Analyze sales calls for discrepancies using dataset files from S3"
    )
    parser.add_argument(
        "--dataset-path",
        required=True,
        help="Path to the dataset JSON file",
    )
    parser.add_argument(
        "--uuid",
        required=True,
        help="UUID of the dataset entry to analyze",
    )

    args = parser.parse_args()

    workflow = DiscrepancyDetectionV2Workflow()

    logger.info("=" * 60)
    logger.info("DATASET-BASED DISCREPANCY DETECTION WORKFLOW")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset_path}")
    logger.info(f"UUID: {args.uuid}")
    logger.info("")

    try:
        result = await workflow.execute_for_dataset_entry(
            uuid=args.uuid,
            dataset_path=args.dataset_path,
        )

        print("\n" + "=" * 60)
        print("WORKFLOW RESULT")
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))
        print("=" * 60)

    except Exception as e:
        logger.error(f"Failed to process dataset entry: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
