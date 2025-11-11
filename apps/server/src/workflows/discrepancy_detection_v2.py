import json
import os
from pathlib import Path

from braintrust import JSONAttachment, init_logger
from pydantic import BaseModel, Field

from evals.estimate_deviation.schemas import (
    Deviation,
    DeviationOccurrence,
    PredictedLineItem,
)
from src.ai.base import ContentAnalysisRequest
from src.ai.providers import get_ai_provider
from src.utils.logger import logger
from src.utils.rilla import simplify_rilla_transcript
from src.workflows.config import get_discrepancy_detection_settings

# Force OpenAI provider for this workflow
os.environ["AI_PROVIDER"] = "openai"

# Pricebook vector store ID (created via scripts/ingest_pricebook.py)
PRICEBOOK_VECTOR_STORE_ID = "vs_690e9d9523a8819192c6f111227b90a5"


class DiscrepancyDetectionV2Workflow:
    """Core discrepancy detection workflow logic.

    Analyzes estimate, form, and transcript data to identify discrepancies.
    Pure workflow logic with no S3 or dataset dependencies.
    """

    def __init__(self, level: int = 1, enable_braintrust: bool | None = None):
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

    async def _analyze_content(
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
        DynamicDiscrepancyResult = self._create_dynamic_deviation_model(
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
        logger.info("Initiating AI analysis...")

        request = ContentAnalysisRequest(
            audio_path=None,  # No audio for now
            transcript_text=transcript_json,  # Pass compact JSON as text
            prompt=prompt,
            temperature=0.7,
            vector_store_ids=[PRICEBOOK_VECTOR_STORE_ID],
        )

        result = await self.ai_provider.analyze_content_with_structured_output(
            request=request,
            response_model=DynamicDiscrepancyResult,
        )

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
