#!/usr/bin/env python3
"""Check when jobs and their parent projects were created."""

import asyncio
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ["CRM_PROVIDER"] = "service_titan"

from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.schemas import ProjectByIdRequest
from src.utils.logger import logger


async def main():
    # All 320xxx job IDs from jobs.txt
    sample_job_ids = [
        320851692,
        320786103,
        320851757,
        320922092,
        320904333,
    ]

    provider = get_crm_provider()
    tenant_id = getattr(provider, "tenant_id", 0)

    try:
        for job_id in sample_job_ids:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Checking Job ID: {job_id}")

                # Get the job
                job = await provider.get_job(job_id)
                logger.info(f"  Job created: {job.created_at}")

                # Get the project
                if hasattr(job, 'provider_data') and job.provider_data.get('project_id'):
                    project_id = job.provider_data.get('project_id')
                    logger.info(f"  Project ID: {project_id}")

                    project_request = ProjectByIdRequest(
                        tenant=int(tenant_id),
                        project_id=int(project_id)
                    )
                    project = await provider.get_project_by_id(project_request)
                    # ProjectResponse has created_on, not created_at
                    project_created = project.created_on if hasattr(project, 'created_on') else project.created_at
                    logger.info(f"  Project created: {project_created}")

                    # Check if job has Rilla link
                    if job.provider_data.get('summary'):
                        import re
                        pattern = r"https://app\.rillavoice\.com/conversations/single\?id=[a-f0-9-]+"
                        match = re.search(pattern, job.provider_data.get('summary'), re.IGNORECASE)
                        logger.info(f"  Has Rilla link: {bool(match)}")
                else:
                    logger.warning(f"  No project_id found in job data")

            except Exception as e:
                logger.error(f"  Error checking job {job_id}: {e}")
                continue

    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
