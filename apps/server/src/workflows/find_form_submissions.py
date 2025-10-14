"""
Find form submissions for projects with sold estimates in a specific price range.

This script queries ServiceTitan for form submissions (form ID 2933) and filters
for submissions associated with projects that have sold estimates between $15,000-$80,000.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime

from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.schemas import (
    EstimateItemsRequest,
    EstimatesRequest,
    FormSubmissionsRequest,
    ProjectByIdRequest,
)
from src.utils.logger import logger


class FormSubmissionFinder:
    """Find form submissions matching specific criteria."""

    def __init__(self):
        """Initialize the finder."""
        self.crm_provider = get_crm_provider()
        self.tenant_id = getattr(self.crm_provider, "tenant_id", 0)

    async def find_submissions_with_estimate_range(
        self,
        form_id: int = 2933,
        min_estimate: float = 15000.0,
        max_estimate: float = 80000.0,
        max_results: int = 3,
        page_size: int = 50,
    ) -> list[dict]:
        """
        Find form submissions with sold estimates in the specified range.

        Args:
            form_id: Form ID to query (default: 2933 - Appointment Result V2)
            min_estimate: Minimum estimate total (inclusive)
            max_estimate: Maximum estimate total (inclusive)
            max_results: Maximum number of matching submissions to return
            page_size: Number of submissions to fetch per page

        Returns:
            List of matching form submission records with estimate info
        """
        logger.info("=" * 80)
        logger.info("FORM SUBMISSION FINDER")
        logger.info("=" * 80)
        logger.info(f"Form ID: {form_id}")
        logger.info(f"Estimate range: ${min_estimate:,.2f} - ${max_estimate:,.2f}")
        logger.info(f"Max results: {max_results}")
        logger.info("")

        matching_submissions = []
        page = 1
        total_checked = 0

        while len(matching_submissions) < max_results:
            logger.info(f"Fetching form submissions - Page {page}")

            # Fetch form submissions
            # Use get_form_submissions if available (ServiceTitan), otherwise use get_all_form_submissions (base interface)
            if hasattr(self.crm_provider, "get_form_submissions"):
                form_request = FormSubmissionsRequest(
                    tenant=int(self.tenant_id),
                    form_id=form_id,
                    page=page,
                    page_size=page_size,
                    status="Any",
                )
                form_result = await self.crm_provider.get_form_submissions(form_request)
            else:
                # Fallback to base interface method
                form_result = await self.crm_provider.get_all_form_submissions(
                    form_ids=[form_id],
                    status="Any",
                )
            submissions = form_result.data

            if not submissions:
                logger.info("No more form submissions to process")
                break

            logger.info(f"Processing {len(submissions)} submissions from page {page}")

            # Process each submission
            for submission in submissions:
                total_checked += 1

                # Extract job ID from owners
                job_id = self._extract_job_id(submission)
                if not job_id:
                    logger.debug(f"Submission {submission.id} has no job owner, skipping")
                    continue

                # Get submission timestamp
                submitted_on = (
                    submission.submitted_on
                    if hasattr(submission, "submitted_on")
                    else submission.get("submitted_on")
                )

                try:
                    # Get job details to find project
                    job = await self.crm_provider.get_job(job_id)
                    project_id = job.project_id

                    if not project_id:
                        logger.debug(f"Job {job_id} has no project, skipping")
                        continue

                    # Find sold estimate for this project
                    sold_estimate = await self._find_sold_estimate(job_id, project_id)

                    if not sold_estimate:
                        logger.debug(
                            f"Job {job_id} / Project {project_id} has no sold estimate, skipping"
                        )
                        continue

                    # Calculate total estimate value
                    estimate_total = sold_estimate.subtotal + sold_estimate.tax

                    # Check if estimate is in range
                    if min_estimate <= estimate_total <= max_estimate:
                        logger.info(f"✅ MATCH FOUND!")
                        logger.info(f"   Submission ID: {submission.id}")
                        logger.info(f"   Job ID: {job_id}")
                        logger.info(f"   Project ID: {project_id}")
                        logger.info(f"   Estimate ID: {sold_estimate.id}")
                        logger.info(f"   Estimate Total: ${estimate_total:,.2f}")
                        logger.info(
                            f"   Submitted On: {submitted_on.isoformat() if submitted_on else 'N/A'}"
                        )
                        logger.info("")

                        matching_submissions.append(
                            {
                                "submission_id": submission.id,
                                "job_id": job_id,
                                "project_id": project_id,
                                "estimate_id": sold_estimate.id,
                                "estimate_total": estimate_total,
                                "estimate_subtotal": sold_estimate.subtotal,
                                "estimate_tax": sold_estimate.tax,
                                "submitted_on": (
                                    submitted_on.isoformat() if submitted_on else None
                                ),
                                "submission_data": submission,
                            }
                        )

                        if len(matching_submissions) >= max_results:
                            break

                    else:
                        logger.debug(
                            f"Job {job_id} estimate ${estimate_total:,.2f} not in range, skipping"
                        )

                except Exception as e:
                    logger.warning(f"Error processing submission {submission.id}: {e}")
                    continue

            # Check if we should continue to next page
            if len(matching_submissions) >= max_results:
                break

            # Check if pagination is supported
            if hasattr(form_result, "has_more"):
                if not form_result.has_more:
                    logger.info("No more pages available")
                    break
                page += 1
            else:
                # MockCRM doesn't support pagination, so we're done
                logger.info("Provider doesn't support pagination, stopping")
                break

        logger.info("=" * 80)
        logger.info(f"SEARCH COMPLETE")
        logger.info(f"Total submissions checked: {total_checked}")
        logger.info(f"Matching submissions found: {len(matching_submissions)}")
        logger.info("=" * 80)

        return matching_submissions

    def _extract_job_id(self, submission) -> int | None:
        """Extract job ID from submission owners."""
        owners = (
            submission.owners
            if hasattr(submission, "owners")
            else submission.get("owners", [])
        )

        for owner in owners:
            owner_dict = (
                owner
                if isinstance(owner, dict)
                else owner.__dict__
                if hasattr(owner, "__dict__")
                else {}
            )
            if owner_dict.get("type") == "Job":
                return owner_dict.get("id")

        return None

    async def _find_sold_estimate(self, job_id: int, project_id: int):
        """
        Find the sold estimate for a job/project.

        Strategy:
        1. Check if the job has a sold estimate
        2. If not, query all estimates for the project and find the sold one
        3. If multiple sold estimates, take the most recent
        """
        # Step 1: Try to find sold estimate for this specific job
        job_estimates_request = EstimatesRequest(
            tenant=int(self.tenant_id),
            job_id=job_id,
            page=1,
            page_size=50,
        )
        job_estimates_response = await self.crm_provider.get_estimates(
            job_estimates_request
        )

        # Check for sold estimates on this job
        job_sold_estimates = [
            e for e in job_estimates_response.estimates if e.sold_on is not None
        ]

        if len(job_sold_estimates) > 0:
            if len(job_sold_estimates) > 1:
                job_sold_estimates.sort(key=lambda e: e.sold_on, reverse=True)
            return job_sold_estimates[0]

        # Step 2: No sold estimate on job, search at project level
        project_estimates_request = EstimatesRequest(
            tenant=int(self.tenant_id),
            project_id=project_id,
            page=1,
            page_size=50,
        )
        project_estimates_response = await self.crm_provider.get_estimates(
            project_estimates_request
        )

        # Filter for sold estimates
        project_sold_estimates = [
            e for e in project_estimates_response.estimates if e.sold_on is not None
        ]

        if len(project_sold_estimates) == 0:
            return None

        if len(project_sold_estimates) > 1:
            project_sold_estimates.sort(key=lambda e: e.sold_on, reverse=True)

        return project_sold_estimates[0]


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Find form submissions with sold estimates in a specific price range"
    )
    parser.add_argument(
        "--form-id",
        type=int,
        default=2933,
        help="Form ID to query (default: 2933)",
    )
    parser.add_argument(
        "--min-estimate",
        type=float,
        default=15000.0,
        help="Minimum estimate total in dollars (default: 15000)",
    )
    parser.add_argument(
        "--max-estimate",
        type=float,
        default=80000.0,
        help="Maximum estimate total in dollars (default: 80000)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="Maximum number of results to return (default: 3)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="Number of submissions to fetch per page (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional output file path to save results as JSON",
    )

    args = parser.parse_args()

    finder = FormSubmissionFinder()
    results = await finder.find_submissions_with_estimate_range(
        form_id=args.form_id,
        min_estimate=args.min_estimate,
        max_estimate=args.max_estimate,
        max_results=args.max_results,
        page_size=args.page_size,
    )

    # Print results summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Submission ID: {result['submission_id']}")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Project ID: {result['project_id']}")
        print(f"   Estimate ID: {result['estimate_id']}")
        print(f"   Estimate Total: ${result['estimate_total']:,.2f}")
        print(f"   Submitted On: {result['submitted_on']}")

    # Save to file if requested
    if args.output:
        # Convert submission_data to dict for JSON serialization
        output_results = []
        for result in results:
            output_result = result.copy()
            submission = result["submission_data"]
            if hasattr(submission, "model_dump"):
                output_result["submission_data"] = submission.model_dump()
            elif hasattr(submission, "__dict__"):
                output_result["submission_data"] = submission.__dict__
            else:
                output_result["submission_data"] = dict(submission)
            output_results.append(output_result)

        with open(args.output, "w") as f:
            json.dump(output_results, f, indent=2, default=str)
        print(f"\n✅ Results saved to: {args.output}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
