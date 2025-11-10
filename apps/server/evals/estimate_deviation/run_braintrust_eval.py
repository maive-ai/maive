"""Braintrust-powered evaluation for discrepancy detection.

This eval uses Braintrust's Eval() framework to:
- Load ground truth labels from Braintrust dataset
- Run workflow on each input
- Apply custom scorers
- Automatically aggregate and display results

Usage:
    uv run python -m evals.estimate_deviation.run_braintrust_eval
"""

import argparse
import asyncio

import braintrust
from braintrust import Eval

from evals.estimate_deviation.scorers import (
    classification_accuracy_scorer_bt,
    detection_binary_scorer_bt,
    false_negative_scorer_bt,
    false_positive_scorer_bt,
    occurrence_accuracy_scorer_bt,
)
from src.utils.logger import logger
from src.workflows.discrepancy_detection_v2 import DiscrepancyDetectionV2Workflow


async def task(input, hooks):
    """Run workflow on a single dataset entry.

    Args:
        input: Dict with uuid, project_id, job_id, estimate_id
        hooks: Braintrust hooks for adding metadata

    Returns:
        Dict with deviations and cost_savings
    """
    uuid = input["uuid"]
    logger.info(f"Running workflow for {uuid}")

    workflow = DiscrepancyDetectionV2Workflow(prelabel=False, experiment=None)

    # Execute workflow (will fetch data from S3)
    result = await workflow.execute_for_dataset_entry(
        uuid=uuid, dataset_path=None  # None means fetch from S3
    )

    # Return simplified output for scoring
    return {
        "deviations": [d.model_dump() for d in result["deviations"]],
        "cost_savings": result["cost_savings"],
    }


def main():
    """Main entry point for Braintrust eval."""
    parser = argparse.ArgumentParser(
        description="Run Braintrust-powered eval on discrepancy detection"
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="ground-truth-labels",
        help="Name of Braintrust dataset to evaluate against",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Name for this eval experiment (defaults to auto-generated)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BRAINTRUST DISCREPANCY DETECTION EVAL")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset_name}")
    logger.info(f"Experiment: {args.experiment_name or 'auto-generated'}")
    logger.info("")

    # Load dataset from Braintrust
    dataset = braintrust.init_dataset(
        project="discrepancy-detection", name=args.dataset_name
    )

    # Run eval
    result = Eval(
        "discrepancy-detection",
        data=lambda: dataset,
        task=task,
        scores=[
            classification_accuracy_scorer_bt,
            false_positive_scorer_bt,
            false_negative_scorer_bt,
            occurrence_accuracy_scorer_bt,
            detection_binary_scorer_bt,
        ],
        experiment_name=args.experiment_name,
        metadata={
            "workflow_version": "v2",
            "eval_type": "full",
        },
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("EVAL COMPLETE")
    logger.info("=" * 60)
    logger.info("View results at: https://braintrust.dev")
    logger.info(f"Summary: {result.summary}")


if __name__ == "__main__":
    asyncio.run(main())
