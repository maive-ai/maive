import json
import os
import tempfile
from pathlib import Path

import braintrust
from braintrust import JSONAttachment, init_logger
from pydantic import BaseModel, Field

from evals.estimate_deviation.schemas import (
    Deviation,
    DeviationOccurrence,
    PredictedLineItem,
)
from src.ai.providers import get_ai_provider
from src.utils.logger import logger
from src.utils.rilla import simplify_rilla_transcript

# Import the prompt from the config module so braintrust isn't in the request path
from src.workflows.config import (
    DISCREPANCY_DETECTION_PROMPT,
    get_discrepancy_detection_settings,
)

# Force OpenAI provider for this workflow
os.environ["AI_PROVIDER"] = "openai"

# Pricebook vector store ID (created via scripts/ingest_pricebook.py)
PRICEBOOK_VECTOR_STORE_ID = "vs_690e9d9523a8819192c6f111227b90a5"


class DiscrepancyDetectionV2Workflow:
    """Core discrepancy detection workflow logic.

    Analyzes estimate, form, and transcript data to identify discrepancies.
    Pure workflow logic with no S3 or dataset dependencies.
    """

    def __init__(
        self,
        level: int = 1,
        enable_braintrust: bool | None = None,
    ):
        """Initialize the workflow.

        Args:
            level: Maximum class level to include (1, 2, or 3). Default 1.
                   Level 1 includes only level 1 classes.
                   Level 2 includes level 1 and 2 classes.
                   Level 3 includes all classes.
            enable_braintrust: Override the default Braintrust config. If None, uses settings from environment
        """
        # Get workflow settings
        workflow_settings = get_discrepancy_detection_settings()

        # Use provided override or fall back to config
        self.enable_braintrust = (
            enable_braintrust
            if enable_braintrust is not None
            else workflow_settings.enable_braintrust_logging
        )
        self.project_name = workflow_settings.braintrust_project_name
        self.project = braintrust.Project(name=self.project_name)

        # Create AI provider with Braintrust config
        self.ai_provider = get_ai_provider(
            enable_braintrust=self.enable_braintrust,
            braintrust_project_name=self.project_name
            if self.enable_braintrust
            else None,
        )
        self.level = level

        # Initialize Braintrust logger if enabled
        self.braintrust_logger = None
        if self.enable_braintrust:
            self.braintrust_logger = init_logger(project=self.project_name)
            logger.info(
                f"Braintrust logging enabled for workflow (project: {self.project_name})"
            )
        else:
            logger.info("Braintrust logging disabled for workflow")

    def _create_dynamic_deviation_model(self, allowed_labels: list[str]):
        """Create a dynamic Deviation model with enum constrained to allowed labels.

        Args:
            allowed_labels: List of allowed deviation class labels

        Returns:
            Pydantic model class with list of deviations (no summary field)
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

        class DynamicDiscrepancyResult(BaseModel):
            """Structured output for discrepancy detection (no summary)."""

            deviations: list[DynamicDeviation] = Field(
                description="List of all deviations found between the conversation and documented data"
            )

        return DynamicDiscrepancyResult

    def _process_transcript(self, transcript_path: str) -> dict:
        """Load and simplify transcript if needed.

        Args:
            transcript_path: Path to the transcript JSON file

        Returns:
            Processed transcript data (simplified if Rilla format)

        Raises:
            ValueError: If transcript is empty or invalid
        """
        logger.info("[WORKFLOW] Loading transcript", transcript_path=transcript_path)
        with open(transcript_path, "r") as f:
            transcript_data = json.load(f)

        if not transcript_data:
            raise ValueError("Transcript file is empty - no conversation data found.")

        # Simplify if Rilla format detected
        if isinstance(transcript_data, list) and len(transcript_data) > 0:
            first_entry = transcript_data[0]
            if "speaker" in first_entry and "words" in first_entry:
                logger.info("[WORKFLOW] Simplifying Rilla format transcript")
                try:
                    original_size = len(json.dumps(transcript_data))
                    transcript_data = simplify_rilla_transcript(transcript_data)
                    simplified_size = len(json.dumps(transcript_data))
                    savings_pct = 100 - (simplified_size / original_size * 100)
                    logger.info(
                        "[WORKFLOW] Transcript simplified",
                        original_tokens=original_size // 4,
                        simplified_tokens=simplified_size // 4,
                        savings_pct=round(savings_pct, 1),
                    )
                except Exception as e:
                    logger.warning(
                        "[WORKFLOW] Failed to simplify transcript, using original",
                        error=str(e),
                    )

        return transcript_data

    async def run(
        self,
        estimate_data: dict,
        form_data: dict | None,
        audio_path: str,
        transcript_path: str,
    ) -> list[Deviation]:
        """Analyze estimate, form, and audio/transcript for discrepancies.

        Args:
            estimate_data: Estimate data from S3 JSON file
            form_data: Form submission data from S3 JSON file
            audio_path: Path to the audio file (optional, not currently used)
            transcript_path: Path to the transcript JSON file (required)

        Returns:
            list[Deviation]: List of detected deviations

        Raises:
            ValueError: If transcript_path not provided
        """
        if not transcript_path:
            raise ValueError("transcript_path is required")

        # Process transcript
        transcript_data = self._process_transcript(transcript_path)

        # Upload transcript as file (too large for prompt)
        file_ids = []
        logger.info("[WORKFLOW] Uploading transcript file")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as transcript_file:
            json.dump(transcript_data, transcript_file, indent=2)
            transcript_temp_path = transcript_file.name

        try:
            transcript_metadata = await self.ai_provider.upload_file(
                file_path=transcript_temp_path,
                purpose="user_data",
            )
            file_ids.append(transcript_metadata.id)
            logger.info(
                "[WORKFLOW] Transcript uploaded", file_id=transcript_metadata.id
            )
        finally:
            # Clean up temporary file
            os.unlink(transcript_temp_path)

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
        DynamicDiscrepancyResult = self._create_dynamic_deviation_model(
            filtered_class_labels
        )

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

        # Format estimate for prompt
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

        # Use the module-level prompt (loaded once at import time)
        # Build prompt with variables (transcript uploaded as file, not embedded)
        prompt_params = DISCREPANCY_DETECTION_PROMPT.build(
            deviation_classes=deviation_classes_formatted,
            notes_to_production=json.dumps(notes_to_production, indent=2),
            estimate_data=json.dumps(formatted_estimate, indent=2),
        )

        # Extract the user message content from the built prompt
        # Braintrust prompts return messages array, we need just the text for our API
        user_message = None
        for msg in prompt_params.get("messages", []):
            if msg.get("role") == "user":
                user_message = msg.get("content")
                break

        if not user_message:
            raise ValueError("No user message found in Braintrust prompt")

        # Log the prompt for debugging
        logger.info(
            "[WORKFLOW] Built prompt from Braintrust",
            prompt_preview=user_message,
            prompt_length=len(user_message),
        )

        # Use AI provider to analyze with structured output
        logger.info("[WORKFLOW] Initiating AI analysis")
        result = await self.ai_provider.generate_structured_content(
            prompt=user_message,
            response_schema=DynamicDiscrepancyResult,
            file_ids=file_ids,
            vector_store_ids=[PRICEBOOK_VECTOR_STORE_ID],
        )

        logger.info("[WORKFLOW] Generated deviations", deviations=result.deviations)
        return result.deviations

    def log_workflow_execution(
        self,
        estimate_data: dict,
        form_data: dict | None,
        transcript_data: dict,
        deviations: list[Deviation],
        metadata: dict | None = None,
    ) -> None:
        """Log workflow execution to Braintrust.

        This logs the top-level workflow inputs and outputs. Individual AI provider
        calls are automatically traced if Braintrust logging is enabled.

        Args:
            estimate_data: Estimate data
            form_data: Form data (optional)
            transcript_data: Transcript data
            deviations: Detected deviations
            metadata: Optional metadata (uuid, project_id, etc.)
        """
        if not self.braintrust_logger:
            return

        try:
            # Use JSONAttachment for large inputs
            input_data = {
                "estimate": JSONAttachment(
                    data=estimate_data, filename="estimate.json"
                ),
                "transcript": JSONAttachment(
                    data=transcript_data, filename="transcript.json"
                ),
            }

            if form_data:
                input_data["form"] = JSONAttachment(
                    data=form_data, filename="form.json"
                )

            # Log to Braintrust
            self.braintrust_logger.log(
                input=input_data,
                output={"deviations": [d.model_dump() for d in deviations]},
                metadata=metadata or {},
            )

            logger.info("Logged workflow execution to Braintrust")
        except Exception as e:
            logger.error(f"Failed to log workflow execution to Braintrust: {e}")
