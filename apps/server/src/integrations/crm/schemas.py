"""
CRM-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to CRM operations,
project management, and status tracking across different CRM providers.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.integrations.crm.constants import CRMProvider, EstimateReviewStatus, Status

# ============================================================================
# UNIVERSAL SCHEMAS - Work across all CRM providers
# ============================================================================


class Job(BaseModel):
    """Universal job model that works across all CRM providers."""

    id: str = Field(..., description="Unique job identifier (provider-specific format)")
    name: str | None = Field(None, description="Job name/title")
    number: str | None = Field(None, description="Job number")
    status: str = Field(..., description="Current job status (provider-specific)")
    status_id: int | str | None = Field(None, description="Status identifier")
    workflow_type: str | None = Field(None, description="Workflow/record type name")
    description: str | None = Field(None, description="Job description")

    # Customer/contact information
    customer_id: str | None = Field(None, description="Associated customer/contact ID")
    customer_name: str | None = Field(None, description="Customer name")

    # Address
    address_line1: str | None = Field(None, description="Address line 1")
    address_line2: str | None = Field(None, description="Address line 2")
    city: str | None = Field(None, description="City")
    state: str | None = Field(None, description="State/province")
    postal_code: str | None = Field(None, description="ZIP/postal code")
    country: str | None = Field(None, description="Country")

    # Dates (ISO format strings for universality)
    created_at: str | None = Field(None, description="Creation timestamp (ISO format)")
    updated_at: str | None = Field(
        None, description="Last update timestamp (ISO format)"
    )
    completed_at: str | None = Field(
        None, description="Completion timestamp (ISO format)"
    )

    # Sales/team
    sales_rep_id: str | None = Field(None, description="Sales representative ID")
    sales_rep_name: str | None = Field(None, description="Sales representative name")

    # Provider-specific data
    provider: CRMProvider = Field(..., description="CRM provider name")
    provider_data: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific data"
    )

    # Notes/activities
    notes: list["Note"] | None = Field(
        None, description="List of notes/activities for this job"
    )


class JobList(BaseModel):
    """Universal job list response with pagination."""

    jobs: list[Job] = Field(..., description="List of jobs")
    total_count: int = Field(..., description="Total number of jobs")
    provider: CRMProvider = Field(..., description="CRM provider name")
    page: int | None = Field(None, description="Current page number (if paginated)")
    page_size: int | None = Field(None, description="Page size (if paginated)")
    has_more: bool | None = Field(None, description="Whether more results exist")


class Contact(BaseModel):
    """Universal contact/customer model that works across all CRM providers."""

    id: str = Field(
        ..., description="Unique contact identifier (provider-specific format)"
    )
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    company: str | None = Field(None, description="Company name")
    display_name: str | None = Field(None, description="Display name")

    # Contact information
    email: str | None = Field(None, description="Email address")
    phone: str | None = Field(None, description="Primary phone number")
    mobile_phone: str | None = Field(None, description="Mobile phone")
    work_phone: str | None = Field(None, description="Work phone")

    # Address
    address_line1: str | None = Field(None, description="Address line 1")
    address_line2: str | None = Field(None, description="Address line 2")
    city: str | None = Field(None, description="City")
    state: str | None = Field(None, description="State/province")
    postal_code: str | None = Field(None, description="ZIP/postal code")
    country: str | None = Field(None, description="Country")

    # Classification
    status: str | None = Field(None, description="Contact status")
    workflow_type: str | None = Field(None, description="Workflow/record type name")

    # Dates
    created_at: str | None = Field(None, description="Creation timestamp (ISO format)")
    updated_at: str | None = Field(
        None, description="Last update timestamp (ISO format)"
    )

    # Provider-specific data
    provider: CRMProvider = Field(..., description="CRM provider name")
    provider_data: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific data"
    )


class ContactList(BaseModel):
    """Universal contact list response with pagination."""

    contacts: list[Contact] = Field(..., description="List of contacts")
    total_count: int = Field(..., description="Total number of contacts")
    provider: CRMProvider = Field(..., description="CRM provider name")
    page: int | None = Field(None, description="Current page number (if paginated)")
    page_size: int | None = Field(None, description="Page size (if paginated)")
    has_more: bool | None = Field(None, description="Whether more results exist")


class Project(BaseModel):
    """Universal project model that works across all CRM providers.

    In hierarchical CRMs (Service Titan), projects are top-level containers that
    may contain multiple jobs. In flat CRMs (JobNimbus), projects and jobs are
    the same entity.
    """

    id: str = Field(
        ..., description="Unique project identifier (provider-specific format)"
    )
    name: str | None = Field(None, description="Project name/title")
    number: str | None = Field(None, description="Project number")
    status: str = Field(..., description="Current project status (provider-specific)")
    status_id: int | str | None = Field(None, description="Status identifier")
    sub_status: str | None = Field(None, description="Project sub-status name")
    sub_status_id: int | str | None = Field(None, description="Sub-status identifier")
    workflow_type: str | None = Field(None, description="Workflow/record type name")
    description: str | None = Field(None, description="Project description")

    # Customer/contact information
    customer_id: str | None = Field(None, description="Associated customer/contact ID")
    customer_name: str | None = Field(None, description="Customer name")
    location_id: str | None = Field(None, description="Location identifier")

    # Address
    address_line1: str | None = Field(None, description="Address line 1")
    address_line2: str | None = Field(None, description="Address line 2")
    city: str | None = Field(None, description="City")
    state: str | None = Field(None, description="State/province")
    postal_code: str | None = Field(None, description="ZIP/postal code")
    country: str | None = Field(None, description="Country")

    # Dates (ISO format strings for universality)
    created_at: str | None = Field(None, description="Creation timestamp (ISO format)")
    updated_at: str | None = Field(
        None, description="Last update timestamp (ISO format)"
    )
    start_date: str | None = Field(None, description="Project start date (ISO format)")
    target_completion_date: str | None = Field(
        None, description="Target completion date (ISO format)"
    )
    actual_completion_date: str | None = Field(
        None, description="Actual completion date (ISO format)"
    )

    # Insurance/claim information
    claim_number: str | None = Field(None, description="Insurance claim number")
    date_of_loss: str | None = Field(None, description="Date of loss (ISO format)")
    insurance_company: str | None = Field(
        None, description="Insurance company/carrier name"
    )
    adjuster_name: str | None = Field(None, description="Insurance adjuster name")
    adjuster_phone: str | None = Field(
        None, description="Insurance adjuster phone number"
    )
    adjuster_email: str | None = Field(
        None, description="Insurance adjuster email address"
    )

    # Sales/team
    sales_rep_id: str | None = Field(None, description="Sales representative ID")
    sales_rep_name: str | None = Field(None, description="Sales representative name")

    # Provider-specific data
    provider: CRMProvider = Field(..., description="CRM provider name")
    provider_data: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific data"
    )

    # Notes/activities
    notes: list["Note"] | None = Field(
        None, description="List of notes/activities for this project"
    )


class ProjectList(BaseModel):
    """Universal project list response with pagination."""

    projects: list[Project] = Field(..., description="List of projects")
    total_count: int = Field(..., description="Total number of projects")
    provider: CRMProvider = Field(..., description="CRM provider name")
    page: int | None = Field(None, description="Current page number (if paginated)")
    page_size: int | None = Field(None, description="Page size (if paginated)")
    has_more: bool | None = Field(None, description="Whether more results exist")


class Note(BaseModel):
    """Universal note/activity model that works across all CRM providers."""

    id: str | None = Field(None, description="Note identifier")
    text: str = Field(..., description="Note text content")
    entity_id: str = Field(..., description="ID of the entity this note belongs to")
    entity_type: str = Field(
        ..., description="Type of entity (job, contact, project, etc.)"
    )
    created_by_id: str | None = Field(None, description="Creator identifier")
    created_by_name: str | None = Field(None, description="Creator name")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str | None = Field(
        None, description="Last update timestamp (ISO format)"
    )
    is_pinned: bool = Field(default=False, description="Whether the note is pinned")

    # Provider-specific data
    provider: CRMProvider = Field(..., description="CRM provider name")
    provider_data: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific data"
    )


class ProjectSummary(BaseModel):
    """AI-generated project summary with structured information."""

    summary: str = Field(
        ..., description="Brief one-sentence summary of the project status"
    )
    recent_actions: list[str] = Field(
        default_factory=list,
        description="List of recent actions taken on the project (2-3 bullet points)",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="List of recommended next steps (2-3 bullet points)",
    )


# ============================================================================
# LEGACY/PROVIDER-SPECIFIC SCHEMAS - To be deprecated/moved
# ============================================================================


class ProjectStatusResponse(BaseModel):
    """Response model for project status information.

    DEPRECATED: Legacy schema. Use universal Project schema instead.
    """

    project_id: str = Field(..., description="Unique project identifier")
    status: Status = Field(..., description="Current project status")
    provider: CRMProvider = Field(..., description="CRM provider")
    updated_at: datetime | None = Field(
        None, description="Last status update timestamp"
    )
    provider_data: dict[str, Any] | None = Field(
        None, description="Provider-specific data"
    )


class ProjectStatusListResponse(BaseModel):
    """Response model for multiple project statuses."""

    projects: list[ProjectStatusResponse] = Field(
        ..., description="List of project statuses"
    )
    total_count: int = Field(..., description="Total number of projects")
    provider: CRMProvider = Field(..., description="CRM provider")


class JobRequest(BaseModel):
    """Request model for getting a specific job."""

    job_id: int = Field(..., description="ID of the job to retrieve")
    tenant: int = Field(..., description="Tenant ID")


class EstimateByIdRequest(BaseModel):
    """Request model for getting a specific estimate by ID."""

    tenant: int = Field(..., description="Tenant ID")
    estimate_id: int = Field(..., description="ID of the estimate to retrieve")


class EstimatesRequest(BaseModel):
    """Request model for getting estimates with filters."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    job_id: int | None = Field(
        None, description="Job ID to filter estimates", alias="jobId"
    )
    project_id: int | None = Field(
        None, description="Project ID to filter estimates", alias="projectId"
    )
    page: int | None = Field(None, description="Page number for pagination")
    page_size: int | None = Field(
        None, description="Page size for pagination (max 50)", le=50, alias="pageSize"
    )
    ids: str | None = Field(None, description="Comma separated string of estimate IDs")


