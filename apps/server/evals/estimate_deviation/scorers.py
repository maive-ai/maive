"""Evaluation scorers for discrepancy detection workflow.

These scorers compare predicted deviations against ground truth labels
to measure classification accuracy, precision, recall, and other metrics.
"""

from collections import defaultdict

from pydantic import BaseModel, Field

from evals.estimate_deviation.schemas import Deviation


class ClassificationScores(BaseModel):
    """Classification accuracy metrics."""

    overall_precision: float
    overall_recall: float
    overall_f1: float
    # Per-class metrics stored as extra fields
    model_config = {"extra": "allow"}


class ConfusionMatrixScores(BaseModel):
    """Confusion matrix for classification."""

    confusion_matrix: dict[str, dict[str, int]]
    all_classes: list[str]
    total_ground_truth: int
    total_predicted: int


class FalsePositiveScores(BaseModel):
    """False positive analysis."""

    false_positive_count: int
    false_positive_rate: float
    false_positive_classes: list[str]


class FalseNegativeScores(BaseModel):
    """False negative analysis."""

    false_negative_count: int
    false_negative_rate: float
    false_negative_classes: list[str]


class TimestampError(BaseModel):
    """Timestamp mismatch details."""

    deviation_class: str = Field(alias="class")
    expected: str
    closest_predicted: str | None
    error_seconds: float | None

    model_config = {"populate_by_name": True}


class OccurrenceScores(BaseModel):
    """Occurrence timestamp accuracy metrics."""

    occurrence_accuracy: float
    matched_occurrences: int
    total_occurrences: int
    timestamp_errors: list[TimestampError]


class DetectionScores(BaseModel):
    """Binary detection metrics."""

    binary_detection_accuracy: float
    predicted_has_deviations: bool
    ground_truth_has_deviations: bool


def classification_accuracy_scorer(
    output: list[Deviation], expected: list[Deviation]
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
    predicted_classes = [d.deviation_class for d in output]
    ground_truth_classes = [d.deviation_class for d in expected]

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
    output: list[Deviation], expected: list[Deviation]
) -> ConfusionMatrixScores:
    """Generate confusion matrix for deviation classification.

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        ConfusionMatrixScores with confusion matrix and class counts
    """
    # Extract deviation classes
    predicted_classes = [d.deviation_class for d in output]
    ground_truth_classes = [d.deviation_class for d in expected]

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
        total_predicted=len(output),
    )


def false_positive_scorer(
    output: list[Deviation], expected: list[Deviation]
) -> FalsePositiveScores:
    """Count false positive deviations (hallucinations).

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        FalsePositiveScores with count and rate
    """
    predicted_classes = [d.deviation_class for d in output]
    ground_truth_classes = [d.deviation_class for d in expected]

    # False positives: predicted classes not in ground truth
    false_positives = [c for c in predicted_classes if c not in ground_truth_classes]

    fp_count = len(false_positives)
    total_predicted = len(output)

    fp_rate = fp_count / total_predicted if total_predicted > 0 else 0.0

    return FalsePositiveScores(
        false_positive_count=fp_count,
        false_positive_rate=fp_rate,
        false_positive_classes=false_positives,
    )


def false_negative_scorer(
    output: list[Deviation], expected: list[Deviation]
) -> FalseNegativeScores:
    """Count false negative deviations (missed detections).

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        FalseNegativeScores with count and rate
    """
    predicted_classes = [d.deviation_class for d in output]
    ground_truth_classes = [d.deviation_class for d in expected]

    # False negatives: ground truth classes not in predicted
    false_negatives = [c for c in ground_truth_classes if c not in predicted_classes]

    fn_count = len(false_negatives)
    total_ground_truth = len(expected)

    fn_rate = fn_count / total_ground_truth if total_ground_truth > 0 else 0.0

    return FalseNegativeScores(
        false_negative_count=fn_count,
        false_negative_rate=fn_rate,
        false_negative_classes=false_negatives,
    )


