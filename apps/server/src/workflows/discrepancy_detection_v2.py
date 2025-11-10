"""
Simplified discrepancy detection workflow for evaluation purposes.

This workflow analyzes sales calls for discrepancies using pre-collected dataset files:
- Loads dataset entries by UUID
- Downloads estimate, form, recording, and transcript from S3
- Analyzes with AI for discrepancies
- Outputs results without any CRM updates (evaluation-only)

Uses OpenAI provider for this workflow (forced via environment variable).
"""

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from pydantic import BaseModel, Field

from src.ai.base import ContentAnalysisRequest
from src.ai.providers import get_ai_provider
from src.utils.braintrust_tracing import (
    braintrust_experiment,
    braintrust_span,
)
from src.utils.logger import logger

# Force OpenAI provider for this workflow
os.environ["AI_PROVIDER"] = "openai"

# Pricebook vector store ID (created via scripts/ingest_pricebook.py)
PRICEBOOK_VECTOR_STORE_ID = "vs_690e9d9523a8819192c6f111227b90a5"


def convert_to_mp3(input_path: str, mp3_path: str, bitrate: str = "64k") -> bool:
    """Convert any audio file to MP3 using ffmpeg with specified bitrate.

    Args:
        input_path: Path to input audio file
        mp3_path: Path where MP3 should be saved
        bitrate: Audio bitrate (default: 64k)

    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-b:a", bitrate, "-y", mp3_path],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting {input_path} to MP3: {e}")
        return False


def _format_timestamp_from_seconds(seconds: float, use_hours: bool) -> str:
    """
    Convert timestamp from seconds to MM:SS or HH:MM:SS format.

    Args:
        seconds: Timestamp in seconds
        use_hours: If True, use HH:MM:SS format; if False, use MM:SS

    Returns:
        Formatted timestamp stringS
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if use_hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def simplify_rilla_transcript(rilla_transcript: list[dict]) -> dict:
    """
    Convert Rilla word-level transcript to compact format for LLM efficiency.

    Reduces token count by ~70% by:
    - Combining words into space-separated strings
    - Using parallel arrays for timestamps and confidence
    - Grouping by speaker turns
    - Using shorter timestamp format when possible

    Args:
        rilla_transcript: List of Rilla entries with format:
            [{"speaker": str, "words": [{"word": str, "start_time": float, "confidence": float}]}]

    Returns:
        Compact format dict:
            {
                "conversations": [
                    {
                        "speaker": str,
                        "words": str (space-separated),
                        "timestamps": [str] (MM:SS or HH:MM:SS),
                        "confidence": [float]
                    }
                ]
            }

    Raises:
        ValueError: If transcript is empty or malformed
    """
    if not rilla_transcript:
        raise ValueError("Transcript is empty")

    # Determine if we need hours in timestamps (any timestamp >= 1 hour)
    max_time = 0.0
    for entry in rilla_transcript:
        words = entry.get("words", [])
        if words:
            for word_obj in words:
                start_time = word_obj.get("start_time", 0)
                max_time = max(max_time, start_time)

    use_hours = max_time >= 3600

    # Group by speaker turns (consecutive entries with same speaker)
    conversations = []
    current_speaker = None
    current_words = []
    current_timestamps = []
    current_confidence = []

    for entry in rilla_transcript:
        speaker = entry.get("speaker", "Unknown")
        words = entry.get("words", [])

        if not words:
            continue

        # If speaker changed, save previous turn and start new one
        if speaker != current_speaker and current_words:
            conversations.append(
                {
                    "speaker": current_speaker,
                    "words": " ".join(current_words),
                    "timestamps": current_timestamps,
                    "confidence": current_confidence,
                }
            )
            current_words = []
            current_timestamps = []
            current_confidence = []

        current_speaker = speaker

        # Extract word, timestamp, confidence from each word object
        for word_obj in words:
            word = word_obj.get("word", "")
            start_time = word_obj.get("start_time", 0)
            conf = word_obj.get("confidence", 0.0)

            if word:  # Skip empty words
                current_words.append(word)
                current_timestamps.append(
                    _format_timestamp_from_seconds(start_time, use_hours)
                )
                current_confidence.append(round(conf, 2))

    # Don't forget the last turn
    if current_words:
        conversations.append(
            {
                "speaker": current_speaker,
                "words": " ".join(current_words),
                "timestamps": current_timestamps,
                "confidence": current_confidence,
            }
        )

    if not conversations:
        raise ValueError("No valid conversation turns found in transcript")

    return {"conversations": conversations}