class EstimateStatus(BaseModel):
    """Estimate status model with value and name."""

    value: int = Field(..., description="Status value")
    name: str = Field(..., description="Status name")


class JobResponse(BaseModel):
    """Response model for Service Titan job information."""

    id: int = Field(..., description="ID of the job")
    job_number: str = Field(..., description="Job number", alias="jobNumber")
    project_id: int | None = Field(
        None, description="ID of the job's project", alias="projectId"
    )
    customer_id: int = Field(
        ..., description="ID of the job's customer", alias="customerId"
    )
    location_id: int = Field(
        ..., description="ID of the job's location", alias="locationId"
    )
    job_status: str = Field(..., description="Status of the job", alias="jobStatus")
    completed_on: datetime | None = Field(
        None,
        description="Date/time (in UTC) when the job was completed",
        alias="completedOn",
    )
    business_unit_id: int = Field(
        ..., description="ID of the job's business unit", alias="businessUnitId"
    )
    job_type_id: int = Field(..., description="ID of job type", alias="jobTypeId")
    priority: str = Field(..., description="Priority of the job")
    campaign_id: int = Field(
        ..., description="ID of the job's campaign", alias="campaignId"
    )
    appointment_count: int = Field(
        ..., description="Number of appointments on the job", alias="appointmentCount"
    )
    first_appointment_id: int = Field(
        ...,
        description="ID of the first appointment on the job",
        alias="firstAppointmentId",
    )
    last_appointment_id: int = Field(
        ...,
        description="ID of the last appointment on the job",
        alias="lastAppointmentId",
    )
    recall_for_id: int | None = Field(
        None,
        description="ID of the job for which this job is a recall",
        alias="recallForId",
    )
    warranty_id: int | None = Field(
        None,
        description="ID of the job for which this job is a warranty",
        alias="warrantyId",
    )
    no_charge: bool = Field(
        ..., description="Whether the job is a no-charge job", alias="noCharge"
    )
    notifications_enabled: bool = Field(
        ...,
        description="Whether notifications will be sent to customers",
        alias="notificationsEnabled",
    )
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the job was created",
        alias="createdOn",
    )
    created_by_id: int = Field(
        ..., description="ID of the user who created the job", alias="createdById"
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when job was last modified",
        alias="modifiedOn",
    )
    tag_type_ids: list[int] = Field(
        ..., description="Tags on the job", alias="tagTypeIds"
    )
    customer_po: str | None = Field(None, description="Customer PO", alias="customerPo")
    invoice_id: int | None = Field(
        None,
        description="ID of the invoice associated with this job",
        alias="invoiceId",
    )
    total: float | None = Field(None, description="Total amount of the job")
    summary: str | None = Field(None, description="Job summary")


