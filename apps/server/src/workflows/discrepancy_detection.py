"""
Discrepancy detection workflow using AI provider abstraction.

This workflow analyzes sales calls for discrepancies between:
- Audio conversation content
- Sold estimate details
- Form submissions (Notes to Production)

Uses the AI provider abstraction, defaulting to Gemini but configurable via AI_PROVIDER env var.
"""

import asyncio
import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.ai.base import AudioAnalysisRequest
from src.ai.providers import get_ai_provider
from src.integrations.crm.base import CRMError
from src.integrations.crm.constants import SubStatus
from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.schemas import (
    EstimateItemsRequest,
    EstimatesRequest,
    ExternalDataItem,
    FormSubmissionOwnerFilter,
    FormSubmissionsRequest,
    ProjectByIdRequest,
    UpdateProjectRequest,
)
from src.utils.logger import logger


class DiscrepancyReview(BaseModel):
    """Structured output for discrepancy review."""

    needs_review: bool = Field(
        description="True if discrepancies were found and the job needs review, False otherwise"
    )
    hold_explanation: str = Field(
        description="Concise explanation of discrepancies found with timestamps (MM:SS format)"
    )


class DiscrepancyDetectionWorkflow:
    """Workflow for detecting discrepancies in sales calls using AI providers."""

    def __init__(self):
        """Initialize the workflow."""
        self.ai_provider = get_ai_provider()
        self.crm_provider = get_crm_provider()

    async def execute(
        self,
        project_id: int,
        audio_path: str,
        known_sold_estimate_id: int | None = None,
    ) -> dict:
        """Execute the discrepancy detection workflow.

        Args:
            project_id: Project ID to analyze
            audio_path: Path to the audio file of the sales call
            known_sold_estimate_id: Optional known estimate ID (for manual override)

        Returns:
            dict: Workflow result with status and details

        Raises:
            CRMError: If CRM operations fail
            Exception: For other errors
        """
        try:
            logger.info("=" * 60)
            logger.info(f"DISCREPANCY DETECTION WORKFLOW - Project {project_id}")
            logger.info("=" * 60)

            # Step 1: Fetch project details
            logger.info(f"\nStep 1: Fetching project {project_id}")
            project = await self._fetch_project(project_id)
            logger.info(f"✅ Project fetched: {project.number}")

            # Step 2: Get the sold estimate
            logger.info("\nStep 2: Getting sold estimate")
            if known_sold_estimate_id:
                logger.info(f"   Using known estimate ID: {known_sold_estimate_id}")
                selected_estimate = await self.crm_provider.get_estimate(
                    known_sold_estimate_id
                )
            else:
                logger.info("   Auto-discovering sold estimate...")
                selected_estimate = await self._find_sold_estimate(project_id)

            logger.info(f"✅ Selected estimate: {selected_estimate.id}")
            logger.info(f"   Name: {selected_estimate.name or '(no name)'}")
            logger.info(f"   Total: ${selected_estimate.subtotal + selected_estimate.tax:,.2f}")

            job_id = selected_estimate.job_id
            if not job_id:
                raise CRMError(
                    f"Selected estimate {selected_estimate.id} has no associated job",
                    "NO_JOB",
                )

            # Step 3: Get estimate items
            logger.info(f"\nStep 3: Fetching estimate items for estimate {selected_estimate.id}")
            items_result = await self._fetch_estimate_items(selected_estimate.id)
            logger.info(f"✅ Found {len(items_result.items)} items")

            # Step 4: Get form submission (Notes to Production)
            logger.info(f"\nStep 4: Fetching form submission for job {job_id}")
            notes_to_production = await self._fetch_form_submission(job_id)

            if notes_to_production:
                logger.info("✅ Found Notes to Production data")
            else:
                logger.warning(f"⚠️ No Notes to Production found for job {job_id}")
                notes_to_production = {"message": "No Notes to Production found"}

            # Step 5: Analyze audio with AI
            logger.info("\nStep 5: Analyzing audio for discrepancies")
            review_result = await self._analyze_audio(
                audio_path=audio_path,
                estimate=selected_estimate,
                estimate_items=items_result.items,
                notes_to_production=notes_to_production,
            )

            logger.info("✅ Analysis complete")
            logger.info(f"   Needs Review: {review_result.needs_review}")
            logger.info(f"   Explanation: {review_result.hold_explanation}")

            # Step 6: Conditional project hold
            if review_result.needs_review:
                logger.info("\nStep 6: Discrepancy found - Updating project to HOLD")
                await self._put_project_on_hold(project_id, review_result.hold_explanation)
                logger.info("✅ Project updated and note added")
            else:
                logger.info("\nStep 6: No discrepancies found - No action needed")

            logger.info("\n✅ DISCREPANCY DETECTION WORKFLOW COMPLETE")

            return {
                "status": "success",
                "project_id": project_id,
                "estimate_id": selected_estimate.id,
                "needs_review": review_result.needs_review,
                "explanation": review_result.hold_explanation,
                "action_taken": "project_on_hold" if review_result.needs_review else "none",
            }

        except CRMError as e:
            logger.error(
                f"❌ CRM error during workflow: {e.message} (Code: {e.error_code})"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error during workflow: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise

    async def _fetch_project(self, project_id: int):
        """Fetch project details."""
        # Get tenant_id if available (ServiceTitan), default to 0 for Mock
        tenant_id = getattr(self.crm_provider, "tenant_id", 0)
        project_request = ProjectByIdRequest.model_validate(
            {"tenant": int(tenant_id), "projectId": project_id}
        )
        return await self.crm_provider.get_project_by_id(project_request)

    async def _find_sold_estimate(self, project_id: int):
        """Find the sold estimate for a project."""
        logger.info(f"   Querying estimates by project ID: {project_id}")

        tenant_id = getattr(self.crm_provider, "tenant_id", 0)
        estimates_request = EstimatesRequest(
            tenant=int(tenant_id),
            project_id=project_id,
            page=1,
            page_size=50,
        )

        estimates_response = await self.crm_provider.get_estimates(estimates_request)
        logger.info(
            f"   Found {len(estimates_response.estimates)} estimates for project {project_id}"
        )

        # Filter for sold estimates (has sold_on date)
        sold_estimates = [e for e in estimates_response.estimates if e.sold_on is not None]

        for estimate in estimates_response.estimates:
            status_info = f"sold_on={estimate.sold_on}"
            if estimate.sold_on:
                logger.info(
                    f"   - Estimate {estimate.id}: {estimate.name or '(no name)'} - SOLD ({status_info})"
                )
            else:
                logger.info(
                    f"   - Estimate {estimate.id}: {estimate.name or '(no name)'} - NOT SOLD ({status_info})"
                )

        if len(sold_estimates) == 0:
            error_msg = (
                f"No sold estimates found for project {project_id}. "
                f"Found {len(estimates_response.estimates)} total estimates, but none are marked as sold."
            )
            raise CRMError(error_msg, "NO_SOLD_ESTIMATE")
        elif len(sold_estimates) > 1:
            estimate_list = ", ".join([str(e.id) for e in sold_estimates])
            error_msg = f"Multiple sold estimates found for project {project_id}: {estimate_list}"
            raise CRMError(error_msg, "MULTIPLE_SOLD_ESTIMATES")

        return sold_estimates[0]

    async def _fetch_estimate_items(self, estimate_id: int):
        """Fetch items for an estimate."""
        tenant_id = getattr(self.crm_provider, "tenant_id", 0)
        items_request = EstimateItemsRequest(
            tenant=int(tenant_id),
            estimate_id=estimate_id,
            page=1,
            page_size=50,
        )
        return await self.crm_provider.get_estimate_items(items_request)

    async def _fetch_form_submission(self, job_id: int):
        """Fetch form submission (Notes to Production) for a job."""
        tenant_id = getattr(self.crm_provider, "tenant_id", 0)
        form_request = FormSubmissionsRequest(
            tenant=int(tenant_id),
            form_id=2933,  # Appointment Result V2
            page=1,
            page_size=10,
            status="Any",
            owners=[FormSubmissionOwnerFilter(type="Job", id=job_id)],
        )
        form_result = await self.crm_provider.get_form_submissions(form_request)

        # Extract Notes to Production
        submissions = form_result.data
        if not submissions:
            return None

        submission = submissions[0]
        units = submission.get("units", [])
        for unit in units:
            if isinstance(unit, dict) and unit.get("name") == "Notes to Production":
                return unit

        return None

    async def _analyze_audio(
        self,
        audio_path: str,
        estimate,
        estimate_items,
        notes_to_production,
    ) -> DiscrepancyReview:
        """Analyze audio for discrepancies using AI."""
        # Format estimate data
        estimate_data = {
            "estimate_id": estimate.id,
            "name": estimate.name,
            "subtotal": estimate.subtotal,
            "tax": estimate.tax,
            "items": [
                {
                    "description": item.description,
                    "quantity": item.qty,
                    "unit_rate": item.unit_rate,
                    "total": item.total,
                    "sku_name": item.sku.name,
                }
                for item in estimate_items
            ],
        }

        prompt = f"""You are an expert sales admin for a roofing company. You are reviewing the audio from a conversation between one of our sales reps and a customer. Please listen to and understand the contents of the audio conversation, the contents of the estimate, and any notes to production that the sales rep submitted via form following the conversation.

Identify what, if anything, mentioned during the conversation that was not updated in the estimate or logged in the form. If there is any information that would affect the roofing service provided or how it is provided, then please flag the conversation for review.

Simply and concisely log what was not included in the estimate or form but stated during the audio conversation. In this concise message of the discrepancy, please include a timestamp in the audio when the discrepancy occurred in format (MM:SS).

**Estimate Contents:**
{json.dumps(estimate_data, indent=2)}

**Notes to Production:**
{json.dumps(notes_to_production, indent=2)}
"""

        request = AudioAnalysisRequest(
            audio_path=audio_path,
            prompt=prompt,
            temperature=0.7,
        )

        # Use AI provider to analyze audio with structured output
        logger.info(f"   Using AI provider: {self.ai_provider.__class__.__name__}")
        review_result = await self.ai_provider.analyze_audio_with_structured_output(
            request=request,
            response_model=DiscrepancyReview,
        )

        return review_result

    async def _put_project_on_hold(self, project_id: int, explanation: str):
        """Put project on hold and add a note."""
        # Update project status to HOLD with Sales Hold substatus
        tenant_id = getattr(self.crm_provider, "tenant_id", 0)
        update_request = UpdateProjectRequest(
            tenant=int(tenant_id),
            project_id=project_id,
            status_id=383,  # Hold status ID
            sub_status_id=SubStatus.SALES_SALES_HOLD.value,
            external_data=[
                ExternalDataItem(key="managed_by", value="maive_ai"),
                ExternalDataItem(key="action", value="discrepancy_detected"),
                ExternalDataItem(key="timestamp", value=datetime.now(UTC).isoformat()),
            ],
        )

        await self.crm_provider.update_project(update_request)
        logger.info("✅ Project updated to HOLD status")

        # Add note to project
        note_text = f"Maive AI - I detected job details discussed in sales call not being tracked in Service Titan: {explanation}"
        logger.info("   Adding note to project (pinned to top):")
        logger.info(f"   Note content: {note_text}")

        await self.crm_provider.add_project_note(
            project_id=project_id, text=note_text, pin_to_top=True
        )


async def main():
    """Main entry point for standalone execution."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m src.workflows.discrepancy_detection <project_id> <audio_path> [estimate_id]")
        print("\nExample:")
        print("  python -m src.workflows.discrepancy_detection 261980979 ./audio.mp3")
        print("  python -m src.workflows.discrepancy_detection 261980979 ./audio.mp3 12345")
        sys.exit(1)

    project_id = int(sys.argv[1])
    audio_path = sys.argv[2]
    estimate_id = int(sys.argv[3]) if len(sys.argv) > 3 else None

    workflow = DiscrepancyDetectionWorkflow()
    result = await workflow.execute(
        project_id=project_id,
        audio_path=audio_path,
        known_sold_estimate_id=estimate_id,
    )

    print("\n" + "=" * 60)
    print("WORKFLOW RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
