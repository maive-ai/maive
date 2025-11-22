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
    parent_id: int | None = Field(
        None, description="Parent location ID", alias="parentId"
    )
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
    new_status: int | None = Field(
        None, description="New status ID if status change", alias="newStatus"
    )
    old_status: int | None = Field(
        None, description="Old status ID if status change", alias="oldStatus"
    )


# Job schemas


class JobNimbusJobResponse(BaseModel):
    """Response model for a JobNimbus job."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Core identifiers
    recid: int | None = Field(None, description="Record ID")
    jnid: str = Field(..., description="JobNimbus unique ID")
    customer: str = Field(..., description="Customer JNID")
    type: str = Field(..., description="Record type (should be 'job')")

    # Metadata
    merged: str | None = Field(None, description="Merged entity ID if merged")
    class_id: int | None = Field(None, description="Class ID", alias="classId")
    class_name: str | None = Field(None, description="Class name", alias="className")
    rules: list[dict] | None = Field(None, description="Rules associated with job")
    external_id: str | None = Field(
        None, description="External ID if synced", alias="externalId"
    )

    # Creator info
    created_by: str = Field(..., description="Creator JNID", alias="createdBy")
    created_by_name: str | None = Field(
        None, description="Creator name (None for automations)", alias="createdByName"
    )

    # Dates
    date_created: int = Field(
        ..., description="Unix timestamp of creation", alias="dateCreated"
    )
    date_updated: int = Field(
        ..., description="Unix timestamp of last update", alias="dateUpdated"
    )
    date_status_change: int | None = Field(
        None,
        description="Unix timestamp of last status change",
        alias="dateStatusChange",
    )
    date_start: int | None = Field(
        None, description="Start date timestamp", alias="dateStart"
    )
    date_end: int | None = Field(
        None, description="End date timestamp", alias="dateEnd"
    )
    all_day: bool | None = Field(
        None, description="Whether this is an all-day event", alias="allDay"
    )
    all_day_start_date: str | None = Field(
        None, description="All-day start date", alias="allDayStartDate"
    )
    all_day_end_date: str | None = Field(
        None, description="All-day end date", alias="allDayEndDate"
    )

    # Status flags
    is_active: bool = Field(
        ..., description="Whether the job is active", alias="isActive"
    )
    is_archived: bool | None = Field(
        None, description="Whether the job is archived", alias="isArchived"
    )
    is_lead: bool | None = Field(
        None, description="Whether this is a lead", alias="isLead"
    )
    is_closed: bool | None = Field(
        None, description="Whether the job is closed", alias="isClosed"
    )

    # Job-specific fields
    name: str = Field(..., description="Job name")
    number: str | None = Field(None, description="Job number")
    record_type: int = Field(..., description="Record type ID", alias="recordType")
    record_type_name: str = Field(
        ..., description="Workflow name", alias="recordTypeName"
    )
    status: int | None = Field(None, description="Status ID")
    status_name: str | None = Field(None, description="Status name", alias="statusName")
    description: str | None = Field(None, description="Job description")

    # Financial - Estimates
    approved_estimate_total: float | None = Field(
        None, description="Approved estimate total", alias="approvedEstimateTotal"
    )
    last_estimate: float | None = Field(
        None, description="Last estimate amount", alias="lastEstimate"
    )
    last_estimate_date_estimate: int | None = Field(
        None, description="Last estimate date", alias="lastEstimateDateEstimate"
    )
    last_estimate_date_created: int | None = Field(
        None, description="Last estimate created date", alias="lastEstimateDateCreated"
    )
    last_estimate_number: str | None = Field(
        None, description="Last estimate number", alias="lastEstimateNumber"
    )
    last_estimate_jnid: str | None = Field(
        None, description="Last estimate JNID", alias="lastEstimateJnid"
    )

    # Financial - Invoices
    approved_invoice_total: float | None = Field(
        None, description="Approved invoice total", alias="approvedInvoiceTotal"
    )
    approved_invoice_due: float | None = Field(
        None, description="Approved invoice due amount", alias="approvedInvoiceDue"
    )
    last_invoice: float | None = Field(
        None, description="Last invoice amount", alias="lastInvoice"
    )
    last_invoice_date_invoice: int | None = Field(
        None, description="Last invoice date", alias="lastInvoiceDateInvoice"
    )
    last_invoice_date_created: int | None = Field(
        None, description="Last invoice created date", alias="lastInvoiceDateCreated"
    )
    last_invoice_number: str | None = Field(
        None, description="Last invoice number", alias="lastInvoiceNumber"
    )
    last_invoice_jnid: str | None = Field(
        None, description="Last invoice JNID", alias="lastInvoiceJnid"
    )

    # Financial - Budget
    last_budget_gross_profit: float | None = Field(
        None, description="Last budget gross profit", alias="lastBudgetGrossProfit"
    )
    last_budget_gross_margin: float | None = Field(
        None, description="Last budget gross margin", alias="lastBudgetGrossMargin"
    )
    last_budget_revenue: float | None = Field(
        None, description="Last budget revenue", alias="lastBudgetRevenue"
    )

    # Parent/Primary contact financials
    parent_approved_invoice_total: float | None = Field(
        None,
        description="Parent approved invoice total",
        alias="parentApprovedInvoiceTotal",
    )
    parent_approved_invoice_due: float | None = Field(
        None,
        description="Parent approved invoice due",
        alias="parentApprovedInvoiceDue",
    )
    parent_last_invoice: float | None = Field(
        None, description="Parent last invoice", alias="parentLastInvoice"
    )
    parent_approved_estimate_total: float | None = Field(
        None,
        description="Parent approved estimate total",
        alias="parentApprovedEstimateTotal",
    )
    parent_last_estimate: float | None = Field(
        None, description="Parent last estimate", alias="parentLastEstimate"
    )

    # Parent/Primary contact info
    parent_fax_number: str | None = Field(
        None, description="Parent fax number", alias="parentFaxNumber"
    )
    parent_home_phone: str | None = Field(
        None, description="Parent home phone", alias="parentHomePhone"
    )
    parent_mobile_phone: str | None = Field(
        None, description="Parent mobile phone", alias="parentMobilePhone"
    )
    parent_work_phone: str | None = Field(
        None, description="Parent work phone", alias="parentWorkPhone"
    )

    # Sales and contact info
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(
        None, description="Sales rep name", alias="salesRepName"
    )
    source: int | None = Field(None, description="Lead source ID")
    source_name: str | None = Field(
        None, description="Lead source name", alias="sourceName"
    )

    # Address fields
    address_line1: str | None = Field(
        None, description="Address line 1", alias="addressLine1"
    )
    address_line2: str | None = Field(
        None, description="Address line 2", alias="addressLine2"
    )
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    country_name: str | None = Field(None, description="Country", alias="countryName")
    zip: str | None = Field(None, description="ZIP code")
    geo: GeoLocation | None = Field(None, description="Geographic coordinates")

    # Related entities and teams
    related: list[RelatedEntity] | None = Field(None, description="Related entities")
    primary: RelatedEntity | None = Field(None, description="Primary related entity")
    location: LocationInfo | None = Field(None, description="Location information")
    owners: list[OwnerInfo] = Field(default_factory=list, description="List of owners")
    subcontractors: list[dict] | None = Field(
        None, description="Subcontractors assigned"
    )

    # Counts and attachments
    attachment_count: int | None = Field(
        None, description="Number of attachments", alias="attachmentCount"
    )
    task_count: int | None = Field(
        None, description="Number of tasks", alias="taskCount"
    )
    tags: list[str] | None = Field(None, description="Tags associated with job")

    # Time tracking
    actual_time: float | None = Field(
        None, description="Actual time spent", alias="actualTime"
    )
    estimated_time: float | None = Field(
        None, description="Estimated time", alias="estimatedTime"
    )

    # Other metadata
    image_id: str | None = Field(None, description="Image ID", alias="imageId")
    open_edge_id: str | None = Field(
        None, description="OpenEdge ID", alias="openEdgeId"
    )
    fieldassists: list[dict] | None = Field(None, description="Field assists")

    # Integration fields
    sunlight_status_and_id: dict | None = Field(
        None, description="Sunlight status and ID", alias="sunlightStatusAndId"
    )
    sunlight_events: dict | None = Field(
        None, description="Sunlight events", alias="sunlightEvents"
    )

    # Stage dates
    stage_dates_overrides: dict | None = Field(
        None, description="Stage dates overrides", alias="stageDatesOverrides"
    )
    stage_dates_overrides_on: dict | None = Field(
        None,
        description="Stage dates overrides on flags",
        alias="stageDatesOverridesOn",
    )

    # Custom fields - Clean, typed properties that map to JobNimbus human-readable field names
    # Use these in your code for IDE autocomplete and type safety!

    solar: str | None = Field(
        None, description="Solar installation status", alias="Solar?"
    )
    gutters: str | None = Field(
        None, description="Gutter work needed", alias="Gutters?"
    )
    peril_type: str | None = Field(
        None, description="Type of peril/damage", alias="Peril Type:"
    )
    insurance_company: str | None = Field(
        None, description="Insurance company name", alias="Insurance Company:"
    )
    claim_number: str | None = Field(
        None, description="Insurance claim number", alias="Claim Number:"
    )
    decking_type: str | None = Field(
        None, description="Type of roof decking", alias="Decking Type:"
    )
    sales_rep_commission: str | None = Field(
        None, description="Sales rep commission details", alias="Sales Rep Commission:"
    )
    shingle_layers: str | None = Field(
        None, description="Number of shingle layers", alias="Shingle Layers:"
    )
    how_cooked: str | None = Field(
        None, description="Job complexity/condition rating", alias="How Cooked?"
    )
    filed_storm_date: int | None = Field(
        None, description="Storm date filed (unix timestamp)", alias="Filed Storm Date:"
    )
    roof_pitch: int | None = Field(
        None, description="Major roof pitch (X/12)", alias="Maj. Roof Pitch (X/12):"
    )
    acv_rps_policy: bool | None = Field(
        None, description="ACV/RPS policy flag", alias="ACV/RPS Policy:"
    )

    # Programmatic custom field names (legacy - prefer the named fields above)
    cf_string_2: str | None = Field(
        None, description="Custom string field 2 (maps to Solar?)"
    )
    cf_string_3: str | None = Field(
        None, description="Custom string field 3 (maps to Gutters?)"
    )
    cf_string_7: str | None = Field(
        None, description="Custom string field 7 (maps to Peril Type)"
    )
    cf_string_8: str | None = Field(
        None, description="Custom string field 8 (maps to Insurance Company)"
    )
    cf_string_9: str | None = Field(
        None, description="Custom string field 9 (maps to Claim Number)"
    )
    cf_string_13: str | None = Field(
        None, description="Custom string field 13 (maps to Decking Type)"
    )
    cf_string_19: str | None = Field(
        None, description="Custom string field 19 (maps to Sales Rep Commission)"
    )
    cf_string_26: str | None = Field(
        None, description="Custom string field 26 (maps to Shingle Layers)"
    )
    cf_string_27: str | None = Field(
        None, description="Custom string field 27 (maps to How Cooked?)"
    )
    cf_date_1: int | None = Field(
        None, description="Custom date field 1 (maps to Filed Storm Date)"
    )
    cf_long_2: int | None = Field(
        None, description="Custom long field 2 (maps to Maj. Roof Pitch)"
    )
    cf_boolean_1: bool | None = Field(
        None, description="Custom boolean field 1 (maps to ACV/RPS Policy)"
    )

    # Additional custom fields are captured via extra="allow"


class JobNimbusJobsListResponse(BaseModel):
    """Response model for list of jobs."""

    count: int = Field(..., description="Total count of jobs")
    results: list[JobNimbusJobResponse] = Field(..., description="List of jobs")


class JobNimbusCreateJobRequest(BaseModel):
    """Request model for creating a new job."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Job name (required)")
    record_type_name: str = Field(
        ..., description="Workflow name (required)", alias="recordTypeName"
    )
    status_name: str = Field(
        ..., description="Status name (required)", alias="statusName"
    )
    source_name: str | None = Field(
        None, description="Lead source name", alias="sourceName"
    )
    description: str | None = Field(None, description="Job description")

    # Address fields
    address_line1: str | None = Field(
        None, description="Address line 1", alias="addressLine1"
    )
    address_line2: str | None = Field(
        None, description="Address line 2", alias="addressLine2"
    )
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    zip: str | None = Field(None, description="ZIP code")
    geo: dict[str, float] | None = Field(
        None, description="Geographic coordinates (lat, lon)"
    )

    # Primary contact
    primary: dict[str, str] | None = Field(
        None, description="Primary contact (id: jnid)"
    )