class EstimateResponse(BaseModel):
    """Response model for Service Titan estimate information."""

    id: int = Field(..., description="ID of the estimate")
    job_id: int | None = Field(
        None, description="ID of the associated job", alias="jobId"
    )
    project_id: int | None = Field(
        None, description="ID of the associated project", alias="projectId"
    )
    location_id: int | None = Field(
        None, description="ID of the location", alias="locationId"
    )
    customer_id: int | None = Field(
        None, description="ID of the customer", alias="customerId"
    )
    name: str | None = Field(None, description="Name of the estimate")
    job_number: str | None = Field(None, description="Job number", alias="jobNumber")
    status: EstimateStatus | None = Field(None, description="Status of the estimate")
    review_status: EstimateReviewStatus = Field(
        ..., description="Review status of the estimate", alias="reviewStatus"
    )
    summary: str | None = Field(None, description="Summary of the estimate")
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the estimate was created",
        alias="createdOn",
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when estimate was last modified",
        alias="modifiedOn",
    )
    sold_on: datetime | None = Field(
        None,
        description="Date/time (in UTC) when the estimate was sold",
        alias="soldOn",
    )
    sold_by: int | None = Field(
        None, description="ID of who sold the estimate", alias="soldBy"
    )
    active: bool = Field(..., description="Whether the estimate is active")
    subtotal: float = Field(..., description="Subtotal amount")
    tax: float = Field(..., description="Tax amount")
    business_unit_id: int | None = Field(
        None, description="ID of the business unit", alias="businessUnitId"
    )
    business_unit_name: str | None = Field(
        None, description="Name of the business unit", alias="businessUnitName"
    )
    is_recommended: bool = Field(
        ..., description="Whether this estimate is recommended", alias="isRecommended"
    )
    budget_code_id: int | None = Field(
        None, description="ID of the budget code", alias="budgetCodeId"
    )
    is_change_order: bool = Field(
        ...,
        description="Whether this estimate is a change order",
        alias="isChangeOrder",
    )


