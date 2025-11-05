#!/usr/bin/env python3
"""
Script to export Rilla links from Service Titan projects to CSV.

This script:
1. Iterates through all projects
2. Finds sold estimates for each project (filtered by sold date if specified)
3. Extracts Rilla links from job summaries
4. Outputs CSV with: estimate_sold_date, project_id, job_id, estimate_id, rilla_link

Usage:
    # Export all Rilla links
    esc run maive/maive-infra/will-dev -- uv run python scripts/export_rilla_links_csv.py

    # Export Rilla links for estimates sold in July 2025
    esc run maive/maive-infra/will-dev -- uv run python scripts/export_rilla_links_csv.py --start-date 2025-07-09 --end-date 2025-07-10
"""

import argparse
import asyncio
import csv
import os
import re
from datetime import datetime
from pathlib import Path

from tqdm.asyncio import tqdm

os.environ["CRM_PROVIDER"] = "service_titan"

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
    parser = argparse.ArgumentParser(
        description="Export Rilla links from Service Titan projects"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=False,
        help="Start date for filtering estimates by sold date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=False,
        help="End date for filtering estimates by sold date (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Exporting Rilla Links to CSV")
    logger.info("=" * 80)
    logger.info("🔒 READ-ONLY MODE")
    if args.start_date and args.end_date:
        logger.info(
            f"Filtering estimates sold between: {args.start_date} to {args.end_date}"
        )
        logger.info(
            "Using wider project date range for initial filtering (reduces API calls)"
        )
    else:
        logger.info("Searching all estimates (no date filter)")
    logger.info("")

    provider = get_crm_provider()
    tenant_id = getattr(provider, "tenant_id", 0)

    # Create output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = output_dir / f"rilla_links_{timestamp}.csv"

    # CSV columns
    fieldnames = [
        "estimate_sold_date",
        "project_id",
        "job_id",
        "estimate_id",
        "rilla_link",
    ]

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

            # Parse date filters for estimate filtering
            from datetime import datetime as dt
            from datetime import timedelta, timezone

            start_date_obj = None
            end_date_obj = None

            # Project date filters (use wider range to capture relevant projects)
            filters = {}

            if args.start_date:
                start_date_obj = dt.fromisoformat(args.start_date)
                # Make timezone-aware if it's naive
                if start_date_obj.tzinfo is None:
                    start_date_obj = start_date_obj.replace(tzinfo=timezone.utc)

                # Use a wider range for project filtering (60 days before)
                # This ensures we catch projects created before the estimate was sold
                project_start = (start_date_obj - timedelta(days=60)).strftime(
                    "%Y-%m-%d"
                )
                filters["createdOnOrAfter"] = project_start
                logger.info(f"Fetching projects created on or after: {project_start}")

            if args.end_date:
                end_date_obj = dt.fromisoformat(args.end_date)
                # Make timezone-aware if it's naive
                if end_date_obj.tzinfo is None:
                    # Set to end of day
                    end_date_obj = end_date_obj.replace(
                        hour=23, minute=59, second=59, tzinfo=timezone.utc
                    )

                # Use a wider range for project filtering (30 days after)
                project_end = (end_date_obj + timedelta(days=30)).strftime("%Y-%m-%d")
                filters["createdBefore"] = project_end
                logger.info(f"Fetching projects created before: {project_end}")

            logger.info("")

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

                        try:
                            # Find sold estimates for this project
                            estimates_request = EstimatesRequest(
                                tenant=int(tenant_id),
                                project_id=int(project_id),
                                page=1,
                                page_size=50,
                            )
                            estimates_response = await provider.get_estimates(
                                estimates_request
                            )

                            # Filter for sold estimates
                            sold_estimates = [
                                e
                                for e in estimates_response.estimates
                                if e.sold_on is not None
                            ]

                            if not sold_estimates:
                                return None

                            # Filter by date range if provided
                            if start_date_obj or end_date_obj:
                                filtered_estimates = []
                                for e in sold_estimates:
                                    # e.sold_on is already a datetime object
                                    sold_date = e.sold_on

                                    # Check if within date range
                                    if start_date_obj and sold_date < start_date_obj:
                                        continue
                                    if end_date_obj and sold_date > end_date_obj:
                                        continue

                                    filtered_estimates.append(e)

                                sold_estimates = filtered_estimates

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
                                logger.info(
                                    f"  ✓ Project {project_id}: Found Rilla link (sold: {estimate.sold_on})"
                                )
                                return {
                                    "estimate_sold_date": estimate.sold_on.isoformat()
                                    if estimate.sold_on
                                    else "",
                                    "project_id": project_id,
                                    "job_id": job_id,
                                    "estimate_id": estimate.id,
                                    "rilla_link": rilla_url,
                                }

                            return None

                        except Exception as e:
                            logger.warning(
                                f"  Error processing project {project_id}: {e}"
                            )
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
