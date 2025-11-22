"""
Workflow-specific Pydantic schemas.

This module contains schemas for workflow requests and responses.
"""

from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    """AI-generated project summary with structured information."""

    summary: str = Field(
        ..., description="Brief one-sentence summary of the project status"
    )
    recent_actions: list[str] = Field(
        default_factory=list,
        description="List of recent actions taken on the project (2-3 bullet points)",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="List of recommended next steps (2-3 bullet points)",
    )
