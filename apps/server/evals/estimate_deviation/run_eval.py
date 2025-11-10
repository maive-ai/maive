"""Run evaluation for discrepancy detection workflow.

This script evaluates the workflow against ground truth labels and reports metrics.
"""

import argparse
import asyncio
from pathlib import Path

from evals.estimate_deviation.schemas import (
    DatasetEntry,
    get_labeled_entries,
    load_dataset,
    AggregateMetrics,
    AllScores,
    DiscrepancyDetectionOutput,
    EvalResult,
    EvalSummary,
    ExpectedOutput,
)
from evals.estimate_deviation.scorers import (
    classification_accuracy_scorer,
    confusion_matrix_scorer,
    detection_binary_scorer,
    false_negative_scorer,
    false_positive_scorer,
    occurrence_accuracy_scorer,
)
from src.utils.logger import logger
from src.workflows.discrepancy_detection_v2 import DiscrepancyDetectionV2Workflow

# Import Braintrust for evals
try:
    import braintrust

    BRAINTRUST_AVAILABLE = True
except ImportError:
    BRAINTRUST_AVAILABLE = False
    logger.warning("Braintrust not installed. Eval reporting will be limited.")


async def run_eval_on_entry(
    workflow: DiscrepancyDetectionV2Workflow,
    entry: DatasetEntry,
    dataset_path: str,
) -> EvalResult:
    """Run workflow and compare to ground truth labels.

    Args:
        workflow: Initialized workflow instance
        entry: Dataset entry with labels
        dataset_path: Path to dataset JSON

    Returns:
        EvalResult with prediction, expected, and scores
    """
    uuid = entry.uuid
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating UUID: {uuid}")
    logger.info(f"{'='*60}")

    # Run workflow
    try:
        result_dict = await workflow.execute_for_dataset_entry(
            uuid=uuid, dataset_path=dataset_path
        )
        prediction = DiscrepancyDetectionOutput(**result_dict)
    except Exception as e:
        logger.error(f"Workflow failed for {uuid}: {e}")
        raise

    # Prepare expected output from labels
    if not entry.labels:
        raise ValueError(f"Entry {uuid} has no labels")

    expected = ExpectedOutput(deviations=entry.labels.deviations)

    # Apply scorers
    try:
        classification_scores = classification_accuracy_scorer(prediction, expected)
        confusion_matrix_scores = confusion_matrix_scorer(prediction, expected)
        false_positive_scores = false_positive_scorer(prediction, expected)
        false_negative_scores = false_negative_scorer(prediction, expected)
        occurrence_scores = occurrence_accuracy_scorer(prediction, expected)
        detection_scores = detection_binary_scorer(prediction, expected)

        scores = AllScores(
            classification=classification_scores,
            confusion_matrix=confusion_matrix_scores,
            false_positives=false_positive_scores,
            false_negatives=false_negative_scores,
            occurrences=occurrence_scores,
            detection=detection_scores,
        )
    except Exception as e:
        logger.error(f"Scoring failed for {uuid}: {e}")
        raise

    logger.info(f"\n✅ Evaluation complete for {uuid}")
    logger.info(f"Overall F1: {scores.classification.overall_f1:.3f}")
    logger.info(
        f"False Positives: {scores.false_positives.false_positive_count}"
    )
    logger.info(
        f"False Negatives: {scores.false_negatives.false_negative_count}"
    )

    return EvalResult(
        uuid=uuid,
        prediction=prediction,
        expected=expected,
        scores=scores,
    )


async def run_eval(
    dataset_path: str,
    subset_uuids: list[str] | None = None,
    experiment_name: str | None = None,
) -> EvalSummary:
    """Run evaluation on labeled dataset entries.

    Args:
        dataset_path: Path to dataset.json
        subset_uuids: Optional list of specific UUIDs to evaluate
        experiment_name: Optional Braintrust experiment name

    Returns:
        EvalSummary with results and aggregate metrics
    """
    logger.info("=" * 60)
    logger.info("DISCREPANCY DETECTION EVALUATION")
    logger.info("=" * 60)
    logger.info(f"Dataset: {dataset_path}")
    logger.info("")

    # Load labeled entries
    if subset_uuids:
        dataset = load_dataset(dataset_path)
        labeled_entries = [
            e for e in dataset if e.labels is not None and e.uuid in subset_uuids
        ]
        logger.info(f"Evaluating subset: {len(labeled_entries)} entries")
    else:
        labeled_entries = get_labeled_entries(dataset_path)
        logger.info(f"Found {len(labeled_entries)} labeled entries")

    if not labeled_entries:
        logger.error("No labeled entries found. Please label some dataset entries first.")
        raise ValueError("No labeled entries found")

    # Initialize workflow
    workflow = DiscrepancyDetectionV2Workflow(prelabel=False, experiment=None)

    # Run evaluation on each entry
    results: list[EvalResult] = []
    errors = 0
    for entry in labeled_entries:
        try:
            result = await run_eval_on_entry(workflow, entry, dataset_path)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to evaluate {entry.uuid}: {e}")
            errors += 1

    # Aggregate metrics
    aggregate_metrics = aggregate_scores(results, errors)

    # Print summary
    print_eval_summary(aggregate_metrics)

    # Create summary
    summary = EvalSummary(
        results=results,
        aggregate_metrics=aggregate_metrics,
        total_entries=len(labeled_entries),
    )

    # Log to Braintrust if available
    if BRAINTRUST_AVAILABLE and experiment_name:
        try:
            log_to_braintrust(summary, experiment_name)
        except Exception as e:
            logger.error(f"Failed to log to Braintrust: {e}")

    return summary