class DeviationOccurrence(BaseModel):
    """Timestamp and context for a deviation occurrence."""

    rilla_conversation_index: int = Field(
        description="Zero-based index into the list of Rilla conversations (0 for first conversation, 1 for second, etc.)"
    )
    timestamp: str = Field(
        description="Timestamp in HH:MM:SS or MM:SS format when this deviation was mentioned in the conversation",
        pattern=r"^(([01]?[0-9]|2[0-3]):)?([0-5][0-9]):([0-5][0-9])$",
    )


class PredictedLineItem(BaseModel):
    """Predicted estimate line item for a deviation."""

    description: str = Field(
        description="Description of the line item (e.g., 'Ridge Vent', 'Attic Fan')"
    )
    quantity: float | None = Field(
        default=None, description="Predicted quantity for the line item"
    )
    unit: str | None = Field(
        default=None, description="Unit of measurement (e.g., 'LF', 'EA', 'SQ', '%')"
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes or context for the line item prediction",
    )

    # Pricebook matching fields
    matched_pricebook_item_id: int | None = Field(
        default=None,
        description="ID of the matched pricebook item from the vector store (if found)",
    )
    matched_pricebook_item_code: str | None = Field(
        default=None,
        description="Item code of the matched pricebook item (e.g., 'MAT-001')",
    )
    matched_pricebook_item_display_name: str | None = Field(
        default=None,
        description="Display name of the matched pricebook item",
    )
    unit_cost: float | None = Field(
        default=None,
        description="Unit cost from the matched pricebook item's primaryVendor",
    )
    total_cost: float | None = Field(
        default=None,
        description="Total cost calculated as unit_cost × quantity",
    )


class Deviation(BaseModel):
    """A single deviation found between conversation and documentation."""

    deviation_class: str = Field(
        description="The label of the deviation class from the classes list"
    )
    explanation: str = Field(
        description="A brief explanation of what specific deviation was found"
    )
    occurrences: list[DeviationOccurrence] = Field(
        description="List of specific timestamps where this deviation was mentioned in the conversation(s)"
    )


class DiscrepancyReview(BaseModel):
    """Structured output for discrepancy review with classified deviations."""

    deviations: list[Deviation] = Field(
        description="List of all deviations found between the conversation and documented data"
    )
    summary: str = Field(
        description="Brief overall summary of findings (e.g., 'Found 3 deviations: material specifications, additional services, and special requests not documented')"
    )