class SkuModel(BaseModel):
    """SKU model for estimate items."""

    id: int = Field(..., description="SKU ID")
    name: str = Field(..., description="SKU name")
    display_name: str = Field(..., description="Display name", alias="displayName")
    type: str = Field(..., description="SKU type")
    sold_hours: float = Field(..., description="Sold hours", alias="soldHours")
    general_ledger_account_id: int = Field(
        ..., description="General ledger account ID", alias="generalLedgerAccountId"
    )
    general_ledger_account_name: str = Field(
        ..., description="General ledger account name", alias="generalLedgerAccountName"
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when SKU was last modified",
        alias="modifiedOn",
    )


class EstimateItemResponse(BaseModel):
    """Response model for estimate item information."""

    id: int = Field(..., description="ID of the estimate item")
    sku: SkuModel = Field(..., description="SKU details")
    sku_account: str = Field(..., description="SKU account", alias="skuAccount")
    description: str = Field(..., description="Item description")
    membership_type_id: int | None = Field(
        None, description="Membership type ID", alias="membershipTypeId"
    )
    qty: float = Field(..., description="Quantity")
    unit_rate: float = Field(..., description="Unit rate", alias="unitRate")
    total: float = Field(..., description="Total amount")
    unit_cost: float = Field(..., description="Unit cost", alias="unitCost")
    total_cost: float = Field(..., description="Total cost", alias="totalCost")
    item_group_name: str | None = Field(
        None, description="Item group name", alias="itemGroupName"
    )
    item_group_root_id: int | None = Field(
        None, description="Item group root ID", alias="itemGroupRootId"
    )
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the item was created",
        alias="createdOn",
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the item was last modified",
        alias="modifiedOn",
    )
    chargeable: bool | None = Field(None, description="Whether the item is chargeable")
    invoice_item_id: int | None = Field(
        None,
        description="The invoice item which was created from this estimate item",
        alias="invoiceItemId",
    )
    budget_code_id: int | None = Field(
        None, description="Budget code ID", alias="budgetCodeId"
    )


class EstimatesListResponse(BaseModel):
    """Response model for estimates list."""

    estimates: list[EstimateResponse] = Field(..., description="List of estimates")
    total_count: int | None = Field(
        None, description="Total count of estimates (if requested)"
    )
    page: int | None = Field(None, description="Current page number")
    page_size: int | None = Field(None, description="Page size")
    has_more: bool | None = Field(None, description="Whether there are more estimates")


class EstimateItemsRequest(BaseModel):
    """Request model for getting estimate items."""

    tenant: int = Field(..., description="Tenant ID")
    estimate_id: int | None = Field(
        None, description="Estimate ID to filter items", alias="estimateId"
    )
    ids: str | None = Field(
        None, description="Comma separated string of item IDs (max 50)"
    )
    active: str | None = Field(
        None, description="Filter by active status (True, False, Any)"
    )
    page: int | None = Field(None, description="Page number for pagination")
    page_size: int | None = Field(
        None,
        description="Page size for pagination (default 50)",
        le=50,
        alias="pageSize",
    )


class EstimateItemsResponse(BaseModel):
    """Response model for estimate items list."""

    items: list[EstimateItemResponse] = Field(..., description="List of estimate items")
    total_count: int | None = Field(
        None, description="Total count of items (if requested)"
    )
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Whether there are more items")