def aggregate_scores(results: list[EvalResult], error_count: int) -> AggregateMetrics:
    """Aggregate scores across all evaluation results.

    Args:
        results: List of evaluation results from run_eval_on_entry
        error_count: Number of failed evaluations

    Returns:
        AggregateMetrics with aggregated metrics
    """
    if not results:
        raise ValueError("No successful evaluations to aggregate")

    # Aggregate classification metrics
    avg_f1 = sum(r.scores.classification.overall_f1 for r in results) / len(results)
    avg_precision = sum(r.scores.classification.overall_precision for r in results) / len(results)
    avg_recall = sum(r.scores.classification.overall_recall for r in results) / len(results)

    # Aggregate false positives/negatives
    total_fp = sum(r.scores.false_positives.false_positive_count for r in results)
    total_fn = sum(r.scores.false_negatives.false_negative_count for r in results)

    # Aggregate occurrence accuracy
    avg_occurrence_accuracy = sum(
        r.scores.occurrences.occurrence_accuracy for r in results
    ) / len(results)

    return AggregateMetrics(
        avg_f1=avg_f1,
        avg_precision=avg_precision,
        avg_recall=avg_recall,
        total_false_positives=total_fp,
        total_false_negatives=total_fn,
        avg_occurrence_accuracy=avg_occurrence_accuracy,
        total_evaluated=len(results),
        total_errors=error_count,
    )


def print_eval_summary(metrics: AggregateMetrics) -> None:
    """Print evaluation summary to console.

    Args:
        metrics: Aggregated metrics from aggregate_scores
    """
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Entries Evaluated: {metrics.total_evaluated}")
    print(f"Errors: {metrics.total_errors}")
    print("")
    print("Classification Metrics:")
    print(f"  Average F1 Score:   {metrics.avg_f1:.3f}")
    print(f"  Average Precision:  {metrics.avg_precision:.3f}")
    print(f"  Average Recall:     {metrics.avg_recall:.3f}")
    print("")
    print("Error Analysis:")
    print(f"  Total False Positives:  {metrics.total_false_positives}")
    print(f"  Total False Negatives:  {metrics.total_false_negatives}")
    print("")
    print("Occurrence Accuracy:")
    print(f"  Average Timestamp Accuracy: {metrics.avg_occurrence_accuracy:.3f}")
    print("=" * 60)


def log_to_braintrust(summary: EvalSummary, experiment_name: str) -> None:
    """Log evaluation results to Braintrust.

    Args:
        summary: Complete evaluation summary
        experiment_name: Name for Braintrust experiment
    """
    logger.info(f"Logging evaluation results to Braintrust: {experiment_name}")

    # Create eval
    braintrust.init(
        project="discrepancy-detection",
        experiment=experiment_name,
    )

    # Log each result
    for result in summary.results:
        braintrust.log(
            input={"uuid": result.uuid},
            output=result.prediction.model_dump(mode="json"),
            expected=result.expected.model_dump(mode="json"),
            scores={
                "f1": result.scores.classification.overall_f1,
                "precision": result.scores.classification.overall_precision,
                "recall": result.scores.classification.overall_recall,
                "false_positive_count": result.scores.false_positives.false_positive_count,
                "false_negative_count": result.scores.false_negatives.false_negative_count,
                "occurrence_accuracy": result.scores.occurrences.occurrence_accuracy,
            },
        )

    logger.info("✅ Logged to Braintrust successfully")


async def main():
    """Main entry point for evaluation script."""
    parser = argparse.ArgumentParser(
        description="Evaluate discrepancy detection workflow against ground truth labels"
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="evals/estimate_deviation/dataset.json",
        help="Path to dataset.json file",
    )
    parser.add_argument(
        "--subset",
        type=str,
        nargs="+",
        default=None,
        help="Specific UUIDs to evaluate (space-separated)",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Braintrust experiment name for logging results",
    )

    args = parser.parse_args()

    # Ensure dataset path is absolute
    dataset_path = str(Path(args.dataset_path).resolve())

    # Run evaluation
    await run_eval(
        dataset_path=dataset_path,
        subset_uuids=args.subset,
        experiment_name=args.experiment_name,
    )


if __name__ == "__main__":
    asyncio.run(main())
