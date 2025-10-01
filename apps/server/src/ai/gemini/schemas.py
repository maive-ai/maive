"""Pydantic schemas for Gemini integration requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class FileUploadRequest(BaseModel):
    """Request model for file upload to Gemini Files API."""

    file_path: str = Field(description="Local path to the file to upload")
    display_name: Optional[str] = Field(
        default=None, description="Optional display name for the file"
    )
    mime_type: Optional[str] = Field(
        default=None, description="MIME type of the file (auto-detected if not provided)"
    )


class FileMetadata(BaseModel):
    """Metadata for an uploaded file."""

    name: str = Field(description="Unique name/ID of the file")
    display_name: Optional[str] = Field(description="Display name of the file")
    mime_type: str = Field(description="MIME type of the file")
    size_bytes: int = Field(description="Size of the file in bytes")
    create_time: datetime = Field(description="When the file was created")
    update_time: datetime = Field(description="When the file was last updated")
    expiration_time: datetime = Field(description="When the file will be deleted")
    sha256_hash: str = Field(description="SHA256 hash of the file")
    uri: str = Field(description="URI of the uploaded file")


class GenerateContentRequest(BaseModel):
    """Request model for generating content with Gemini."""

    prompt: str = Field(description="Text prompt for content generation")
    files: Optional[List[str]] = Field(
        default=None, description="List of uploaded file names to include"
    )
    temperature: Optional[float] = Field(
        default=None, description="Temperature override for this request"
    )
    model_name: Optional[str] = Field(
        default=None, description="Model name override for this request"
    )
    thinking_budget: Optional[int] = Field(
        default=None, description="Thinking budget override for this request"
    )
    response_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON schema for structured output"
    )


class GenerateStructuredContentRequest(BaseModel):
    """Request model for generating structured content with Gemini."""

    prompt: str = Field(description="Text prompt for content generation")
    response_model: type[BaseModel] = Field(
        description="Pydantic model class for structured output"
    )
    files: Optional[List[str]] = Field(
        default=None, description="List of uploaded file names to include"
    )
    temperature: Optional[float] = Field(
        default=None, description="Temperature override for this request"
    )
    model_name: Optional[str] = Field(
        default=None, description="Model name override for this request"
    )
    thinking_budget: Optional[int] = Field(
        default=None, description="Thinking budget override for this request"
    )


class GenerateContentResponse(BaseModel):
    """Response model for content generation."""

    text: str = Field(description="Generated text content")
    usage: Optional[Dict[str, Any]] = Field(
        default=None, description="Usage statistics"
    )
    finish_reason: Optional[str] = Field(
        default=None, description="Reason why generation finished"
    )


class ListFilesResponse(BaseModel):
    """Response model for listing uploaded files."""

    files: List[FileMetadata] = Field(description="List of uploaded files")
    next_page_token: Optional[str] = Field(
        default=None, description="Token for pagination"
    )


class DeleteFileResponse(BaseModel):
    """Response model for file deletion."""

    success: bool = Field(description="Whether the deletion was successful")
    message: Optional[str] = Field(
        default=None, description="Additional message about the deletion"
    )