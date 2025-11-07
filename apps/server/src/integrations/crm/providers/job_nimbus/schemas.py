"""
JobNimbus-specific Pydantic schemas for API requests and responses.

This module contains all Pydantic models specific to JobNimbus CRM operations.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Base models for common JobNimbus structures


class GeoLocation(BaseModel):
    """Geographic location model."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class LocationInfo(BaseModel):
    """Location information model."""

    id: int = Field(..., description="Location ID")
    parent_id: int | None = Field(None, description="Parent location ID", alias="parentId")
    name: str | None = Field(None, description="Location name")


class OwnerInfo(BaseModel):
    """Owner information model."""

    id: str = Field(..., description="Owner JNID")


class RelatedEntity(BaseModel):
    """Related entity reference model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(..., description="Entity JNID")
    type: str | None = Field(None, description="Entity type (job, contact, etc)")
    name: str | None = Field(None, description="Entity name")
    number: str | None = Field(None, description="Entity number")
    email: str | None = Field(None, description="Email address if contact")
    subject: str | None = Field(None, description="Subject if email/message")
    new_status: int | None = Field(None, description="New status ID if status change", alias="newStatus")
    old_status: int | None = Field(None, description="Old status ID if status change", alias="oldStatus")


# Job schemas


class JobNimbusJobResponse(BaseModel):
    """Response model for a JobNimbus job."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    recid: int | None = Field(None, description="Record ID")
    jnid: str = Field(..., description="JobNimbus unique ID")
    customer: str = Field(..., description="Customer JNID")
    type: str = Field(..., description="Record type (should be 'job')")
    created_by: str = Field(..., description="Creator JNID", alias="createdBy")
    created_by_name: str = Field(..., description="Creator name", alias="createdByName")
    date_created: int = Field(..., description="Unix timestamp of creation", alias="dateCreated")
    date_updated: int = Field(..., description="Unix timestamp of last update", alias="dateUpdated")
    location: LocationInfo | None = Field(None, description="Location information")
    owners: list[OwnerInfo] = Field(default_factory=list, description="List of owners")
    is_active: bool = Field(..., description="Whether the job is active", alias="isActive")
    is_archived: bool | None = Field(None, description="Whether the job is archived", alias="isArchived")

    # Job-specific fields
    name: str = Field(..., description="Job name")
    number: str | None = Field(None, description="Job number")
    record_type: int = Field(..., description="Record type ID", alias="recordType")
    record_type_name: str = Field(..., description="Workflow name", alias="recordTypeName")
    status: int | None = Field(None, description="Status ID")
    status_name: str | None = Field(None, description="Status name", alias="statusName")
    description: str | None = Field(None, description="Job description")

    # Sales and contact info
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(None, description="Sales rep name", alias="salesRepName")
    source: int | None = Field(None, description="Lead source ID")
    source_name: str | None = Field(None, description="Lead source name", alias="sourceName")

    # Address fields
    address_line1: str | None = Field(None, description="Address line 1", alias="addressLine1")
    address_line2: str | None = Field(None, description="Address line 2", alias="addressLine2")
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    country_name: str | None = Field(None, description="Country", alias="countryName")
    zip: str | None = Field(None, description="ZIP code")
    geo: GeoLocation | None = Field(None, description="Geographic coordinates")

    # Related entities
    related: list[RelatedEntity] | None = Field(None, description="Related entities")
    primary: RelatedEntity | None = Field(None, description="Primary related entity")

    # Custom fields (captured via extra="allow")
    # Examples: "Claim Number", "Date of Loss", "cf_string_1", "cf_date_1", etc.


class JobNimbusJobsListResponse(BaseModel):
    """Response model for list of jobs."""

    count: int = Field(..., description="Total count of jobs")
    results: list[JobNimbusJobResponse] = Field(..., description="List of jobs")


class JobNimbusCreateJobRequest(BaseModel):
    """Request model for creating a new job."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Job name (required)")
    record_type_name: str = Field(..., description="Workflow name (required)", alias="recordTypeName")
    status_name: str = Field(..., description="Status name (required)", alias="statusName")
    source_name: str | None = Field(None, description="Lead source name", alias="sourceName")
    description: str | None = Field(None, description="Job description")

    # Address fields
    address_line1: str | None = Field(None, description="Address line 1", alias="addressLine1")
    address_line2: str | None = Field(None, description="Address line 2", alias="addressLine2")
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    zip: str | None = Field(None, description="ZIP code")
    geo: dict[str, float] | None = Field(None, description="Geographic coordinates (lat, lon)")

    # Primary contact
    primary: dict[str, str] | None = Field(None, description="Primary contact (id: jnid)")


class JobNimbusUpdateJobRequest(BaseModel):
    """Request model for updating a job."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Job name")
    record_type_name: str | None = Field(None, description="Workflow name", alias="recordTypeName")
    status_name: str | None = Field(None, description="Status name", alias="statusName")
    description: str | None = Field(None, description="Job description")

    # Address fields
    address_line1: str | None = Field(None, description="Address line 1", alias="addressLine1")
    address_line2: str | None = Field(None, description="Address line 2", alias="addressLine2")
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    zip: str | None = Field(None, description="ZIP code")