class CRMErrorResponse(BaseModel):
    """Error response from CRM operations."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Provider-specific error code")
    provider: CRMProvider | None = Field(None, description="CRM provider")


class AddJobNoteRequest(BaseModel):
    """Request model for adding a note to a job."""

    tenant: int = Field(..., description="Tenant ID")
    job_id: int = Field(..., description="ID of the job to add note to", alias="jobId")
    text: str = Field(..., description="Text content of the note")
    pin_to_top: bool | None = Field(
        None, description="Whether to pin the note to the top", alias="pinToTop"
    )


class JobNoteResponse(BaseModel):
    """Response model for job note."""

    model_config = {"populate_by_name": True}

    text: str = Field(..., description="Text content of the note")
    is_pinned: bool = Field(
        ..., description="Whether the note is pinned to the top", alias="isPinned"
    )
    created_by_id: int = Field(
        ..., description="ID of user who created this note", alias="createdById"
    )
    created_on: datetime = Field(
        ..., description="Date/time (in UTC) the note was created", alias="createdOn"
    )
    modified_on: datetime = Field(
        ..., description="Date/time (in UTC) the note was modified", alias="modifiedOn"
    )


class AddProjectNoteRequest(BaseModel):
    """Request model for adding a note to a project."""

    tenant: int = Field(..., description="Tenant ID")
    project_id: int = Field(
        ..., description="ID of the project to add note to", alias="projectId"
    )
    text: str = Field(..., description="Text content of the note")
    pin_to_top: bool | None = Field(
        None, description="Whether to pin the note to the top", alias="pinToTop"
    )


class ProjectNoteResponse(BaseModel):
    """Response model for project note."""

    text: str = Field(..., description="Text content of the note")
    is_pinned: bool = Field(
        ..., description="Whether the note is pinned to the top", alias="isPinned"
    )
    created_by_id: int = Field(
        ..., description="ID of user who created this note", alias="createdById"
    )
    created_on: datetime = Field(
        ..., description="Date/time (in UTC) the note was created", alias="createdOn"
    )
    modified_on: datetime = Field(
        ..., description="Date/time (in UTC) the note was modified", alias="modifiedOn"
    )


class JobHoldReasonResponse(BaseModel):
    """Response model for job hold reason."""

    id: int = Field(..., description="Job Hold Reason ID")
    name: str = Field(..., description="Job Hold Reason Name")
    active: bool = Field(..., description="Job Hold Reason Active Status")
    created_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when the reason was created",
        alias="createdOn",
    )
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when reason was last modified",
        alias="modifiedOn",
    )


class JobHoldReasonsListResponse(BaseModel):
    """Response model for paginated list of job hold reasons."""

    page: int = Field(..., description="From which page this output has started")
    page_size: int = Field(
        ..., description="Page size for this query", alias="pageSize"
    )
    has_more: bool = Field(
        ..., description="True if there are more records", alias="hasMore"
    )
    total_count: int | None = Field(
        None, description="Total count of records for this query", alias="totalCount"
    )
    data: list[JobHoldReasonResponse] = Field(
        ..., description="The collection of result items"
    )


class HoldJobRequest(BaseModel):
    """Request model for putting a job on hold."""

    tenant: int = Field(..., description="Tenant ID")
    job_id: int = Field(..., description="ID of the job to put on hold", alias="jobId")
    reason_id: int = Field(..., description="ID of job hold reason", alias="reasonId")
    memo: str = Field(..., description="Memo of job hold reason")


class ProjectSubStatusResponse(BaseModel):
    """Response model for project sub status."""

    id: int = Field(..., description="ID of the project sub status")
    name: str = Field(..., description="Name of the project sub status")
    status_id: int = Field(..., description="Id of the parent status", alias="statusId")
    order: int = Field(..., description="Order of the project status")
    modified_on: datetime = Field(
        ...,
        description="Date/time (in UTC) when project sub status was last modified",
        alias="modifiedOn",
    )
    active: bool = Field(..., description="When true, project sub status is active")


class ProjectSubStatusListResponse(BaseModel):
    """Response model for paginated list of project sub statuses."""

    page: int = Field(..., description="From which page this output has started")
    page_size: int = Field(
        ..., description="Page size for this query", alias="pageSize"
    )
    has_more: bool = Field(
        ..., description="True if there are more records", alias="hasMore"
    )
    total_count: int | None = Field(
        None, description="Total count of records for this query", alias="totalCount"
    )
    data: list[ProjectSubStatusResponse] = Field(
        ..., description="The collection of result items"
    )


class ExternalDataItem(BaseModel):
    """External data key-value pair."""

    key: str = Field(..., description="External data key")
    value: str | None = Field(None, description="External data value")


class ProjectByIdRequest(BaseModel):
    """Request model for getting a project by ID."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    project_id: int = Field(
        ..., description="ID of the project to retrieve", alias="projectId"
    )


