"""
Vertex monitoring application for Service Titan project status.

This application polls the Service Titan API every 5 seconds to monitor
project status changes, with special attention to "ON_HOLD" status transitions.
"""

import asyncio
from datetime import datetime, UTC
from typing import Dict, Set

from src.integrations.crm.base import CRMError
from src.integrations.crm.constants import ProjectStatus
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.utils.logger import logger


class VertexMonitor:
    """Monitor for Service Titan project status changes."""

    def __init__(self):
        """Initialize the vertex monitor."""
        self.provider = ServiceTitanProvider()
        self.previous_statuses: Dict[str, ProjectStatus] = {}
        self.on_hold_projects: Set[str] = set()
        self.poll_interval = 5.0  # seconds

    async def poll_project_statuses(self) -> None:
        """Poll Service Titan for all project statuses and detect changes."""
        try:
            logger.info("Polling Service Titan for project statuses...")

            result = await self.provider.get_all_project_statuses()

            logger.info(f"Retrieved {result.total_count} projects from Service Titan")

            current_time = datetime.now(UTC).isoformat()

            # Track status changes
            current_statuses = {}
            new_on_hold = set()

            for project in result.projects:
                project_id = project.project_id
                current_status = project.status

                current_statuses[project_id] = current_status

                # Check if this is a new project or status change
                if project_id in self.previous_statuses:
                    previous_status = self.previous_statuses[project_id]

                    if previous_status != current_status:
                        logger.info(
                            f"[{current_time}] PROJECT STATUS CHANGE - "
                            f"Project {project_id}: {previous_status} → {current_status}"
                        )

                        # Special logging for ON_HOLD transitions
                        if current_status == ProjectStatus.ON_HOLD:
                            logger.warning(
                                f"🚨 [{current_time}] PROJECT ON HOLD - "
                                f"Project {project_id} moved to ON_HOLD status! "
                                f"Previous status: {previous_status}"
                            )
                            new_on_hold.add(project_id)
                        elif previous_status == ProjectStatus.ON_HOLD:
                            logger.info(
                                f"✅ [{current_time}] PROJECT RESUMED - "
                                f"Project {project_id} moved from ON_HOLD to {current_status}"
                            )
                else:
                    # New project discovered
                    logger.info(
                        f"[{current_time}] NEW PROJECT DISCOVERED - "
                        f"Project {project_id} with status: {current_status}"
                    )

                    if current_status == ProjectStatus.ON_HOLD:
                        logger.warning(
                            f"🚨 [{current_time}] NEW PROJECT ON HOLD - "
                            f"Project {project_id} discovered with ON_HOLD status!"
                        )
                        new_on_hold.add(project_id)

                # Log all current project statuses periodically
                provider_data = project.provider_data or {}
                job_number = provider_data.get("job_number", "N/A")
                logger.debug(
                    f"[{current_time}] Project {project_id} (Job #{job_number}): {current_status}"
                )

            # Update tracking sets
            self.previous_statuses = current_statuses
            self.on_hold_projects.update(new_on_hold)

            # Summary logging
            total_on_hold = sum(1 for status in current_statuses.values() if status == ProjectStatus.ON_HOLD)
            logger.info(
                f"[{current_time}] POLL COMPLETE - "
                f"Total projects: {len(current_statuses)}, "
                f"Currently ON_HOLD: {total_on_hold}, "
                f"New ON_HOLD this poll: {len(new_on_hold)}"
            )

        except CRMError as e:
            logger.error(f"CRM error during polling: {e.message} (Code: {e.error_code})")
        except Exception as e:
            logger.error(f"Unexpected error during polling: {e}")

    async def run_monitor(self) -> None:
        """Run the continuous monitoring loop."""
        logger.info(f"Starting Vertex Monitor - polling every {self.poll_interval} seconds")
        logger.info("Monitoring for Service Titan project status changes...")

        try:
            while True:
                await self.poll_project_statuses()

                # Wait before next poll
                logger.debug(f"Waiting {self.poll_interval} seconds before next poll...")
                await asyncio.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Vertex Monitor stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in monitor loop: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up Vertex Monitor...")
        if hasattr(self.provider, 'close'):
            await self.provider.close()


async def main():
    """Main entry point for the vertex monitoring app."""
    monitor = VertexMonitor()
    await monitor.run_monitor()


if __name__ == "__main__":
    asyncio.run(main())