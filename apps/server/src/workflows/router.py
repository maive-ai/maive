"""
Workflow router for orchestration endpoints.

This module contains API endpoints for multi-service workflows,
including call monitoring and CRM integration.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.ai.voice_ai.schemas import CallRequest, CallResponse, VoiceAIErrorResponse
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.workflows.call_monitoring import CallAndWriteToCRMWorkflow
from src.workflows.dependencies import get_call_monitoring_workflow

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post(
    "/call-and-write-results-to-crm", response_model=CallResponse, status_code=201
)
async def call_and_write_results_to_crm(
    request: CallRequest,
    current_user: User = Depends(get_current_user),
    workflow: CallAndWriteToCRMWorkflow = Depends(get_call_monitoring_workflow),
) -> CallResponse:
    """
    Create an outbound call with monitoring and write results to CRM.

    This workflow endpoint orchestrates:
    1. Creating the call via Voice AI provider
    2. Starting background call monitoring and writing results to CRM
    3. Updating CRM with call results when complete

    Args:
        request: The call request with phone number and context
        current_user: The authenticated user
        workflow: The call monitoring and CRM writing workflow from dependency injection

    Returns:
        CallResponse: The call information

    Raises:
        HTTPException: If call creation fails
    """
    result = await workflow.call_and_write_results_to_crm(
        request=request,
        user_id=current_user.id,
    )

    if isinstance(result, VoiceAIErrorResponse):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=result.error
        )

    return result