class ProjectResponse(BaseModel):
    """Response model for Service Titan project information."""

    model_config = {"populate_by_name": True}

    id: int = Field(..., description="ID of the project")
    number: str | None = Field(None, description="Project number")
    name: str | None = Field(None, description="Project name")
    status: str | None = Field(None, description="Project status name")
    status_id: int | None = Field(
        None, description="Project status ID", alias="statusId"
    )
    sub_status: str | None = Field(
        None, description="Project sub status name", alias="subStatus"
    )
    sub_status_id: int | None = Field(
        None, description="Project sub status ID", alias="subStatusId"
    )
    summary: str | None = Field(None, description="Project summary")
    customer_id: int | None = Field(None, description="Customer ID", alias="customerId")
    location_id: int | None = Field(None, description="Location ID", alias="locationId")
    business_unit_id: int | None = Field(
        None, description="Business unit ID", alias="businessUnitId"
    )
    project_manager_id: int | None = Field(
        None, description="Project manager ID", alias="projectManagerId"
    )
    start_date: datetime | None = Field(
        None, description="Project start date", alias="startDate"
    )
    target_completion_date: datetime | None = Field(
        None, description="Target completion date", alias="targetCompletionDate"
    )
    actual_completion_date: datetime | None = Field(
        None, description="Actual completion date", alias="actualCompletionDate"
    )
    created_on: datetime | None = Field(
        None, description="Date/time (in UTC) when created", alias="createdOn"
    )
    created_by_id: int | None = Field(
        None, description="ID of user who created the project", alias="createdById"
    )
    modified_on: datetime | None = Field(
        None, description="Date/time (in UTC) when last modified", alias="modifiedOn"
    )
    external_data: list[dict[str, Any]] | None = Field(
        None, description="External data", alias="externalData"
    )


class FormSubmissionOwnerFilter(BaseModel):
    """Owner filter for form submissions request."""

    type: str = Field(..., description="Owner type (e.g., 'Job', 'Project')")
    id: int = Field(..., description="Owner ID")


class FormSubmissionsRequest(BaseModel):
    """Request model for getting form submissions."""

    model_config = {"populate_by_name": True}

    tenant: int = Field(..., description="Tenant ID")
    form_id: int | None = Field(
        None, description="Form ID to filter by", alias="formId"
    )
    page: int = Field(default=1, description="Page number for pagination")
    page_size: int = Field(
        default=50, description="Page size for pagination", alias="pageSize"
    )
    status: str | None = Field(
        None, description="Status filter (Started, Completed, Any)"
    )
    owners: list[FormSubmissionOwnerFilter] | None = Field(
        None, description="List of owner filters"
    )


class ProjectSubStatusesRequest(BaseModel):
    """Request model for getting project sub statuses."""

    model_config = {"populate_by_name": True}

    tenant: int = Field(..., description="Tenant ID")
    name: str | None = Field(None, description="Filter by sub status name")
    status_id: int | None = Field(
        None, description="Filter by parent status ID", alias="statusId"
    )
    active: str | None = Field(
        default="True", description="Active status filter (True, False, Any)"
    )
    page: int | None = Field(None, description="Page number for pagination")
    page_size: int | None = Field(
        None, description="Page size for pagination", alias="pageSize"
    )


class UpdateProjectRequest(BaseModel):
    """Request model for updating a project."""

    model_config = {"populate_by_name": True}

    tenant: int = Field(..., description="Tenant ID")
    project_id: int = Field(
        ..., description="ID of the project to update", alias="projectId"
    )
    status_id: int | None = Field(
        None, description="Project status ID", alias="statusId"
    )
    sub_status_id: int | None = Field(
        None, description="Project sub status ID", alias="subStatusId"
    )
    name: str | None = Field(None, description="Project name")
    summary: str | None = Field(None, description="Project summary (HTML)")
    external_data: list[ExternalDataItem] | None = Field(
        None, description="External data to attach to project", alias="externalData"
    )


# Pricebook models


