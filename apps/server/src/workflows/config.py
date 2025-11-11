"""Configuration for workflows."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DiscrepancyDetectionWorkflowSettings(BaseSettings):
    """Settings for Discrepancy Detection workflow.

    Attributes:
        enable_braintrust_logging: Enable Braintrust tracing for AI calls and workflow execution
        braintrust_project_name: Braintrust project name
    """

    model_config = SettingsConfigDict(
        env_prefix="WORKFLOWS_DISCREPANCY_DETECTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enable_braintrust_logging: bool = Field(
        default=False,
        description="Enable Braintrust tracing for AI calls and workflow execution",
    )
    braintrust_project_name: str = Field(
        default="discrepancy-detection",
        description="Braintrust project name",
    )


@lru_cache
def get_discrepancy_detection_settings() -> DiscrepancyDetectionWorkflowSettings:
    """Get cached discrepancy detection workflow settings.

    Returns:
        DiscrepancyDetectionWorkflowSettings: Cached settings instance
    """
    return DiscrepancyDetectionWorkflowSettings()
