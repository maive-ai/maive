"""
Vertex test application for Service Titan project status.

This application fetches a specific completed project for testing purposes.
"""

import asyncio
from datetime import datetime, UTC

from src.integrations.crm.base import CRMError
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
        
        # Use known completed appointment with full timing data
        self.test_appointment_id = "123171400"  # Completed appointment (Done status)
        self.test_job_id = "123171399"         # Associated job ID
        self.test_project_id = "136552187"     # Will be updated if we find the actual project

    async def find_project_with_job(self) -> str | None:
        """Find a project that actually contains the job we want to test with."""
        try:
            logger.info(f"Searching for project that contains job {self.test_job_id}")

            # Get job details to see if it references a project
            job = await self.provider.get_job_status(self.test_job_id)
            job_provider_data = job.provider_data or {}
            referenced_project_id = job_provider_data.get('projectId')

            if referenced_project_id:
                logger.info(f"✅ Job {self.test_job_id} references project {referenced_project_id}")
                return str(referenced_project_id)

            logger.warning(f"Job {self.test_job_id} does not reference a project in its data")
            return None

        except CRMError as e:
            logger.error(f"Failed to get job {self.test_job_id}: {e.message}")
            return None

    async def test_project_hierarchy(self) -> None:
        """Test the full Project -> Jobs -> Appointments hierarchy by iterating through the proper relationships."""
        try:
            current_time = datetime.now(UTC).isoformat()
            logger.info(f"[{current_time}] Starting Project->Jobs->Appointments hierarchy test")

            # Step 1: Find the actual project that contains our test job
            actual_project_id = await self.find_project_with_job()
            if actual_project_id:
                self.test_project_id = actual_project_id
                logger.info(f"Using actual project ID: {self.test_project_id}")
            else:
                logger.info(f"Using fallback project ID: {self.test_project_id}")

            # Step 2: Get project details and try to find its jobs
            logger.info(f"[{current_time}] Step 1: Fetching project {self.test_project_id}")
            project = await self.provider.get_project_status(self.test_project_id)
            logger.info(f"  └─ Project {self.test_project_id}:")
            logger.info(f"      ├─ Status: {project.status}")
            logger.info(f"      └─ Original Status: {project.provider_data.get('original_status', 'N/A')}")

            # Step 3: Since projects don't directly contain jobIds, we'll search jobs that reference this project
            logger.info(f"[{current_time}] Step 2: Finding jobs that belong to project {self.test_project_id}")
            jobs_response = await self.provider.get_all_job_statuses()

            project_jobs = []
            for job in jobs_response.projects[:50]:  # Check first 50 jobs
                job_provider_data = job.provider_data or {}
                job_project_id = job_provider_data.get('projectId')

                if str(job_project_id) == self.test_project_id:
                    project_jobs.append(job.project_id)

            if project_jobs:
                logger.info(f"Found {len(project_jobs)} job(s) for project {self.test_project_id}: {project_jobs}")
            else:
                logger.warning(f"No jobs found for project {self.test_project_id}, using test job {self.test_job_id}")
                project_jobs = [self.test_job_id]

            # Step 4: For each job, get its details and find associated appointments
            logger.info(f"[{current_time}] Step 3: Processing jobs and their appointments")
            for i, job_id in enumerate(project_jobs[:3]):  # Process first 3 jobs
                logger.info(f"Processing job {i+1}/{min(len(project_jobs), 3)}: {job_id}")

                try:
                    job = await self.provider.get_job_status(str(job_id))
                    logger.info(f"  └─ Job {job_id}:")
                    logger.info(f"      ├─ Status: {job.status}")

                    # Get all appointments and find ones for this job
                    appointments_response = await self.provider.get_all_appointment_statuses()
                    job_appointments = []

                    for appt in appointments_response.projects:
                        appt_provider_data = appt.provider_data or {}
                        appt_job_id = appt_provider_data.get('job_id')

                        if str(appt_job_id) == str(job_id):
                            job_appointments.append(appt.project_id)

                    if job_appointments:
                        logger.info(f"      └─ Found {len(job_appointments)} appointment(s): {job_appointments}")

                        # Get details for first appointment
                        appointment_id = job_appointments[0]
                        appointment = await self.provider.get_appointment_status(str(appointment_id))
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
                                conversations = await self.rilla_service.get_conversations_for_appointment(
                                    appointment_id=str(appointment_id),
                                    start_time=start_time,
                                    end_time=end_time,
                                )

                                if conversations:
                                    logger.info(f"✅ Found {len(conversations)} Rilla conversation(s)")
                                    for conv in conversations:
                                        logger.info(f"├─ {conv.title} ({conv.duration}s)")
                                        logger.info(f"├─ User: {conv.user.name}")
                                        logger.info(f"└─ URL: {conv.rilla_url}")
                                else:
                                    logger.warning("⚠️ No Rilla conversations found")
                            except Exception as e:
                                logger.error(f"❌ Error querying Rilla: {e}")
                        else:
                            logger.warning("⚠️ Missing timing data, skipping Rilla query")

                    else:
                        logger.info(f"      └─ No appointments found for job {job_id}")

                except CRMError as e:
                    logger.error(f"Failed to get job {job_id}: {e.message}")

            logger.info(f"[{current_time}] HIERARCHY TEST COMPLETE")
            logger.info("✅ Successfully demonstrated Project->Jobs->Appointments hierarchy with iterating over relationships!")

        except CRMError as e:
            logger.error(f"CRM error during hierarchy test: {e.message} (Code: {e.error_code})")
        except Exception as e:
            logger.error(f"Unexpected error during hierarchy test: {e}")

    async def run_test(self) -> None:
        """Run the project hierarchy test."""
        logger.info("Starting Vertex Tester - testing Project->Jobs->Appointments hierarchy")

        try:
            await self.test_project_hierarchy()

        except KeyboardInterrupt:
            logger.info("Vertex Tester stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in test: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up Vertex Tester...")
        if hasattr(self.provider, 'close'):
            await self.provider.close()
        if hasattr(self.rilla_service, 'rilla_client') and hasattr(self.rilla_service.rilla_client, 'close'):
            await self.rilla_service.rilla_client.close()


async def main():
    """Main entry point for the vertex testing app."""
    tester = VertexTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())