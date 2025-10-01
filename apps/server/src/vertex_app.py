"""
Vertex test application for Service Titan project status.

This application fetches a specific completed project for testing purposes.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from src.integrations.crm.base import CRMError
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.rilla.client import RillaClient
from src.integrations.rilla.config import get_rilla_settings
from src.integrations.rilla.schemas import ConversationsExportRequest
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
        self.test_job_id = "123171399"  # Associated job ID
        self.test_project_id = (
            "136552187"  # Will be updated if we find the actual project
        )

    async def find_project_with_job(self) -> str | None:
        """Find a project that actually contains the job we want to test with."""
        try:
            logger.info(f"Searching for project that contains job {self.test_job_id}")

            # Get job details to see if it references a project
            job = await self.provider.get_job_status(self.test_job_id)
            job_provider_data = job.provider_data or {}
            referenced_project_id = job_provider_data.get("projectId")

            if referenced_project_id:
                logger.info(
                    f"✅ Job {self.test_job_id} references project {referenced_project_id}"
                )
                return str(referenced_project_id)

            logger.warning(
                f"Job {self.test_job_id} does not reference a project in its data"
            )
            return None

        except CRMError as e:
            logger.error(f"Failed to get job {self.test_job_id}: {e.message}")
            return None

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
                                        logger.info(
                                            f"├─ Conversation ID: {conv.conversation_id}"
                                        )
                                        logger.info(
                                            f"├─ Recording ID: {conv.recording_id}"
                                        )
                                        logger.info(f"├─ Rilla URL: {conv.rilla_url}")
                                        logger.info(
                                            f"├─ CRM Event ID: {conv.crm_event_id}"
                                        )
                                        logger.info(f"├─ Job Number: {conv.job_number}")
                                        logger.info(f"├─ ST Link: {conv.st_link}")
                                        logger.info(
                                            f"├─ Job Summary: {conv.job_summary}"
                                        )
                                        logger.info(f"├─ Outcome: {conv.outcome}")
                                        logger.info(f"├─ Audio URL: {conv.audio_url}")
                                        logger.info(
                                            f"├─ Transcript URL: {conv.transcript_url}"
                                        )
                                        logger.info(f"└─ User: {conv.user.name}")
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

    async def test_rilla_last_30_days(self) -> None:
        """Test Rilla API for last 30 days in 24-hour intervals and search for audioUrl/transcriptUrl."""
        try:
            now = datetime.now(UTC)
            logger.info("=" * 80)
            logger.info("TESTING RILLA API - Last 30 days (24-hour intervals)")
            logger.info(f"Current time: {now}")
            logger.info("=" * 80)

            # Track results across all days
            most_recent_audio_date = None
            most_recent_transcript_date = None
            total_conversations_checked = 0
            days_with_audio = 0
            days_with_transcript = 0

            # Query each day separately (last 30 days)
            for day_offset in range(30, -1, -1):
                day_start = now - timedelta(days=day_offset + 1)
                day_end = now - timedelta(days=day_offset)

                # Align to start and end of day for cleaner intervals
                # day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
                # day_end = day_end.replace(hour=23, minute=59, second=59, microsecond=999999)

                logger.info(
                    f"\n📅 Day {day_offset + 1}/30: {day_start.strftime('%Y-%m-%d')} - {day_end.strftime('%Y-%m-%d')}"
                )

                try:
                    # Query Rilla API for this 24-hour period
                    response = await self.rilla_service.export_all_conversations(
                        request=ConversationsExportRequest(
                            from_date=day_start,
                            to_date=day_end,
                        )
                    )

                    conversations_count = len(response.conversations)
                    total_conversations_checked += conversations_count

                    if conversations_count > 0:
                        logger.info(f"   Found {conversations_count} conversations")

                        # Check for audioUrl and transcriptUrl in this day's conversations
                        day_has_audio = False
                        day_has_transcript = False

                        for conv in response.conversations:
                            if conv.audio_url is not None:
                                day_has_audio = True
                                if (
                                    most_recent_audio_date is None
                                    or day_start > most_recent_audio_date
                                ):
                                    most_recent_audio_date = day_start

                            if conv.transcript_url is not None:
                                day_has_transcript = True
                                if (
                                    most_recent_transcript_date is None
                                    or day_start > most_recent_transcript_date
                                ):
                                    most_recent_transcript_date = day_start

                        if day_has_audio:
                            days_with_audio += 1
                            logger.info("   🎵 Contains audioUrl")

                        if day_has_transcript:
                            days_with_transcript += 1
                            logger.info("   📝 Contains transcriptUrl")

                        if not day_has_audio and not day_has_transcript:
                            logger.info("   ❌ No audioUrl or transcriptUrl found")
                    else:
                        logger.info("   No conversations found")

                except Exception as e:
                    logger.error(f"   ❌ Error querying day {day_offset + 1}: {e}")
                    continue

            # Final results summary
            logger.info("\n" + "=" * 80)
            logger.info("FINAL RESULTS - Last 30 Days Analysis:")
            logger.info(f"Total conversations checked: {total_conversations_checked}")
            logger.info(f"Days with audioUrl: {days_with_audio}/30")
            logger.info(f"Days with transcriptUrl: {days_with_transcript}/30")

            if most_recent_audio_date:
                logger.info(
                    f"🎵 Most recent date with audioUrl: {most_recent_audio_date.strftime('%Y-%m-%d')}"
                )
            else:
                logger.info("🎵 No audioUrl found in any of the last 30 days")

            if most_recent_transcript_date:
                logger.info(
                    f"📝 Most recent date with transcriptUrl: {most_recent_transcript_date.strftime('%Y-%m-%d')}"
                )
            else:
                logger.info("📝 No transcriptUrl found in any of the last 30 days")

            # Determine overall result
            has_either_field = (
                most_recent_audio_date is not None
                or most_recent_transcript_date is not None
            )
            logger.info(f"Has either audioUrl OR transcriptUrl: {has_either_field}")

            if has_either_field:
                most_recent_either = max(
                    filter(None, [most_recent_audio_date, most_recent_transcript_date])
                )
                logger.info(
                    f"🗓️ Most recent date with either field: {most_recent_either.strftime('%Y-%m-%d')}"
                )

            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ Error testing Rilla for last 30 days: {e}")

    async def test_rilla_recent(self) -> None:
        """Test Rilla API with recent data (last 24 hours) and search for audioUrl/transcriptUrl."""
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

            # Search for audioUrl and transcriptUrl across ALL conversations
            has_audio_url = False
            has_transcript_url = False
            conversations_with_audio = []
            conversations_with_transcript = []

            logger.info(
                f"\n🔍 Searching ALL {len(response.conversations)} conversations for audioUrl and transcriptUrl..."
            )

            for conv in response.conversations:
                if conv.audio_url is not None:
                    has_audio_url = True
                    conversations_with_audio.append(
                        {
                            "title": conv.title,
                            "conversation_id": conv.conversation_id,
                            "audio_url": conv.audio_url,
                        }
                    )

                if conv.transcript_url is not None:
                    has_transcript_url = True
                    conversations_with_transcript.append(
                        {
                            "title": conv.title,
                            "conversation_id": conv.conversation_id,
                            "transcript_url": conv.transcript_url,
                        }
                    )

            # Log results
            if conversations_with_audio:
                logger.info(
                    f"🎵 Found {len(conversations_with_audio)} conversations with audioUrl:"
                )
                for conv in conversations_with_audio:
                    logger.info(f"   • {conv['title']} ({conv['conversation_id']})")
                    logger.info(f"     Audio URL: {conv['audio_url']}")
            else:
                logger.info("🎵 No conversations found with audioUrl")

            if conversations_with_transcript:
                logger.info(
                    f"📝 Found {len(conversations_with_transcript)} conversations with transcriptUrl:"
                )
                for conv in conversations_with_transcript:
                    logger.info(f"   • {conv['title']} ({conv['conversation_id']})")
                    logger.info(f"     Transcript URL: {conv['transcript_url']}")
            else:
                logger.info("📝 No conversations found with transcriptUrl")

            # Log final boolean results
            logger.info("\n" + "=" * 60)
            logger.info("FINAL RESULTS:")
            logger.info(f"Has audioUrl: {has_audio_url}")
            logger.info(f"Has transcriptUrl: {has_transcript_url}")
            logger.info(
                f"Has either audioUrl OR transcriptUrl: {has_audio_url or has_transcript_url}"
            )
            logger.info("=" * 60)

            if response.conversations:
                logger.info("\n📋 First 3 conversations (detailed):")
                for i, conv in enumerate(response.conversations[:3]):
                    logger.info(f"\n   [{i + 1}] {conv.title}")
                    logger.info(f"       Date: {conv.date}")
                    logger.info(f"       Duration: {conv.duration}s")
                    logger.info(f"       Conversation ID: {conv.conversation_id}")
                    logger.info(f"       Recording ID: {conv.recording_id}")
                    logger.info(f"       Rilla URL: {conv.rilla_url}")
                    logger.info(f"       CRM Event ID: {conv.crm_event_id}")
                    logger.info(f"       Job Number: {conv.job_number}")
                    logger.info(f"       ST Link: {conv.st_link}")
                    logger.info(f"       Job Summary: {conv.job_summary}")
                    logger.info(f"       Outcome: {conv.outcome}")
                    logger.info(f"       Audio URL: {conv.audio_url}")
                    logger.info(f"       Transcript URL: {conv.transcript_url}")
                    logger.info(f"       User: {conv.user.name}")
            else:
                logger.warning("⚠️  No conversations found in the last 24 hours")

        except Exception as e:
            logger.error(f"❌ Error testing Rilla: {e}")

    async def run_test(self) -> None:
        """Run the Rilla API test for last 30 days."""
        logger.info("Starting Vertex Tester - testing Rilla API for last 30 days")

        try:
            # Test Rilla API for last 30 days in 24-hour intervals
            await self.test_rilla_last_30_days()

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
