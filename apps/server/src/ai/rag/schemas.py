"""Pydantic schemas for RAG API endpoints."""

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


class VectorStoreStatusResponse(BaseModel):
    """Response containing vector store status."""

    vector_store_id: str
    file_count: int
    total_size_bytes: int
    total_size_mb: float
    jurisdictions_count: int
    cities_count: int
    states_count: int
    last_synced: str | None
    is_ready: bool


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
