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
        logger.error("[WORKFLOW] Error converting audio to MP3", input_path=input_path, error=str(e))
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

    def __init__(self, prelabel: bool = False):
        """Initialize the workflow.

        Args:
            prelabel: If True, use all classes; if False, use only level 1 classes
        """
        self.ai_provider = get_ai_provider()
        self.s3_client = boto3.client("s3")
        self.prelabel = prelabel

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
        logger.info("[WORKFLOW] Loading dataset from path", path=dataset_path)
        with open(dataset_path, "r") as f:
            dataset = json.load(f)

        for entry in dataset:
            if entry.get("uuid") == uuid:
                logger.info("[WORKFLOW] Found dataset entry", uuid=uuid)
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
                logger.info("[WORKFLOW] Downloading from S3", s3_uri=s3_uri)
                # Download from S3
                self.s3_client.download_fileobj(
                    Bucket=bucket, Key=key, Fileobj=tmp_file
                )
                logger.info("[WORKFLOW] Downloaded to temporary path", tmp_path=tmp_path)

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
            logger.info("[WORKFLOW] Starting discrepancy detection", uuid=uuid)

            # Step 1: Load dataset entry
            logger.info("[WORKFLOW] Loading dataset entry", uuid=uuid)
            entry = self._load_dataset_entry(dataset_path, uuid)

            logger.info("[WORKFLOW] Dataset entry loaded", project_id=entry['project_id'], job_id=entry['job_id'], estimate_id=entry['estimate_id'], labels_count=len(entry.get('labels', [])))

            # Step 2: Download estimate from S3
            logger.info("[WORKFLOW] Downloading estimate from S3")
            estimate_s3_uri = entry.get("estimate_s3_uri")
            if not estimate_s3_uri:
                raise ValueError("No estimate_s3_uri in dataset entry")

            async with self._download_from_s3(
                estimate_s3_uri, ".json"
            ) as estimate_path:
                with open(estimate_path, "r") as f:
                    estimate_data = json.load(f)
                logger.info("[WORKFLOW] Estimate data loaded")

                # Step 3: Download form from S3
                logger.info("[WORKFLOW] Downloading form submission from S3")
                form_s3_uri = entry.get("form_s3_uri")
                if not form_s3_uri:
                    logger.warning("[WORKFLOW] No form_s3_uri in dataset entry")
                    form_data = None
                else:
                    async with self._download_from_s3(
                        form_s3_uri, ".json"
                    ) as form_path:
                        with open(form_path, "r") as f:
                            form_data = json.load(f)
                        logger.info("[WORKFLOW] Form data loaded")

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

                logger.info("[WORKFLOW] Downloading recording and transcript from S3")
                logger.info("[WORKFLOW] Recordings available", count=len(recording_uris))
                logger.info("[WORKFLOW] Transcripts available", count=len(transcript_uris))

                # Download both recording and transcript (use first if multiple)
                async with self._download_from_s3(
                    recording_uris[0], ".m4a"
                ) as recording_path:
                    logger.info("[WORKFLOW] Recording downloaded")

                    async with self._download_from_s3(
                        transcript_uris[0], ".json"
                    ) as transcript_path:
                        logger.info("[WORKFLOW] Transcript downloaded")

                        # Step 5: Analyze with AI using both audio and transcript
                        logger.info("[WORKFLOW] Analyzing with AI")
                        review_result = await self._analyze_content(
                            estimate_data=estimate_data,
                            form_data=form_data,
                            audio_path=recording_path,
                            transcript_path=transcript_path,
                        )

            logger.info("[WORKFLOW] Analysis complete")
            logger.info("[WORKFLOW] Analysis summary", summary=review_result.summary)
            logger.info("[WORKFLOW] Deviations found", count=len(review_result.deviations))

            # Log each deviation
            if review_result.deviations:
                logger.info("[WORKFLOW] Detected deviations")
                for i, deviation in enumerate(review_result.deviations, 1):
                    logger.info(
                        "[WORKFLOW] Deviation found",
                        index=i,
                        deviation_class=deviation.deviation_class,
                        explanation=deviation.explanation
                    )
                    if deviation.occurrences:
                        logger.info(
                            "[WORKFLOW] Deviation occurrences",
                            count=len(deviation.occurrences)
                        )
                        for occ in deviation.occurrences:
                            logger.info(
                                "[WORKFLOW] Occurrence",
                                conversation_index=occ.rilla_conversation_index,
                                timestamp=occ.timestamp
                            )
                    else:
                        logger.info("[WORKFLOW] Occurrences: None (not discussed in conversation)")
                    if deviation.predicted_line_item:
                        logger.info(
                            "[WORKFLOW] Predicted line item",
                            description=deviation.predicted_line_item.description
                        )
                        if deviation.predicted_line_item.quantity:
                            logger.info(
                                "[WORKFLOW] Line item quantity",
                                quantity=deviation.predicted_line_item.quantity,
                                unit=deviation.predicted_line_item.unit or ''
                            )
                        if deviation.predicted_line_item.notes:
                            logger.info(
                                "[WORKFLOW] Line item notes",
                                notes=deviation.predicted_line_item.notes
                            )

                        # Log pricebook matching info
                        if deviation.predicted_line_item.matched_pricebook_item_id:
                            logger.info(
                                "[WORKFLOW] Matched pricebook item",
                                display_name=deviation.predicted_line_item.matched_pricebook_item_display_name,
                                code=deviation.predicted_line_item.matched_pricebook_item_code,
                                unit_cost=deviation.predicted_line_item.unit_cost,
                                total_cost=deviation.predicted_line_item.total_cost
                            )
                        else:
                            logger.info("[WORKFLOW] No pricebook match found")

            # Calculate total cost savings
            total_cost_savings = 0.0
            matched_items_count = 0
            unmatched_items_count = 0

            for deviation in review_result.deviations:
                if deviation.predicted_line_item:
                    if deviation.predicted_line_item.total_cost:
                        total_cost_savings += deviation.predicted_line_item.total_cost
                        matched_items_count += 1
                    elif deviation.predicted_line_item.matched_pricebook_item_id is None:
                        unmatched_items_count += 1

            # Log cost savings summary
            if matched_items_count > 0 or unmatched_items_count > 0:
                logger.info("[WORKFLOW] Cost savings summary", total_cost_savings=total_cost_savings, matched_items=matched_items_count, unmatched_items=unmatched_items_count)

            # Print Rilla links
            rilla_links = entry.get("rilla_links", [])
            if rilla_links:
                logger.info("[WORKFLOW] Rilla conversation links", link_count=len(rilla_links))
                for i, link in enumerate(rilla_links):
                    logger.info("[WORKFLOW] Rilla link", index=i, link=link)

            logger.info("[WORKFLOW] Discrepancy detection workflow complete")

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
            logger.error("[WORKFLOW] Error during workflow", error=str(e))
            import traceback

            logger.error("[WORKFLOW] Traceback", traceback=traceback.format_exc())
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
        logger.info("[WORKFLOW] Loading transcript", transcript_path=transcript_path)
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
                        "[WORKFLOW] Detected original Rilla format, attempting simplification"
                    )
                    simplified = simplify_rilla_transcript(transcript_data)
                    simplified_size = len(json.dumps(simplified))
                    savings_pct = 100 - (simplified_size / original_size * 100)
                    logger.info(
                        "[WORKFLOW] Simplified transcript",
                        original_tokens=original_size // 4,
                        simplified_tokens=simplified_size // 4,
                        savings_pct=round(savings_pct, 1)
                    )
                    transcript_data = simplified
                else:
                    logger.info(
                        "[WORKFLOW] Transcript already in compact format"
                    )
            else:
                logger.info(
                    "[WORKFLOW] Transcript already in compact format"
                )
        except Exception as e:
            logger.warning("[WORKFLOW] Failed to simplify transcript", error=str(e))
            logger.info("[WORKFLOW] Using original transcript format")
            # transcript_data remains unchanged

        # Convert to JSON string for passing to LLM
        transcript_json = json.dumps(transcript_data, indent=2)
        logger.info("[WORKFLOW] Final transcript size", tokens=len(transcript_json) // 4)

        # Load deviation classes from JSON file (always use classes.json)
        classes_path = (
            Path(__file__).parent.parent.parent
            / "evals"
            / "estimate_deviation"
            / "classes.json"
        )

        with open(classes_path, "r") as f:
            classes_data = json.load(f)

        # Filter classes based on mode
        if self.prelabel:
            # Use all classes in prelabel mode
            filtered_classes = classes_data["classes"]
            logger.info("[WORKFLOW] Using all classes (prelabel mode)", count=len(filtered_classes))
        else:
            # Use only level 1 classes in standard mode
            filtered_classes = [
                cls for cls in classes_data["classes"] if cls.get("level") == 1
            ]
            logger.info(
                "[WORKFLOW] Using level 1 classes (standard mode)",
                count=len(filtered_classes)
            )

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
        logger.info("[WORKFLOW] Initiating AI analysis")
        logger.info("[WORKFLOW] Using GPT-5 with transcript and pricebook vector store for RAG")

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
        "--prelabel",
        action="store_true",
        help="Use classes.json instead of classes.json for deviation detection",
    )

    args = parser.parse_args()

    workflow = DiscrepancyDetectionV2Workflow(prelabel=args.prelabel)

    logger.info("[WORKFLOW] Starting workflow")
    logger.info("[WORKFLOW] Dataset path", dataset_path=args.dataset_path)
    logger.info("[WORKFLOW] UUID", uuid=args.uuid)
    logger.info("[WORKFLOW] Mode", mode='Prelabel' if args.prelabel else 'Standard')

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
        logger.error("[WORKFLOW] Failed to process dataset entry", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
