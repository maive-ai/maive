"""Evaluation scorers for discrepancy detection workflow.

These scorers compare predicted deviations against ground truth labels
to measure classification accuracy, precision, recall, and other metrics.
"""

from collections import defaultdict

from evals.estimate_deviation.schemas import (
    ClassificationScores,
    ConfusionMatrixScores,
    DetectionScores,
    DiscrepancyDetectionOutput,
    ExpectedOutput,
    FalseNegativeScores,
    FalsePositiveScores,
    OccurrenceScores,
    TimestampError,
)


def classification_accuracy_scorer(
    output: DiscrepancyDetectionOutput, expected: ExpectedOutput
) -> ClassificationScores:
    """Score classification accuracy with per-class precision, recall, and F1.

    Compares predicted deviation classes against ground truth labels.

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        ClassificationScores with per-class and overall metrics
    """
    # Extract deviation classes
    predicted_classes = [d.deviation_class for d in output.deviations]
    ground_truth_classes = [d.deviation_class for d in expected.deviations]

    # Calculate per-class metrics
    all_classes = set(predicted_classes + ground_truth_classes)
    per_class_metrics = {}

    for cls in all_classes:
        # True positives: in both predicted and ground truth
        tp = sum(1 for c in predicted_classes if c == cls and c in ground_truth_classes)

        # False positives: in predicted but not in ground truth
        fp = sum(
            1 for c in predicted_classes if c == cls and c not in ground_truth_classes
        )

        # False negatives: in ground truth but not in predicted
        fn = sum(
            1 for c in ground_truth_classes if c == cls and c not in predicted_classes
        )

        # Calculate precision, recall, F1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        per_class_metrics[f"{cls}_precision"] = precision
        per_class_metrics[f"{cls}_recall"] = recall
        per_class_metrics[f"{cls}_f1"] = f1

    # Overall metrics (macro-averaged)
    if all_classes:
        overall_precision = sum(
            per_class_metrics[f"{cls}_precision"] for cls in all_classes
        ) / len(all_classes)
        overall_recall = sum(
            per_class_metrics[f"{cls}_recall"] for cls in all_classes
        ) / len(all_classes)
        overall_f1 = sum(per_class_metrics[f"{cls}_f1"] for cls in all_classes) / len(
            all_classes
        )
    else:
        overall_precision = overall_recall = overall_f1 = 0.0

    return ClassificationScores(
        overall_precision=overall_precision,
        overall_recall=overall_recall,
        overall_f1=overall_f1,
        **per_class_metrics,
    )


def confusion_matrix_scorer(
    output: DiscrepancyDetectionOutput, expected: ExpectedOutput
) -> ConfusionMatrixScores:
    """Generate confusion matrix for deviation classification.

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        ConfusionMatrixScores with confusion matrix and class counts
    """
    # Extract deviation classes
    predicted_classes = [d.deviation_class for d in output.deviations]
    ground_truth_classes = [d.deviation_class for d in expected.deviations]

    # Build confusion matrix
    all_classes = sorted(set(predicted_classes + ground_truth_classes))
    confusion_matrix = defaultdict(lambda: defaultdict(int))

    # For each ground truth class, count predictions
    for gt_cls in ground_truth_classes:
        # Find if this was predicted (simple matching by class name)
        if gt_cls in predicted_classes:
            confusion_matrix[gt_cls][gt_cls] += 1
            # Remove from predicted to avoid double counting
            predicted_classes.remove(gt_cls)
        else:
            # Missed this ground truth (false negative)
            confusion_matrix[gt_cls]["<missed>"] += 1

    # Remaining predictions are false positives
    for pred_cls in predicted_classes:
        confusion_matrix["<none>"][pred_cls] += 1

    return ConfusionMatrixScores(
        confusion_matrix=dict(confusion_matrix),
        all_classes=all_classes,
        total_ground_truth=len(ground_truth_classes),
        total_predicted=len(output.deviations),
    )


def false_positive_scorer(
    output: DiscrepancyDetectionOutput, expected: ExpectedOutput
) -> FalsePositiveScores:
    """Count false positive deviations (hallucinations).

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        FalsePositiveScores with count and rate
    """
    predicted_classes = [d.deviation_class for d in output.deviations]
    ground_truth_classes = [d.deviation_class for d in expected.deviations]

    # False positives: predicted classes not in ground truth
    false_positives = [c for c in predicted_classes if c not in ground_truth_classes]

    fp_count = len(false_positives)
    total_predicted = len(output.deviations)

    fp_rate = fp_count / total_predicted if total_predicted > 0 else 0.0

    return FalsePositiveScores(
        false_positive_count=fp_count,
        false_positive_rate=fp_rate,
        false_positive_classes=false_positives,
    )


