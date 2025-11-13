"""Pydantic schemas for evaluation results and metrics."""

from pydantic import BaseModel, Field


class PredictedLineItem(BaseModel):
    """Predicted estimate line item for a deviation."""

    quantity: float | None = Field(
        default=None, description="Predicted quantity for the line item"
    )
    # Pricebook matching fields
    matched_pricebook_item_id: int | None = Field(
        default=None,
        description="ID of the pricebook item from the vector store (if found)",
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
        description="Total cost calculated as unit_cost × quantity, or amount saved if a line item is a discount",
    )


# Workflow models (shared between workflow and evals)
class DeviationOccurrence(BaseModel):
    """Timestamp and context for a deviation occurrence."""

    conversation_idx: int = Field(
        description="Zero-based index into the list of Rilla conversations (0 for first conversation, 1 for second, etc.)"
    )
    timestamp: str = Field(
        description="Timestamp in HH:MM:SS or MM:SS format when this deviation was mentioned in the conversation",
        pattern=r"^(?:[0-9]{1,2}:)?[0-5][0-9]:[0-5][0-9]$",
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
