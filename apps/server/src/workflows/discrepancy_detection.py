"""
Discrepancy detection workflow using AI provider abstraction.

This workflow analyzes sales calls for discrepancies between:
- Audio conversation content
- Sold estimate details
- Form submissions (Notes to Production)

Uses the AI provider abstraction, defaulting to Gemini but configurable via AI_PROVIDER env var.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm

from src.ai.base import ContentAnalysisRequest
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
        description="Concise explanation of discrepancies found with timestamps (HH:MM:SS format)"
    )


class DiscrepancyDetectionWorkflow:
    """Workflow for detecting discrepancies in sales calls using AI providers."""

    def __init__(self):
        """Initialize the workflow."""
        self.ai_provider = get_ai_provider()
        self.crm_provider = get_crm_provider()

    async def execute_for_job(
        self,
        job_id: int,
        audio_path: str | None = None,
        transcript_path: str | None = None,
        form_submission: dict | None = None,
    ) -> dict:
        """Execute the discrepancy detection workflow for a single job.

        Args:
            job_id: Job ID to analyze
            audio_path: Path to the audio file of the sales call (optional if transcript provided)
            transcript_path: Path to the transcript JSON file (optional, alternative to audio)
            form_submission: Optional form submission data (if already fetched)

        Returns:
            dict: Workflow result with status and details

        Raises:
            CRMError: If CRM operations fail
            Exception: For other errors
        """
        try:
            logger.info("=" * 60)
            logger.info(f"DISCREPANCY DETECTION WORKFLOW - Job {job_id}")
            logger.info("=" * 60)

            # Step 1: Get the job details
            logger.info(f"\nStep 1: Fetching job {job_id}")
            job = await self.crm_provider.get_job(job_id)
            logger.info(f"✅ Job fetched: {job.job_number}")

            project_id = job.project_id
            if not project_id:
                raise CRMError(f"Job {job_id} has no associated project", "NO_PROJECT")

            # Step 2: Get the sold estimate (try job first, then project)
            logger.info("\nStep 2: Getting sold estimate")
            selected_estimate = await self._find_sold_estimate(job_id, project_id)

            logger.info(f"✅ Selected estimate: {selected_estimate.id}")
            logger.info(f"   Name: {selected_estimate.name or '(no name)'}")
            logger.info(
                f"   Total: ${selected_estimate.subtotal + selected_estimate.tax:,.2f}"
            )

            # Step 3: Get estimate items
            logger.info(
                f"\nStep 3: Fetching estimate items for estimate {selected_estimate.id}"
            )
            items_result = await self._fetch_estimate_items(selected_estimate.id)

            # Filter to only include active, customer-facing items visible in GUI/PDF
            # - Items with invoice_item_id are on invoices, not the estimate (not visible in GUI/PDF)
            # - Items with chargeable=False are internal cost tracking (materials/labor included in service items)
            # - Items with chargeable=null or True are customer-facing line items
            active_items = [
                item
                for item in items_result.items
                if item.invoice_item_id is None and item.chargeable is not False
            ]
            filtered_count = len(items_result.items) - len(active_items)
            logger.info(
                f"✅ Found {len(active_items)} active chargeable items (filtered out {filtered_count} invoiced/non-chargeable items)"
            )

            # Save raw estimate data to JSON file
            estimate_data_output = {
                "estimate": selected_estimate.model_dump()
                if hasattr(selected_estimate, "model_dump")
                else selected_estimate.__dict__,
                "items": [
                    item.model_dump() if hasattr(item, "model_dump") else item.__dict__
                    for item in active_items
                ],
            }
            output_filename = f"estimate_data_job_{job_id}_estimate_{selected_estimate.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_filename, "w") as f:
                json.dump(estimate_data_output, f, indent=2, default=str)
            logger.info(f"✅ Estimate data saved to: {output_filename}")

            # Step 4: Get form submission (Notes to Production)
            if form_submission:
                logger.info("\nStep 4: Using provided form submission")
                notes_to_production = self._extract_notes_from_submission(
                    form_submission
                )
            else:
                logger.info(f"\nStep 4: Fetching form submission for job {job_id}")
                notes_to_production = await self._fetch_form_submission(job_id)

            if notes_to_production:
                logger.info("✅ Found Notes to Production data")
            else:
                logger.warning(f"⚠️ No Notes to Production found for job {job_id}")
                notes_to_production = {"message": "No Notes to Production found"}

            # Step 5: Analyze audio/transcript with AI
            logger.info("\nStep 5: Analyzing audio/transcript for discrepancies")
            review_result = await self._analyze_audio(
                audio_path=audio_path,
                transcript_path=transcript_path,
                estimate=selected_estimate,
                estimate_items=active_items,
                notes_to_production=notes_to_production,
            )

            logger.info("✅ Analysis complete")
            logger.info(f"   Needs Review: {review_result.needs_review}")
            logger.info(f"   Explanation: {review_result.hold_explanation}")

            # Step 6: Conditional project hold
            if review_result.needs_review:
                logger.info("\nStep 6: Discrepancy found - Updating project to HOLD")
                await self._put_project_on_hold(
                    project_id, review_result.hold_explanation
                )
                logger.info("✅ Project updated and note added")
            else:
                logger.info("\nStep 6: No discrepancies found - No action needed")

            logger.info("\n✅ DISCREPANCY DETECTION WORKFLOW COMPLETE")

            return {
                "status": "success",
                "job_id": job_id,
                "project_id": project_id,
                "estimate_id": selected_estimate.id,
                "needs_review": review_result.needs_review,
                "explanation": review_result.hold_explanation,
                "action_taken": "project_on_hold"
                if review_result.needs_review
                else "none",
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

    async def _find_sold_estimate(self, job_id: int, project_id: int):
        """Find the sold estimate for a job, with fallback to project-level search.

        Strategy:
        1. Check if the job has a sold estimate
        2. If not, query all estimates for the project and find the sold one
        3. If multiple sold estimates, take the most recent
        """
        tenant_id = getattr(self.crm_provider, "tenant_id", 0)

        # Step 1: Try to find sold estimate for this specific job
        logger.info(f"   Querying estimates for job {job_id}")
        job_estimates_request = EstimatesRequest(
            tenant=int(tenant_id),
            job_id=job_id,
            page=1,
            page_size=50,
        )
        job_estimates_response = await self.crm_provider.get_estimates(
            job_estimates_request
        )
        logger.info(
            f"   Found {len(job_estimates_response.estimates)} estimates for job {job_id}"
        )

        # Check for sold estimates on this job
        job_sold_estimates = [
            e for e in job_estimates_response.estimates if e.sold_on is not None
        ]

        if len(job_sold_estimates) > 0:
            logger.info(
                f"   ✅ Found {len(job_sold_estimates)} sold estimate(s) on job {job_id}"
            )
            if len(job_sold_estimates) > 1:
                estimate_list = ", ".join([str(e.id) for e in job_sold_estimates])
                logger.warning(
                    f"   Multiple sold estimates found: {estimate_list}. Using most recent."
                )
                job_sold_estimates.sort(key=lambda e: e.sold_on, reverse=True)
            return job_sold_estimates[0]

        # Step 2: No sold estimate on job, search at project level
        logger.info(f"   No sold estimate found for job {job_id}")
        logger.info(f"   Searching for sold estimates across project {project_id}")

        project_estimates_request = EstimatesRequest(
            tenant=int(tenant_id),
            project_id=project_id,
            page=1,
            page_size=50,
        )
        project_estimates_response = await self.crm_provider.get_estimates(
            project_estimates_request
        )
        logger.info(
            f"   Found {len(project_estimates_response.estimates)} total estimates for project {project_id}"
        )

        # Filter for sold estimates
        project_sold_estimates = [
            e for e in project_estimates_response.estimates if e.sold_on is not None
        ]

        if len(project_sold_estimates) == 0:
            raise CRMError(
                f"No sold estimates found for job {job_id} or project {project_id}. "
                f"Found {len(project_estimates_response.estimates)} total estimates at project level, but none are sold.",
                "NO_SOLD_ESTIMATE",
            )

        logger.info(
            f"   ✅ Found {len(project_sold_estimates)} sold estimate(s) at project level"
        )

        if len(project_sold_estimates) > 1:
            estimate_list = ", ".join([str(e.id) for e in project_sold_estimates])
            logger.warning(
                f"   Multiple sold estimates found: {estimate_list}. Using most recent."
            )
            project_sold_estimates.sort(key=lambda e: e.sold_on, reverse=True)

        return project_sold_estimates[0]

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

        submission = (
            submissions[0]
            if isinstance(submissions[0], dict)
            else submissions[0].__dict__
        )
        return self._extract_notes_from_submission(submission)

    def _extract_notes_from_submission(self, submission):
        """Extract Notes to Production from a form submission."""
        if hasattr(submission, "units"):
            units = submission.units
        else:
            units = submission.get("units", [])

        for unit in units:
            unit_dict = (
                unit
                if isinstance(unit, dict)
                else unit.__dict__
                if hasattr(unit, "__dict__")
                else {}
            )
            if unit_dict.get("name") == "Notes to Production":
                return unit_dict

        return None

    async def _analyze_audio(
        self,
        audio_path: str | None,
        transcript_path: str | None,
        estimate,
        estimate_items,
        notes_to_production,
    ) -> DiscrepancyReview:
        """Analyze audio/transcript for discrepancies using AI.

        Can handle:
        - Audio only
        - Transcript only
        - Both audio and transcript together
        """
        if not audio_path and not transcript_path:
            raise ValueError("Either audio_path or transcript_path must be provided")

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

        # Load transcript if provided
        transcript_text = None
        if transcript_path:
            logger.info(f"   Loading transcript from: {transcript_path}")
            with open(transcript_path, "r") as f:
                transcript_data = json.load(f)

            # Format transcript for readability
            transcript_lines = []
            for entry in transcript_data:
                speaker = entry.get("speaker", "Unknown")
                text = entry.get("transcript", "")
                timestamp = entry.get("start_time", "00:00:00")
                transcript_lines.append(f"[{timestamp}] {speaker}: {text}")

            transcript_text = "\n".join(transcript_lines)
            logger.info(f"   Loaded transcript with {len(transcript_data)} entries")

        # Build the prompt
        prompt = f"""You are an expert sales admin for a roofing company. You are reviewing a conversation between one of our sales reps and a customer. The conversation may be provided as audio, transcript, or both.