def false_negative_scorer(
    output: DiscrepancyDetectionOutput, expected: ExpectedOutput
) -> FalseNegativeScores:
    """Count false negative deviations (missed detections).

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        FalseNegativeScores with count and rate
    """
    predicted_classes = [d.deviation_class for d in output.deviations]
    ground_truth_classes = [d.deviation_class for d in expected.deviations]

    # False negatives: ground truth classes not in predicted
    false_negatives = [c for c in ground_truth_classes if c not in predicted_classes]

    fn_count = len(false_negatives)
    total_ground_truth = len(expected.deviations)

    fn_rate = fn_count / total_ground_truth if total_ground_truth > 0 else 0.0

    return FalseNegativeScores(
        false_negative_count=fn_count,
        false_negative_rate=fn_rate,
        false_negative_classes=false_negatives,
    )


def occurrence_accuracy_scorer(
    output: DiscrepancyDetectionOutput, expected: ExpectedOutput, tolerance_seconds: int = 30
) -> OccurrenceScores:
    """Score timestamp accuracy for deviation occurrences.

    Checks if predicted timestamps are within tolerance of ground truth timestamps.

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations
        tolerance_seconds: Tolerance for timestamp matching (default: 30s)

    Returns:
        OccurrenceScores with accuracy metrics
    """

    total_occurrences_gt = 0
    matched_occurrences = 0
    timestamp_errors = []

    def parse_timestamp(ts_str: str) -> int:
        """Parse HH:MM:SS or MM:SS timestamp to seconds."""
        parts = ts_str.split(":")
        if len(parts) == 3:
            # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return 0

    # Match deviations by class
    for gt_dev in expected.deviations:
        gt_class = gt_dev.deviation_class
        gt_occurrences = gt_dev.occurrences or []

        # Find matching predicted deviation
        pred_dev = next(
            (d for d in output.deviations if d.deviation_class == gt_class), None
        )

        if pred_dev and gt_occurrences:
            pred_occurrences = pred_dev.occurrences or []
            total_occurrences_gt += len(gt_occurrences)

            # Check each ground truth occurrence
            for gt_occ in gt_occurrences:
                gt_ts = parse_timestamp(gt_occ.timestamp)

                # Find closest predicted occurrence
                closest_match = None
                min_diff = float("inf")

                for pred_occ in pred_occurrences:
                    pred_ts = parse_timestamp(pred_occ.timestamp)
                    diff = abs(gt_ts - pred_ts)

                    if diff < min_diff:
                        min_diff = diff
                        closest_match = pred_occ

                # Check if within tolerance
                if closest_match and min_diff <= tolerance_seconds:
                    matched_occurrences += 1
                else:
                    timestamp_errors.append(
                        TimestampError(
                            deviation_class=gt_class,
                            expected=gt_occ.timestamp,
                            closest_predicted=(
                                closest_match.timestamp if closest_match else None
                            ),
                            error_seconds=min_diff if closest_match else None,
                        )
                    )

    accuracy = (
        matched_occurrences / total_occurrences_gt if total_occurrences_gt > 0 else 0.0
    )

    return OccurrenceScores(
        occurrence_accuracy=accuracy,
        matched_occurrences=matched_occurrences,
        total_occurrences=total_occurrences_gt,
        timestamp_errors=timestamp_errors,
    )


def detection_binary_scorer(
    output: DiscrepancyDetectionOutput, expected: ExpectedOutput
) -> DetectionScores:
    """Binary detection scorer: did we detect any deviations when we should have?

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        DetectionScores with binary detection accuracy
    """
    has_deviations_predicted = len(output.deviations) > 0
    has_deviations_ground_truth = len(expected.deviations) > 0

    # Binary accuracy: did we get it right?
    correct = has_deviations_predicted == has_deviations_ground_truth

    return DetectionScores(
        binary_detection_accuracy=1.0 if correct else 0.0,
        predicted_has_deviations=has_deviations_predicted,
        ground_truth_has_deviations=has_deviations_ground_truth,
    )
