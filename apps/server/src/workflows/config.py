"""Configuration for workflows."""

from functools import lru_cache

from braintrust import load_prompt
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logger import logger


class DiscrepancyDetectionWorkflowSettings(BaseSettings):
    """Settings for Discrepancy Detection workflow.

    Attributes:
        enable_braintrust_logging: Enable Braintrust tracing for AI calls and workflow execution
        braintrust_project_name: Braintrust project name
        prompt_version: Specific prompt version to pin (optional)
    """

    model_config = SettingsConfigDict(
        env_prefix="WORKFLOWS_DISCREPANCY_DETECTION_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enable_braintrust_logging: bool = Field(
        env_prefix="WORKFLOWS_DISCREPANCY_DETECTION_",
        default=False,
        description="Enable Braintrust tracing for AI calls and workflow execution",
    )
    braintrust_project_name: str = Field(
        env_prefix="WORKFLOWS_DISCREPANCY_DETECTION_",
        default="discrepancy-detection",
        description="Braintrust project name",
    )
    prompt_version: str | None = Field(
        env_prefix="WORKFLOWS_DISCREPANCY_DETECTION_",
        default=None,
        description="Specific Braintrust prompt version to pin (numeric string like '1000196126440992772'). If None, uses latest version.",
    )


@lru_cache
def get_discrepancy_detection_settings() -> DiscrepancyDetectionWorkflowSettings:
    """Get cached discrepancy detection workflow settings.

    Returns:
        DiscrepancyDetectionWorkflowSettings: Cached settings instance
    """
    return DiscrepancyDetectionWorkflowSettings()


# Load prompt once at module import time
def _load_discrepancy_detection_prompt():
    """Load the discrepancy detection prompt from Braintrust.

    This is called once when the module is imported to avoid loading on every request.
    """
    settings = get_discrepancy_detection_settings()

    try:
        if settings.prompt_version:
            logger.info(
                "Loading pinned prompt version from Braintrust",
                version=settings.prompt_version,
            )
            return load_prompt(
                project=settings.braintrust_project_name,
                slug="discrepancy-detection-prompt",
                version=settings.prompt_version,
            )
        else:
            logger.info("Loading latest prompt version from Braintrust")
            return load_prompt(
                project=settings.braintrust_project_name,
                slug="discrepancy-detection-prompt",
            )
    except Exception as e:
        logger.error("Failed to load prompt from Braintrust", error=str(e))
        raise


# Load prompt at module initialization (happens once per import)
DISCREPANCY_DETECTION_PROMPT = _load_discrepancy_detection_prompt()
