"""Pydantic schemas for RAG API endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IngestApifyRequest(BaseModel):
    """Request to ingest documents from Apify results."""

    apify_results: list[dict[str, Any]] = Field(
        ...,
        description="List of scraped results from Apify",
        examples=[
            [
                {
                    "url": "https://example.com/building-codes",
                    "title": "City of Leawood Building Codes",
                    "content": "<html>...</html>",
                    "metadata": {"notes": "Roofing codes section"},
                }
            ]
        ],
    )


class IngestApifyResponse(BaseModel):
    """Response from ingesting Apify documents."""

    total_documents: int
    successful: int
    failed: int
    errors: list[dict[str, Any]]
    file_ids: list[str]
    vector_store_id: str


class VectorStoreStatus(BaseModel):
    """Status of the building codes vector store."""

    vector_store_id: str
    file_count: int
    total_size_bytes: int
    jurisdictions_count: int
    cities_count: int
    states_count: int
    last_synced: datetime | None = None
    is_ready: bool = True


class UploadDocumentRequest(BaseModel):
    """Request to upload a single document manually."""

    content: str = Field(..., description="Document text content")
    jurisdiction_name: str = Field(..., description="Name of jurisdiction")
    jurisdiction_level: str = Field(
        ..., description="Level: international, national, state, county, city, unknown"
    )
    city: str | None = None
    county: str | None = None
    state: str | None = None
    code_type: str = Field(default="general", description="Type of code")
    document_title: str | None = None
    source_url: str | None = None
    version: str | None = None


class UploadDocumentResponse(BaseModel):
    """Response from uploading a document."""

    file_id: str
    filename: str
    vector_store_id: str


class JurisdictionLevel(str, Enum):
    """Level of jurisdiction for building codes."""

    INTERNATIONAL = "international"
    NATIONAL = "national"
    STATE = "state"
    COUNTY = "county"
    CITY = "city"
    UNKNOWN = "unknown"


class CodeType(str, Enum):
    """Type of building code."""

    ROOFING = "roofing"
    STRUCTURAL = "structural"
    FIRE = "fire"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    MECHANICAL = "mechanical"
    GENERAL = "general"
    OTHER = "other"


class CodeDocumentMetadata(BaseModel):
    """Metadata for a building code document.

    This captures what we know from scraping - we don't make assumptions
    about relationships between international/state/city codes until we
    analyze the content.
    """

    # Basic identification
    jurisdiction_name: str = Field(
        ..., description="Name of jurisdiction (e.g., 'Leawood', 'Kansas', 'IBC')"
    )
    jurisdiction_level: JurisdictionLevel = Field(
        ..., description="Level of jurisdiction"
    )

    # Geographic context (when applicable)
    city: str | None = Field(None, description="City name if city-level code")
    county: str | None = Field(None, description="County name if applicable")
    state: str | None = Field(None, description="State name or abbreviation")
    country: str = Field(default="USA", description="Country code")

    # Code classification
    code_type: CodeType = Field(
        default=CodeType.GENERAL, description="Type of building code"
    )
    code_section: str | None = Field(
        None,
        description="Specific section or chapter (e.g., 'Chapter 15', 'Section 1507')",
    )
    document_title: str | None = Field(None, description="Title of the code document")

    # Source information
    source_url: str | None = Field(None, description="Original URL of the code")
    scrape_date: datetime = Field(
        default_factory=datetime.utcnow, description="When this was scraped"
    )

    # Version/date information (from document if available)
    effective_date: datetime | None = Field(
        None, description="Date the code became effective (if stated in document)"
    )
    version: str | None = Field(
        None, description="Version or year (e.g., '2021 IBC', 'v3.2')"
    )

    # Relationships (to be populated later via analysis)
    adopts_code: str | None = Field(
        None, description="Name of code this jurisdiction adopts (e.g., 'IBC 2021')"
    )
    has_amendments: bool | None = Field(
        None, description="Whether this jurisdiction has amendments to adopted code"
    )

    # Additional context
    notes: str | None = Field(None, description="Any additional notes or context")

    def to_openai_metadata(self) -> dict[str, str]:
        """Convert to OpenAI file metadata format.

        OpenAI file metadata values must be strings and there's a limit
        on number of keys, so we include only the most useful fields.

        Returns:
            dict[str, str]: Metadata dictionary for OpenAI
        """
        metadata = {
            "jurisdiction_name": self.jurisdiction_name,
            "jurisdiction_level": self.jurisdiction_level.value,
            "code_type": self.code_type.value,
            "country": self.country,
        }

        if self.city:
            metadata["city"] = self.city

        if self.state:
            metadata["state"] = self.state

        if self.county:
            metadata["county"] = self.county

        if self.code_section:
            metadata["code_section"] = self.code_section

        if self.source_url:
            metadata["source_url"] = self.source_url

        if self.version:
            metadata["version"] = self.version

        if self.document_title:
            metadata["document_title"] = self.document_title

        if self.adopts_code:
            metadata["adopts_code"] = self.adopts_code

        metadata["scrape_date"] = self.scrape_date.isoformat()

        return metadata
