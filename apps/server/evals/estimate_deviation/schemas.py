"""Pydantic schemas for evaluation results and metrics."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.workflows.discrepancy_detection_v2 import Deviation


# Ground truth label schemas
class GroundTruthLabel(BaseModel):
    """Ground truth labels for a dataset entry.

    Uses the same Deviation model as workflow output to ensure structural
    compatibility during evaluation. This allows direct comparison between
    predicted and ground truth deviations.
    """

    deviations: list[Deviation] = Field(
        description="List of verified deviations (ground truth)"
    )
    notes: str | None = Field(
        default=None,
        description="Optional notes from the labeler about edge cases or ambiguities",
    )
    verified_by: str | None = Field(
        default=None, description="Who verified these labels"
    )
    verified_at: str | None = Field(
        default=None, description="ISO timestamp when labels were verified"
    )


class DatasetEntry(BaseModel):
    """Dataset entry with optional ground truth labels."""

    uuid: str
    project_created_date: str
    estimate_sold_date: str
    project_id: str
    job_id: str
    estimate_id: str
    estimate_s3_uri: str
    form_s3_uri: str
    rilla_links: list[str]
    rilla_recordings_s3_uri: list[str]
    rilla_transcripts_s3_uri: list[str]
    labels: GroundTruthLabel | None = None


# Workflow output schemas
class CostSavings(BaseModel):
    """Cost savings summary."""

    total: float
    matched_items: int
    unmatched_items: int


class DiscrepancyDetectionOutput(BaseModel):
    """Structured output from discrepancy detection workflow."""

    status: str
    uuid: str
    project_id: str
    job_id: str
    estimate_id: str
    summary: str
    deviations: list[Deviation]
    cost_savings: CostSavings
    rilla_links: list[str]
    timestamp: str


class ExpectedOutput(BaseModel):
    """Expected output (ground truth) for evaluation."""

    deviations: list[Deviation]


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


class AllScores(BaseModel):
    """All scorer outputs combined."""

    classification: ClassificationScores
    confusion_matrix: ConfusionMatrixScores
    false_positives: FalsePositiveScores
    false_negatives: FalseNegativeScores
    occurrences: OccurrenceScores
    detection: DetectionScores


class EvalResult(BaseModel):
    """Single evaluation result with prediction, expected, and scores."""

    uuid: str
    prediction: DiscrepancyDetectionOutput
    expected: ExpectedOutput
    scores: AllScores
    error: str | None = None


class AggregateMetrics(BaseModel):
    """Aggregated metrics across all evaluations."""

    avg_f1: float
    avg_precision: float
    avg_recall: float
    total_false_positives: int
    total_false_negatives: int
    avg_occurrence_accuracy: float
    total_evaluated: int
    total_errors: int


class EvalSummary(BaseModel):
    """Complete evaluation summary."""

    results: list[EvalResult]
    aggregate_metrics: AggregateMetrics
    total_entries: int


# Dataset helper functions
def load_dataset(dataset_path: str) -> list[DatasetEntry]:
    """Load dataset from JSON file.

    Args:
        dataset_path: Path to dataset.json file

    Returns:
        List of dataset entries

    Raises:
        FileNotFoundError: If dataset file doesn't exist
        ValueError: If dataset JSON is invalid
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(path, "r") as f:
        data = json.load(f)

    return [DatasetEntry(**entry) for entry in data]


def save_dataset(dataset: list[DatasetEntry], dataset_path: str) -> None:
    """Save dataset to JSON file.

    Args:
        dataset: List of dataset entries
        dataset_path: Path to dataset.json file
    """
    path = Path(dataset_path)

    # Convert to dict and write
    data = [entry.model_dump(mode="json", exclude_none=False) for entry in dataset]

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_labeled_entries(dataset_path: str) -> list[DatasetEntry]:
    """Get only dataset entries that have ground truth labels.

    Args:
        dataset_path: Path to dataset.json file

    Returns:
        List of labeled dataset entries
    """
    dataset = load_dataset(dataset_path)
    return [entry for entry in dataset if entry.labels is not None]


def add_labels_to_entry(
    dataset_path: str,
    uuid: str,
    deviations: list[Deviation],
    notes: str | None = None,
    verified_by: str | None = None,
) -> None:
    """Add ground truth labels to a dataset entry.

    Args:
        dataset_path: Path to dataset.json file
        uuid: UUID of the entry to label
        deviations: List of verified deviations
        notes: Optional notes about the labels
        verified_by: Who verified these labels

    Raises:
        ValueError: If UUID not found in dataset
    """
    dataset = load_dataset(dataset_path)

    # Find the entry
    entry = None
    for e in dataset:
        if e.uuid == uuid:
            entry = e
            break

    if entry is None:
        raise ValueError(f"UUID {uuid} not found in dataset")

    # Add labels
    entry.labels = GroundTruthLabel(
        deviations=deviations,
        notes=notes,
        verified_by=verified_by,
        verified_at=datetime.now(UTC).isoformat(),
    )

    # Save updated dataset
    save_dataset(dataset, dataset_path)


def validate_labels(dataset_path: str) -> dict[str, Any]:
    """Validate all labels in the dataset.

    Checks that all labeled entries have valid schema and returns statistics.

    Args:
        dataset_path: Path to dataset.json file

    Returns:
        Dict with validation results and statistics
    """
    dataset = load_dataset(dataset_path)
    labeled_entries = [e for e in dataset if e.labels is not None]

    stats = {
        "total_entries": len(dataset),
        "labeled_entries": len(labeled_entries),
        "unlabeled_entries": len(dataset) - len(labeled_entries),
        "total_deviations": sum(
            len(e.labels.deviations) for e in labeled_entries if e.labels
        ),
        "deviation_class_counts": {},
        "entries_with_occurrences": 0,
        "entries_with_predicted_line_items": 0,
    }

    # Count deviation classes
    for entry in labeled_entries:
        if entry.labels:
            for deviation in entry.labels.deviations:
                cls = deviation.deviation_class
                stats["deviation_class_counts"][cls] = (
                    stats["deviation_class_counts"].get(cls, 0) + 1
                )

                if deviation.occurrences:
                    stats["entries_with_occurrences"] += 1

                if deviation.predicted_line_item:
                    stats["entries_with_predicted_line_items"] += 1

    return stats
