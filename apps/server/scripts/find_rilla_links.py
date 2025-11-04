"""
Script to find Rilla links on Service Titan jobs and estimates.

This script exports job and estimate data for a date range and searches
for "rilla" case-insensitively across all fields.

Usage:
    esc run maive/maive-infra/will-dev -- uv run python scripts/find_rilla_links.py
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to path so we can import the app
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Force Service Titan provider for this script
os.environ["CRM_PROVIDER"] = "service_titan"

from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.providers.service_titan.constants import ServiceTitanEndpoints
from src.integrations.crm.schemas import EstimatesRequest
from src.utils.logger import logger


def search_for_rilla(data: Any, path: str = "") -> list[tuple[str, Any]]:
    """
    Recursively search for "rilla" case-insensitively in data.

    Args:
        data: The data to search (dict, list, or primitive)
        path: Current path in the data structure

    Returns:
        List of tuples (path, value) where "rilla" was found
    """
    matches = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # Check if key contains "rilla"
            if isinstance(key, str) and "rilla" in key.lower():
                matches.append((current_path, key))

            # Check if value contains "rilla"
            if isinstance(value, str) and "rilla" in value.lower():
                matches.append((current_path, value))

            # Recursively search nested structures
            matches.extend(search_for_rilla(value, current_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"

            # Check if item is a string containing "rilla"
            if isinstance(item, str) and "rilla" in item.lower():
                matches.append((current_path, item))

            # Recursively search nested structures
            matches.extend(search_for_rilla(item, current_path))

    elif isinstance(data, str) and "rilla" in data.lower():
        matches.append((path, data))

    return matches


async def fetch_jobs_with_rilla(
    provider,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """
    Fetch all jobs in date range and search for "rilla".

    Args:
        provider: CRM provider instance
        start_date: Start date for filtering jobs (inclusive)
        end_date: End date for filtering jobs (inclusive)

    Returns:
        List of jobs with Rilla matches, each containing the full job data and matches
    """
    logger.info(
        f"Fetching jobs with Rilla links between {start_date.date()} and {end_date.date()}..."
    )

    matching_jobs = []
    page = 1
    page_size = 50
    has_more = True

    base_api_url = provider.base_api_url
    tenant_id = provider.tenant_id

    while has_more:
        job_list = await provider.get_all_jobs(
            filters=None,
            page=page,
            page_size=page_size,
        )

        logger.info(f"   Processing page {page} ({len(job_list.jobs)} jobs)")

        for job in job_list.jobs:
            # Filter by date range
            if job.created_at:
                try:
                    created_at = (
                        datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
                        if isinstance(job.created_at, str)
                        else job.created_at
                    )
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=UTC)

                    if created_at < start_date or created_at > end_date:
                        continue
                except (ValueError, AttributeError) as e:
                    logger.warning(
                        f"   Could not parse created_at for job {job.id}: {e}"
                    )
                    continue

            # Fetch full project details to get raw JSON response
            try:
                url = f"{base_api_url}{ServiceTitanEndpoints.PROJECT_BY_ID.format(tenant_id=tenant_id, id=int(job.id))}"
                response = await provider._make_authenticated_request("GET", url)
                response.raise_for_status()
                job_data = response.json()

                # Search for "rilla" in the entire job data
                matches = search_for_rilla(job_data)

                if matches:
                    matching_jobs.append(
                        {
                            "job_id": job.id,
                            "job_number": job.number,
                            "job_data": job_data,
                            "matches": matches,
                        }
                    )
                    logger.info(
                        f"   Found Rilla in job {job.number} (ID: {job.id}) - {len(matches)} match(es)"
                    )

            except Exception as e:
                logger.warning(f"   Could not fetch full details for job {job.id}: {e}")
                continue

        has_more = job_list.has_more or False

        if has_more:
            page += 1
        else:
            logger.info(f"   Completed search through all {page} page(s)")
            break

    return matching_jobs


async def fetch_estimates_with_rilla(
    provider,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """
    Fetch all estimates in date range and search for "rilla".

    Args:
        provider: CRM provider instance
        start_date: Start date for filtering estimates (inclusive)
        end_date: End date for filtering estimates (inclusive)

    Returns:
        List of estimates with Rilla matches, each containing the full estimate data and matches
    """
    logger.info(
        f"Fetching estimates with Rilla links between {start_date.date()} and {end_date.date()}..."
    )

    matching_estimates = []
    page = 1
    page_size = 50
    has_more = True

    tenant_id = provider.tenant_id
    base_api_url = provider.base_api_url

    while has_more:
        estimates_request = EstimatesRequest(
            tenant=int(tenant_id),
            job_id=None,
            project_id=None,
            page=page,
            page_size=page_size,
        )

        estimates_response = await provider.get_estimates(estimates_request)

        logger.info(
            f"   Processing page {page} ({len(estimates_response.estimates)} estimates)"
        )

        for estimate in estimates_response.estimates:
            # Filter by date if provided
            created_on = getattr(estimate, "created_on", None)
            if created_on:
                if isinstance(created_on, str):
                    try:
                        created_on = datetime.fromisoformat(
                            created_on.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        created_on = None

                if created_on:
                    if created_on.tzinfo is None:
                        created_on = created_on.replace(tzinfo=UTC)

                    if created_on < start_date or created_on > end_date:
                        continue

            # Fetch full estimate details to get raw JSON response
            try:
                estimate_id = getattr(estimate, "id", None)
                if not estimate_id:
                    continue

                url = f"{base_api_url}{ServiceTitanEndpoints.ESTIMATE_BY_ID.format(tenant_id=tenant_id, id=int(estimate_id))}"
                response = await provider._make_authenticated_request("GET", url)
                response.raise_for_status()
                estimate_data = response.json()

                # Log externalLinks field if present
                external_links = estimate_data.get("externalLinks") or []
                if external_links:
                    logger.info(
                        f"   Estimate {getattr(estimate, 'id', 'N/A')} has {len(external_links)} external link(s):"
                    )
                    for link in external_links:
                        link_name = link.get("name", "N/A")
                        link_url = link.get("url", "N/A")
                        logger.info(f"     - {link_name}: {link_url}")

                # Search for "rilla" in the entire estimate data
                matches = search_for_rilla(estimate_data)

                if matches:
                    matching_estimates.append(
                        {
                            "estimate_id": getattr(estimate, "id", None),
                            "estimate_data": estimate_data,
                            "matches": matches,
                            "external_links": external_links,
                        }
                    )
                    logger.info(
                        f"   Found Rilla in estimate {getattr(estimate, 'id', 'N/A')} - {len(matches)} match(es)"
                    )
                elif external_links:
                    # Log external links even if no Rilla matches found
                    matching_estimates.append(
                        {
                            "estimate_id": getattr(estimate, "id", None),
                            "estimate_data": estimate_data,
                            "matches": [],
                            "external_links": external_links,
                        }
                    )

            except Exception as e:
                logger.warning(
                    f"   Could not process estimate {getattr(estimate, 'id', 'N/A')}: {e}"
                )
                continue

        has_more = estimates_response.has_more or False

        if has_more:
            page += 1
        else:
            logger.info(f"   Completed search through all {page} page(s)")
            break

    return matching_estimates


async def main():
    """Main function to find Rilla links on jobs and estimates."""
    # Date range: 07/01/2025 to 11/1/2025
    start_date = datetime(2025, 7, 1, tzinfo=UTC)
    end_date = datetime(2025, 11, 1, tzinfo=UTC)

    logger.info("=" * 80)
    logger.info("Finding Rilla Links on Service Titan Jobs and Estimates")
    logger.info("=" * 80)
    logger.info("🔒 READ-ONLY MODE: No changes will be made to Service Titan")
    logger.info("")
    logger.info(f"Date Range: {start_date.date()} to {end_date.date()}")
    logger.info("")

    provider = get_crm_provider()

    try:
        # Fetch jobs and estimates with Rilla
        jobs_with_rilla = await fetch_jobs_with_rilla(provider, start_date, end_date)
        estimates_with_rilla = await fetch_estimates_with_rilla(
            provider, start_date, end_date
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("RESULTS")
        logger.info("=" * 80)

        # Output directory for exported data
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export jobs with Rilla
        if jobs_with_rilla:
            logger.info(f"✅ Found {len(jobs_with_rilla)} job(s) with Rilla links")
            logger.info("")

            jobs_file = output_dir / f"jobs_with_rilla_{timestamp}.json"
            with open(jobs_file, "w") as f:
                json.dump(jobs_with_rilla, f, indent=2, default=str)

            logger.info(f"Exported job data to: {jobs_file}")
            logger.info("")

            # Log summary of matches
            for job in jobs_with_rilla:
                logger.info(
                    f"  Job {job['job_number']} (ID: {job['job_id']}) - {len(job['matches'])} match(es):"
                )
                for path, value in job["matches"][:5]:  # Show first 5 matches
                    value_str = (
                        str(value)[:100] + "..."
                        if len(str(value)) > 100
                        else str(value)
                    )
                    logger.info(f"    - {path}: {value_str}")
                if len(job["matches"]) > 5:
                    logger.info(f"    ... and {len(job['matches']) - 5} more match(es)")
                logger.info("")
        else:
            logger.info("❌ No jobs found with Rilla links")

        # Export estimates with Rilla
        if estimates_with_rilla:
            logger.info(
                f"✅ Found {len(estimates_with_rilla)} estimate(s) with Rilla links"
            )
            logger.info("")

            estimates_file = output_dir / f"estimates_with_rilla_{timestamp}.json"
            with open(estimates_file, "w") as f:
                json.dump(estimates_with_rilla, f, indent=2, default=str)

            logger.info(f"Exported estimate data to: {estimates_file}")
            logger.info("")

            # Log summary of matches
            for estimate in estimates_with_rilla:
                logger.info(
                    f"  Estimate {estimate['estimate_id']} - {len(estimate['matches'])} match(es):"
                )
                for path, value in estimate["matches"][:5]:  # Show first 5 matches
                    value_str = (
                        str(value)[:100] + "..."
                        if len(str(value)) > 100
                        else str(value)
                    )
                    logger.info(f"    - {path}: {value_str}")
                if len(estimate["matches"]) > 5:
                    logger.info(
                        f"    ... and {len(estimate['matches']) - 5} more match(es)"
                    )
                logger.info("")
        else:
            logger.info("❌ No estimates found with Rilla links")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Error searching for Rilla links: {e}", exc_info=True)
        raise
    finally:
        if hasattr(provider, "close"):
            await provider.close()
        logger.info("")
        logger.info("Script completed")


if __name__ == "__main__":
    asyncio.run(main())