Please review and understand the contents of the conversation, the estimate, and any notes to production that the sales rep submitted via form following the conversation.

Identify what, if anything, mentioned during the conversation that was not updated in the estimate or logged in the form. If there is any information that would affect the roofing service provided or how it is provided, then please flag the conversation for review.

Simply and concisely log what was not included in the estimate or form but stated during the conversation. In this concise message of the discrepancy, please include a timestamp when the discrepancy occurred in format (HH:MM:SS).

There are several fields in the conversation, production, notes, and estimate that you should consider for this analysis.
- Shingle type, color, brand
- Replacing pipe boots with rubber synthetic with mesh

There are several fields in the estimate that you should explicity NOT consider for this analysis. DO NOT mention them in your response.
- Customer's name
- Insulation, spray foam insulation
- Roof decking material type
- Plank decking

**Estimate Contents:**
{json.dumps(estimate_data, indent=2)}

**Notes to Production:**
{json.dumps(notes_to_production, indent=2)}
"""

        # Use AI provider to analyze with structured output
        logger.info("   Initiating AI analysis...")

        request = ContentAnalysisRequest(
            audio_path=audio_path,
            transcript_text=transcript_text,
            prompt=prompt,
            temperature=0.7,
        )

        review_result = await self.ai_provider.analyze_content_with_structured_output(
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
    parser = argparse.ArgumentParser(
        description="Analyze sales calls for discrepancies in form submissions within a time range"
    )
    parser.add_argument(
        "--audio-path",
        help="Path to the audio file of the sales call (optional if transcript provided)",
    )
    parser.add_argument(
        "--transcript-path",
        help="Path to the transcript JSON file (optional if audio provided)",
    )
    parser.add_argument(
        "--job-id",
        type=int,
        help="Specific job ID to analyze (skips time-based form submission search)",
    )
    parser.add_argument(
        "--start-time",
        default="2025-07-03T12:25:00-07:00",
        help="Start time for form submissions (ISO format with timezone: YYYY-MM-DDTHH:MM:SS±HH:MM). Default: 2025-07-03T12:25:00-07:00 (PDT)",
    )
    parser.add_argument(
        "--end-time",
        default="2025-07-03T12:30:00-07:00",
        help="End time for form submissions (ISO format with timezone: YYYY-MM-DDTHH:MM:SS±HH:MM). Default: 2025-07-03T12:30:00-07:00 (PDT)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.audio_path and not args.transcript_path:
        parser.error("Either --audio-path or --transcript-path must be provided")

    workflow = DiscrepancyDetectionWorkflow()

    # Handle single job analysis if job-id is provided
    if args.job_id:
        logger.info("=" * 60)
        logger.info("SINGLE JOB DISCREPANCY DETECTION WORKFLOW")
        logger.info("=" * 60)
        logger.info(f"Job ID: {args.job_id}")
        if args.audio_path:
            logger.info(f"Audio file: {args.audio_path}")
        if args.transcript_path:
            logger.info(f"Transcript file: {args.transcript_path}")
        logger.info("")

        try:
            result = await workflow.execute_for_job(
                job_id=args.job_id,
                audio_path=args.audio_path,
                transcript_path=args.transcript_path,
            )

            print("\n" + "=" * 60)
            print("WORKFLOW RESULT")
            print("=" * 60)
            print(json.dumps(result, indent=2, default=str))
            print("=" * 60)

        except Exception as e:
            logger.error(f"Failed to process job {args.job_id}: {e}")
            raise

        return

    # Parse timestamps for batch processing
    start_time = datetime.fromisoformat(args.start_time)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    end_time = datetime.fromisoformat(args.end_time)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    logger.info("=" * 60)
    logger.info("BATCH DISCREPANCY DETECTION WORKFLOW")
    logger.info("=" * 60)
    logger.info(f"Time range: {start_time} to {end_time}")
    if args.audio_path:
        logger.info(f"Audio file: {args.audio_path}")
    if args.transcript_path:
        logger.info(f"Transcript file: {args.transcript_path}")
    logger.info("")

    # Step 1: Fetch all form submissions in the time range
    logger.info("Fetching form submissions in time range...")
    tenant_id = getattr(workflow.crm_provider, "tenant_id", 0)

    # Note: ServiceTitan API doesn't support time-based filtering directly,
    # so we'll fetch recent submissions and filter by submitted_on
    form_request = FormSubmissionsRequest(
        tenant=int(tenant_id),
        form_id=2933,  # Appointment Result V2
        page=1,
        page_size=200,  # Fetch more to ensure we get all in the time range
        status="Any",
    )

    form_result = await workflow.crm_provider.get_form_submissions(form_request)

    # Filter submissions by time range
    submissions_in_range = []
    for submission in form_result.data:
        submitted_on = (
            submission.submitted_on
            if hasattr(submission, "submitted_on")
            else submission.get("submitted_on")
        )
        if submitted_on and start_time <= submitted_on <= end_time:
            submissions_in_range.append(submission)

    logger.info(f"Found {len(submissions_in_range)} form submissions in time range")

    if not submissions_in_range:
        logger.warning("No form submissions found in the specified time range")
        return

    # Step 2: Extract job IDs from submissions
    job_ids = []
    submission_by_job = {}

    for submission in submissions_in_range:
        owners = (
            submission.owners
            if hasattr(submission, "owners")
            else submission.get("owners", [])
        )
        for owner in owners:
            owner_dict = (
                owner
                if isinstance(owner, dict)
                else owner.__dict__
                if hasattr(owner, "__dict__")
                else {}
            )
            if owner_dict.get("type") == "Job":
                job_id = owner_dict.get("id")
                if job_id:
                    job_ids.append(job_id)
                    submission_by_job[job_id] = submission

    logger.info(f"Found {len(job_ids)} unique jobs to process")
    logger.info("")

    # Step 3: Process each job
    results = []
    failed_jobs = []

    for job_id in tqdm(job_ids, desc="Processing jobs"):
        try:
            result = await workflow.execute_for_job(
                job_id=job_id,
                audio_path=args.audio_path,
                transcript_path=args.transcript_path,
                form_submission=submission_by_job.get(job_id),
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process job {job_id}: {e}")
            failed_jobs.append({"job_id": job_id, "error": str(e)})

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("BATCH WORKFLOW RESULTS")
    print("=" * 60)
    print(f"Total jobs processed: {len(results)}")
    print(f"Failed jobs: {len(failed_jobs)}")

    needs_review_count = sum(1 for r in results if r.get("needs_review"))
    print(f"Jobs needing review: {needs_review_count}")
    print("")

    if results:
        print("Successful results:")
        print(json.dumps(results, indent=2, default=str))

    if failed_jobs:
        print("\nFailed jobs:")
        print(json.dumps(failed_jobs, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
