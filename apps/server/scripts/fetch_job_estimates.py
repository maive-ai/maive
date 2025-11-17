"""
Script to fetch all estimates for a given job ID from Service Titan.

This script fetches estimates associated with a specific job ID using
the Service Titan Sales API.

Usage:
    uv run python scripts/fetch_job_estimates.py --job-id <job_id>

Example:
    uv run python scripts/fetch_job_estimates.py --job-id 123456
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.crm.schemas import EstimateItemsRequest, EstimatesRequest, ProjectByIdRequest
from src.utils.logger import logger


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def fetch_estimate_items(provider: ServiceTitanProvider, estimate_id: int) -> list[dict]:
    """
    Fetch customer-facing items for a specific estimate ID.

    Only fetches the first page (50 items) and filters to active, customer-facing items
    visible in GUI/PDF (matching discrepancy_detection.py behavior).

    Args:
        provider: ServiceTitanProvider instance
        estimate_id: The Service Titan estimate ID to fetch items for

    Returns:
        List of customer-facing items for the estimate
    """
    config = get_crm_settings()
    tenant_id = config.provider_config.tenant_id

    request = EstimateItemsRequest(
        tenant=int(tenant_id),
        estimate_id=estimate_id,
        page=1,
        page_size=50,
    )

    response = await provider.get_estimate_items(request)

    # Filter to only include active, customer-facing items visible in GUI/PDF
    # - Items with invoice_item_id are on invoices, not the estimate (not visible in GUI/PDF)
    # - Items with chargeable=False are internal cost tracking (materials/labor included in service items)
    # - Items with chargeable=null or True are customer-facing line items
    active_items = [
        item.model_dump(by_alias=True)
        for item in response.items
        if item.invoice_item_id is None and item.chargeable is not False
    ]

    logger.debug(
        f"Fetched {len(active_items)} customer-facing items for estimate {estimate_id} "
        f"(filtered from {len(response.items)} total items)"
    )

    return active_items


async def fetch_project_jobs(provider: ServiceTitanProvider, project_id: int) -> list[int]:
    """
    Fetch all job IDs associated with a project.

    Args:
        provider: ServiceTitanProvider instance
        project_id: The Service Titan project ID

    Returns:
        List of job IDs associated with the project
    """
    config = get_crm_settings()
    tenant_id = config.provider_config.tenant_id

    # Get the project details
    project_request = ProjectByIdRequest(
        tenant=int(tenant_id),
        project_id=project_id,
    )

    project = await provider.get_project_by_id(project_request)

    # Service Titan projects don't have a direct list of job IDs
    # We need to query estimates by project_id and extract unique job IDs from them
    estimates_request = EstimatesRequest(
        tenant=int(tenant_id),
        project_id=project_id,
        page=1,
        page_size=50,
    )

    response = await provider.get_estimates(estimates_request)

    # Extract unique job IDs from estimates
    job_ids = list(set([estimate.job_id for estimate in response.estimates if estimate.job_id]))

    logger.info(f"Found {len(job_ids)} unique jobs for project {project_id}")

    return job_ids


async def fetch_job_estimates(provider: ServiceTitanProvider, job_id: int) -> list[dict]:
    """
    Fetch all estimates for a specific job ID with their items.

    Args:
        provider: ServiceTitanProvider instance
        job_id: The Service Titan job ID to fetch estimates for

    Returns:
        List of all estimates for the job with their items
    """
    config = get_crm_settings()
    tenant_id = config.provider_config.tenant_id

    all_estimates = []
    page = 1
    has_more = True

    while has_more:
        request = EstimatesRequest(
            tenant=int(tenant_id),
            job_id=job_id,
            page=page,
            page_size=50,
        )

        response = await provider.get_estimates(request)

        # Convert Pydantic models to dicts
        estimates = [estimate.model_dump(by_alias=True) for estimate in response.estimates]
        all_estimates.extend(estimates)

        has_more = response.has_more or False
        total_count = response.total_count

        logger.info(
            f"Fetched page {page} of estimates for job {job_id} "
            f"({len(estimates)} estimates, {len(all_estimates)} total"
            f"{f', {total_count} available' if total_count else ''})"
        )

        if has_more:
            page += 1
        else:
            break

    # Now fetch items for each estimate
    for estimate in all_estimates:
        estimate_id = estimate['id']
        logger.info(f"Fetching items for estimate {estimate_id}...")
        items = await fetch_estimate_items(provider, estimate_id)
        estimate['items'] = items
        logger.info(f"  ✓ Fetched {len(items)} items for estimate {estimate_id}")

    return all_estimates


async def main():
    """Main function to fetch and log estimates for a given job ID or project ID."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Fetch all estimates for a given Service Titan job ID or project ID"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--job-id",
        type=int,
        help="The Service Titan job ID to fetch estimates for",
    )
    group.add_argument(
        "--project-id",
        type=int,
        help="The Service Titan project ID to fetch estimates for (fetches all jobs in project)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scripts/output/job_estimates.json",
        help="Output file path (default: scripts/output/job_estimates.json)",
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    if args.job_id:
        logger.info(f"Fetching Estimates for Job ID: {args.job_id}")
    else:
        logger.info(f"Fetching Estimates for Project ID: {args.project_id}")
    logger.info("=" * 80)

    # Load configuration
    config = get_crm_settings()
    provider_config = config.provider_config

    # Initialize provider with credentials
    provider = ServiceTitanProvider(
        tenant_id=provider_config.tenant_id,
        client_id=provider_config.client_id,
        client_secret=provider_config.client_secret,
        app_key=provider_config.app_key,
        base_api_url=provider_config.base_api_url,
        token_url=provider_config.token_url,
    )

    try:
        # Determine which mode we're in
        if args.job_id:
            # Single job mode
            logger.info(f"\nFetching estimates for job {args.job_id}...")
            all_estimates = await fetch_job_estimates(provider, args.job_id)
            job_ids = [args.job_id]
        else:
            # Project mode - fetch all jobs first
            logger.info(f"\nFetching jobs for project {args.project_id}...")
            job_ids = await fetch_project_jobs(provider, args.project_id)

            if not job_ids:
                logger.info(f"\nNo jobs found for project {args.project_id}")
                return

            logger.info(f"Found {len(job_ids)} jobs in project {args.project_id}")

            # Fetch estimates for all jobs
            all_estimates = []
            for job_id in job_ids:
                logger.info(f"\nFetching estimates for job {job_id}...")
                job_estimates = await fetch_job_estimates(provider, job_id)
                all_estimates.extend(job_estimates)
                logger.info(f"  ✓ Fetched {len(job_estimates)} estimates for job {job_id}")

        if not all_estimates:
            logger.info(f"\nNo estimates found")
            return

        logger.info(f"\n✓ Total estimates fetched: {len(all_estimates)}")

        # Log estimate details
        logger.info("\nEstimate details:")
        for estimate in all_estimates:
            logger.info(f"\n  Estimate ID: {estimate['id']}")
            logger.info(f"    Number: {estimate.get('number', 'N/A')}")
            logger.info(f"    Name: {estimate.get('name', 'N/A')}")
            logger.info(f"    Status: {estimate.get('status', 'N/A')}")
            logger.info(f"    Job ID: {estimate.get('jobId', 'N/A')}")
            logger.info(f"    Project ID: {estimate.get('projectId', 'N/A')}")
            logger.info(f"    Items: {len(estimate.get('items', []))} line items")
            # Handle summary field - it might be a dict or string
            summary = estimate.get('summary', {})
            if isinstance(summary, dict):
                subtotal = summary.get('subtotal', 0)
                logger.info(f"    Summary: ${subtotal:,.2f}")
            else:
                logger.info(f"    Summary: {summary}")
            logger.info(f"    Created: {estimate.get('createdOn', 'N/A')}")
            logger.info(f"    Modified: {estimate.get('modifiedOn', 'N/A')}")

            # Log sold info if available
            if estimate.get('soldOn'):
                logger.info(f"    Sold On: {estimate['soldOn']}")
                if estimate.get('soldBy'):
                    logger.info(f"    Sold By: {estimate['soldBy']}")

        # Save each estimate to a separate file
        output_dir = Path("scripts/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\nSaving estimates to {output_dir}...")

        for estimate in all_estimates:
            estimate_id = estimate['id']
            estimate_file = output_dir / f"estimate_{estimate_id}.json"

            with open(estimate_file, "w") as f:
                json.dump(estimate, f, indent=2, cls=DateTimeEncoder)

            logger.info(f"  ✓ Saved estimate {estimate_id} to {estimate_file}")

        # Also save a summary file
        if args.job_id:
            summary_file = output_dir / f"job_{args.job_id}_summary.json"
            summary_data = {
                "job_id": args.job_id,
                "total_estimates": len(all_estimates),
                "estimate_ids": [estimate['id'] for estimate in all_estimates],
            }
        else:
            summary_file = output_dir / f"project_{args.project_id}_summary.json"
            summary_data = {
                "project_id": args.project_id,
                "job_ids": job_ids,
                "total_jobs": len(job_ids),
                "total_estimates": len(all_estimates),
                "estimate_ids": [estimate['id'] for estimate in all_estimates],
            }

        with open(summary_file, "w") as f:
            json.dump(summary_data, f, indent=2, cls=DateTimeEncoder)

        logger.info(f"\n✓ Saved {len(all_estimates)} estimate files to {output_dir}")
        logger.info(f"✓ Saved summary to {summary_file}")

    except Exception as e:
        if args.job_id:
            logger.error(f"\n✗ Error fetching estimates for job {args.job_id}: {e}", exc_info=True)
        else:
            logger.error(f"\n✗ Error fetching estimates for project {args.project_id}: {e}", exc_info=True)
        raise
    finally:
        await provider.close()
        logger.info("\n" + "=" * 80)
        logger.info("Script completed")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
