"""
Vertex test application for Service Titan project status.

This application fetches a specific completed project for testing purposes.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from src.ai.gemini import get_gemini_client
from src.ai.gemini.schemas import FileUploadRequest, GenerateContentRequest
from src.integrations.crm.base import CRMError
from src.integrations.crm.constants import FormStatus
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.rilla.client import RillaClient
from src.integrations.rilla.config import get_rilla_settings
from src.integrations.rilla.service import RillaService
from src.utils.logger import logger


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
            estimates = await self.provider.get_estimates(job_id=job_id)

            logger.info(f"✅ Found {len(estimates)} estimates for job {job_id}")

            # Log estimate IDs
            estimate_ids = [estimate.id for estimate in estimates]
            logger.info(f"   Estimate IDs: {estimate_ids}")

            # Step 3: Check which estimates have 'sold' status
            logger.info(f"\\nStep 3: Checking estimate statuses")
            sold_estimates = []

            for estimate in estimates:
                logger.info(f"\\n   Estimate {estimate.id}:")
                logger.info(f"      Name: {estimate.name}")
                logger.info(f"      Review Status: {estimate.review_status}")
                logger.info(f"      Active: {estimate.active}")
                logger.info(f"      Modified On: {estimate.modified_on}")

                if estimate.status:
                    logger.info(f"      Status Value: {estimate.status.value}")
                    logger.info(f"      Status Name: {estimate.status.name}")

                    # Check if status indicates 'sold' (you may need to adjust this condition)
                    if estimate.status.name.lower() == "sold" or "sold" in estimate.status.name.lower():
                        sold_estimates.append(estimate)
                        logger.info("      ✅ This estimate is SOLD!")
                else:
                    logger.info("      Status: None")

                logger.info(f"      Subtotal: ${estimate.subtotal}")
                logger.info(f"      Tax: ${estimate.tax}")
                logger.info(f"      Total: ${estimate.subtotal + estimate.tax}")
                logger.info(f"      Is Recommended: {estimate.is_recommended}")

            # Step 4: Apply selection logic for sold estimates
            logger.info(f"\\nStep 4: Applying selection logic for sold estimates")
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
                logger.info(f"   Multiple sold estimates found, applying selection criteria...")

                # Filter by active = True
                active_sold_estimates = [e for e in sold_estimates if e.active]
                logger.info(f"   Active sold estimates: {len(active_sold_estimates)}")

                if len(active_sold_estimates) == 1:
                    selected_estimate = active_sold_estimates[0]
                    logger.info(f"   ✅ Single active sold estimate selected: {selected_estimate.id}")
                else:
                    # If no active estimates or multiple active estimates, choose most recent by modified_on
                    estimates_to_choose_from = active_sold_estimates if active_sold_estimates else sold_estimates
                    logger.info(f"   Choosing from {len(estimates_to_choose_from)} estimates based on most recent modified_on date")

                    # Sort by modified_on descending (most recent first)
                    selected_estimate = max(estimates_to_choose_from, key=lambda x: x.modified_on)
                    logger.info(f"   ✅ Most recent estimate selected: {selected_estimate.id} (modified: {selected_estimate.modified_on})")

            # Summary with selected estimate details
            logger.info(f"\\n📊 Final Summary:")
            logger.info(f"   Total estimates: {len(estimates)}")
            logger.info(f"   Sold estimates: {len(sold_estimates)}")
            logger.info(f"   Selected estimate ID: {selected_estimate.id}")
            logger.info(f"   Selected estimate details:")
            logger.info(f"      Name: {selected_estimate.name}")
            logger.info(f"      Active: {selected_estimate.active}")
            logger.info(f"      Modified On: {selected_estimate.modified_on}")
            logger.info(f"      Subtotal: ${selected_estimate.subtotal}")
            logger.info(f"      Tax: ${selected_estimate.tax}")
            logger.info(f"      Total: ${selected_estimate.subtotal + selected_estimate.tax}")

            if selected_estimate.sold_on:
                logger.info(f"      Sold On: {selected_estimate.sold_on}")
            if selected_estimate.sold_by:
                logger.info(f"      Sold By: {selected_estimate.sold_by}")

            # Step 5: Fetch and log items for the selected estimate
            logger.info(f"\\nStep 5: Fetching items for estimate {selected_estimate.id}")
            items_response = await self.provider.get_estimate_items(estimate_id=selected_estimate.id)

            logger.info(f"✅ Found {len(items_response.items)} items for estimate {selected_estimate.id}")

            if items_response.items:
                logger.info("\\n📦 Estimate Items:")
                for i, item in enumerate(items_response.items):
                    logger.info(f"\\n   [{i + 1}] Item {item.id}")
                    logger.info(f"       SKU: {item.sku.name} ({item.sku.display_name})")
                    logger.info(f"       Quantity: {item.qty}")
                    logger.info(f"       Unit Cost: ${item.unit_cost:.2f}")
                    logger.info(f"       Total: ${item.total:.2f}")
            else:
                logger.warning("⚠️ No items found for this estimate")

            logger.info("\\n✅ JOB AND ESTIMATES TEST COMPLETE")

        except CRMError as e:
            logger.error(f"❌ CRM error during job and estimates test: {e.message} (Code: {e.error_code})")
        except Exception as e:
            logger.error(f"❌ Unexpected error during job and estimates test: {e}")

    async def run_test(self) -> None:
        """Run the form submissions test."""
        logger.info("Starting Vertex Tester - testing Form Submissions endpoint")

        try:
            # Test the new job and estimates functionality
            await self.test_job_and_estimates()

            # Test Gemini API with a joke
            await self.test_gemini_joke()

            # Test Gemini API with file upload and analysis
            await self.test_gemini_file_analysis()

            # Test form submissions endpoint
            await self.test_form_submissions()

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
