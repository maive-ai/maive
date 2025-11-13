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
from pathlib import Path

import braintrust
from braintrust import Eval

from evals.estimate_deviation.scorers import comprehensive_deviation_scorer
from src.utils.logger import logger
from src.workflows.discrepancy_detection_v2 import DiscrepancyDetectionV2Workflow


async def task(input, hooks):
    """Run workflow on a single dataset entry.

    Args:
        input: Dict with JSONAttachment objects (estimate, form, transcripts)
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
    transcript = input.get("transcript")
    if transcript:
        transcript_data = extract_json(transcript)
    else:
        transcripts = input.get("transcripts", [])
        transcript_data = None
        for transcript in transcripts:
            transcript_data += extract_json(transcript)
            if transcript_data:
                break

    if not estimate_data or not transcript_data:
        raise ValueError("Missing required data: estimate and transcript are required")

    # Create workflow (prompt is loaded at module level in config)
    workflow = DiscrepancyDetectionV2Workflow()

    # Handle bytes if JSONAttachment returned bytes instead of parsed JSON
    if isinstance(transcript_data, bytes):
        transcript_dict = json_module.loads(transcript_data.decode("utf-8"))
    else:
        transcript_dict = transcript_data

    # Write transcript to temp file (required by run)
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_transcript:
        json_module.dump(transcript_dict, temp_transcript)
        temp_transcript_path = temp_transcript.name

    try:
        # Call run directly
        deviations = await workflow.run(
            estimate_data=estimate_data,
            form_data=form_data,
            audio_path=None,  # No audio in eval
            transcript_path=temp_transcript_path,
        )
    finally:
        # Clean up temp file
        Path(temp_transcript_path).unlink(missing_ok=True)

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
        "-d",
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

    # Run eval with comprehensive LLM-based scorer
    result = Eval(
        "discrepancy-detection",
        data=lambda: dataset,
        task=task,
        scores=[
            comprehensive_deviation_scorer,
        ],
        experiment_name=args.experiment_name,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("EVAL COMPLETE")
    logger.info("=" * 60)
    logger.info("View results at: https://braintrust.dev")
    logger.info(f"Summary: {result.summary}")


if __name__ == "__main__":
    main()