class DiscrepancyDetectionV2Workflow:
    """Simplified workflow for detecting discrepancies using S3 dataset files."""

    def __init__(
        self, level: int = 1, prelabel: bool = False, experiment: Any | None = None
    ):
        """Initialize the workflow.

        Args:
            level: Maximum class level to include (1, 2, or 3). Default 1.
                   Level 1 includes only level 1 classes.
                   Level 2 includes level 1 and 2 classes.
                   Level 3 includes all classes.
            prelabel: If True, marks output as prelabel data (metadata only)
            experiment: Optional Braintrust experiment for tracing
        """
        self.ai_provider = get_ai_provider()
        self.s3_client = boto3.client("s3")
        self.level = level
        self.prelabel = prelabel
        self.experiment = experiment

    def _create_dynamic_deviation_model(self, allowed_labels: list[str]):
        """Create a dynamic Deviation model with enum constrained to allowed labels.

        Args:
            allowed_labels: List of allowed deviation class labels

        Returns:
            Pydantic model class for Deviation with constrained enum
        """
        from typing import Literal

        # Create a Literal type with the allowed labels
        DeviationClassLiteral = Literal[tuple(allowed_labels)]

        class DynamicDeviation(BaseModel):
            """A single deviation found between conversation and documentation."""

            deviation_class: DeviationClassLiteral = Field(
                description="The label of the deviation class from the classes list"
            )
            explanation: str = Field(
                description="A brief explanation of what specific deviation was found"
            )
            occurrences: list[DeviationOccurrence] | None = Field(
                default=None,
                description="List of specific timestamps where this deviation was mentioned in the conversation(s). Not required for deviations where the item was not discussed.",
            )
            predicted_line_item: PredictedLineItem | None = Field(
                default=None,
                description="Optional predicted estimate line item for deviations that include line item prediction",
            )

        class DynamicDiscrepancyReview(BaseModel):
            """Structured output for discrepancy review with classified deviations."""

            deviations: list[DynamicDeviation] = Field(
                description="List of all deviations found between the conversation and documented data"
            )
            summary: str = Field(description="Brief overall summary of findings")

        return DynamicDiscrepancyReview

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
        # Execute the internal workflow logic first to get project IDs
        result = await self._execute_internal(uuid, dataset_path)

        # Create span for tracing if experiment is provided
        # Include project metadata in input for easy dataset creation
        with braintrust_span(
            self.experiment,
            name=f"discrepancy_detection_{uuid[:8]}",
            input={
                "uuid": uuid,
                "project_id": result["project_id"],
                "job_id": result["job_id"],
                "estimate_id": result["estimate_id"],
            },
            metadata={
                "prelabel": self.prelabel,
            },
        ) as span:
            # Log simplified output for dataset conversion
            # Only include deviations and cost_savings, matching expected format
            if span:
                output_data = {
                    "deviations": result["deviations"],
                    "cost_savings": result["cost_savings"],
                }

                # When prelabeling, set both output and expected so the UI shows
                # the model's prediction as the expected value (which can then be corrected)
                if self.prelabel:
                    span.log(output=output_data, expected=output_data)
                else:
                    span.log(output=output_data)

        return result

    async def _execute_internal(self, uuid: str, dataset_path: str) -> dict[str, Any]:
        """Internal execution logic for the workflow.

        Args:
            uuid: UUID of the dataset entry
            dataset_path: Path to dataset JSON

        Returns:
            Workflow result dict
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

            async with self._download_from_s3(
                estimate_s3_uri, ".json"
            ) as estimate_path:
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
                    async with self._download_from_s3(
                        form_s3_uri, ".json"
                    ) as form_path:
                        with open(form_path, "r") as f:
                            form_data = json.load(f)
                        logger.info("✅ Form data loaded")

                # Step 4: Download recording and transcript from S3 (both required)
                recording_uris = entry.get("rilla_recordings_s3_uri", [])
                transcript_uris = entry.get("rilla_transcripts_s3_uri", [])

                # Enforce both recording and transcript are present
                if not recording_uris or len(recording_uris) == 0:
                    raise ValueError(
                        f"No recording available for UUID {uuid}. Both recording and transcript are required."
                    )
                if not transcript_uris or len(transcript_uris) == 0:
                    raise ValueError(
                        f"No transcript available for UUID {uuid}. Both recording and transcript are required."
                    )

                logger.info("\nStep 4: Downloading recording and transcript from S3")
                logger.info(f"   Recordings available: {len(recording_uris)}")
                logger.info(f"   Transcripts available: {len(transcript_uris)}")

                # Download both recording and transcript (use first if multiple)
                async with self._download_from_s3(
                    recording_uris[0], ".m4a"
                ) as recording_path:
                    logger.info("   ✅ Recording downloaded")

                    async with self._download_from_s3(
                        transcript_uris[0], ".json"
                    ) as transcript_path:
                        logger.info("   ✅ Transcript downloaded")

                        # Step 5: Analyze with AI using both audio and transcript
                        logger.info(
                            "\nStep 5: Analyzing with both audio and transcript"
                        )
                        review_result = await self._analyze_content(
                            estimate_data=estimate_data,
                            form_data=form_data,
                            audio_path=recording_path,
                            transcript_path=transcript_path,
                        )

            logger.info("\n✅ Analysis complete")
            logger.info(f"   Summary: {review_result.summary}")
            logger.info(f"   Deviations Found: {len(review_result.deviations)}")

            # Log each deviation
            if review_result.deviations:
                logger.info("\n📋 Detected Deviations:")
                for i, deviation in enumerate(review_result.deviations, 1):
                    logger.info(f"\n   {i}. [{deviation.deviation_class}]")
                    logger.info(f"      {deviation.explanation}")
                    if deviation.occurrences:
                        logger.info(
                            f"      Occurrences ({len(deviation.occurrences)}):"
                        )
                        for occ in deviation.occurrences:
                            logger.info(
                                f"        • Conversation {occ.rilla_conversation_index} at {occ.timestamp}"
                            )
                    else:
                        logger.info(
                            "      Occurrences: None (not discussed in conversation)"
                        )
                    if deviation.predicted_line_item:
                        logger.info(
                            f"      Predicted Line Item: {deviation.predicted_line_item.description}"
                        )
                        if deviation.predicted_line_item.quantity:
                            logger.info(
                                f"        Quantity: {deviation.predicted_line_item.quantity} {deviation.predicted_line_item.unit or ''}"
                            )
                        if deviation.predicted_line_item.notes:
                            logger.info(
                                f"        Notes: {deviation.predicted_line_item.notes}"
                            )

                        # Log pricebook matching info
                        if deviation.predicted_line_item.matched_pricebook_item_id:
                            logger.info(
                                f"        ✅ Matched Pricebook Item: {deviation.predicted_line_item.matched_pricebook_item_display_name}"
                            )
                            logger.info(
                                f"           Code: {deviation.predicted_line_item.matched_pricebook_item_code}"
                            )
                            if deviation.predicted_line_item.unit_cost is not None:
                                logger.info(
                                    f"           Unit Cost: ${deviation.predicted_line_item.unit_cost:.2f}"
                                )
                            if deviation.predicted_line_item.total_cost is not None:
                                logger.info(
                                    f"           Total Cost: ${deviation.predicted_line_item.total_cost:.2f}"
                                )
                        else:
                            logger.info("        ⚠️  No pricebook match found")

            # Calculate total cost savings
            total_cost_savings = 0.0
            matched_items_count = 0
            unmatched_items_count = 0

            for deviation in review_result.deviations:
                if deviation.predicted_line_item:
                    if deviation.predicted_line_item.total_cost:
                        total_cost_savings += deviation.predicted_line_item.total_cost
                        matched_items_count += 1
                    elif (
                        deviation.predicted_line_item.matched_pricebook_item_id is None
                    ):
                        unmatched_items_count += 1

            # Log cost savings summary
            if matched_items_count > 0 or unmatched_items_count > 0:
                logger.info("\n💰 Cost Savings Summary:")
                logger.info(f"   Total Cost Savings: ${total_cost_savings:.2f}")
                logger.info(f"   Matched Items: {matched_items_count}")
                if unmatched_items_count > 0:
                    logger.info(f"   ⚠️  Unmatched Items: {unmatched_items_count}")

            # Print Rilla links
            rilla_links = entry.get("rilla_links", [])
            if rilla_links:
                logger.info("\n🔗 Rilla Conversation Links:")
                for i, link in enumerate(rilla_links):
                    logger.info(f"   {i}. {link}")

            logger.info("\n✅ DISCREPANCY DETECTION V2 WORKFLOW COMPLETE")

            return {
                "status": "success",
                "uuid": uuid,
                "project_id": entry["project_id"],
                "job_id": entry["job_id"],
                "estimate_id": entry["estimate_id"],
                "summary": review_result.summary,
                "deviations": [
                    {
                        "class": dev.deviation_class,
                        "explanation": dev.explanation,
                        "occurrences": [
                            {
                                "conversation_index": occ.rilla_conversation_index,
                                "timestamp": occ.timestamp,
                            }
                            for occ in dev.occurrences
                        ]
                        if dev.occurrences
                        else [],
                        "predicted_line_item": {
                            "description": dev.predicted_line_item.description,
                            "quantity": dev.predicted_line_item.quantity,
                            "unit": dev.predicted_line_item.unit,
                            "notes": dev.predicted_line_item.notes,
                            "matched_pricebook_item_id": dev.predicted_line_item.matched_pricebook_item_id,
                            "matched_pricebook_item_code": dev.predicted_line_item.matched_pricebook_item_code,
                            "matched_pricebook_item_display_name": dev.predicted_line_item.matched_pricebook_item_display_name,
                            "unit_cost": dev.predicted_line_item.unit_cost,
                            "total_cost": dev.predicted_line_item.total_cost,
                        }
                        if dev.predicted_line_item
                        else None,
                    }
                    for dev in review_result.deviations
                ],
                "cost_savings": {
                    "total": total_cost_savings,
                    "matched_items": matched_items_count,
                    "unmatched_items": unmatched_items_count,
                },
                "rilla_links": rilla_links,
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
        audio_path: str,
        transcript_path: str,
    ) -> DiscrepancyReview:
        """Analyze estimate, form, and audio/transcript for discrepancies.

        Args:
            estimate_data: Estimate data from S3 JSON file
            form_data: Form submission data from S3 JSON file
            audio_path: Path to the audio file (required)
            transcript_path: Path to the transcript JSON file (required)

        Returns:
            DiscrepancyReview: Analysis result

        Raises:
            ValueError: If audio_path or transcript_path not provided
        """
        if not audio_path or not transcript_path:
            raise ValueError("Both audio_path and transcript_path are required")

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

        # Load and process transcript
        logger.info(f"   Loading transcript from: {transcript_path}")
        with open(transcript_path, "r") as f:
            transcript_data = json.load(f)

        # Validate transcript is not empty
        if not transcript_data:
            raise ValueError("Transcript file is empty - no conversation data found.")

        # Try to simplify transcript if it's in original Rilla format
        original_size = len(json.dumps(transcript_data))
        try:
            # Check if it's a list (Rilla format) with expected structure
            if isinstance(transcript_data, list) and len(transcript_data) > 0:
                first_entry = transcript_data[0]
                if "speaker" in first_entry and "words" in first_entry:
                    logger.info(
                        "   Detected original Rilla format, attempting simplification..."
                    )
                    simplified = simplify_rilla_transcript(transcript_data)
                    simplified_size = len(json.dumps(simplified))
                    savings_pct = 100 - (simplified_size / original_size * 100)
                    logger.info(
                        f"   ✅ Simplified: {original_size // 4} → {simplified_size // 4} tokens (~{savings_pct:.1f}% reduction)"
                    )
                    transcript_data = simplified
                else:
                    logger.info(
                        "   Transcript already in compact format or unknown format, using as-is"
                    )
            else:
                logger.info(
                    "   Transcript already in compact format or unknown format, using as-is"
                )
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to simplify transcript: {e}")
            logger.info("   Using original transcript format")
            # transcript_data remains unchanged

        # Convert to JSON string for passing to LLM
        transcript_json = json.dumps(transcript_data, indent=2)
        logger.info(f"   ✅ Final transcript size: ~{len(transcript_json) // 4} tokens")

        # Load deviation classes from JSON file (always use classes.json)
        classes_path = (
            Path(__file__).parent.parent.parent
            / "evals"
            / "estimate_deviation"
            / "classes.json"
        )

        with open(classes_path, "r") as f:
            classes_data = json.load(f)

        # Filter classes based on level
        if self.level == 1:
            # Level 1 only
            filtered_classes = [c for c in classes_data["classes"] if c["level"] == 1]
            logger.info(f"   Using {len(filtered_classes)} level 1 classes")
        elif self.level == 2:
            # Level 1 and 2
            filtered_classes = [c for c in classes_data["classes"] if c["level"] <= 2]
            logger.info(f"   Using {len(filtered_classes)} level 1-2 classes")
        elif self.level == 3:
            # All levels
            filtered_classes = classes_data["classes"]
            logger.info(f"   Using all {len(filtered_classes)} classes (all levels)")
        else:
            raise ValueError(f"Invalid level: {self.level}. Must be 1, 2, or 3")

        # Format deviation classes for the prompt (using filtered classes)
        deviation_classes_text = []
        filtered_class_labels = []
        for cls in filtered_classes:
            deviation_classes_text.append(
                f"**{cls['label']}** - {cls['title']}\n{cls['description']}"
            )
            filtered_class_labels.append(cls["label"])
        deviation_classes_formatted = "\n\n".join(deviation_classes_text)

        # Create dynamic response model based on filtered classes
        DynamicDiscrepancyReview = self._create_dynamic_deviation_model(
            filtered_class_labels
        )

        # Load and build the prompt from template
        prompt_template_path = Path(__file__).parent / "discrepancy_detection_prompt.md"
        with open(prompt_template_path, "r") as f:
            prompt_template = f.read()

        # Format the template with all data
        prompt = prompt_template.format(
            deviation_classes=deviation_classes_formatted,
            estimate_data=json.dumps(formatted_estimate, indent=2),
            notes_to_production=json.dumps(notes_to_production, indent=2),
        )

        # Use AI provider to analyze with structured output
        logger.info("   Initiating AI analysis...")
        logger.info("   Using GPT-5 with transcript and pricebook vector store for RAG")

        request = ContentAnalysisRequest(
            audio_path=None,  # No audio for now
            transcript_text=transcript_json,  # Pass compact JSON as text
            prompt=prompt,
            temperature=0.7,
            vector_store_ids=[PRICEBOOK_VECTOR_STORE_ID],
        )

        review_result = await self.ai_provider.analyze_content_with_structured_output(
            request=request,
            response_model=DynamicDiscrepancyReview,
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
    parser.add_argument(
        "--level",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Maximum deviation class level to include (1=level 1 only, 2=levels 1-2, 3=all levels). Default: 1",
    )
    parser.add_argument(
        "--prelabel",
        action="store_true",
        help="Mark this run as prelabel data (for Braintrust metadata only, does not affect class filtering)",
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
    logger.info("DATASET-BASED DISCREPANCY DETECTION WORKFLOW")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset_path}")
    logger.info(f"UUID: {args.uuid}")
    logger.info(
        f"Class Level: {args.level} ({'Level 1 only' if args.level == 1 else f'Levels 1-{args.level}' if args.level == 2 else 'All levels'})"
    )
    logger.info(f"Prelabel Mode: {'Yes' if args.prelabel else 'No'}")
    logger.info(f"Tracing: {'Enabled' if args.trace else 'Disabled'}")
    if args.trace and args.experiment_name:
        logger.info(f"Experiment: {args.experiment_name}")
    logger.info("")

    try:
        # Create Braintrust experiment if tracing enabled
        if args.trace:
            with braintrust_experiment(
                experiment_name=args.experiment_name,
                project_name="discrepancy-detection",
            ) as experiment:
                workflow = DiscrepancyDetectionV2Workflow(
                    level=args.level, prelabel=args.prelabel, experiment=experiment
                )

                result = await workflow.execute_for_dataset_entry(
                    uuid=args.uuid,
                    dataset_path=args.dataset_path,
                )
        else:
            # Run without tracing
            workflow = DiscrepancyDetectionV2Workflow(
                level=args.level, prelabel=args.prelabel
            )

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
