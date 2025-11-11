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
        input: Dict with JSONAttachment objects (estimate, form, rilla_transcripts)
        hooks: Braintrust hooks

    Returns:
        Dict with deviations
    """
    import json as json_module

    logger.info("Running workflow with parsed data from Braintrust")

    # Helper to extract JSON from JSONAttachment (handles bytes)
    def extract_json(attachment):
        if not attachment:
            return None
        data = attachment.data
        if isinstance(data, bytes):
            return json_module.loads(data.decode("utf-8"))
        return data

    # Extract JSON data from JSONAttachment objects
    estimate_data = extract_json(input.get("estimate"))
    form_data = extract_json(input.get("form"))

    # Get first transcript (we only use one)
    rilla_transcripts = input.get("rilla_transcripts", [])
    transcript_data = (
        extract_json(rilla_transcripts[0]) if rilla_transcripts else None
    )

    if not estimate_data or not transcript_data:
        raise ValueError("Missing required data: estimate and transcript are required")

    # Create workflow and run with parsed data (no S3 fetching!)
    workflow = DiscrepancyDetectionV2Workflow(prelabel=False, experiment=None)

    deviations = await workflow.execute_with_parsed_data(
        estimate_data=estimate_data,
        form_data=form_data,
        transcript_data=transcript_data,
    )

    # Return simplified output for scoring
    return {
        "deviations": [d.model_dump() for d in deviations],
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
    main()