# Contact schemas


class JobNimbusContactResponse(BaseModel):
    """Response model for a JobNimbus contact."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    recid: int | None = Field(None, description="Record ID")
    jnid: str = Field(..., description="JobNimbus unique ID")
    customer: str = Field(..., description="Customer JNID")
    type: str = Field(..., description="Record type (should be 'contact')")
    created_by: str = Field(..., description="Creator JNID", alias="createdBy")
    created_by_name: str = Field(..., description="Creator name", alias="createdByName")
    date_created: int = Field(..., description="Unix timestamp of creation", alias="dateCreated")
    date_updated: int = Field(..., description="Unix timestamp of last update", alias="dateUpdated")
    location: LocationInfo | None = Field(None, description="Location information")
    owners: list[OwnerInfo] = Field(default_factory=list, description="List of owners")
    is_active: bool | None = Field(None, description="Whether the contact is active", alias="isActive")
    is_archived: bool | None = Field(None, description="Whether the contact is archived", alias="isArchived")
    is_sub: bool | None = Field(None, description="Whether the contact is a subcontractor", alias="isSub")

    # Contact-specific fields
    first_name: str | None = Field(None, description="First name", alias="firstName")
    last_name: str | None = Field(None, description="Last name", alias="lastName")
    display_name: str | None = Field(None, description="Display name", alias="displayName")
    company: str | None = Field(None, description="Company name")
    description: str | None = Field(None, description="Contact description")

    # Contact information
    email: str | None = Field(None, description="Email address")
    home_phone: str | None = Field(None, description="Home phone", alias="homePhone")
    mobile_phone: str | None = Field(None, description="Mobile phone", alias="mobilePhone")
    work_phone: str | None = Field(None, description="Work phone", alias="workPhone")
    fax_number: str | None = Field(None, description="Fax number", alias="faxNumber")
    website: str | None = Field(None, description="Website URL")

    # Address fields
    address_line1: str | None = Field(None, description="Address line 1", alias="addressLine1")
    address_line2: str | None = Field(None, description="Address line 2", alias="addressLine2")
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    country_name: str | None = Field(None, description="Country", alias="countryName")
    zip: str | None = Field(None, description="ZIP code")
    geo: GeoLocation | None = Field(None, description="Geographic coordinates")

    # Workflow fields
    record_type: int | None = Field(None, description="Record type ID", alias="recordType")
    record_type_name: str | None = Field(None, description="Workflow name", alias="recordTypeName")
    status: int | None = Field(None, description="Status ID")
    status_name: str | None = Field(None, description="Status name", alias="statusName")
    source: int | None = Field(None, description="Lead source ID")
    source_name: str | None = Field(None, description="Lead source name", alias="sourceName")

    # Sales rep
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(None, description="Sales rep name", alias="salesRepName")

    # Related entities
    related: list[RelatedEntity] | None = Field(None, description="Related entities")


class JobNimbusContactsListResponse(BaseModel):
    """Response model for list of contacts."""

    count: int = Field(..., description="Total count of contacts")
    results: list[JobNimbusContactResponse] = Field(..., description="List of contacts")


class JobNimbusCreateContactRequest(BaseModel):
    """Request model for creating a new contact."""

    model_config = ConfigDict(populate_by_name=True)

    # At least one of these is required
    first_name: str | None = Field(None, description="First name", alias="firstName")
    last_name: str | None = Field(None, description="Last name", alias="lastName")
    display_name: str | None = Field(None, description="Display name", alias="displayName")
    company: str | None = Field(None, description="Company name")

    record_type_name: str = Field(..., description="Workflow name (required)", alias="recordTypeName")
    status_name: str = Field(..., description="Status name (required)", alias="statusName")
    source_name: str | None = Field(None, description="Lead source name", alias="sourceName")

    # Contact information
    email: str | None = Field(None, description="Email address")
    home_phone: str | None = Field(None, description="Home phone", alias="homePhone")
    mobile_phone: str | None = Field(None, description="Mobile phone", alias="mobilePhone")
    work_phone: str | None = Field(None, description="Work phone", alias="workPhone")

    # Address fields
    address_line1: str | None = Field(None, description="Address line 1", alias="addressLine1")
    address_line2: str | None = Field(None, description="Address line 2", alias="addressLine2")
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    zip: str | None = Field(None, description="ZIP code")
    geo: dict[str, float] | None = Field(None, description="Geographic coordinates (lat, lon)")


class JobNimbusUpdateContactRequest(BaseModel):
    """Request model for updating a contact."""

    model_config = ConfigDict(populate_by_name=True)

    first_name: str | None = Field(None, description="First name", alias="firstName")
    last_name: str | None = Field(None, description="Last name", alias="lastName")
    company: str | None = Field(None, description="Company name")
    record_type_name: str | None = Field(None, description="Workflow name", alias="recordTypeName")
    status_name: str | None = Field(None, description="Status name", alias="statusName")

    # Contact information
    email: str | None = Field(None, description="Email address")
    home_phone: str | None = Field(None, description="Home phone", alias="homePhone")
    mobile_phone: str | None = Field(None, description="Mobile phone", alias="mobilePhone")
    work_phone: str | None = Field(None, description="Work phone", alias="workPhone")

    # Address fields
    address_line1: str | None = Field(None, description="Address line 1", alias="addressLine1")
    address_line2: str | None = Field(None, description="Address line 2", alias="addressLine2")
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    zip: str | None = Field(None, description="ZIP code")


# Activity (Note) schemas


class JobNimbusActivityResponse(BaseModel):
    """Response model for a JobNimbus activity (note)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Core fields
    jnid: str = Field(..., description="JobNimbus unique ID")
    type: str = Field(..., description="Record type (should be 'activity')")
    customer: str = Field(..., description="Customer JNID")
    created_by: str = Field(..., description="Creator JNID", alias="createdBy")
    created_by_name: str = Field(..., description="Creator name", alias="createdByName")
    date_created: int = Field(..., description="Unix timestamp of creation", alias="dateCreated")
    date_updated: int = Field(..., description="Unix timestamp of last update", alias="dateUpdated")
    is_active: bool = Field(..., description="Whether the activity is active", alias="isActive")
    is_archived: bool = Field(..., description="Whether the activity is archived", alias="isArchived")
    is_editable: bool = Field(..., description="Whether the activity is editable", alias="isEditable")
    is_private: bool | None = Field(None, description="Whether the activity is private", alias="isPrivate")
    is_status_change: bool | None = Field(None, description="Whether this is a status change", alias="isStatusChange")

    # Activity-specific fields
    note: str = Field(..., description="Note text")
    record_type: int | None = Field(None, description="Record type ID", alias="recordType")
    record_type_name: str = Field(..., description="Activity type name", alias="recordTypeName")
    source: str | None = Field(None, description="Source of the activity")
    
    # Optional metadata
    email_status: str | None = Field(None, description="Email status if applicable", alias="emailStatus")
    external_id: str | None = Field(None, description="External ID if synced", alias="externalId")
    merged: str | None = Field(None, description="Merged entity ID if merged")
    stack: str | None = Field(None, description="Stack information")

    # Sales rep
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(None, description="Sales rep name", alias="salesRepName")

    # Related entities
    primary: RelatedEntity | None = Field(None, description="Primary related entity")
    related: list[RelatedEntity] | None = Field(None, description="Related entities")
    owners: list[OwnerInfo] | None = Field(None, description="List of owners")
    location: LocationInfo | None = Field(None, description="Location information")
    rules: list[dict] | None = Field(None, description="Rules associated with activity")


class JobNimbusActivitiesListResponse(BaseModel):
    """Response model for list of activities."""

    model_config = ConfigDict(populate_by_name=True)

    count: int = Field(..., description="Total count of activities")
    results: list[JobNimbusActivityResponse] = Field(..., description="List of activities", alias="activity")


class JobNimbusCreateActivityRequest(BaseModel):
    """Request model for creating a new activity (note)."""

    model_config = ConfigDict(populate_by_name=True)

    note: str = Field(..., description="Note text (required)")
    record_type_name: str = Field(..., description="Activity type name (required)", alias="recordTypeName")
    primary: dict[str, str] = Field(..., description="Primary related entity (id: jnid)")
    date_created: int | None = Field(None, description="Unix timestamp of creation", alias="dateCreated")


# Query/Filter schemas


class JobNimbusQueryFilter(BaseModel):
    """Model for JobNimbus ElasticSearch-style query filters."""

    must: list[dict[str, Any]] | None = Field(None, description="Must match conditions")
    should: list[dict[str, Any]] | None = Field(None, description="Should match conditions")
    must_not: list[dict[str, Any]] | None = Field(None, description="Must not match conditions", alias="mustNot")
