"""Pydantic schemas for evaluation results and metrics."""

from pydantic import BaseModel, Field

from src.utils.braintrust_tracing import JSONAttachment


# Workflow models (shared between workflow and evals)
class DeviationOccurrence(BaseModel):
    """Timestamp and context for a deviation occurrence."""

    rilla_conversation_index: int = Field(
        description="Zero-based index into the list of Rilla conversations (0 for first conversation, 1 for second, etc.)"
    )
    timestamp: str = Field(
        description="Timestamp in HH:MM:SS or MM:SS format when this deviation was mentioned in the conversation",
        pattern=r"^(([01]?[0-9]|2[0-3]):)?([0-5][0-9]):([0-5][0-9])$",
    )


class PredictedLineItem(BaseModel):
    """Predicted estimate line item for a deviation."""

    description: str = Field(
        description="Description of the line item (e.g., 'Ridge Vent', 'Attic Fan')"
    )
    quantity: float | None = Field(
        default=None, description="Predicted quantity for the line item"
    )
    unit: str | None = Field(
        default=None, description="Unit of measurement (e.g., 'LF', 'EA', 'SQ', '%')"
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes or context for the line item prediction",
    )

    # Pricebook matching fields
    matched_pricebook_item_id: int | None = Field(
        default=None,
        description="ID of the matched pricebook item from the vector store (if found)",
    )
    matched_pricebook_item_code: str | None = Field(
        default=None,
        description="Item code of the matched pricebook item (e.g., 'MAT-001')",
    )
    matched_pricebook_item_display_name: str | None = Field(
        default=None,
        description="Display name of the matched pricebook item",
    )
    unit_cost: float | None = Field(
        default=None,
        description="Unit cost from the matched pricebook item's primaryVendor",
    )
    total_cost: float | None = Field(
        default=None,
        description="Total cost calculated as unit_cost × quantity",
    )


class Deviation(BaseModel):
    """A single deviation found between conversation and documentation."""

    deviation_class: str = Field(
        description="The label of the deviation class from the classes list"
    )
    explanation: str = Field(
        description="A brief explanation of what specific deviation was found"
    )
    occurrences: list[DeviationOccurrence] | None = Field(
        default=None,
        description="List of specific timestamps where this deviation was mentioned in the conversation(s). Not required for deviations where the item was not discussed.",
    )
    predicted_line_item: PredictedLineItem | None = Field(
        default=None,
        description="Optional predicted estimate line item for deviations that include line item prediction",
    )


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


# Braintrust tracing schemas
class BraintrustSpanInput(BaseModel):
    """Input structure for Braintrust span logging.

    Contains only the actual JSON data files being processed.
    Uses Braintrust JSONAttachment objects to upload JSON content to Braintrust storage
    for viewing/downloading in the Braintrust UI.
    """

    estimate: JSONAttachment | None = None
    form: JSONAttachment | None = None
    rilla_transcripts: list[JSONAttachment] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class BraintrustSpanMetadata(BaseModel):
    """Metadata structure for Braintrust span logging.

    Contains identifying information and context about the data.
    """

    uuid: str
    project_id: str
    job_id: str
    estimate_id: str
    prelabel: bool
    rilla_links: list[str] = Field(default_factory=list)
    project_created_date: str | None = None
    estimate_sold_date: str | None = None