class MaterialResponse(BaseModel):
    """Response model for a single material from the pricebook."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Material ID")
    code: str = Field(..., description="Material code/SKU")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: str | None = Field(None, description="Material description")
    cost: float | None = Field(None, description="Material cost")
    price: float | None = Field(None, description="Material price")
    member_price: float | None = Field(
        None, description="Member price", alias="memberPrice"
    )
    add_on_price: float | None = Field(
        None, description="Add-on price", alias="addOnPrice"
    )
    add_on_member_price: float | None = Field(
        None, description="Add-on member price", alias="addOnMemberPrice"
    )
    active: bool = Field(..., description="Whether the material is active")
    primary_vendor: dict[str, Any] | None = Field(
        None, description="Primary vendor info", alias="primaryVendor"
    )
    other_vendors: list[dict[str, Any]] | None = Field(
        None, description="Other vendors", alias="otherVendors"
    )
    manufacturer: str | None = Field(None, description="Manufacturer name")
    manufacturer_number: str | None = Field(
        None, description="Manufacturer part number", alias="manufacturerNumber"
    )
    cost_type: str | None = Field(None, description="Cost type", alias="costType")
    item_url: str | None = Field(None, description="Item URL", alias="itemUrl")


class ServiceResponse(BaseModel):
    """Response model for a single service from the pricebook."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Service ID")
    code: str = Field(..., description="Service code/SKU")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: str | None = Field(None, description="Service description")
    price: float | None = Field(None, description="Service price")
    member_price: float | None = Field(
        None, description="Member price", alias="memberPrice"
    )
    add_on_price: float | None = Field(
        None, description="Add-on price", alias="addOnPrice"
    )
    add_on_member_price: float | None = Field(
        None, description="Add-on member price", alias="addOnMemberPrice"
    )
    active: bool = Field(..., description="Whether the service is active")
    warranty_id: int | None = Field(None, description="Warranty ID", alias="warrantyId")
    account: str | None = Field(None, description="Account name/code")
    categories: list[dict[str, Any]] | None = Field(
        None, description="Service categories"
    )
    taxable: bool | None = Field(None, description="Whether the service is taxable")
    hours: float | None = Field(None, description="Service hours")


