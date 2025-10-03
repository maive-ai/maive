"""
Vertex test application for Service Titan project status.

This application fetches a specific completed project for testing purposes.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from src.ai.gemini import get_gemini_client
from src.ai.gemini.schemas import FileUploadRequest, GenerateStructuredContentRequest
from src.integrations.crm.base import CRMError
from src.integrations.crm.constants import (
    JOB_HOLD_REASON_NAMES,
    FormStatus,
    JobHoldReasonId,
    Status,
    SubStatus,
)
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.crm.schemas import (
    EstimateItemsRequest,
    EstimatesRequest,
    ExternalDataItem,
    UpdateProjectRequest,
)
from src.integrations.rilla.client import RillaClient
from src.integrations.rilla.config import get_rilla_settings
from src.integrations.rilla.service import RillaService
from src.utils.logger import logger


class DiscrepancyReview(BaseModel):
    """Structured output for discrepancy review."""

    needs_review: bool = Field(
        description="True if discrepancies were found and the job needs review, False otherwise"
    )
    hold_explanation: str = Field(
        description="Concise explanation of discrepancies found with timestamps (MM:SS format)"
    )


class VertexTester:
    """Tester for Service Titan single project status."""

    def __init__(self):
        """Initialize the vertex tester."""
        self.provider = ServiceTitanProvider()

        # Initialize Rilla client and service manually (not using FastAPI dependency)
        rilla_settings = get_rilla_settings()
        rilla_client = RillaClient(settings=rilla_settings)
        self.rilla_service = RillaService(rilla_client=rilla_client)

        # Form submissions test configuration
        self.test_form_ids = [2933]  # Appointment Result V2

    async def test_form_submissions(self) -> None:
        """Test the form submissions endpoint for completed forms."""
        try:
            current_time = datetime.now(UTC).isoformat()
            logger.info(f"[{current_time}] Starting Form Submissions test")

            logger.info(f"Testing form submissions for form IDs: {self.test_form_ids}")
            logger.info(f"With status: {FormStatus.COMPLETED}")
            logger.info("No owner filter applied - querying all completed submissions")

            # Get form submissions with completed status, no owner filter
            submissions_response = await self.provider.get_all_form_submissions(
                form_ids=self.test_form_ids, status=FormStatus.COMPLETED.value
            )

            logger.info("✅ Form submissions response:")
            logger.info(f"   Total submissions: {submissions_response.total_count}")
            logger.info(f"   Submissions in response: {len(submissions_response.data)}")

            # Log details of first few submissions
            if submissions_response.data:
                logger.info("\\n📋 First 5 completed form submissions:")
                for i, submission in enumerate(submissions_response.data[:5]):
                    logger.info(f"\\n   [{i + 1}] Submission {submission.id}")
                    logger.info(f"       Status: {submission.status}")
                    logger.info(f"       Submitted On: {submission.submitted_on}")
                    logger.info(f"       Form ID: {submission.form_id}")
                    if submission.form_name:
                        logger.info(f"       Form Name: {submission.form_name}")
                    if submission.owners:
                        logger.info(f"       Owners: {len(submission.owners)} owner(s)")
            else:
                logger.warning(
                    "⚠️ No completed form submissions found for the specified form"
                )

            logger.info(f"[{current_time}] FORM SUBMISSIONS TEST COMPLETE")

        except CRMError as e:
            logger.error(
                f"CRM error during form submissions test: {e.message} (Code: {e.error_code})"
            )
        except Exception as e:
            logger.error(f"Unexpected error during form submissions test: {e}")

    async def test_project_hierarchy(self) -> None:
        """Test the full Project -> Jobs -> Appointments hierarchy by iterating through the proper relationships."""
        try:
            current_time = datetime.now(UTC).isoformat()
            logger.info(
                f"[{current_time}] Starting Project->Jobs->Appointments hierarchy test"
            )

            # Step 1: Find the actual project that contains our test job
            actual_project_id = await self.find_project_with_job()
            if actual_project_id:
                self.test_project_id = actual_project_id
                logger.info(f"Using actual project ID: {self.test_project_id}")
            else:
                logger.info(f"Using fallback project ID: {self.test_project_id}")

            # Step 2: Get project details and try to find its jobs
            logger.info(
                f"[{current_time}] Step 1: Fetching project {self.test_project_id}"
            )
            project = await self.provider.get_project_status(self.test_project_id)
            logger.info(f"  └─ Project {self.test_project_id}:")
            logger.info(f"      ├─ Status: {project.status}")
            logger.info(
                f"      └─ Original Status: {project.provider_data.get('original_status', 'N/A')}"
            )

            # Step 3: Since projects don't directly contain jobIds, we'll search jobs that reference this project
            logger.info(
                f"[{current_time}] Step 2: Finding jobs that belong to project {self.test_project_id}"
            )
            jobs_response = await self.provider.get_all_job_statuses()

            project_jobs = []
            for job in jobs_response.projects[:50]:  # Check first 50 jobs
                job_provider_data = job.provider_data or {}
                job_project_id = job_provider_data.get("projectId")

                if str(job_project_id) == self.test_project_id:
                    project_jobs.append(job.project_id)

            if project_jobs:
                logger.info(
                    f"Found {len(project_jobs)} job(s) for project {self.test_project_id}: {project_jobs}"
                )
            else:
                logger.warning(
                    f"No jobs found for project {self.test_project_id}, using test job {self.test_job_id}"
                )
                project_jobs = [self.test_job_id]

            # Step 4: For each job, get its details and find associated appointments
            logger.info(
                f"[{current_time}] Step 3: Processing jobs and their appointments"
            )
            for i, job_id in enumerate(project_jobs[:3]):  # Process first 3 jobs
                logger.info(
                    f"Processing job {i + 1}/{min(len(project_jobs), 3)}: {job_id}"
                )

                try:
                    job = await self.provider.get_job_status(str(job_id))
                    logger.info(f"  └─ Job {job_id}:")
                    logger.info(f"      ├─ Status: {job.status}")

                    # Get all appointments and find ones for this job
                    appointments_response = (
                        await self.provider.get_all_appointment_statuses()
                    )
                    job_appointments = []

                    for appt in appointments_response.projects:
                        appt_provider_data = appt.provider_data or {}
                        appt_job_id = appt_provider_data.get("job_id")

                        if str(appt_job_id) == str(job_id):
                            job_appointments.append(appt.project_id)

                    if job_appointments:
                        logger.info(
                            f"      └─ Found {len(job_appointments)} appointment(s): {job_appointments}"
                        )

                        # Get details for first appointment
                        appointment_id = job_appointments[0]
                        appointment = await self.provider.get_appointment_status(
                            str(appointment_id)
                        )
                        appt_provider_data = appointment.provider_data or {}

                        start_time = appt_provider_data.get("start_time")
                        end_time = appt_provider_data.get("end_time")

                        logger.info(f"          └─ Appointment {appointment_id}:")
                        logger.info(f"              ├─ Status: {appointment.status}")
                        logger.info(f"              ├─ Start: {start_time}")
                        logger.info(f"              └─ End: {end_time}")

                        # Query Rilla for conversations related to this appointment
                        if start_time and end_time:
                            try:
                                logger.info("Querying Rilla API...")
                                response = await self.rilla_service.get_conversations_for_appointment(
                                    appointment_id=str(appointment_id),
                                    start_time=start_time,
                                    end_time=end_time,
                                )

                                if response.conversations:
                                    logger.info(
                                        f"✅ Found {len(response.conversations)} Rilla conversation(s)"
                                    )
                                    logger.info(
                                        f"   (Page {response.current_page}/{response.total_pages}, Total: {response.total_conversations})"
                                    )
                                    for conv in response.conversations:
                                        logger.info(
                                            f"├─ {conv.title} ({conv.duration}s)"
                                        )
                                        logger.info(f"├─ User: {conv.user.name}")
                                        logger.info(f"└─ URL: {conv.rilla_url}")
                                else:
                                    logger.warning("⚠️ No Rilla conversations found")
                            except Exception as e:
                                logger.error(f"❌ Error querying Rilla: {e}")
                        else:
                            logger.warning(
                                "⚠️ Missing timing data, skipping Rilla query"
                            )

                    else:
                        logger.info(f"      └─ No appointments found for job {job_id}")

                except CRMError as e:
                    logger.error(f"Failed to get job {job_id}: {e.message}")

            logger.info(f"[{current_time}] HIERARCHY TEST COMPLETE")
            logger.info(
                "✅ Successfully demonstrated Project->Jobs->Appointments hierarchy with iterating over relationships!"
            )

        except CRMError as e:
            logger.error(
                f"CRM error during hierarchy test: {e.message} (Code: {e.error_code})"
            )
        except Exception as e:
            logger.error(f"Unexpected error during hierarchy test: {e}")

    async def test_rilla_recent(self) -> None:
        """Test Rilla API with recent data (last 24 hours)."""
        try:
            now = datetime.now(UTC)
            start_time = now - timedelta(hours=24)
            end_time = now

            logger.info("=" * 60)
            logger.info("TESTING RILLA API - Last 24 hours")
            logger.info(f"Time range: {start_time} to {end_time}")
            logger.info("=" * 60)

            # Query without filtering by appointment_id (pass None to see all conversations)
            response = await self.rilla_service.get_conversations_for_appointment(
                appointment_id=None,
                start_time=start_time,
                end_time=end_time,
                padding_hours=0,  # No padding since we're already using 24 hours
            )

            logger.info("✅ Rilla API Response:")
            logger.info(f"   Total conversations: {response.total_conversations}")
            logger.info(
                f"   Current page: {response.current_page}/{response.total_pages}"
            )
            logger.info(f"   Conversations in this page: {len(response.conversations)}")

            if response.conversations:
                logger.info("\n📋 First 3 conversations:")
                for i, conv in enumerate(response.conversations[:3]):
                    logger.info(f"\n   [{i + 1}] {conv.title}")
                    logger.info(f"       Date: {conv.date}")
                    logger.info(f"       Duration: {conv.duration}s")
                    logger.info(f"       CRM Event ID: {conv.crm_event_id}")
                    logger.info(f"       User: {conv.user.name}")
            else:
                logger.warning("⚠️  No conversations found in the last 24 hours")

        except Exception as e:
            logger.error(f"❌ Error testing Rilla: {e}")

    async def test_gemini_joke(self) -> None:
        """Test Gemini API with a simple joke request."""
        try:
            logger.info("=" * 60)
            logger.info("TESTING GEMINI API - Tell me a joke")
            logger.info("=" * 60)

            # Initialize Gemini client
            gemini_client = get_gemini_client()

            # Create request for a joke
            request = GenerateContentRequest(prompt="Tell me a joke")

            # Generate content
            response = await gemini_client.generate_content(request)

            logger.info("✅ Gemini API Response:")
            logger.info(f"   Generated text: {response.text}")
            if response.usage:
                logger.info(f"   Usage: {response.usage}")
            if response.finish_reason:
                logger.info(f"   Finish reason: {response.finish_reason}")

        except Exception as e:
            logger.error(f"❌ Error testing Gemini: {e}")

    async def test_gemini_file_analysis(self) -> None:
        """Test Gemini API with file upload and analysis."""
        try:
            logger.info("=" * 60)
            logger.info("TESTING GEMINI API - File Upload and Analysis")
            logger.info("=" * 60)

            # Initialize Gemini client
            gemini_client = get_gemini_client()

            # Path to the PNG file
            file_path = "/Users/willcray/maive/packages/brand/logos/Maive-Main-Logo-Transparent-Dark-Text.png"

            logger.info(f"Uploading file: {file_path}")

            # Upload the file
            upload_request = FileUploadRequest(
                file_path=file_path, display_name="Maive Logo"
            )

            uploaded_file = await gemini_client.upload_file(upload_request)

            logger.info("✅ File uploaded successfully:")
            logger.info(f"   File name: {uploaded_file.name}")
            logger.info(f"   Display name: {uploaded_file.display_name}")
            logger.info(f"   MIME type: {uploaded_file.mime_type}")
            logger.info(f"   Size: {uploaded_file.size_bytes} bytes")
            logger.info(f"   URI: {uploaded_file.uri}")

            # Generate content using the uploaded file
            logger.info("Requesting file analysis from Gemini...")

            analysis_request = GenerateContentRequest(
                prompt="Please describe this image in detail. What do you see? What are the colors, design elements, and overall style?",
                files=[uploaded_file.name],
            )

            response = await gemini_client.generate_content(analysis_request)

            logger.info("✅ Gemini File Analysis Response:")
            logger.info(f"   Generated analysis: {response.text}")
            if response.usage:
                logger.info(f"   Usage: {response.usage}")
            if response.finish_reason:
                logger.info(f"   Finish reason: {response.finish_reason}")

            # Clean up - delete the uploaded file
            logger.info("Cleaning up uploaded file...")
            delete_response = await gemini_client.delete_file(uploaded_file.name)

            if delete_response.success:
                logger.info("✅ File cleaned up successfully")
            else:
                logger.warning(f"⚠️ File cleanup failed: {delete_response.message}")

        except Exception as e:
            logger.error(f"❌ Error testing Gemini file analysis: {e}")

    async def test_job_and_estimates(self) -> None:
        """Test the new job and estimates functionality."""
        try:
            job_id = 136544265
            logger.info("=" * 60)
            logger.info(f"TESTING JOB AND ESTIMATES - Job ID: {job_id}")
            logger.info("=" * 60)

            # Step 1: Get the job details
            logger.info(f"Step 1: Fetching job {job_id}")
            job = await self.provider.get_job(job_id)

            logger.info("✅ Job Details:")
            logger.info(f"   Job ID: {job.id}")
            logger.info(f"   Job Number: {job.job_number}")
            logger.info(f"   Job Status: {job.job_status}")
            logger.info(f"   Customer ID: {job.customer_id}")
            logger.info(f"   Location ID: {job.location_id}")
            logger.info(f"   Project ID: {job.project_id}")

            # Step 2: Get all estimates for this job
            logger.info(f"\\nStep 2: Fetching estimates for job {job_id}")
            estimates_request = EstimatesRequest(
                tenant=self.provider.tenant_id, job_id=job_id
            )
            estimates_response = await self.provider.get_estimates(estimates_request)

            logger.info(
                f"✅ Found {len(estimates_response.estimates)} estimates for job {job_id}"
            )

            # Log estimate IDs
            estimate_ids = [estimate.id for estimate in estimates_response.estimates]
            logger.info(f"   Estimate IDs: {estimate_ids}")

            # Step 3: Check which estimates have 'sold' status
            logger.info("\\nStep 3: Checking estimate statuses")
            sold_estimates = []

            for estimate in estimates_response.estimates:
                logger.info(f"\\n   Estimate {estimate.id}:")
                logger.info(f"      Name: {estimate.name}")
                logger.info(f"      Review Status: {estimate.review_status}")
                logger.info(f"      Active: {estimate.active}")
                logger.info(f"      Modified On: {estimate.modified_on}")

                if estimate.status:
                    logger.info(f"      Status Value: {estimate.status.value}")
                    logger.info(f"      Status Name: {estimate.status.name}")

                    # Check if status indicates 'sold' (you may need to adjust this condition)
                    if (
                        estimate.status.name.lower() == "sold"
                        or "sold" in estimate.status.name.lower()
                    ):
                        sold_estimates.append(estimate)
                        logger.info("      ✅ This estimate is SOLD!")
                else:
                    logger.info("      Status: None")

                logger.info(f"      Subtotal: ${estimate.subtotal}")
                logger.info(f"      Tax: ${estimate.tax}")
                logger.info(f"      Total: ${estimate.subtotal + estimate.tax}")
                logger.info(f"      Is Recommended: {estimate.is_recommended}")

            # Step 4: Apply selection logic for sold estimates
            logger.info("\\nStep 4: Applying selection logic for sold estimates")
            logger.info(f"   Found {len(sold_estimates)} sold estimates")

            if len(sold_estimates) == 0:
                error_msg = f"❌ ERROR: No sold estimates found for job {job_id}"
                logger.error(error_msg)
                raise CRMError(error_msg, "NO_SOLD_ESTIMATES")

            selected_estimate = None

            if len(sold_estimates) == 1:
                selected_estimate = sold_estimates[0]
                logger.info(f"   ✅ Single sold estimate found: {selected_estimate.id}")
            else:
                logger.info(
                    "   Multiple sold estimates found, applying selection criteria..."
                )

                # Filter by active = True
                active_sold_estimates = [e for e in sold_estimates if e.active]
                logger.info(f"   Active sold estimates: {len(active_sold_estimates)}")

                if len(active_sold_estimates) == 1:
                    selected_estimate = active_sold_estimates[0]
                    logger.info(
                        f"   ✅ Single active sold estimate selected: {selected_estimate.id}"
                    )
                else:
                    # If no active estimates or multiple active estimates, choose most recent by modified_on
                    estimates_to_choose_from = (
                        active_sold_estimates
                        if active_sold_estimates
                        else sold_estimates
                    )
                    logger.info(
                        f"   Choosing from {len(estimates_to_choose_from)} estimates based on most recent modified_on date"
                    )

                    # Sort by modified_on descending (most recent first)
                    selected_estimate = max(
                        estimates_to_choose_from, key=lambda x: x.modified_on
                    )
                    logger.info(
                        f"   ✅ Most recent estimate selected: {selected_estimate.id} (modified: {selected_estimate.modified_on})"
                    )

            # Summary with selected estimate details
            logger.info("\\n📊 Final Summary:")
            logger.info(f"   Total estimates: {len(estimates_response.estimates)}")
            logger.info(f"   Sold estimates: {len(sold_estimates)}")
            logger.info(f"   Selected estimate ID: {selected_estimate.id}")
            logger.info("   Selected estimate details:")
            logger.info(f"      Name: {selected_estimate.name}")
            logger.info(f"      Active: {selected_estimate.active}")
            logger.info(f"      Modified On: {selected_estimate.modified_on}")
            logger.info(f"      Subtotal: ${selected_estimate.subtotal}")
            logger.info(f"      Tax: ${selected_estimate.tax}")
            logger.info(
                f"      Total: ${selected_estimate.subtotal + selected_estimate.tax}"
            )

            if selected_estimate.sold_on:
                logger.info(f"      Sold On: {selected_estimate.sold_on}")
            if selected_estimate.sold_by:
                logger.info(f"      Sold By: {selected_estimate.sold_by}")

            # Step 5: Fetch and log items for the selected estimate
            logger.info(
                f"\\nStep 5: Fetching items for estimate {selected_estimate.id}"
            )
            items_request = EstimateItemsRequest(
                tenant=self.provider.tenant_id, estimate_id=selected_estimate.id
            )
            items_response = await self.provider.get_estimate_items(items_request)

            logger.info(
                f"✅ Found {len(items_response.items)} items for estimate {selected_estimate.id}"
            )

            if items_response.items:
                logger.info("\\n📦 Estimate Items:")
                for i, item in enumerate(items_response.items):
                    logger.info(f"\\n   [{i + 1}] Item {item.id}")
                    logger.info(
                        f"       SKU: {item.sku.name} ({item.sku.display_name})"
                    )
                    logger.info(f"       Quantity: {item.qty}")
                    logger.info(f"       Unit Cost: ${item.unit_cost:.2f}")
                    logger.info(f"       Total: ${item.total:.2f}")
            else:
                logger.warning("⚠️ No items found for this estimate")

            logger.info("\\n✅ JOB AND ESTIMATES TEST COMPLETE")

        except CRMError as e:
            logger.error(
                f"❌ CRM error during job and estimates test: {e.message} (Code: {e.error_code})"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error during job and estimates test: {e}")

    async def test_job_hold_and_estimates(self) -> None:
        """Test getting job estimates and putting the job on hold."""
        try:
            job_id = 141751428
            logger.info("=" * 60)
            logger.info(f"TESTING JOB HOLD AND ESTIMATES - Job ID: {job_id}")
            logger.info("=" * 60)

            # Step 0: Fetch project substatuses
            logger.info("\nStep 0: Fetching all project substatuses")
            try:
                substatuses_response = await self.provider.get_project_substatuses(active="True")
                logger.info(f"✅ Found {len(substatuses_response.data)} active project substatuses:")
                for substatus in substatuses_response.data:
                    logger.info(f"   ID: {substatus.id:8} | Status ID: {substatus.status_id:3} | Name: {substatus.name}")
            except Exception as e:
                logger.error(f"❌ Error fetching project substatuses: {e}")

            # Step 1: Get the job details
            logger.info(f"\nStep 1: Fetching job {job_id}")
            job = await self.provider.get_job(job_id)

            logger.info("✅ Job Details:")
            logger.info(f"   Job ID: {job.id}")
            logger.info(f"   Job Number: {job.job_number}")
            logger.info(f"   Job Status: {job.job_status}")
            logger.info(f"   Customer ID: {job.customer_id}")
            logger.info(f"   Location ID: {job.location_id}")
            logger.info(f"   Project ID: {job.project_id}")

            # Step 1.5: If job is canceled, remove the cancellation
            if job.job_status == "Canceled":
                logger.info(f"\n⚠️ Job {job_id} is in Canceled status, removing cancellation...")
                await self.provider.remove_job_cancellation(job_id)
                logger.info("✅ Cancellation removed successfully")

                # Re-fetch the job to get updated status
                job = await self.provider.get_job(job_id)
                logger.info(f"   Updated Job Status: {job.job_status}")

            # Step 2: Get all estimates for this job
            logger.info(f"\nStep 2: Fetching estimates for job {job_id}")
            estimates_request = EstimatesRequest(
                tenant=self.provider.tenant_id, job_id=job_id
            )
            estimates_response = await self.provider.get_estimates(estimates_request)

            logger.info(
                f"✅ Found {len(estimates_response.estimates)} estimates for job {job_id}"
            )

            # Log estimate IDs
            estimate_ids = [estimate.id for estimate in estimates_response.estimates]
            logger.info(f"   Estimate IDs: {estimate_ids}")

            # Step 3: Check which estimates have 'sold' status
            logger.info("\nStep 3: Checking estimate statuses")
            sold_estimates = []

            for estimate in estimates_response.estimates:
                logger.info(f"\n   Estimate {estimate.id}:")
                logger.info(f"      Name: {estimate.name}")
                logger.info(f"      Review Status: {estimate.review_status}")
                logger.info(f"      Active: {estimate.active}")
                logger.info(f"      Modified On: {estimate.modified_on}")

                if estimate.status:
                    logger.info(f"      Status Value: {estimate.status.value}")
                    logger.info(f"      Status Name: {estimate.status.name}")

                    # Check if status indicates 'sold'
                    if (
                        estimate.status.name.lower() == "sold"
                        or "sold" in estimate.status.name.lower()
                    ):
                        sold_estimates.append(estimate)
                        logger.info("      ✅ This estimate is SOLD!")
                else:
                    logger.info("      Status: None")

                logger.info(f"      Subtotal: ${estimate.subtotal}")
                logger.info(f"      Tax: ${estimate.tax}")

            # Step 4: Apply selection logic for sold estimates
            logger.info("\nStep 4: Applying selection logic for sold estimates")
            logger.info(f"   Found {len(sold_estimates)} sold estimates")

            if len(sold_estimates) == 0:
                error_msg = f"❌ ERROR: No sold estimates found for job {job_id}"
                logger.error(error_msg)
                raise CRMError(error_msg, "NO_SOLD_ESTIMATES")

            selected_estimate = None

            if len(sold_estimates) == 1:
                selected_estimate = sold_estimates[0]
                logger.info(f"   ✅ Single sold estimate found: {selected_estimate.id}")
            else:
                logger.info(
                    "   Multiple sold estimates found, applying selection criteria..."
                )

                # Filter by active = True
                active_sold_estimates = [e for e in sold_estimates if e.active]
                logger.info(f"   Active sold estimates: {len(active_sold_estimates)}")

                if len(active_sold_estimates) == 1:
                    selected_estimate = active_sold_estimates[0]
                    logger.info(
                        f"   ✅ Single active sold estimate selected: {selected_estimate.id}"
                    )
                else:
                    # If no active estimates or multiple active estimates, choose most recent by modified_on
                    estimates_to_choose_from = (
                        active_sold_estimates
                        if active_sold_estimates
                        else sold_estimates
                    )
                    logger.info(
                        f"   Choosing from {len(estimates_to_choose_from)} estimates based on most recent modified_on date"
                    )

                    # Sort by modified_on descending (most recent first)
                    selected_estimate = max(
                        estimates_to_choose_from, key=lambda x: x.modified_on
                    )
                    logger.info(
                        f"   ✅ Most recent estimate selected: {selected_estimate.id} (modified: {selected_estimate.modified_on})"
                    )

            # Summary with selected estimate details
            logger.info("\n📊 Selected Estimate Summary:")
            logger.info(f"   Estimate ID: {selected_estimate.id}")
            logger.info(f"   Name: {selected_estimate.name}")
            logger.info(f"   Active: {selected_estimate.active}")
            logger.info(f"   Modified On: {selected_estimate.modified_on}")
            logger.info(f"   Subtotal: ${selected_estimate.subtotal}")
            logger.info(f"   Tax: ${selected_estimate.tax}")

            # Step 5: Get available hold reasons
            logger.info("\nStep 5: Fetching job hold reasons")
            hold_reasons_response = await self.provider.get_job_hold_reasons(
                active="True"
            )

            logger.info(
                f"✅ Found {len(hold_reasons_response.data)} active hold reasons"
            )

            if not hold_reasons_response.data:
                raise CRMError("No active hold reasons found", "NO_HOLD_REASONS")

            # Log all hold reasons
            logger.info("\n📋 Available Hold Reasons:")
            for i, reason in enumerate(hold_reasons_response.data):
                logger.info(f"   [{i + 1}] ID: {reason.id} - Name: {reason.name}")

            # Use the "2nd Look Needed" hold reason
            hold_reason_id = JobHoldReasonId.SECOND_LOOK_NEEDED
            hold_reason_name = JOB_HOLD_REASON_NAMES[hold_reason_id]

            # Verify the reason exists in the available reasons
            available_reason_ids = [r.id for r in hold_reasons_response.data]
            if hold_reason_id.value not in available_reason_ids:
                logger.warning(
                    f"⚠️ Hold reason ID {hold_reason_id.value} not found in available reasons, using first available"
                )
                hold_reason_id_value = hold_reasons_response.data[0].id
                hold_reason_name = hold_reasons_response.data[0].name
            else:
                hold_reason_id_value = hold_reason_id.value

            logger.info(
                f"\n   Using hold reason: {hold_reason_name} (ID: {hold_reason_id_value})"
            )

            # Step 6: Put the job on hold with the message
            logger.info(f"\nStep 6: Putting job {job_id} on hold")
            memo = "hey from maive.ai"
            await self.provider.hold_job(job_id, hold_reason_id_value, memo)

            logger.info("✅ Job put on hold successfully:")
            logger.info(f"   Reason: {hold_reason_name}")
            logger.info(f"   Memo: {memo}")

            # Step 7: Verify the final job status
            logger.info(f"\nStep 7: Verifying final job status")
            final_job = await self.provider.get_job(job_id)
            logger.info(f"✅ Final Job Status: {final_job.job_status}")

            logger.info("\n✅ JOB HOLD AND ESTIMATES TEST COMPLETE")

        except CRMError as e:
            logger.error(
                f"❌ CRM error during test: {e.message} (Code: {e.error_code})"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error during test: {e}")

    async def test_update_project(self) -> None:
        """Test updating a project status with Maive identification."""
        try:
            project_id = 279331225
            logger.info("=" * 60)
            logger.info(f"TESTING PROJECT UPDATE - Project ID: {project_id}")
            logger.info("=" * 60)

            # Step 1: Get the current project details
            logger.info(f"\nStep 1: Fetching project {project_id}")
            try:
                project = await self.provider.get_project_by_id(project_id)
                logger.info("✅ Current Project Details:")
                logger.info(f"   Project ID: {project.get('id')}")
                logger.info(f"   Project Number: {project.get('number')}")
                logger.info(f"   Status: {project.get('status')}")
                logger.info(f"   Status ID: {project.get('statusId')}")
                logger.info(f"   SubStatus: {project.get('subStatus')}")
                logger.info(f"   SubStatus ID: {project.get('subStatusId')}")
            except Exception as e:
                logger.info(f"⚠️ Could not fetch project details: {e}")

            # Step 2: Update project to Sales Hold substatus with Maive identification
            logger.info(f"\nStep 2: Updating project {project_id} to Sales Hold")
            logger.info(f"   Using SubStatus: SALES_SALES_HOLD (ID: {SubStatus.SALES_SALES_HOLD.value})")

            update_request = UpdateProjectRequest(
                tenant=int(self.provider.tenant_id),
                project_id=project_id,
                status_id=383,  # Status ID for "Sales 1 - Sales Hold" substatus
                sub_status_id=SubStatus.SALES_SALES_HOLD.value,
                external_data=[
                    ExternalDataItem(key="managed_by", value="maive_ai"),
                    ExternalDataItem(key="action", value="sales_hold"),
                    ExternalDataItem(key="timestamp", value=datetime.now(UTC).isoformat())
                ]
            )

            result = await self.provider.update_project(update_request)
            logger.info("✅ Project updated successfully!")
            logger.info(f"   New Status: {result.get('status')}")
            logger.info(f"   New SubStatus: {result.get('subStatus')}")
            logger.info(f"   External Data: {result.get('externalData', [])}")

            # Step 3: Add a note to the project
            logger.info(f"\nStep 3: Adding note to project {project_id}")
            note_text = "discrepancy found between call recording, estimate, and cool down form"
            note_result = await self.provider.add_project_note(project_id, note_text, pin_to_top=True)
            logger.info("✅ Project note added successfully!")
            logger.info(f"   Note Text: {note_result.text}")
            logger.info(f"   Is Pinned: {note_result.is_pinned}")
            logger.info(f"   Created On: {note_result.created_on}")

            logger.info("\n✅ PROJECT UPDATE AND NOTE TEST COMPLETE")

        except CRMError as e:
            logger.error(f"❌ CRM error during test: {e.message} (Code: {e.error_code})")
        except Exception as e:
            logger.error(f"❌ Unexpected error during test: {e}")

    async def test_analyze_form_fields(self) -> None:
        """Analyze form 2933 to extract all possible fields across multiple submissions."""
        try:
            form_id = 2933
            logger.info("=" * 60)
            logger.info(f"ANALYZING FORM {form_id} - Extracting All Fields")
            logger.info("=" * 60)

            # Track all unique fields across submissions
            all_fields: dict[str, dict[str, Any]] = {}

            # Fetch multiple pages to get comprehensive field coverage
            max_pages = 5
            submissions_analyzed = 0

            for page in range(1, max_pages + 1):
                logger.info(f"\nFetching submissions page {page}...")

                result = await self.provider.get_form_submissions(
                    form_id=form_id,
                    page=page,
                    page_size=50,
                    status="Any"
                )

                submissions = result.get("data", [])
                if not submissions:
                    logger.info(f"No more submissions found on page {page}")
                    break

                logger.info(f"✅ Found {len(submissions)} submissions on page {page}")
                submissions_analyzed += len(submissions)

                # Extract fields from each submission
                for submission in submissions:
                    units = submission.get("units", [])
                    for unit in units:
                        if isinstance(unit, dict) and "units" in unit:
                            # This is a unit container with sections
                            unit_name = unit.get("name", "Unknown Unit")
                            sections = unit.get("units", [])

                            for section in sections:
                                if isinstance(section, dict):
                                    section_type = section.get("type", "")

                                    # Look for field data
                                    field_id = section.get("id", "")
                                    field_name = section.get("name", "")
                                    field_type = section_type

                                    # Create unique key for field
                                    field_key = f"{unit_name}::{field_name}::{field_id}"

                                    if field_key not in all_fields:
                                        all_fields[field_key] = {
                                            "unit": unit_name,
                                            "id": field_id,
                                            "name": field_name,
                                            "type": field_type,
                                            "sample_value": section.get("value") or section.get("values")
                                        }

                if not result.get("hasMore", False):
                    logger.info("No more pages available")
                    break

            # Display results
            logger.info("\n" + "=" * 60)
            logger.info(f"ANALYSIS COMPLETE")
            logger.info("=" * 60)
            logger.info(f"📊 Total Submissions Analyzed: {submissions_analyzed}")
            logger.info(f"📝 Unique Fields Found: {len(all_fields)}")
            logger.info("\n" + "=" * 60)
            logger.info("FIELD DETAILS:")
            logger.info("=" * 60)

            # Group by unit for better organization
            fields_by_unit: dict[str, list[dict[str, Any]]] = {}
            for field_info in all_fields.values():
                unit = field_info["unit"]
                if unit not in fields_by_unit:
                    fields_by_unit[unit] = []
                fields_by_unit[unit].append(field_info)

            # Display organized by unit
            for unit, fields in sorted(fields_by_unit.items()):
                logger.info(f"\n📁 Unit: {unit}")
                logger.info("-" * 60)
                for field in sorted(fields, key=lambda x: x["name"] or ""):
                    logger.info(f"  • Field: {field['name'] or '(unnamed)'}")
                    logger.info(f"    ID: {field['id']}")
                    logger.info(f"    Type: {field['type']}")
                    if field['sample_value'] is not None:
                        sample = str(field['sample_value'])
                        if len(sample) > 50:
                            sample = sample[:50] + "..."
                        logger.info(f"    Sample: {sample}")
                    logger.info("")

            logger.info("\n✅ FORM FIELD ANALYSIS COMPLETE")

        except CRMError as e:
            logger.error(f"❌ CRM error during form analysis: {e.message} (Code: {e.error_code})")
        except Exception as e:
            logger.error(f"❌ Unexpected error during form analysis: {e}")

    async def test_discrepancy_detection_workflow(self) -> None:
        """Complete workflow: fetch project, estimate, form, analyze audio for discrepancies."""
        try:
            project_id = 261980979
            audio_path = "/Users/willcray/maive/vertex-demo-convo.mp3"
            # Set to None to attempt auto-discovery, or provide a known estimate ID from the GUI
            known_sold_estimate_id = None  # TODO: Set this if auto-discovery fails

            logger.info("=" * 60)
            logger.info(f"DISCREPANCY DETECTION WORKFLOW - Project {project_id}")
            logger.info("=" * 60)

            # Step 1: Fetch project details
            logger.info(f"\nStep 1: Fetching project {project_id}")
            project = await self.provider.get_project_by_id(project_id)
            logger.info(f"✅ Project fetched: {project.get('number')}")

            # Step 2: Get the sold estimate
            logger.info(f"\nStep 2: Getting sold estimate")

            if known_sold_estimate_id is not None:
                # Use the known estimate ID directly
                logger.info(f"   Using known estimate ID: {known_sold_estimate_id}")
                selected_estimate = await self.provider.get_estimate(known_sold_estimate_id)
                logger.info(f"✅ Retrieved estimate: {selected_estimate.id}")
            else:
                # Attempt auto-discovery by getting estimates for this project
                logger.info(f"   Attempting auto-discovery of sold estimate...")
                logger.info(f"   Querying estimates by project ID: {project_id}")

                # Get estimates for this project
                estimates_request = EstimatesRequest(
                    tenant=int(self.provider.tenant_id),
                    project_id=project_id,
                    page=1,
                    page_size=50
                )

                estimates_response = await self.provider.get_estimates(estimates_request)
                logger.info(f"   Found {len(estimates_response.estimates)} estimates for project {project_id}")

                # Filter for sold estimates (sold_on date indicates the estimate was sold)
                sold_estimates = []
                for estimate in estimates_response.estimates:
                    is_approved = estimate.review_status.value == "Approved"
                    has_sold_date = estimate.sold_on is not None

                    # An estimate is sold if it has a sold_on date
                    if has_sold_date:
                        sold_estimates.append(estimate)
                        approval_status = "Approved" if is_approved else estimate.review_status.value
                        logger.info(f"   - Estimate {estimate.id}: {estimate.name or '(no name)'} - SOLD ({approval_status}, sold on {estimate.sold_on})")
                    else:
                        status_info = f"review_status={estimate.review_status.value}, sold_on=None"
                        logger.info(f"   - Estimate {estimate.id}: {estimate.name or '(no name)'} - NOT SOLD ({status_info})")

                if len(sold_estimates) == 0:
                    error_msg = (
                        f"No sold estimates found for project {project_id}. "
                        f"Found {len(estimates_response.estimates)} total estimates, but none are marked as sold.\n"
                        f"Please check the ServiceTitan GUI and manually set known_sold_estimate_id."
                    )
                    raise CRMError(error_msg, "NO_SOLD_ESTIMATE")
                elif len(sold_estimates) > 1:
                    estimate_list = ", ".join([str(e.id) for e in sold_estimates])
                    error_msg = (
                        f"Multiple sold estimates found for project {project_id}: {estimate_list}.\n"
                        f"Please manually set known_sold_estimate_id to the correct estimate ID."
                    )
                    raise CRMError(error_msg, "MULTIPLE_SOLD_ESTIMATES")

                selected_estimate = sold_estimates[0]
                logger.info(f"✅ Auto-discovered sold estimate: {selected_estimate.id}")

            # Log estimate details for verification
            logger.info(f"   Estimate Name: {selected_estimate.name or '(no name)'}")
            logger.info(f"   Subtotal: ${selected_estimate.subtotal:,.2f}")
            logger.info(f"   Tax: ${selected_estimate.tax:,.2f}")
            logger.info(f"   Total: ${selected_estimate.subtotal + selected_estimate.tax:,.2f}")
            if selected_estimate.sold_on:
                logger.info(f"   Sold On: {selected_estimate.sold_on}")

            # Get the job_id from the estimate
            job_id = selected_estimate.job_id
            if not job_id:
                raise CRMError(f"Selected estimate {selected_estimate.id} has no associated job", "NO_JOB")
            logger.info(f"   Associated job: {job_id}")

            # Get estimate items
            items_request = EstimateItemsRequest(
                tenant=int(self.provider.tenant_id),
                estimate_id=selected_estimate.id,
                page=1,
                page_size=50
            )
            items_result = await self.provider.get_estimate_items(items_request)
            logger.info(f"   Estimate has {len(items_result.items)} items")

            # Log first few items for verification
            logger.info(f"   First {min(5, len(items_result.items))} items:")
            for i, item in enumerate(items_result.items[:5]):
                logger.info(f"     {i+1}. {item.description[:60]}... (Qty: {item.qty}, Total: ${item.total:,.2f})")

            # Step 3: Get form submission (Notes to Production)
            logger.info(f"\nStep 3: Fetching form 2933 submission for job {job_id}")
            form_result = await self.provider.get_form_submissions(
                form_id=2933,
                page=1,
                page_size=10,
                status="Any",
                owners=[{"type": "Job", "id": job_id}]
            )

            # Extract Notes to Production from the submission(s)
            notes_to_production = None
            submissions = form_result.get("data", [])

            if submissions:
                # Since we filtered by job owner, submissions should be for our job
                submission = submissions[0]
                units = submission.get("units", [])
                for unit in units:
                    if isinstance(unit, dict) and unit.get("name") == "Notes to Production":
                        notes_to_production = unit
                        break

            if notes_to_production:
                logger.info(f"✅ Found Notes to Production data")
            else:
                logger.warning(f"⚠️ No Notes to Production found for job {job_id}")
                notes_to_production = {"message": "No Notes to Production found"}

            # Step 4: Upload audio to Gemini
            logger.info(f"\nStep 4: Uploading audio to Gemini Files API")
            gemini_client = get_gemini_client()
            upload_request = FileUploadRequest(file_path=audio_path)
            uploaded_file = await gemini_client.upload_file(upload_request)
            logger.info(f"✅ Audio uploaded: {uploaded_file.name}")

            # Step 5: Prepare data for Gemini
            logger.info(f"\nStep 5: Preparing data for analysis")

            # Format estimate data
            estimate_data = {
                "estimate_id": selected_estimate.id,
                "name": selected_estimate.name,
                "subtotal": selected_estimate.subtotal,
                "tax": selected_estimate.tax,
                "items": [
                    {
                        "description": item.description,
                        "quantity": item.qty,
                        "unit_rate": item.unit_rate,
                        "total": item.total,
                        "sku_name": item.sku.name
                    }
                    for item in items_result.items
                ]
            }

            prompt = f"""You are an expert sales admin for a roofing company. You are reviewing the audio from a conversation between one of our sales reps and a customer. Please listen to and understand the contents of the audio conversation, the contents of the estimate, and any notes to production that the sales rep submitted via form following the conversation.