class JobNimbusUpdateJobRequest(BaseModel):
    """Request model for updating a job."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Job name")
    record_type_name: str | None = Field(
        None, description="Workflow name", alias="recordTypeName"
    )
    status_name: str | None = Field(None, description="Status name", alias="statusName")
    description: str | None = Field(None, description="Job description")

    # Address fields
    address_line1: str | None = Field(
        None, description="Address line 1", alias="addressLine1"
    )
    address_line2: str | None = Field(
        None, description="Address line 2", alias="addressLine2"
    )
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
    created_by_name: str | None = Field(
        None, description="Creator name (None for automations)", alias="createdByName"
    )
    date_created: int = Field(
        ..., description="Unix timestamp of creation", alias="dateCreated"
    )
    date_updated: int = Field(
        ..., description="Unix timestamp of last update", alias="dateUpdated"
    )
    location: LocationInfo | None = Field(None, description="Location information")
    owners: list[OwnerInfo] = Field(default_factory=list, description="List of owners")
    is_active: bool | None = Field(
        None, description="Whether the contact is active", alias="isActive"
    )
    is_archived: bool | None = Field(
        None, description="Whether the contact is archived", alias="isArchived"
    )
    is_sub: bool | None = Field(
        None, description="Whether the contact is a subcontractor", alias="isSub"
    )

    # Contact-specific fields
    first_name: str | None = Field(None, description="First name", alias="firstName")
    last_name: str | None = Field(None, description="Last name", alias="lastName")
    display_name: str | None = Field(
        None, description="Display name", alias="displayName"
    )
    company: str | None = Field(None, description="Company name")
    description: str | None = Field(None, description="Contact description")

    # Contact information
    email: str | None = Field(None, description="Email address")
    home_phone: str | None = Field(None, description="Home phone", alias="homePhone")
    mobile_phone: str | None = Field(
        None, description="Mobile phone", alias="mobilePhone"
    )
    work_phone: str | None = Field(None, description="Work phone", alias="workPhone")
    fax_number: str | None = Field(None, description="Fax number", alias="faxNumber")
    website: str | None = Field(None, description="Website URL")

    # Address fields
    address_line1: str | None = Field(
        None, description="Address line 1", alias="addressLine1"
    )
    address_line2: str | None = Field(
        None, description="Address line 2", alias="addressLine2"
    )
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    country_name: str | None = Field(None, description="Country", alias="countryName")
    zip: str | None = Field(None, description="ZIP code")
    geo: GeoLocation | None = Field(None, description="Geographic coordinates")

    # Workflow fields
    record_type: int | None = Field(
        None, description="Record type ID", alias="recordType"
    )
    record_type_name: str | None = Field(
        None, description="Workflow name", alias="recordTypeName"
    )
    status: int | None = Field(None, description="Status ID")
    status_name: str | None = Field(None, description="Status name", alias="statusName")
    source: int | None = Field(None, description="Lead source ID")
    source_name: str | None = Field(
        None, description="Lead source name", alias="sourceName"
    )

    # Sales rep
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(
        None, description="Sales rep name", alias="salesRepName"
    )

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
    display_name: str | None = Field(
        None, description="Display name", alias="displayName"
    )
    company: str | None = Field(None, description="Company name")

    record_type_name: str = Field(
        ..., description="Workflow name (required)", alias="recordTypeName"
    )
    status_name: str = Field(
        ..., description="Status name (required)", alias="statusName"
    )
    source_name: str | None = Field(
        None, description="Lead source name", alias="sourceName"
    )

    # Contact information
    email: str | None = Field(None, description="Email address")
    home_phone: str | None = Field(None, description="Home phone", alias="homePhone")
    mobile_phone: str | None = Field(
        None, description="Mobile phone", alias="mobilePhone"
    )
    work_phone: str | None = Field(None, description="Work phone", alias="workPhone")

    # Address fields
    address_line1: str | None = Field(
        None, description="Address line 1", alias="addressLine1"
    )
    address_line2: str | None = Field(
        None, description="Address line 2", alias="addressLine2"
    )
    city: str | None = Field(None, description="City")
    state_text: str | None = Field(None, description="State", alias="stateText")
    zip: str | None = Field(None, description="ZIP code")
    geo: dict[str, float] | None = Field(
        None, description="Geographic coordinates (lat, lon)"
    )


class JobNimbusUpdateContactRequest(BaseModel):
    """Request model for updating a contact."""

    model_config = ConfigDict(populate_by_name=True)

    first_name: str | None = Field(None, description="First name", alias="firstName")
    last_name: str | None = Field(None, description="Last name", alias="lastName")
    company: str | None = Field(None, description="Company name")
    record_type_name: str | None = Field(
        None, description="Workflow name", alias="recordTypeName"
    )
    status_name: str | None = Field(None, description="Status name", alias="statusName")

    # Contact information
    email: str | None = Field(None, description="Email address")
    home_phone: str | None = Field(None, description="Home phone", alias="homePhone")
    mobile_phone: str | None = Field(
        None, description="Mobile phone", alias="mobilePhone"
    )
    work_phone: str | None = Field(None, description="Work phone", alias="workPhone")

    # Address fields
    address_line1: str | None = Field(
        None, description="Address line 1", alias="addressLine1"
    )
    address_line2: str | None = Field(
        None, description="Address line 2", alias="addressLine2"
    )
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
    created_by_name: str | None = Field(None, description="Creator name", alias="createdByName")
    date_created: int = Field(
        ..., description="Unix timestamp of creation", alias="dateCreated"
    )
    date_updated: int = Field(
        ..., description="Unix timestamp of last update", alias="dateUpdated"
    )
    is_active: bool = Field(
        ..., description="Whether the activity is active", alias="isActive"
    )
    is_archived: bool = Field(
        ..., description="Whether the activity is archived", alias="isArchived"
    )
    is_editable: bool = Field(
        ..., description="Whether the activity is editable", alias="isEditable"
    )
    is_private: bool | None = Field(
        None, description="Whether the activity is private", alias="isPrivate"
    )
    is_status_change: bool | None = Field(
        None, description="Whether this is a status change", alias="isStatusChange"
    )

    # Activity-specific fields
    note: str = Field(..., description="Note text")
    record_type: int | None = Field(
        None, description="Record type ID", alias="recordType"
    )
    record_type_name: str | None = Field(
        None, description="Activity type name", alias="recordTypeName"
    )
    source: str | None = Field(None, description="Source of the activity")

    # Optional metadata
    email_status: str | None = Field(
        None, description="Email status if applicable", alias="emailStatus"
    )
    external_id: str | None = Field(
        None, description="External ID if synced", alias="externalId"
    )
    merged: str | None = Field(None, description="Merged entity ID if merged")
    stack: str | None = Field(None, description="Stack information")

    # Sales rep
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(
        None, description="Sales rep name", alias="salesRepName"
    )

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
    results: list[JobNimbusActivityResponse] = Field(
        ..., description="List of activities", alias="activity"
    )


class JobNimbusCreateActivityRequest(BaseModel):
    """Request model for creating a new activity (note)."""

    model_config = ConfigDict(populate_by_name=True)

    note: str = Field(..., description="Note text (required)")
    record_type_name: str = Field(
        ..., description="Activity type name (required)", alias="recordTypeName"
    )
    primary: dict[str, str] = Field(
        ..., description="Primary related entity (id: jnid)"
    )
    date_created: int | None = Field(
        None, description="Unix timestamp of creation", alias="dateCreated"
    )


# File/Attachment schemas


class JobNimbusFileResponse(BaseModel):
    """Response model for a single file/attachment."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Core fields
    jnid: str = Field(..., description="JobNimbus unique ID")
    customer: str = Field(..., description="Customer ID")
    type: str = Field(..., description="Record type (e.g., 'attachment')")

    # File metadata
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type", alias="contentType")
    size: int = Field(..., description="File size in bytes")

    # Timestamps
    date_created: int = Field(
        ..., description="Unix timestamp of creation", alias="dateCreated"
    )
    date_updated: int = Field(
        ..., description="Unix timestamp of last update", alias="dateUpdated"
    )

    # Creator info
    created_by: str = Field(..., description="Creator JNID", alias="createdBy")
    created_by_name: str | None = Field(
        None, description="Creator name (None for automations)", alias="createdByName"
    )

    # Status flags
    is_active: bool = Field(
        True, description="Whether the file is active", alias="isActive"
    )
    is_archived: bool = Field(
        False, description="Whether the file is archived", alias="isArchived"
    )
    is_private: bool = Field(
        False, description="Whether the file is private", alias="isPrivate"
    )

    # Classification
    record_type: int = Field(..., description="Record type ID", alias="recordType")
    record_type_name: str = Field(
        ..., description="File type name", alias="recordTypeName"
    )

    # Optional fields
    description: str | None = Field(None, description="File description/caption")

    # Relationships
    primary: RelatedEntity | None = Field(None, description="Primary related entity")
    related: list[RelatedEntity] | None = Field(
        None, description="Related entities (jobs, contacts)"
    )
    owners: list[OwnerInfo] | None = Field(None, description="List of owners")

    # Sales rep
    sales_rep: str | None = Field(None, description="Sales rep JNID", alias="salesRep")
    sales_rep_name: str | None = Field(
        None, description="Sales rep name", alias="salesRepName"
    )


class JobNimbusFilesListResponse(BaseModel):
    """Response model for list of files."""

    model_config = ConfigDict(populate_by_name=True)

    count: int = Field(..., description="Total count of files")
    results: list[JobNimbusFileResponse] = Field(
        ..., description="List of files", alias="files"
    )


class FileMetadata(BaseModel):
    """Simplified file metadata for API responses."""

    id: str = Field(..., description="File JNID")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    record_type_name: str = Field(..., description="File type name")
    description: str | None = Field(None, description="File description/caption")
    date_created: int = Field(..., description="Unix timestamp of creation")
    created_by_name: str = Field(..., description="Creator name")
    is_private: bool = Field(False, description="Whether the file is private")


# Query/Filter schemas


class JobNimbusQueryFilter(BaseModel):
    """Model for JobNimbus ElasticSearch-style query filters."""

    must: list[dict[str, Any]] | None = Field(None, description="Must match conditions")
    should: list[dict[str, Any]] | None = Field(
        None, description="Should match conditions"
    )
    must_not: list[dict[str, Any]] | None = Field(
        None, description="Must not match conditions", alias="mustNot"
    )
