"""
FastAPI dependencies for workflow orchestration.

This module provides dependency injection functions for workflow-related
FastAPI endpoints, composing multiple services together.
"""

from fastapi import Depends

from src.ai.voice_ai.dependencies import get_voice_ai_service
from src.ai.voice_ai.service import VoiceAIService
from src.db.calls.repository import CallRepository
from src.db.dependencies import get_call_repository
from src.integrations.crm.dependencies import get_crm_service
from src.integrations.crm.service import CRMService
from src.workflows.call_monitoring import CallAndWriteToCRMWorkflow
from src.workflows.project_summary import ProjectSummaryWorkflow


def get_call_monitoring_workflow(
    voice_ai_service: VoiceAIService = Depends(get_voice_ai_service),
    crm_service: CRMService = Depends(get_crm_service),
    call_repository: CallRepository = Depends(get_call_repository),
) -> CallAndWriteToCRMWorkflow:
    """
    FastAPI dependency for getting the call monitoring workflow.

    This workflow orchestrates Voice AI call creation and CRM updates.

    Args:
        voice_ai_service: The Voice AI service from dependency injection
        crm_service: The CRM service from dependency injection
        call_repository: The call repository from dependency injection

    Returns:
        CallAndWriteToCRMWorkflow: The workflow instance
    """
    return CallAndWriteToCRMWorkflow(
        voice_ai_service=voice_ai_service,
        crm_service=crm_service,
        call_repository=call_repository,
    )


def get_project_summary_workflow(
    crm_service: CRMService = Depends(get_crm_service),
) -> ProjectSummaryWorkflow:
    """
    FastAPI dependency for getting the project summary workflow.

    This workflow generates AI-powered summaries of projects based on their notes.

    Args:
        crm_service: The CRM service from dependency injection

    Returns:
        ProjectSummaryWorkflow: The workflow instance
    """
    return ProjectSummaryWorkflow(crm_service=crm_service)