def occurrence_accuracy_scorer(
    output: list[Deviation], expected: list[Deviation], tolerance_seconds: int = 30
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
    for gt_dev in expected:
        gt_class = gt_dev.deviation_class
        gt_occurrences = gt_dev.occurrences or []

        # Find matching predicted deviation
        pred_dev = next(
            (d for d in output if d.deviation_class == gt_class), None
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
    output: list[Deviation], expected: list[Deviation]
) -> DetectionScores:
    """Binary detection scorer: did we detect any deviations when we should have?

    Args:
        output: Workflow output with deviations
        expected: Ground truth with deviations

    Returns:
        DetectionScores with binary detection accuracy
    """
    has_deviations_predicted = len(output) > 0
    has_deviations_ground_truth = len(expected) > 0

    # Binary accuracy: did we get it right?
    correct = has_deviations_predicted == has_deviations_ground_truth

    return DetectionScores(
        binary_detection_accuracy=1.0 if correct else 0.0,
        predicted_has_deviations=has_deviations_predicted,
        ground_truth_has_deviations=has_deviations_ground_truth,
    )


# Braintrust-compatible scorer wrappers
# These adapt our Pydantic-based scorers to Braintrust's dict-based format


def classification_accuracy_scorer_bt(input, output, expected=None, **kwargs):
    """Braintrust-compatible wrapper for classification accuracy scorer.

    Args:
        input: Input dict with JSONAttachment objects
        output: Output dict with deviations list
        expected: Expected output dict with deviations list
        **kwargs: Additional metadata

    Returns:
        Dict with name, score, and metadata (Braintrust format) or None to skip
    """
    if not expected or "deviations" not in expected:
        return None

    try:
        # Debug: log what we received
        from src.utils.logger import logger as debug_logger

        debug_logger.info(
            f"Scorer received output deviations: {len(output.get('deviations', []))}"
        )
        debug_logger.info(
            f"Scorer received expected deviations: {len(expected.get('deviations', []))}"
        )
        if output.get("deviations"):
            debug_logger.info(
                f"First output deviation keys: {output['deviations'][0].keys() if output['deviations'] else 'empty'}"
            )
        if expected.get("deviations"):
            debug_logger.info(
                f"First expected deviation keys: {expected['deviations'][0].keys() if expected['deviations'] else 'empty'}"
            )

        # Convert deviation dicts to Pydantic Deviation objects
        output_deviations = [Deviation(**d) for d in output["deviations"]]
        expected_deviations = [Deviation(**d) for d in expected["deviations"]]

        # Run scorer logic with lists of Deviation objects
        scores = classification_accuracy_scorer(output_deviations, expected_deviations)

        # Return Braintrust format
        return {
            "name": "classification_f1",
            "score": scores.overall_f1,
            "metadata": {
                "precision": scores.overall_precision,
                "recall": scores.overall_recall,
                **{
                    k: v
                    for k, v in scores.model_dump().items()
                    if k not in ["overall_f1", "overall_precision", "overall_recall"]
                },
            },
        }
    except Exception as e:
        import traceback

        return {
            "name": "classification_f1",
            "score": 0.0,
            "metadata": {"error": str(e), "traceback": traceback.format_exc()},
        }


def false_positive_scorer_bt(input, output, expected=None, **kwargs):
    """Braintrust-compatible wrapper for false positive scorer."""
    if not expected or "deviations" not in expected:
        return None

    try:
        output_deviations = [Deviation(**d) for d in output["deviations"]]
        expected_deviations = [Deviation(**d) for d in expected["deviations"]]

        scores = false_positive_scorer(output_deviations, expected_deviations)

        # Score is inverted - fewer false positives = better score
        fp_rate = scores.false_positive_rate
        score = 1.0 - fp_rate if fp_rate <= 1.0 else 0.0

        return {
            "name": "false_positive_rate",
            "score": score,
            "metadata": {
                "false_positive_count": scores.false_positive_count,
                "false_positive_rate": scores.false_positive_rate,
                "false_positive_classes": scores.false_positive_classes,
            },
        }
    except Exception as e:
        return {
            "name": "false_positive_rate",
            "score": 0.0,
            "metadata": {"error": str(e)},
        }


def false_negative_scorer_bt(input, output, expected=None, **kwargs):
    """Braintrust-compatible wrapper for false negative scorer."""
    if not expected or "deviations" not in expected:
        return None

    try:
        output_deviations = [Deviation(**d) for d in output["deviations"]]
        expected_deviations = [Deviation(**d) for d in expected["deviations"]]

        scores = false_negative_scorer(output_deviations, expected_deviations)

        # Score is inverted - fewer false negatives = better score
        fn_rate = scores.false_negative_rate
        score = 1.0 - fn_rate if fn_rate <= 1.0 else 0.0

        return {
            "name": "false_negative_rate",
            "score": score,
            "metadata": {
                "false_negative_count": scores.false_negative_count,
                "false_negative_rate": scores.false_negative_rate,
                "false_negative_classes": scores.false_negative_classes,
            },
        }
    except Exception as e:
        return {
            "name": "false_negative_rate",
            "score": 0.0,
            "metadata": {"error": str(e)},
        }


def occurrence_accuracy_scorer_bt(input, output, expected=None, **kwargs):
    """Braintrust-compatible wrapper for occurrence accuracy scorer."""
    if not expected or "deviations" not in expected:
        return None

    try:
        output_deviations = [Deviation(**d) for d in output["deviations"]]
        expected_deviations = [Deviation(**d) for d in expected["deviations"]]

        scores = occurrence_accuracy_scorer(output_deviations, expected_deviations)

        return {
            "name": "occurrence_accuracy",
            "score": scores.occurrence_accuracy,
            "metadata": {
                "matched_occurrences": scores.matched_occurrences,
                "total_occurrences": scores.total_occurrences,
                "timestamp_errors": [e.model_dump() for e in scores.timestamp_errors],
            },
        }
    except Exception as e:
        return {
            "name": "occurrence_accuracy",
            "score": 0.0,
            "metadata": {"error": str(e)},
        }


def detection_binary_scorer_bt(input, output, expected=None, **kwargs):
    """Braintrust-compatible wrapper for binary detection scorer."""
    if not expected or "deviations" not in expected:
        return None

    try:
        output_deviations = [Deviation(**d) for d in output["deviations"]]
        expected_deviations = [Deviation(**d) for d in expected["deviations"]]

        scores = detection_binary_scorer(output_deviations, expected_deviations)

        return {
            "name": "binary_detection_accuracy",
            "score": scores.binary_detection_accuracy,
            "metadata": {
                "predicted_has_deviations": scores.predicted_has_deviations,
                "ground_truth_has_deviations": scores.ground_truth_has_deviations,
            },
        }
    except Exception as e:
        return {
            "name": "binary_detection_accuracy",
            "score": 0.0,
            "metadata": {"error": str(e)},
        }
