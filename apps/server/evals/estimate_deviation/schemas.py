"""Pydantic schemas for evaluation results and metrics."""

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
    cost_savings: CostSavings | None = Field(
        default=None,
        description="Optional cost savings for validation (from prelabel or manual entry)",
    )


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