Identify what, if anything, mentioned during the conversation that was not updated in the estimate or logged in the form. If there is any information that would affect the roofing service provided or how it is provided, then please flag the conversation for review.

Simply and concisely log what was not included in the estimate or form but stated during the audio conversation. In this concise message of the discrepancy, please include a timestamp in the audio when the discrepancy occurred in format (MM:SS).

**Estimate Contents:**
{json.dumps(estimate_data, indent=2)}

**Notes to Production:**
{json.dumps(notes_to_production, indent=2)}
"""

            # Step 6: Call Gemini with structured output
            logger.info(f"\nStep 6: Analyzing audio for discrepancies")
            structured_request = GenerateStructuredContentRequest(
                prompt=prompt,
                response_model=DiscrepancyReview,
                files=[uploaded_file.name],
                temperature=0.7
            )

            review_result = await gemini_client.generate_structured_content(structured_request)
            logger.info(f"✅ Analysis complete")
            logger.info(f"   Needs Review: {review_result.needs_review}")
            logger.info(f"   Explanation: {review_result.hold_explanation}")

            # Step 7: Conditional project hold
            if review_result.needs_review:
                logger.info(f"\nStep 7: Discrepancy found - Updating project to HOLD")

                # Update project status to HOLD with Sales Hold substatus
                update_request = UpdateProjectRequest(
                    tenant=int(self.provider.tenant_id),
                    project_id=project_id,
                    status_id=383,  # Hold status ID
                    sub_status_id=SubStatus.SALES_SALES_HOLD.value,
                    external_data=[
                        ExternalDataItem(key="managed_by", value="maive_ai"),
                        ExternalDataItem(key="action", value="discrepancy_detected"),
                        ExternalDataItem(key="timestamp", value=datetime.now(UTC).isoformat())
                    ]
                )

                await self.provider.update_project(update_request)
                logger.info(f"✅ Project updated to HOLD status")

                # Add note to project with prefix
                note_text = f"Maive AI - I detected job details discussed in sales call not being tracked in Service Titan: {review_result.hold_explanation}"
                logger.info(f"   Adding note to project (pinned to top):")
                logger.info(f"   Note content: {note_text}")
                await self.provider.add_project_note(
                    project_id=project_id,
                    text=note_text,
                    pin_to_top=True
                )
                logger.info(f"✅ Note added to project")
            else:
                logger.info(f"\nStep 7: No discrepancies found - No action needed")

            # Step 8: Cleanup - delete uploaded audio
            logger.info(f"\nStep 8: Cleaning up uploaded file")
            await gemini_client.delete_file(uploaded_file.name)
            logger.info(f"✅ Audio file deleted from Gemini")

            logger.info("\n✅ DISCREPANCY DETECTION WORKFLOW COMPLETE")

        except CRMError as e:
            logger.error(f"❌ CRM error during workflow: {e.message} (Code: {e.error_code})")
        except Exception as e:
            logger.error(f"❌ Unexpected error during workflow: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def run_test(self) -> None:
        """Run the discrepancy detection workflow."""
        logger.info("Starting Vertex Tester - Discrepancy Detection Workflow")

        try:
            # Run the comprehensive workflow
            await self.test_discrepancy_detection_workflow()

        except KeyboardInterrupt:
            logger.info("Vertex Tester stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in test: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up Vertex Tester...")
        if hasattr(self.provider, "close"):
            await self.provider.close()
        if hasattr(self.rilla_service, "rilla_client") and hasattr(
            self.rilla_service.rilla_client, "close"
        ):
            await self.rilla_service.rilla_client.close()


async def main():
    """Main entry point for the vertex testing app."""
    tester = VertexTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
