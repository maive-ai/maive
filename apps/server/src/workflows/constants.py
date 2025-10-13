from enum import Enum


class ClaimStatus(str, Enum):
    """Claim status values."""

    NONE = "None"
    PROCESSING = "Processing"
    APPROVED = "Approved"
    PARTIALLY_APPROVED = "Partially Approved"
    PENDING_REVIEW = "Pending Review"
    DENIED = "Denied"
