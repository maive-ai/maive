#!/usr/bin/env python3
"""
Script to export Rilla links from Service Titan projects to CSV.

This script:
1. Iterates through all projects
2. Finds sold estimates for each project
3. Extracts Rilla links from job summaries
4. Outputs CSV with: date_created, project_id, job_id, estimate_id, rilla_link

Usage:
    esc run maive/maive-infra/will-dev -- uv run python scripts/export_rilla_links_csv_v2.py --start-date 2025-07-01 --end-date 2025-07-31
"""

import argparse
import asyncio
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from tqdm.asyncio import tqdm

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ["CRM_PROVIDER"] = "service_titan"

# ruff: noqa: E402
from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.schemas import EstimatesRequest
from src.utils.logger import logger


def extract_rilla_url(job_summary: str | None) -> str | None:
    """
    Extract Rilla URL from a job summary field.

    Args:
        job_summary: The job summary text (HTML/plain text)

    Returns:
        The Rilla URL if found, None otherwise

    Example:
        >>> extract_rilla_url("... Rilla link: https://app.rillavoice.com/conversations/single?id=abc123 ...")
        'https://app.rillavoice.com/conversations/single?id=abc123'
    """
    if not job_summary:
        return None

    # Pattern to match Rilla URLs
    pattern = r"https://app\.rillavoice\.com/conversations/single\?id=[a-f0-9-]+"

    match = re.search(pattern, job_summary, re.IGNORECASE)
    if match:
        return match.group(0)

    return None


async def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Export Rilla links from Service Titan projects")
    parser.add_argument(
        "--start-date",
        type=str,
        required=False,
        help="Start date for project filtering (YYYY-MM-DD) - Note: not currently implemented",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=False,
        help="End date for project filtering (YYYY-MM-DD) - Note: not currently implemented",
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Exporting Rilla Links to CSV")
    logger.info("=" * 80)
    logger.info("🔒 READ-ONLY MODE")
    if args.start_date and args.end_date:
        logger.info(f"Date Range: {args.start_date} to {args.end_date} (filtering not implemented)")
    else:
        logger.info("Searching all projects")
    logger.info("")

    provider = get_crm_provider()
    tenant_id = getattr(provider, "tenant_id", 0)

    # Create output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = output_dir / f"rilla_links_{timestamp}.csv"

    # CSV columns
    fieldnames = ["date_created", "project_id", "job_id", "estimate_id", "rilla_link"]

    total_projects = 0
    projects_with_rilla = 0
    total_rilla_links = 0

    # Semaphore to limit concurrent requests (avoid overwhelming API)
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

    try:
        with open(csv_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Iterate through projects using CRM provider
            page = 1
            page_size = 50
            has_more = True

            # Date filters for Service Titan
            filters = {}
            if args.start_date:
                filters["createdOnOrAfter"] = args.start_date
            if args.end_date:
                filters["createdBefore"] = args.end_date

            while has_more:
                logger.info(f"Fetching projects page {page}...")

                # Fetch projects using the CRM provider's method
                projects_response = await provider.get_all_projects(
                    filters=filters,
                    page=page,
                    page_size=page_size,
                )

                projects = projects_response.projects
                has_more = projects_response.has_more

                logger.info(f"  Processing {len(projects)} projects...")

                # Process projects in parallel
                async def process_project(project):
                    """Process a single project and return result if Rilla link found."""
                    async with semaphore:  # Limit concurrent requests
                        project_id = project.id
                        created_on = project.created_at if project.created_at else ""

                        try:
                            # Find sold estimates for this project
                            estimates_request = EstimatesRequest(
                                tenant=int(tenant_id),
                                project_id=int(project_id),
                                page=1,
                                page_size=50,
                            )
                            estimates_response = await provider.get_estimates(estimates_request)

                            # Filter for sold estimates
                            sold_estimates = [
                                e for e in estimates_response.estimates if e.sold_on is not None
                            ]

                            if not sold_estimates:
                                return None

                            # Get the most recent sold estimate
                            sold_estimates.sort(key=lambda e: e.sold_on, reverse=True)
                            estimate = sold_estimates[0]

                            # Get the job ID from the estimate
                            job_id = estimate.job_id
                            if not job_id:
                                return None

                            # Fetch the job using CRM provider
                            job = await provider.get_job(int(job_id))

                            # Get job summary from provider_data (Service Titan specific)
                            job_summary = job.provider_data.get("summary")

                            # Extract Rilla URL
                            rilla_url = extract_rilla_url(job_summary)

                            if rilla_url:
                                logger.info(f"  ✓ Project {project_id}: Found Rilla link")
                                return {
                                    "date_created": created_on,
                                    "project_id": project_id,
                                    "job_id": job_id,
                                    "estimate_id": estimate.id,
                                    "rilla_link": rilla_url,
                                }

                            return None

                        except Exception as e:
                            logger.warning(f"  Error processing project {project_id}: {e}")
                            return None

                # Process all projects in parallel with concurrency limit
                tasks = [process_project(p) for p in projects]
                results = await tqdm.gather(
                    *tasks,
                    desc=f"Page {page}",
                    total=len(projects),
                    leave=False,
                )

                # Write results to CSV
                for result in results:
                    if result:
                        projects_with_rilla += 1
                        total_rilla_links += 1
                        writer.writerow(result)

                total_projects += len(projects)
                page += 1

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total projects processed: {total_projects}")
        logger.info(f"Projects with Rilla links: {projects_with_rilla}")
        logger.info(f"Total Rilla links found: {total_rilla_links}")
        logger.info(f"\n✓ CSV file saved to: {csv_file}")

        if total_rilla_links > 0:
            logger.info("\n📊 Sample data:")
            # Read and display first 5 rows
            with open(csv_file, "r") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    logger.info(f"  {row}")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise
    finally:
        await provider.close()
        logger.info("\nScript completed")


if __name__ == "__main__":
    asyncio.run(main())
