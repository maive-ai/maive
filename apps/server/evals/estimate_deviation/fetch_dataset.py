#!/usr/bin/env python3
"""
Script to export Rilla links from Service Titan projects to JSON and upload estimate data to S3.

This script:
1. Iterates through all projects
2. Finds sold estimates for each project (filtered by sold date if specified)
3. Extracts Rilla links from job summaries
4. Fetches full estimate data (estimate + items) as JSON
5. Fetches form submission data (Form ID 104: Appointment Result) as JSON
6. Uploads estimate data to S3 at s3://vertex-rilla-data/val/<uuid>/estimate.json
7. Uploads form data to S3 at s3://vertex-rilla-data/val/<uuid>/form.json
8. Outputs JSON array with: uuid, project_created_date, estimate_sold_date, project_id, job_id, estimate_id, estimate_s3_uri, form_s3_uri, rilla_links, rilla_recordings_s3_uri, rilla_transcripts_s3_uri

Usage:
    # Export all Rilla links
    esc run maive/maive-infra/will-dev -- uv run python scripts/fetch_dataset.py

    # Export Rilla links for estimates sold in July 2025
    esc run maive/maive-infra/will-dev -- uv run python scripts/fetch_dataset.py --start-date 2025-07-09 --end-date 2025-07-10
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from tqdm.asyncio import tqdm

os.environ["CRM_PROVIDER"] = "service_titan"

from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.schemas import (
    EstimateItemsRequest,
    EstimatesRequest,
    FormSubmissionOwnerFilter,
    FormSubmissionsRequest,
)
from src.utils.logger import logger


def extract_rilla_urls(job_summary: str | None) -> list[str]:
    """
    Extract all Rilla URLs from a job summary field.

    Args:
        job_summary: The job summary text (HTML/plain text)

    Returns:
        List of Rilla URLs found (empty list if none found)

    Example:
        >>> extract_rilla_urls("... Rilla link: https://app.rillavoice.com/conversations/single?id=abc123 ...")
        ['https://app.rillavoice.com/conversations/single?id=abc123']
    """
    if not job_summary:
        return []

    # Pattern to match Rilla URLs
    pattern = r"https://app\.rillavoice\.com/conversations/single\?id=[a-f0-9-]+"

    # Find all matches
    matches = re.findall(pattern, job_summary, re.IGNORECASE)
    return matches


def extract_rilla_uuid(rilla_url: str) -> str | None:
    """
    Extract the UUID from a Rilla URL.

    Args:
        rilla_url: The Rilla URL

    Returns:
        The UUID if found, None otherwise

    Example:
        >>> extract_rilla_uuid("https://app.rillavoice.com/conversations/single?id=abc123-def456")
        'abc123-def456'
    """
    if not rilla_url:
        return None

    # Extract the id parameter from the URL
    pattern = r"id=([a-f0-9-]+)"
    match = re.search(pattern, rilla_url, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def upload_to_s3(local_file: str, s3_path: str) -> bool:
    """
    Upload a file to S3 using AWS CLI.

    Args:
        local_file: Path to local file
        s3_path: Full S3 path (e.g., s3://bucket/key)

    Returns:
        True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            ["aws", "s3", "cp", local_file, s3_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to upload to S3: {e.stderr}")
        return False


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
    logger.info("Exporting Rilla Links to JSON and Uploading Estimate Data to S3")
    logger.info("=" * 80)
    logger.info("📤 S3 Upload Mode: s3://vertex-rilla-data/val/<uuid>/estimate.json")
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
    json_file = output_dir / f"rilla_links_{timestamp}.json"

    total_projects = 0
    projects_with_rilla = 0
    total_rilla_links = 0
    successful_estimate_uploads = 0
    successful_form_uploads = 0

    # Collect all results to write as JSON array at the end
    all_results = []

    # Semaphore to limit concurrent requests (avoid overwhelming API)
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

    try:
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
            project_start = (start_date_obj - timedelta(days=60)).strftime("%Y-%m-%d")
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

                                # Make sold_date timezone-aware if it's not
                                if sold_date.tzinfo is None:
                                    from datetime import timezone

                                    sold_date = sold_date.replace(tzinfo=timezone.utc)

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

                        # Extract Rilla URLs (as a list)
                        rilla_urls = extract_rilla_urls(job_summary)

                        if rilla_urls:
                            # Use the first Rilla URL for the UUID and S3 upload
                            first_rilla_url = rilla_urls[0]
                            uuid = extract_rilla_uuid(first_rilla_url)
                            if not uuid:
                                logger.warning(
                                    f"  Could not extract UUID from Rilla URL: {first_rilla_url}"
                                )
                                return None

                            logger.info(
                                f"  ✓ Project {project_id}: Found {len(rilla_urls)} Rilla link(s) (UUID: {uuid})"
                            )

                            # Fetch estimate items
                            items_request = EstimateItemsRequest(
                                tenant=int(tenant_id),
                                estimate_id=estimate.id,
                                page=1,
                                page_size=50,
                            )
                            items_response = await provider.get_estimate_items(
                                items_request
                            )

                            # Filter to only include active, customer-facing items
                            active_items = [
                                item
                                for item in items_response.items
                                if item.invoice_item_id is None
                                and item.chargeable is not False
                            ]

                            # Create estimate data JSON
                            estimate_data = {
                                "estimate": estimate.model_dump()
                                if hasattr(estimate, "model_dump")
                                else estimate.__dict__,
                                "items": [
                                    item.model_dump()
                                    if hasattr(item, "model_dump")
                                    else item.__dict__
                                    for item in active_items
                                ],
                            }

                            # Save estimate to temporary file
                            temp_estimate_file = (
                                output_dir / f"temp_estimate_{uuid}.json"
                            )
                            with open(temp_estimate_file, "w") as f:
                                json.dump(estimate_data, f, indent=2, default=str)

                            # Upload estimate to S3
                            estimate_s3_path = (
                                f"s3://vertex-rilla-data/val/{uuid}/estimate.json"
                            )
                            estimate_upload_success = upload_to_s3(
                                str(temp_estimate_file), estimate_s3_path
                            )
                            if estimate_upload_success:
                                logger.info(
                                    f"    ✓ Uploaded estimate data to {estimate_s3_path}"
                                )
                            else:
                                logger.warning(
                                    "    ⚠️ Failed to upload estimate data to S3"
                                )

                            # Clean up temp estimate file
                            temp_estimate_file.unlink()

                            # Fetch form submission data (Form ID 104: Appointment Result)
                            form_upload_success = False
                            form_s3_path = (
                                f"s3://vertex-rilla-data/val/{uuid}/form.json"
                            )
                            try:
                                form_request = FormSubmissionsRequest(
                                    tenant=int(tenant_id),
                                    form_id=104,  # Appointment Result form
                                    page=1,
                                    page_size=10,
                                    status="Any",
                                    owners=[
                                        FormSubmissionOwnerFilter(type="Job", id=job_id)
                                    ],
                                )
                                form_result = await provider.get_form_submissions(
                                    form_request
                                )

                                if form_result.data:
                                    # Get the first (most recent) submission
                                    form_submission = form_result.data[0]

                                    # Convert to dict for JSON serialization
                                    form_data = (
                                        form_submission.model_dump()
                                        if hasattr(form_submission, "model_dump")
                                        else form_submission.__dict__
                                    )

                                    # Save form to temporary file
                                    temp_form_file = (
                                        output_dir / f"temp_form_{uuid}.json"
                                    )
                                    with open(temp_form_file, "w") as f:
                                        json.dump(form_data, f, indent=2, default=str)

                                    # Upload form to S3
                                    form_upload_success = upload_to_s3(
                                        str(temp_form_file), form_s3_path
                                    )
                                    if form_upload_success:
                                        logger.info(
                                            f"    ✓ Uploaded form data to {form_s3_path}"
                                        )
                                    else:
                                        logger.warning(
                                            "    ⚠️ Failed to upload form data to S3"
                                        )

                                    # Clean up temp form file
                                    temp_form_file.unlink()
                                else:
                                    logger.info(
                                        "    ℹ️  No form submission found for this job"
                                    )
                            except Exception as e:
                                logger.warning(f"    ⚠️ Error fetching form data: {e}")

                            return {
                                "uuid": uuid,
                                "project_created_date": project.created_at
                                if project.created_at
                                else "",
                                "estimate_sold_date": estimate.sold_on.isoformat()
                                if estimate.sold_on
                                else "",
                                "project_id": project_id,
                                "job_id": job_id,
                                "estimate_id": estimate.id,
                                "estimate_s3_uri": estimate_s3_path
                                if estimate_upload_success
                                else "",
                                "form_s3_uri": form_s3_path
                                if form_upload_success
                                else "",
                                "rilla_links": rilla_urls,  # Store as list in JSONL
                                "rilla_recordings_s3_uri": "",  # Empty for now
                                "rilla_transcripts_s3_uri": "",  # Empty for now
                                "labels": "",  # Empty for now
                                "notes": "",  # Empty for now
                                "estimate_upload_success": estimate_upload_success,
                                "form_upload_success": form_upload_success,
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

            # Collect results
            for result in results:
                if result:
                    projects_with_rilla += 1
                    total_rilla_links += 1
                    if result.get("estimate_upload_success", False):
                        successful_estimate_uploads += 1
                    if result.get("form_upload_success", False):
                        successful_form_uploads += 1
                    # Remove upload success flags from JSON output
                    json_row = {
                        k: v
                        for k, v in result.items()
                        if k not in ["estimate_upload_success", "form_upload_success"]
                    }
                    all_results.append(json_row)

            total_projects += len(projects)
            page += 1

        # Write all results to JSON file
        with open(json_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total projects processed: {total_projects}")
        logger.info(f"Projects with Rilla links: {projects_with_rilla}")
        logger.info(f"Total Rilla links found: {total_rilla_links}")
        logger.info(
            f"Successful estimate uploads: {successful_estimate_uploads}/{total_rilla_links}"
        )
        logger.info(
            f"Successful form uploads: {successful_form_uploads}/{total_rilla_links}"
        )
        logger.info(f"\n✓ JSON file saved to: {json_file}")

        if total_rilla_links > 0:
            logger.info("\n📊 Sample data:")
            # Display first 5 rows
            for i, row in enumerate(all_results[:5]):
                logger.info(f"  {row}")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise
    finally:
        await provider.close()
        logger.info("\nScript completed")


if __name__ == "__main__":
    asyncio.run(main())
