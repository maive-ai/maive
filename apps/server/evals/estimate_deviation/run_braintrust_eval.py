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
import json
from datetime import datetime
from pathlib import Path

import braintrust
from braintrust import Eval

from evals.estimate_deviation.scorers import comprehensive_deviation_scorer
from src.utils.logger import logger
from src.workflows.discrepancy_detection_v2 import DiscrepancyDetectionV2Workflow

# Global error log file path
ERROR_LOG_FILE = Path(__file__).parent / "error_summary.jsonl"


def log_error_to_file(error_entry: dict):
    """Append error entry to JSONL file for easy reading.

    Args:
        error_entry: Dict with error information to log
    """
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(json.dumps(error_entry) + "\n")


def logging_scorer_wrapper(input, output, expected=None, **kwargs):
    """Wrapper around comprehensive_deviation_scorer that logs errors to file.

    Priority: Log FALSE POSITIVES (predicted deviations that were wrong)
    Also logs: False negatives, occurrence mismatches, line item errors
    """
    from evals.estimate_deviation.schemas import Deviation

    # Run the original scorer
    scores = comprehensive_deviation_scorer(input, output, expected, **kwargs)

    # Extract metrics from the precision score
    precision_score = scores[0]
    metadata = precision_score.metadata

    # Get matched and unmatched deviations
    matches = metadata.get("matches", [])
    tp = metadata.get("tp", 0)
    fp = metadata.get("fp", 0)
    fn = metadata.get("fn", 0)

    # Parse deviations
    output_devs = [Deviation(**d) for d in output.get("deviations", [])]
    expected_devs = [Deviation(**d) for d in expected.get("deviations", [])]

    # Track which predictions were matched
    matched_predicted_explanations = {m["predicted_explanation"] for m in matches}

    # Get dataset ID from kwargs if available
    dataset_id = kwargs.get("id", "unknown")
    timestamp = datetime.now().isoformat()

    # LOG FALSE POSITIVES (TOP PRIORITY)
    false_positives = [
        dev
        for dev in output_devs
        if dev.explanation[:100] not in matched_predicted_explanations
    ]

    for fp_dev in false_positives:
        error_entry = {
            "timestamp": timestamp,
            "dataset_id": dataset_id,
            "error_type": "FALSE_POSITIVE",
            "severity": "HIGH",
            "predicted_deviation": {
                "class": fp_dev.deviation_class,
                "explanation": fp_dev.explanation,
                "occurrences": [
                    {
                        "conversation_idx": occ.conversation_idx,
                        "timestamp": occ.timestamp,
                    }
                    for occ in (fp_dev.occurrences or [])
                ],
                "line_item": (
                    {
                        "display_name": fp_dev.predicted_line_item.matched_pricebook_item_display_name,
                        "quantity": fp_dev.predicted_line_item.quantity,
                        "unit_cost": fp_dev.predicted_line_item.unit_cost,
                    }
                    if fp_dev.predicted_line_item
                    else None
                ),
            },
            "expected_deviations": [
                {
                    "class": exp.deviation_class,
                    "explanation": exp.explanation[:100],
                }
                for exp in expected_devs
            ],
            "metrics": {
                "precision": precision_score.score,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            },
        }
        log_error_to_file(error_entry)
        logger.warning(f"FALSE POSITIVE logged: {fp_dev.explanation[:80]}")

    # Log false negatives
    matched_expected_explanations = {m["expected_explanation"] for m in matches}
    false_negatives = [
        dev
        for dev in expected_devs
        if dev.explanation[:100] not in matched_expected_explanations
    ]

    for fn_dev in false_negatives:
        error_entry = {
            "timestamp": timestamp,
            "dataset_id": dataset_id,
            "error_type": "FALSE_NEGATIVE",
            "severity": "MEDIUM",
            "expected_deviation": {
                "class": fn_dev.deviation_class,
                "explanation": fn_dev.explanation,
                "occurrences": [
                    {
                        "conversation_idx": occ.conversation_idx,
                        "timestamp": occ.timestamp,
                    }
                    for occ in (fn_dev.occurrences or [])
                ],
            },
            "predicted_deviations": [
                {
                    "class": pred.deviation_class,
                    "explanation": pred.explanation[:100],
                }
                for pred in output_devs
            ],
            "metrics": {
                "precision": precision_score.score,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            },
        }
        log_error_to_file(error_entry)
        logger.warning(f"FALSE NEGATIVE logged: {fn_dev.explanation[:80]}")

    return scores


async def task(input, hooks):
    """Run workflow on a single dataset entry.

    Args:
        input: Dict with JSONAttachment objects (estimate, form, transcripts)
        hooks: Braintrust hooks

    Returns:
        Dict with deviations
    """
    import json as json_module
    # import asyncio

    # task_id = id(asyncio.current_task())
    # logger.info(f"[Task {task_id}] Starting workflow with parsed data from Braintrust")

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
        logger.info("Have transcripts", transcripts=transcripts)
        transcript_data = None
        for transcript in transcripts:
            transcript_data = extract_json(transcript)
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
    parser.add_argument(
        "--max-concurrency",
        "-c",
        type=int,
        default=10,
        help="Maximum number of parallel evaluations to run (default: 5)",
    )
    parser.add_argument(
        "--clear-error-log",
        action="store_true",
        help="Clear the error log file before starting evaluation",
    )

    args = parser.parse_args()

    # Clear error log if requested
    if args.clear_error_log:
        if ERROR_LOG_FILE.exists():
            ERROR_LOG_FILE.unlink()
            logger.info(f"Cleared error log: {ERROR_LOG_FILE}")
        else:
            logger.info("No error log to clear")

    logger.info("=" * 60)
    logger.info("BRAINTRUST DISCREPANCY DETECTION EVAL")
    logger.info("=" * 60)
    logger.info(f"Dataset: {args.dataset_name}")
    logger.info(f"Experiment: {args.experiment_name or 'auto-generated'}")
    logger.info(f"Max Concurrency: {args.max_concurrency}")
    logger.info(f"Error Log: {ERROR_LOG_FILE}")
    logger.info("")

    # Load dataset from Braintrust
    dataset = braintrust.init_dataset(
        project="discrepancy-detection", name=args.dataset_name
    )

    # Run eval with logging scorer wrapper (logs errors to file)
    result = Eval(
        "discrepancy-detection",
        data=lambda: dataset,
        task=task,
        scores=[
            logging_scorer_wrapper,
        ],
        experiment_name=args.experiment_name,
        max_concurrency=args.max_concurrency,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("EVAL COMPLETE")
    logger.info("=" * 60)
    logger.info("View results at: https://braintrust.dev")
    logger.info(f"Summary: {result.summary}")
    logger.info("")
    logger.info(f"Error log written to: {ERROR_LOG_FILE}")

    # Count errors by type
    if ERROR_LOG_FILE.exists():
        error_counts = {"FALSE_POSITIVE": 0, "FALSE_NEGATIVE": 0}
        with open(ERROR_LOG_FILE, "r") as f:
            for line in f:
                entry = json.loads(line)
                error_type = entry.get("error_type")
                if error_type in error_counts:
                    error_counts[error_type] += 1

        logger.info(f"Total False Positives: {error_counts['FALSE_POSITIVE']}")
        logger.info(f"Total False Negatives: {error_counts['FALSE_NEGATIVE']}")
        logger.info(f"Review errors with: cat {ERROR_LOG_FILE} | jq .")


if __name__ == "__main__":
    main()
