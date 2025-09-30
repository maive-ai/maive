"""
Vertex test application for Service Titan project status.

This application fetches a specific completed project for testing purposes.
"""

import asyncio
from datetime import datetime, UTC

from src.integrations.crm.base import CRMError
from src.integrations.crm.provider_schemas import ServiceTitanProviderData
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.utils.logger import logger


class VertexTester:
    """Tester for Service Titan single project status."""

    def __init__(self):
        """Initialize the vertex tester."""
        self.provider = ServiceTitanProvider()
        self.test_project_id = "136552187"  # Completed project found via search

    async def test_project_hierarchy(self) -> None:
        """Test the full Project -> Jobs -> Appointments hierarchy."""
        try:
            current_time = datetime.now(UTC).isoformat()
            logger.info(f"[{current_time}] Starting Project->Jobs->Appointments hierarchy test")

            # Step 1: Get the project and its jobIds
            logger.info(f"[{current_time}] Step 1: Fetching project {self.test_project_id}")

            # Get the specific completed project
            try:
                project = await self.provider.get_project_status(self.test_project_id)
                logger.info(f"Successfully retrieved completed project {self.test_project_id}")
                logger.info(f"Project Status: {project.status}")
                logger.info(f"Original Status: {project.provider_data.get('original_status', 'N/A')}")

                # Extract jobIds from provider_data
                provider_data = project.provider_data or {}
                job_ids = provider_data.get("jobIds", [])

                if not job_ids:
                    logger.error(f"No jobIds found in project {self.test_project_id}")
                    logger.info(f"Available project data keys: {list(provider_data.keys())}")
                    logger.info(f"Raw project data: {provider_data}")

                    # Since Service Titan projects don't seem to contain jobIds directly,
                    # let's try a different approach: get all jobs and see if any reference this project
                    logger.info("Alternative approach: searching jobs for ones related to this project")
                    jobs_response = await self.provider.get_all_job_statuses()

                    project_jobs = []
                    for job in jobs_response.projects[:10]:  # Check first 10 jobs
                        job_provider_data = job.provider_data or {}
                        # Look for any reference to our project ID
                        if any(str(self.test_project_id) in str(v) for v in job_provider_data.values()):
                            project_jobs.append(job.project_id)

                    if project_jobs:
                        logger.info(f"Found {len(project_jobs)} job(s) potentially related to project: {project_jobs}")
                        job_ids = project_jobs[:3]  # Use first 3 jobs
                    else:
                        logger.info("No related jobs found, will test with first few available jobs")
                        job_ids = [job.project_id for job in jobs_response.projects[:3]]

            except CRMError as e:
                logger.error(f"Failed to get project {self.test_project_id}: {e.message}")
                return

            # Step 2: Iterate over jobIds
            logger.info(f"[{current_time}] Step 2: Processing {len(job_ids)} jobs")

            for i, job_id in enumerate(job_ids):
                logger.info(f"[{current_time}] Processing job {i+1}/{len(job_ids)}: {job_id}")

                try:
                    # Get job details
                    job = await self.provider.get_job_status(str(job_id))
                    job_provider_data = job.provider_data or {}
                    last_appointment_id = job_provider_data.get("lastAppointmentId")

                    if not last_appointment_id:
                        logger.warning(f"No lastAppointmentId found for job {job_id}")
                        continue

                    logger.info(f"  └─ Job {job_id} has lastAppointmentId: {last_appointment_id}")

                    # Step 3: Get appointment details
                    try:
                        appointment = await self.provider.get_appointment_status(str(last_appointment_id))
                        appt_provider_data = appointment.provider_data or {}

                        start_time = appt_provider_data.get("start_time")
                        end_time = appt_provider_data.get("end_time")

                        logger.info(f"  └─ Appointment {last_appointment_id}:")
                        logger.info(f"      ├─ Status: {appointment.status}")
                        logger.info(f"      ├─ Start: {start_time}")
                        logger.info(f"      └─ End: {end_time}")

                    except CRMError as e:
                        logger.error(f"Failed to get appointment {last_appointment_id}: {e.message}")

                except CRMError as e:
                    logger.error(f"Failed to get job {job_id}: {e.message}")

            logger.info(f"[{current_time}] HIERARCHY TEST COMPLETE")

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


async def main():
    """Main entry point for the vertex testing app."""
    tester = VertexTester()
    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())