class EquipmentResponse(BaseModel):
    """Response model for a single equipment from the pricebook."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Equipment ID")
    code: str = Field(..., description="Equipment code/SKU")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: str | None = Field(None, description="Equipment description")
    price: float | None = Field(None, description="Equipment price")
    member_price: float | None = Field(
        None, description="Member price", alias="memberPrice"
    )
    add_on_price: float | None = Field(
        None, description="Add-on price", alias="addOnPrice"
    )
    add_on_member_price: float | None = Field(
        None, description="Add-on member price", alias="addOnMemberPrice"
    )
    active: bool = Field(..., description="Whether the equipment is active")
    cost: float | None = Field(None, description="Equipment cost")
    manufacturer: str | None = Field(None, description="Manufacturer name")
    model_number: str | None = Field(
        None, description="Model number", alias="modelNumber"
    )
    primary_vendor: dict[str, Any] | None = Field(
        None, description="Primary vendor info", alias="primaryVendor"
    )
    other_vendors: list[dict[str, Any]] | None = Field(
        None, description="Other vendors", alias="otherVendors"
    )


class PricebookItemsRequest(BaseModel):
    """Request model for fetching pricebook items."""

    model_config = ConfigDict(populate_by_name=True)

    tenant: int = Field(..., description="Tenant ID")
    page: int = Field(default=1, description="Page number for pagination")
    page_size: int = Field(
        default=50,
        le=50,
        description="Page size for pagination (max 50)",
        alias="pageSize",
    )
    active: str = Field(
        default="True", description="Filter by active status (True, False, Any)"
    )


class MaterialsListResponse(BaseModel):
    """Response model for paginated list of materials."""

    model_config = ConfigDict(populate_by_name=True)

    data: list[MaterialResponse] = Field(..., description="List of materials")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size", alias="pageSize")
    total_count: int | None = Field(
        None, description="Total count of materials", alias="totalCount"
    )
    has_more: bool = Field(
        ..., description="Whether there are more pages", alias="hasMore"
    )


class ServicesListResponse(BaseModel):
    """Response model for paginated list of services."""

    model_config = ConfigDict(populate_by_name=True)

    data: list[ServiceResponse] = Field(..., description="List of services")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size", alias="pageSize")
    total_count: int | None = Field(
        None, description="Total count of services", alias="totalCount"
    )
    has_more: bool = Field(
        ..., description="Whether there are more pages", alias="hasMore"
    )


class EquipmentListResponse(BaseModel):
    """Response model for paginated list of equipment."""

    model_config = ConfigDict(populate_by_name=True)

    data: list[EquipmentResponse] = Field(..., description="List of equipment")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size", alias="pageSize")
    total_count: int | None = Field(
        None, description="Total count of equipment", alias="totalCount"
    )
    has_more: bool = Field(
        ..., description="Whether there are more pages", alias="hasMore"
    )


# ============================================================================
# PROVIDER-SPECIFIC DATA SCHEMAS
# ============================================================================


class ServiceTitanProviderData(BaseModel):
    """Service Titan specific provider data."""

    appointment_number: str = Field(..., description="Service Titan appointment number")
    job_id: int = Field(..., description="Associated job ID")
    customer_id: int = Field(..., description="Customer identifier")
    active: bool = Field(..., description="Whether appointment is active")
    is_confirmed: bool = Field(..., description="Whether appointment is confirmed")
    original_status: str = Field(
        ..., description="Original Service Titan status string"
    )

    # Optional fields that might be available
    start_time: datetime | None = Field(None, description="Appointment start time")
    end_time: datetime | None = Field(None, description="Appointment end time")
    special_instructions: str | None = Field(None, description="Special instructions")
    arrival_window_start: datetime | None = Field(
        None, description="Arrival window start"
    )
    arrival_window_end: datetime | None = Field(None, description="Arrival window end")

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for future extensibility
        use_enum_values=True,  # Use enum values for serialization
    )


class FormSubmissionOwner(BaseModel):
    """Form submission owner object."""

    type: str = Field(..., description="Owner type (e.g., 'Job')")
    id: int = Field(..., description="Owner ID")


class FormSubmissionRequest(BaseModel):
    """Request model for form submissions."""

    form_id: int = Field(..., description="Form ID to get submissions for")
    owners: list[FormSubmissionOwner] = Field(..., description="List of owner objects")


class FormSubmissionResponse(BaseModel):
    """Individual form submission response from Service Titan API."""

    id: int = Field(..., description="Form submission ID")
    form_id: int = Field(..., description="Form ID", alias="formId")
    form_name: str | None = Field(None, description="Form name", alias="formName")
    submitted_on: datetime = Field(
        ..., description="Submission timestamp", alias="submittedOn"
    )
    created_by_id: int = Field(
        ..., description="ID of user who created the submission", alias="createdById"
    )
    status: str = Field(..., description="Submission status")
    owners: list[FormSubmissionOwner] | None = Field(None, description="Form owners")
    units: list[dict[str, Any]] | None = Field(None, description="Form units/fields")

    model_config = ConfigDict(populate_by_name=True)


class FormSubmissionListResponse(BaseModel):
    """Paginated response for form submissions from Service Titan API."""

    page: int = Field(..., description="From which page this output has started")
    page_size: int = Field(
        ..., description="Page size for this query", alias="pageSize"
    )
    has_more: bool = Field(
        ..., description="True if there are more records", alias="hasMore"
    )
    total_count: int | None = Field(
        None, description="Total count of records", alias="totalCount"
    )
    data: list[FormSubmissionResponse] = Field(
        ..., description="The collection of form submissions"
    )

    model_config = ConfigDict(populate_by_name=True)


class CRMProviderDataFactory:
    """Factory for creating provider-specific data models."""

    @staticmethod
    def create_service_titan_data(raw_data: dict[str, Any]) -> ServiceTitanProviderData:
        """Create Service Titan provider data from raw API response."""
        try:
            # Parse datetime fields
            start_time = None
            if raw_data.get("start"):
                start_time = datetime.fromisoformat(
                    raw_data["start"].replace("Z", "+00:00")
                )

            end_time = None
            if raw_data.get("end"):
                end_time = datetime.fromisoformat(
                    raw_data["end"].replace("Z", "+00:00")
                )

            arrival_window_start = None
            if raw_data.get("arrivalWindowStart"):
                arrival_window_start = datetime.fromisoformat(
                    raw_data["arrivalWindowStart"].replace("Z", "+00:00")
                )

            arrival_window_end = None
            if raw_data.get("arrivalWindowEnd"):
                arrival_window_end = datetime.fromisoformat(
                    raw_data["arrivalWindowEnd"].replace("Z", "+00:00")
                )

            return ServiceTitanProviderData(
                appointment_number=raw_data.get("appointmentNumber", ""),
                job_id=raw_data.get("jobId", 0),
                customer_id=raw_data.get("customerId", 0),
                active=raw_data.get("active", False),
                is_confirmed=raw_data.get("isConfirmed", False),
                original_status=raw_data.get("status") or "unknown",
                start_time=start_time,
                end_time=end_time,
                special_instructions=raw_data.get("specialInstructions"),
                arrival_window_start=arrival_window_start,
                arrival_window_end=arrival_window_end,
            )
        except Exception:
            # Fallback to basic data if parsing fails
            return ServiceTitanProviderData(
                appointment_number=raw_data.get("appointmentNumber", ""),
                job_id=raw_data.get("jobId", 0),
                customer_id=raw_data.get("customerId", 0),
                active=raw_data.get("active", False),
                is_confirmed=raw_data.get("isConfirmed", False),
                original_status=raw_data.get("status") or "unknown",
            )
